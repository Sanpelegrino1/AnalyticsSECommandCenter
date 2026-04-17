# List Tableau Cloud Projects and Content

## Purpose

Inspect Tableau Cloud inventory without hand-building REST requests.

## When to use it

Use this when checking environment state, locating a publish target, or confirming the content footprint of a site.

## Inputs

- Target key.

## Prerequisites

- Valid Tableau PAT in local env.

## Exact steps

1. Run `scripts/tableau/list-projects.ps1 -TargetKey YOUR_TARGET`.
2. Run `scripts/tableau/list-content.ps1 -TargetKey YOUR_TARGET`.
3. If you need details for one object, run `scripts/tableau/inspect-content.ps1`.

## Validation

- Project and content lists return without auth errors.
- Expected project names and content names appear.

## Failure modes

- Auth failure: run the auth bootstrap skill first.
- Large site inventory: rerun with JSON output and filter locally.

## Cleanup or rollback

- None.

## Commands and links

- `scripts/tableau/list-projects.ps1`
- `scripts/tableau/list-content.ps1`
- `scripts/tableau/inspect-content.ps1`
