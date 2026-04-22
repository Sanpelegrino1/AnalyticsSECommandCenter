# Inspect Tableau Next Target

## Purpose

Validate a non-secret Tableau Next target before any later semantic-model creation or update work.

## When to use it

Use this after workspace and semantic-model discovery, and again before any later SDM creation step.

## Inputs

- Salesforce org alias.
- Target key.
- Workspace id from `scripts/tableau/list-next-workspaces.ps1`.
- Optional semantic-model id from `scripts/tableau/list-next-semantic-models.ps1`.

## Prerequisites

- Salesforce CLI auth for the target org works.
- Data Cloud ingestion for the dataset is already stable.
- Workspace and optional semantic-model ids came from live discovery output, not guesses.

## Exact steps

1. Discover workspaces.
2. If needed, discover semantic models for the chosen workspace.
3. Register the target with `scripts/tableau/register-next-target.ps1`.
4. Inspect the target with `scripts/tableau/inspect-next-target.ps1`.

## Validation

- The saved target resolves a live workspace.
- If a semantic model is pinned, it resolves in the same workspace.
- No secrets were written to tracked files.

## Failure modes

- Workspace id no longer exists in the target org.
- Semantic-model id no longer exists in the saved workspace.
- The operator tries to register a target from a label or guess instead of a discovered id.

## Cleanup or rollback

- Remove incorrect target rows from `notes/registries/tableau-next-targets.json`.

## Commands and links

- `scripts/tableau/list-next-workspaces.ps1`
- `scripts/tableau/list-next-semantic-models.ps1`
- `scripts/tableau/register-next-target.ps1`
- `scripts/tableau/inspect-next-target.ps1`
- `notes/registries/tableau-next-targets.json`