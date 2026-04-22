# Inspect Next Semantic Model

## Purpose

Inspect one live Tableau Next semantic-model inventory row directly from a saved target or explicit IDs.

## Required Inputs

- Salesforce org alias or saved Tableau Next target key
- Workspace id when you are not using a saved target
- Semantic-model id or workspace asset id

## Prerequisites

- Salesforce CLI auth works for the target org.
- The workspace and semantic-model identifiers came from live discovery output.

## Exact Steps

1. Discover workspaces with `scripts/tableau/list-next-workspaces.ps1` if needed.
2. Discover semantic models with `scripts/tableau/list-next-semantic-models.ps1` if needed.
3. Run `scripts/tableau/inspect-next-semantic-model.ps1` with a saved target or explicit IDs.

## Validation

- The script returns `SemanticModelValidated` when the semantic model still resolves.
- The output includes workspace id, workspace label, semantic-model id, workspace asset id, and asset usage type.

## Failure Modes

- The semantic-model id no longer exists.
- The workspace id is wrong for the semantic model you are checking.
- The operator tries to inspect a model without a live discovered id.

## Cleanup or Rollback

- Refresh the workspace and semantic-model discovery output and rerun the inspection if the saved ids are stale.
