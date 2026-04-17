# Run SOQL and Export Results

## Purpose

Run a query against an org and export the result for demo prep, data inspection, or handoff.

## When to use it

Use this when validating seed data, checking admin setup state, or producing a quick extract.

## Inputs

- Org alias.
- SOQL query.
- Output path.

## Prerequisites

- The org is authenticated locally.

## Exact steps

1. Run `scripts/salesforce/run-soql.ps1 -TargetOrg YOUR_ALIAS -Query "SELECT ..." -OutputPath tmp/your-export.csv`.
2. If you need Tooling API objects, add `-UseToolingApi`.
3. Review the export in `tmp/`.

## Validation

- The export file exists.
- The row count matches expectations.
- Sample records look structurally correct.

## Failure modes

- Query syntax error: fix the SOQL and rerun.
- Wrong org context: set the right alias first.

## Cleanup or rollback

- Delete temporary exports from `tmp/` when they are no longer useful.

## Commands and links

- `scripts/salesforce/run-soql.ps1`
- `tmp/`
