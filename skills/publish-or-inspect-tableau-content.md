# Publish or Inspect Tableau Content

## Purpose

Publish a workbook or datasource through the chosen automation path, or inspect an existing object in place.

## When to use it

Use this when you need a repeatable publish flow or a quick content inspection without ad hoc API assembly.

## Inputs

- Target key.
- For publish: file path, content type, project id.
- For inspect: content type and id or name.

## Prerequisites

- Tableau auth bootstrap completed.
- A valid PAT available locally.

## Exact steps

1. To inspect, run `scripts/tableau/inspect-content.ps1 -TargetKey YOUR_TARGET -ContentType workbook -Name YOUR_NAME`.
2. To publish, run `scripts/tableau/publish-file.ps1 -TargetKey YOUR_TARGET -ContentType workbook -Path .\path\to\file.twbx -ProjectId YOUR_PROJECT_ID -Overwrite`.
3. After publishing, run `scripts/tableau/list-content.ps1` to confirm the object appears.

## Validation

- Inspect returns the expected JSON object.
- Publish returns a success payload and the object appears in content listing.

## Failure modes

- Wrong project id: list projects first and retry.
- Unsupported file extension: use a workbook or datasource package format supported by the endpoint.
- Publish blocked by permissions: confirm the PAT user can publish into the target project.

## Cleanup or rollback

- Republish with the previous version if needed.
- Remove incorrectly published content directly in Tableau Cloud if required.

## Commands and links

- `scripts/tableau/inspect-content.ps1`
- `scripts/tableau/publish-file.ps1`
- `scripts/tableau/list-content.ps1`