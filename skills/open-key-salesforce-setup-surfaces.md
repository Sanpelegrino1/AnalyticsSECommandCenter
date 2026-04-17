# Open Key Salesforce Setup Surfaces Quickly

## Purpose

Jump directly to the Setup pages that are repeatedly needed during demo-admin work.

## When to use it

Use this when you need fast access to Setup pages without manual click navigation.

## Inputs

- Org alias.
- Surface name.

## Prerequisites

- Authenticated org alias.

## Exact steps

1. Choose one of the supported surfaces: `SetupHome`, `ObjectManager`, `Users`, `PermissionSets`, `PermissionSetGroups`, `LightningApps`, `Flows`, `ConnectedApps`, `InstalledPackages`.
2. Run `scripts/salesforce/open-setup-surface.ps1 -TargetOrg YOUR_ALIAS -Surface SURFACE_NAME`.

## Validation

- The browser opens the expected Salesforce page in the correct org.

## Failure modes

- Unsupported surface name: use one of the supported values.
- Wrong alias: switch context first.

## Cleanup or rollback

- None.

## Commands and links

- `scripts/salesforce/open-setup-surface.ps1`
