# Create and Assign a Permission Set

## Purpose

Create access scaffolding quickly and make permission changes repeatable.

## When to use it

Use this when setting up demo users or granting access to new metadata and apps.

## Inputs

- Org alias.
- Permission set label and API name.
- User or users to assign.

## Prerequisites

- Admin access in the org.

## Exact steps

1. Open `scripts/salesforce/open-setup-surface.ps1 -TargetOrg YOUR_ALIAS -Surface PermissionSets`.
2. Create or update the permission set in Setup.
3. Assign it to the intended users.
4. Retrieve permission set metadata if it should be versioned in the DX project.

## Validation

- The permission set exists.
- The expected user assignments are present.
- Metadata retrieval captures the permission set if needed.

## Failure modes

- Assignment blocked by license mismatch: use a compatible permission set strategy.
- Wrong org: verify alias before assigning.

## Cleanup or rollback

- Remove user assignments.
- Revert permission set metadata or delete the permission set if appropriate.

## Commands and links

- `scripts/salesforce/open-setup-surface.ps1`
- `scripts/salesforce/retrieve-metadata.ps1`
