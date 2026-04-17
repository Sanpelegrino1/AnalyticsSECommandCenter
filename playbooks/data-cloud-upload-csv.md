# Upload CSV to Data Cloud

## Purpose

Use this playbook when you need to bulk-ingest a CSV file into an already configured Salesforce Data Cloud Ingestion API target.

## Inputs

- Data Cloud target key from `notes/registries/data-cloud-targets.json`
- CSV file path
- Local auth secrets in `.env.local` or user environment variables

## Prerequisites

- A Data Cloud Ingestion API connector already exists.
- The target object endpoint and connector name are known.
- A Data Cloud Ingestion API data stream already exists for the object.
- The CSV header row matches the fields defined in the data stream.
- The CSV file is 150 MB or smaller.
- One of these local auth patterns is available:
  - `DATACLOUD_ACCESS_TOKEN` plus `DATACLOUD_TENANT_ENDPOINT`
  - `DATACLOUD_CLIENT_ID` plus `DATACLOUD_REFRESH_TOKEN`, and `DATACLOUD_CLIENT_SECRET` if the connected app requires it

## Exact Steps

1. Inspect the CSV before upload.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-inspect-csv.ps1 -CsvPath .\tmp\orders.csv
```

2. Register the target if it is not already in the registry.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-register-target.ps1 -TargetKey orders-demo -SourceName ecomm_api -ObjectName Orders -TenantEndpoint https://your-tenant.c360a.salesforce.com -SetDefault
```

3. Confirm auth resolves without printing the access token.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-get-access-token.ps1 -TargetKey orders-demo
```

4. Upload the CSV and wait for completion.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-csv.ps1 -TargetKey orders-demo -CsvPath .\tmp\orders.csv
```

5. If the upload fails, inspect the job directly.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-get-job.ps1 -TargetKey orders-demo -JobId <job-id>
```

## Validation

- The upload script returns a job state of `JobComplete`.
- `scripts/salesforce/data-cloud-list-jobs.ps1` shows the job in a completed state.
- The target data stream shows the ingested records in Data Cloud.

## Failure Modes

- `Open` or `UploadComplete` never transitions: auth or processing issue, or the wait timeout is too short.
- `Failed`: the CSV shape or field values do not match the configured data stream.
- `401` or `403`: local secrets or connected-app scopes are incorrect.
- `404`: wrong tenant endpoint or wrong job id.

## Cleanup or Rollback

- Remove bad local secrets from `.env.local` or user environment variables.
- Fix the CSV or the data stream mapping, then rerun the upload with a new job.
- Update `notes/registries/data-cloud-targets.json` if the connector name or tenant endpoint changed.
