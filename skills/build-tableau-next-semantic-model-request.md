# Build Tableau Next Semantic Model Request

## Purpose

Generate or apply a repo-native semantic-model create or update request from a saved Tableau Next target and a manifest-derived spec.

## When to use it

Use this after a Tableau Next target has been registered and inspected, when you want a normalized SDM spec plus a supported semantic-layer REST request body.

## Inputs

- Tableau Next target key.
- Semantic-model API name or a spec path that already carries the model metadata.
- Semantic-model label when not already present in the spec.
- Manifest-derived object mappings and relationship definitions, usually supplied through `-SpecPath`.
- Optional spec path if you are replaying or editing a prior dry-run output.

## Prerequisites

- `scripts/tableau/register-next-target.ps1` has saved a valid target.
- `scripts/tableau/inspect-next-target.ps1` succeeds for that target.
- The active Data Lake Object identities and field mappings are already known and stable.

## Exact steps

1. If the spec does not already exist, build it from the manifest plus the live Data Cloud provisioning report with `scripts/salesforce/build-manifest-semantic-model-spec.ps1`.
2. Build the first request with `scripts/tableau/upsert-next-semantic-model.ps1`, usually from that manifest-derived spec file.
3. Review the generated `SemanticModelSpec` and `SemanticModelRequest` locally.
4. Add `-Apply` to create or update the model and sync manifest relationships through the supported semantic-layer REST APIs.

## Validation

- The helper returns `ApplyStatus = DryRun` by default.
- `build-manifest-semantic-model-spec.ps1` writes a spec that already carries manifest-derived object mappings and relationship definitions.
- The output includes both `SemanticModelSpec` and `SemanticModelRequest`.
- The target workspace still validates during request generation.

## Failure modes

- The saved target no longer resolves a live workspace.
- The primary object is not included in the resolved object mappings.
- The active Data Lake Object names or manifest relationship fields do not match the live semantic definitions being created.

## Cleanup or rollback

- Remove temporary request payloads from `tmp/` when they are no longer needed.
- Rebuild the request from the saved target if object inputs or the target workspace change.

## Commands and links

- `scripts/salesforce/build-manifest-semantic-model-spec.ps1`
- `scripts/tableau/upsert-next-semantic-model.ps1`
- `scripts/tableau/register-next-target.ps1`
- `scripts/tableau/inspect-next-target.ps1`
- `notes/registries/tableau-next-targets.json`