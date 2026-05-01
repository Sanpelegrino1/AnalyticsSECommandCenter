# Upload Manifest Dataset to Data Cloud

## Purpose

Use this playbook when a dataset folder contains multiple CSV files plus a manifest that defines the table list, and you want to upload the full set to Salesforce Data Cloud in one ordered run.

## Inputs

- Manifest path
- Optional shared Data Cloud source name override for the dataset
- Optional target key prefix override if the manifest-derived default is not the live naming scheme
- Local Data Cloud auth secrets in `.env.local` or user environment variables

## Prerequisites

- The Data Cloud Ingestion API connector already exists.
- Either a Data Cloud data stream already exists for each table in the manifest, or you are ready to bootstrap them with `scripts/salesforce/data-cloud-create-manifest-streams.ps1`.
- Each stream field mapping matches the CSV header row for that table.
- The registry contains one target per table, or you are ready to generate them from the manifest.

## Exact Steps

1. Inspect the manifest folder and CSV sizes.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-inspect-csv.ps1 -CsvPath '.\Demos\Sunrun Demo\projects.csv'
```

2. Generate or update the target registry entries for the dataset.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-register-manifest-targets.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -SourceName sunrun_ingest_api -TargetKeyPrefix sunrun -TenantEndpoint https://your-tenant.c360a.salesforce.com
```

3. Check `notes/registries/data-cloud-targets.json` for any remaining org-specific gaps.

- Dataset-derived values should already be refreshed from the manifest.
- If uploads still need live stream metadata, fill only the org-specific fields such as `tenantEndpoint` or connector-specific `objectEndpoint`.

4. If the streams do not already exist, or if you want to reconcile the local generated source with the live org before upload, bootstrap the manifest streams.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-create-manifest-streams.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT_DC -SourceName sunrun_ingest_api -ObjectNamePrefix sunrun
```

- This step reuses compatible schemas, creates or resolves streams idempotently, waits for `ACTIVE` DLO status, refreshes matching registry targets with the live accepted object name and `objectEndpoint`, and writes `salesforce/generated/<sourceName>/provisioning-state.json`.
- The generated metadata remains local source until you deploy it separately.

5. Confirm auth resolves without printing tokens.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-get-access-token.ps1 -TargetKey sunrun-projects
```

6. Upload the full dataset in manifest order. The default path now submits each table job and returns the job ids immediately instead of waiting for all tables to reach terminal states.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-manifest.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetKeyPrefix sunrun
```

7. Only use an explicit completion wait when you are validating one dataset and accept the extra latency.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-manifest.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetKeyPrefix sunrun -WaitForCompletion:$true
```

## Validation

- Each table returns a job id immediately, and explicit waits return a terminal state only when requested.
- `scripts/salesforce/data-cloud-list-jobs.ps1` shows the expected jobs for each target.
- The expected record counts appear in Data Cloud for all uploaded tables.
- If the registry is stale, `data-cloud-upload-manifest.ps1` now stops before upload and names the exact fields that need refreshing.
- If you ran stream bootstrap first, `salesforce/generated/<sourceName>/provisioning-state.json` shows `ACTIVE` DLO acceptance for the provisioned streams.

## Failure Modes

- Registry keys exist but the dataset-derived values no longer match the manifest.
- The dataset registry is current, but the org still lacks the Ingestion API connector needed for stream bootstrap.
- The org contains an incompatible connector schema, so stream bootstrap halts before upload instead of mutating the connector incorrectly.
- One CSV fails field validation because its stream mapping is incomplete or wrong.
- Auth is configured locally for Salesforce but not for Data Cloud token exchange.

## Cleanup or Rollback

- Inspect failed table jobs with `scripts/salesforce/data-cloud-get-job.ps1`.
- Abort stuck jobs with `scripts/salesforce/data-cloud-abort-job.ps1` before rerunning the failed table or rerunning the full manifest upload.
- Rerun `data-cloud-register-manifest-targets.ps1` to refresh dataset-derived target rows.
- Rerun `data-cloud-create-manifest-streams.ps1` if the live streams were recreated, renamed, or only partially provisioned.
- Fix the data stream definition or CSV file, then rerun the failed table or rerun the full manifest upload.