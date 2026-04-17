# Salesforce Org Login and Alias Registration

## Purpose

Authenticate to a Salesforce org with browser-based login and register the alias and non-secret context in the workspace registry.

## When to use it

Use this when onboarding a new demo org, refreshing an alias on a new machine, or re-establishing context after local auth state changes.

## Inputs

- Salesforce alias.
- Login URL or My Domain URL.
- Purpose.
- Notes.

## Prerequisites

- `sf` is installed.
- Browser login is allowed.
- The workspace bootstrap has been run.

## Exact steps

1. Run `scripts/salesforce/login-web.ps1` with `-Alias` and `-InstanceUrl`.
2. Complete the browser login.
3. Let the script update `notes/registries/salesforce-orgs.json`.
4. If this org should be the active default, include `-SetDefault`.
5. Run `scripts/salesforce/list-orgs.ps1` to confirm the alias is visible.

## Validation

- `sf org list` shows the alias.
- `notes/registries/salesforce-orgs.json` contains the alias, login URL, purpose, and notes.
- `scripts/salesforce/open-org.ps1` opens the org without a new login prompt.

## Failure modes

- Wrong login URL: rerun with the correct production, sandbox, or My Domain URL.
- Alias collision: reuse intentionally or update the alias name.
- Browser auth blocked by policy: use a supported non-browser auth path outside tracked files, then register the alias manually.

## Cleanup or rollback

- Remove stale registry entries if an alias is retired.
- If the wrong alias became default, run `scripts/salesforce/set-default-org.ps1` with the correct alias.

## Commands and links

- `scripts/salesforce/login-web.ps1`
- `scripts/salesforce/register-org.ps1`
- `scripts/salesforce/list-orgs.ps1`
