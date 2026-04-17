# Tableau Cloud Auth Bootstrap

## Purpose

Set up a Tableau Cloud target without putting live secrets into tracked files.

## When to use it

Use this when a machine needs Tableau Cloud access for the first time or when registering a new non-secret target profile.

## Inputs

- Target key.
- Server URL.
- Site content URL.
- Optional default project id.
- PAT name and PAT secret in `.env.local` or user environment variables.

## Prerequisites

- Tableau PAT already created.
- `.env.local` exists locally.

## Exact steps

1. Put `TABLEAU_PAT_NAME` and `TABLEAU_PAT_SECRET` in `.env.local`.
2. Run `scripts/tableau/auth-bootstrap.ps1 -TargetKey YOUR_TARGET -ServerUrl ... -SiteContentUrl ... -SetDefault`.
3. Let the script update `notes/registries/tableau-targets.json` with only non-secret metadata.
4. Run `scripts/tableau/auth-status.ps1 -TargetKey YOUR_TARGET`.

## Validation

- Auth status succeeds.
- The registry contains the target metadata.

## Failure modes

- PAT invalid or expired: rotate the PAT locally and retry.
- Wrong site content URL: update the target and retry.

## Cleanup or rollback

- Remove invalid targets from the registry.
- Remove stale PAT values from `.env.local` when rotating credentials.

## Commands and links

- `scripts/tableau/auth-bootstrap.ps1`
- `scripts/tableau/auth-status.ps1`
- `notes/registries/tableau-targets.json`
