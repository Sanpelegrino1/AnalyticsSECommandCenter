# Guided Data Cloud Manifest Setup

## Purpose

Authorize Data Cloud, register manifest-derived targets, and prepare the workspace for manifest uploads with minimal Salesforce navigation.

## Required Inputs

- Manifest path
- Salesforce login or My Domain URL
- Dedicated Data Cloud alias
- Shared source name for the dataset
- Prefixes for target keys and object names

## Prerequisites

- `CommandCenterAuth` is deployed in the target org.
- The operator can authorize the app in a browser.
- The org has Data Cloud provisioned.
- The connector and data streams either already exist or the operator knows the intended source and object naming scheme.

## Exact Steps

1. Run `scripts/salesforce/data-cloud-guided-manifest-setup.ps1` or the `Salesforce Data Cloud: Guided manifest setup` task.
2. Complete browser authorization when prompted.
3. Review the generated registry entries in `notes/registries/data-cloud-targets.json`.
4. Optionally run `scripts/salesforce/data-cloud-generate-schema.ps1` to create a reviewable schema draft under `salesforce/generated/<dataset-or-manifest-name>/`.
5. If the streams do not already exist, or you want live-state reconciliation first, run `scripts/salesforce/data-cloud-create-manifest-streams.ps1`.
6. Review `salesforce/generated/<sourceName>/provisioning-state.json` if you ran stream bootstrap.
7. Upload with `scripts/salesforce/data-cloud-upload-manifest.ps1`.

## Validation

- Data Cloud token exchange succeeds.
- `.env.local` contains the expected local-only alias and client-id values, and refresh-token values remain blank on the preferred Salesforce CLI session path.
- The registry contains one generated target for each manifest table.
- Schema inference remains available as a standalone review helper and is also reused automatically by `scripts/salesforce/data-cloud-create-manifest-streams.ps1`.
- If stream bootstrap ran, the provisioning report shows reused or created streams and `ACTIVE` DLO status.

## Failure Modes

- Token exchange returns `invalid_scope` because the org or app is not ready for `cdp_ingest_api`.
- The standard org alias still returns `invalid_scope`; use the dedicated Data Cloud alias backed by `CommandCenterAuth` rather than assuming the normal alias can exchange into Data Cloud.
- Browser auth completes but no refresh token is returned.
- The org is missing the Ingestion API connector required for live stream bootstrap.
- Generated object names do not match the actual data stream objects, or an existing connector schema is incompatible with the manifest-derived fields.

## Cleanup or Rollback

- Remove bad local auth values from `.env.local`.
- Delete or fix the generated target entries and rerun setup.
- Rerun `scripts/salesforce/data-cloud-create-manifest-streams.ps1` if the live streams were recreated or renamed and the registry needs to be refreshed to the accepted live object names.