# Set Up Data Cloud Ingestion Target

## Purpose

Use this playbook when a new Salesforce org needs its one shared Data Cloud publish connector and the initial ingestion target pattern that later dataset publishes will reuse.

## Inputs

- Salesforce org or Data Cloud tenant where the ingestion target will live
- Shared publish connector name for the org
- CSV sample file
- Target object name
- Optional first target object name

## Prerequisites

- Data Cloud is provisioned in the target org.
- You can create or coordinate creation of an Ingestion API connector.
- You can create or coordinate creation of the matching Ingestion API data stream.
- You know where the object endpoint download is stored.

## Exact Steps

1. Inspect the CSV to capture the header row and rough row count.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-inspect-csv.ps1 -CsvPath .\tmp\sample.csv
```

2. In Data Cloud, create or validate one shared Ingestion API connector for the org and download the object endpoints.

3. Save that connector name in `notes/registries/salesforce-orgs.json` as `dataCloudSourceName` for the org alias so later dataset publishes do not guess.

4. In Data Cloud, create the Ingestion API data stream for the object and map the fields so the CSV header row matches the stream.

5. Register the non-secret target metadata in the repo.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-register-target.ps1 -TargetKey sample-target -SourceName command_center_ingest_api -ObjectName SampleObject -TenantEndpoint https://your-tenant.c360a.salesforce.com -ObjectEndpoint /api/v1/ingest/sources/command_center_ingest_api/SampleObject -Notes "CSV demo source"
```

6. Add the local auth secrets to `.env.local`.

7. Validate the auth and target metadata.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-get-access-token.ps1 -TargetKey sample-target
```

8. Run a small upload using the same target.

## Validation

- The target exists in `notes/registries/data-cloud-targets.json`.
- The auth script returns the expected tenant endpoint.
- A small CSV upload finishes with `JobComplete`.

## Failure Modes

- The connector exists but the object or field names do not match the CSV.
- The tenant endpoint is wrong or missing.
- The local auth secrets cannot exchange into a Data Cloud access token.

## Cleanup or Rollback

- Remove stale target entries from `notes/registries/data-cloud-targets.json`.
- Rotate or remove bad secrets from `.env.local`.
- Delete or archive invalid sample CSV files from `tmp/`.
