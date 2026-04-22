# Provision Data Cloud Manifest Streams

## Purpose

Register manifest-derived connector schemas, create or reconcile Data Cloud streams idempotently, confirm DLO activation, and keep the registry plus generated local metadata aligned with the live org state before upload.

## Required Inputs

- Manifest path
- Dedicated Data Cloud Salesforce alias
- Shared source name for the manifest dataset
- Object naming prefix or naming scheme for the target org

## Prerequisites

- `CommandCenterAuth` is already deployed and the dedicated Data Cloud alias can resolve a token.
- Data Cloud is provisioned in the target org.
- The Ingestion API connector already exists in Data Cloud Setup.
- The manifest files and CSV headers are the intended source of truth for schema inference.

## Exact Steps

1. Confirm Data Cloud auth resolves with the dedicated alias.
2. Run `scripts/salesforce/data-cloud-create-manifest-streams.ps1` with the manifest path, target alias, source name, and object naming inputs.
3. Let the script register any compatible missing schemas, reuse matching live schemas, create or resolve streams, and wait for `ACTIVE` DLO status.
4. Review `salesforce/generated/<sourceName>/provisioning-state.json` for reused versus created artifacts and any registry sync.
5. If desired, deploy the generated metadata from `salesforce/generated/<sourceName>/` separately through the Salesforce metadata workflow.
6. Upload with `scripts/salesforce/data-cloud-upload-manifest.ps1` once the provisioning report and registry look correct.

## Validation

- The script finishes without schema-compatibility errors.
- `provisioning-state.json` exists under `salesforce/generated/<sourceName>/`.
- Each provisioned stream reports DLO status `ACTIVE`.
- Matching rows in `notes/registries/data-cloud-targets.json` now reflect the live accepted `objectName` and `objectEndpoint`.

## Failure Modes

- The org is missing the Ingestion API connector, so the script cannot resolve the connector.
- A connector schema already exists but its fields or types are incompatible with the manifest-derived schema.
- Multiple live streams ambiguously match the same manifest table, so the script stops instead of choosing one implicitly.
- DLO activation never reaches `ACTIVE` before timeout.

## Cleanup or Rollback

- Fix connector or schema issues in the org, then rerun the script.
- If stream names changed because of a collision or recreation, rerun the script to refresh the registry and local generated source.
- If you do not want the generated local source, remove the corresponding folder under `salesforce/generated/<sourceName>/` after review.