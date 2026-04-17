# Retrieve or Deploy Metadata

## Purpose

Use the existing Salesforce DX project as the source-managed hub for metadata retrieve and deploy work.

## When to use it

Use this for normal metadata sync operations against a demo org.

## Inputs

- Org alias.
- Manifest path or metadata selection.

## Prerequisites

- Authenticated org alias.
- The `salesforce/` DX project remains intact.

## Exact steps

1. For manifest retrieval, run `scripts/salesforce/retrieve-metadata.ps1 -TargetOrg YOUR_ALIAS -ManifestPath manifest/package.xml`.
2. For targeted retrieval, add `-Metadata CustomObject:Account` or another metadata identifier.
3. For deployment, run `scripts/salesforce/deploy-metadata.ps1` with the same targeting pattern.
4. Review diffs under `salesforce/force-app/main/default`.

## Validation

- The CLI command completes successfully.
- Expected metadata files appear or update locally.
- Deployed changes are visible in the target org.

## Failure modes

- Manifest path wrong relative to `salesforce/`: fix the path.
- API-level metadata errors: inspect the CLI output and narrow the target.

## Cleanup or rollback

- Re-retrieve to refresh local state.
- Redeploy previous source if you need to reverse a change.

## Commands and links

- `scripts/salesforce/retrieve-metadata.ps1`
- `scripts/salesforce/deploy-metadata.ps1`
- `salesforce/manifest/package.xml`
