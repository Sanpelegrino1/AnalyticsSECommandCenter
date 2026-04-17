# Upload Manifest Dataset to Data Cloud

## Purpose

Use this playbook when a dataset folder contains multiple CSV files plus a manifest that defines the table list, and you want to upload the full set to Salesforce Data Cloud in one ordered run.

## Inputs

- Manifest path
- Shared Data Cloud source name for the dataset
- Optional target key prefix if you do not want to use raw table names as registry keys
- Local Data Cloud auth secrets in `.env.local` or user environment variables

## Prerequisites

- The Data Cloud Ingestion API connector already exists.
- A Data Cloud data stream already exists for each table in the manifest.
- Each stream field mapping matches the CSV header row for that table.
- The registry contains one target per table, or you are ready to generate them from the manifest.

## Exact Steps

1. Inspect the manifest folder and CSV sizes.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-inspect-csv.ps1 -CsvPath '.\scripts\Sunrun Demo\projects.csv'
```

2. Generate or update the target registry entries for the dataset.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-register-manifest-targets.ps1 -ManifestPath '.\scripts\Sunrun Demo\manifest.json' -SourceName sunrun_ingest_api -TargetKeyPrefix sunrun -TenantEndpoint https://your-tenant.c360a.salesforce.com
```

3. Review `notes/registries/data-cloud-targets.json` and correct any object names so they match the actual Data Cloud data streams.

4. Confirm auth resolves without printing tokens.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-get-access-token.ps1 -TargetKey sunrun-projects
```

5. Upload the full dataset in manifest order.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-manifest.ps1 -ManifestPath '.\scripts\Sunrun Demo\manifest.json' -TargetKeyPrefix sunrun
```

## Validation

- Each table returns a job id and a terminal state.
- `scripts/salesforce/data-cloud-list-jobs.ps1` shows the expected jobs for each target.
- The expected record counts appear in Data Cloud for all uploaded tables.

## Failure Modes

- Registry keys exist but object names do not match the actual data stream objects.
- One CSV fails field validation because its stream mapping is incomplete or wrong.
- Auth is configured locally for Salesforce but not for Data Cloud token exchange.

## Cleanup or Rollback

- Update or remove incorrect target entries from `notes/registries/data-cloud-targets.json`.
- Fix the data stream definition or CSV file, then rerun the failed table or rerun the full manifest upload.