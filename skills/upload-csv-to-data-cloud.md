# Upload CSV to Data Cloud

## Purpose

Bulk-upload CSV data into a configured Salesforce Data Cloud ingestion target using the Ingestion API job flow.

## Required Inputs

- Target key from `notes/registries/data-cloud-targets.json`
- CSV path
- Local Data Cloud auth secrets in `.env.local` or user environment variables

## Prerequisites

- The Data Cloud target is already configured and registered.
- The CSV header row matches the data stream fields.
- The file is 150 MB or smaller.

## Exact Steps

1. Inspect the CSV with `scripts/salesforce/data-cloud-inspect-csv.ps1`.
2. Confirm the target metadata with `scripts/salesforce/data-cloud-register-target.ps1` or by reading the registry.
3. Confirm auth resolves with `scripts/salesforce/data-cloud-get-access-token.ps1`.
4. Upload with `scripts/salesforce/data-cloud-upload-csv.ps1`.
5. If needed, inspect the job with `scripts/salesforce/data-cloud-get-job.ps1` or `scripts/salesforce/data-cloud-list-jobs.ps1`.
6. If a previous job is stuck in `Open` or `UploadComplete`, abort it with `scripts/salesforce/data-cloud-abort-job.ps1` before rerunning the upload.

## Validation

- The upload command returns `JobComplete`.
- The data stream reflects the expected records.

## Failure Modes

- Job fails because CSV headers, required fields, or value formats do not match the data stream.
- Auth fails because the connected app, refresh token, or direct Data Cloud token is not valid.
- Wrong tenant endpoint, stale `objectEndpoint`, or connector metadata causes job creation or lookup failures.

## Cleanup or Rollback

- Inspect failed or stuck jobs with `scripts/salesforce/data-cloud-get-job.ps1`.
- Abort stuck `Open` or `UploadComplete` jobs with `scripts/salesforce/data-cloud-abort-job.ps1`.
- Fix the CSV or target definition and rerun the upload as a new job.
- Remove bad local secrets or stale target metadata.
