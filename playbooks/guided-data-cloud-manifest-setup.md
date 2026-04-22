# Guided Data Cloud Manifest Setup

## Purpose

Use this playbook when you want Command Center to handle as much of the Data Cloud setup path as possible from VS Code for a multi-table dataset with a manifest.

## Inputs

- Manifest path
- Salesforce login or My Domain URL
- Dedicated Data Cloud auth alias
- Optional shared Data Cloud source name override for the dataset
- Optional prefix override for generated target keys and object names
- Optional tenant endpoint if you already know it

## Prerequisites

- Data Cloud is provisioned in the target org.
- The repo-managed `CommandCenterAuth` external client app is deployed.
- The user can authorize the connected app in the browser.
- The Data Cloud Ingestion API connector already exists, or the operator can create it in Data Cloud Setup.

## Exact Steps

1. Run the guided setup script or task.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-guided-manifest-setup.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -Alias STORM_TABLEAU_NEXT_DC -LoginUrl https://your-domain.my.salesforce.com -TargetKeyPrefix sunrun -SourceName sunrun_ingest_api -ObjectNamePrefix sunrun -SetDefault
```

2. Complete the browser authorization when the script opens the Salesforce consent page.

3. Let the script write the local Data Cloud auth values into `.env.local` and generate or refresh registry entries in `notes/registries/data-cloud-targets.json`.

4. Review the generated target records.

- Dataset-derived fields are now automatic and deterministic from the manifest: `targetKeyPrefix`, `sourceName`, `objectNamePrefix`, `objectName`, `manifestPath`, `csvPath`, `datasetKey`, `datasetLabel`, and notes.
- Org-specific fields stay separate: `salesforceAlias`, `tenantEndpoint`, and connector-specific `objectEndpoint`.
- Rerunning guided setup refreshes dataset-derived fields without wiping existing `objectEndpoint` values.

5. If you want an operator-review artifact before any deployment or live stream work, run the standalone schema helper.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-generate-schema.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json'
```

- The default schema draft path is `salesforce/generated/<dataset-or-manifest-name>/<dataset-or-manifest-name>-ingestion-api-schema.yaml`.
- The helper is optional for review, but the same shared schema inference now also runs inside `scripts/salesforce/data-cloud-create-manifest-streams.ps1`.

6. If the manifest does not already have live Data Cloud streams, or you want to reconcile the generated metadata to the live org state first, run the manifest stream bootstrap.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-create-manifest-streams.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT_DC -SourceName sunrun_ingest_api -ObjectNamePrefix sunrun
```

- This step registers compatible connector schemas, creates or resolves manifest streams idempotently, waits for each stream's DLO status to become `ACTIVE`, syncs matching registry targets to the live accepted object name and `objectEndpoint`, and writes `salesforce/generated/<sourceName>/provisioning-state.json`.
- The generated metadata under `salesforce/generated/<sourceName>/` remains local source until you deploy it separately with the Salesforce metadata workflow.

7. Upload the manifest dataset.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-manifest.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetKeyPrefix sunrun
```

## Validation

- The script resolves a Data Cloud access token without printing it.
- `DATACLOUD_REFRESH_TOKEN`, `DATACLOUD_CLIENT_ID`, `DATACLOUD_SALESFORCE_ALIAS`, and `DATACLOUD_DEFAULT_TARGET` are populated locally.
- `notes/registries/data-cloud-targets.json` contains one target per manifest table.
- The optional schema draft and generated metadata paths are predictable under `salesforce/generated/` unless you override them.
- `data-cloud-create-manifest-streams.ps1` writes `provisioning-state.json` that records which schemas and streams were reused or created and whether the DLOs reached `ACTIVE`.
- A later manifest upload either starts immediately or stops before upload with explicit stale-row or missing-org-setup guidance.

## Failure Modes

- Browser auth succeeds but Salesforce returns no refresh token.
- The org rejects `cdp_ingest_api` during token exchange.
- The registry is current for the manifest, but the org still lacks the Ingestion API connector required for stream bootstrap.
- A connector schema already exists but is incompatible with the manifest-derived field set, so stream bootstrap stops instead of corrupting the live connector state.
- The chosen override values do not match the live connector naming scheme for that org.

## Cleanup or Rollback

- Remove or rotate the local Data Cloud refresh token in `.env.local`.
- Rerun the guided setup or `data-cloud-register-manifest-targets.ps1` to refresh dataset-derived fields.
- Rerun `data-cloud-create-manifest-streams.ps1` if the live stream objects were recreated or renamed and you need the registry and local generated source refreshed to match the org.
- Update only the remaining org-specific fields in `notes/registries/data-cloud-targets.json` if the live Data Cloud connector metadata changes.