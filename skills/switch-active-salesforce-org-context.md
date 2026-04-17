# Switch Active Salesforce Org Context

## Purpose

Move the workspace default Salesforce target to another existing alias without re-authenticating.

## When to use it

Use this when you are moving between demo orgs during setup, validation, or presentation prep.

## Inputs

- Target alias.

## Prerequisites

- Alias already exists in local Salesforce CLI auth state.

## Exact steps

1. Run `scripts/salesforce/list-orgs.ps1` if you need to confirm the alias.
2. Run `scripts/salesforce/set-default-org.ps1 -Alias YOUR_ALIAS`.
3. Optionally update `.env.local` if you want `SF_DEFAULT_ALIAS` to match the new default.

## Validation

- `sf config set target-org=YOUR_ALIAS` succeeds.
- Opening the org or running SOQL defaults to the expected alias.

## Failure modes

- Alias missing locally: log in first.
- Registry default differs from CLI default: rerun the set-default script to bring them back in sync.

## Cleanup or rollback

- Re-run the same script with the previous alias if you need to revert.

## Commands and links

- `scripts/salesforce/list-orgs.ps1`
- `scripts/salesforce/set-default-org.ps1`
