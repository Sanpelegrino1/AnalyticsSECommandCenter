# Prepare Tableau Next Semantic Model

## Purpose

Use this playbook to prepare and apply a Tableau Next semantic-model effort through the repo's supported semantic-layer REST automation.

## Inputs

- Salesforce org alias for the Tableau Next org
- Dedicated Data Cloud auth alias for the same org if token exchange is required
- Data Cloud target key or manifest-backed target set for the dataset
- Dataset name, business domain, and intended analytic questions
- Confirmation that ingestion jobs have completed successfully for the target dataset

## Prerequisites

- Salesforce Data Cloud ingestion is already stable for the dataset you want to model.
- The repo-managed auth path is already working for the org.
- The dataset's non-secret metadata is already recorded in `notes/registries/data-cloud-targets.json`.
- The operator can sign in to the org with Salesforce CLI and inspect the relevant Data Cloud objects.
- The manifest already captures the intended root table and relationship joins for the dataset.

Stable means all of the following are already true before you start semantic-model work:

1. The required ingestion connector and data stream exist.
2. The registry points at the correct tenant endpoint, source name, object API name, and object endpoint.
3. Recent upload jobs complete without unexplained retries or stale-target failures.
4. The dataset shape is settled enough that semantic-model field design will not be invalidated immediately.

## Exact Steps

1. Confirm the Data Cloud target is healthy.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-list-jobs.ps1 -TargetKey orders-demo
```

2. If you are working from a manifest-backed dataset, use a fresh manifest upload only when you intentionally need to re-validate the end-to-end ingest path. For routine semantic-model preparation, confirming recent successful jobs is enough.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-manifest.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetKeyPrefix sunrun
```

3. Capture the semantic-model planning inputs in operator notes before touching Tableau Next APIs.

- Which Data Cloud objects are in scope.
- Which joins, dimensions, measures, and business labels are expected.
- Which questions the first dashboard or insight flow must answer.
- Which org alias and Data Cloud alias should own the session.

4. Reuse the existing Salesforce CLI auth path for org access. Do not create a separate JSON credential file for Tableau Next.

5. Use the discovery wrappers first to confirm the live workspace and semantic-model inventory before doing any deeper local experiments.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\list-next-workspaces.ps1 -TargetOrg STORM_TABLEAU_NEXT
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\list-next-semantic-models.ps1 -TargetOrg STORM_TABLEAU_NEXT
```

6. Register a stable target only after discovery proves the workspace id, and optionally the existing semantic-model id, you intend to use later.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\register-next-target.ps1 -TargetKey juju-demo-sdm -TargetOrg STORM_TABLEAU_NEXT -WorkspaceId 1DyKZ000000kA8f0AE -Purpose "Tableau Next semantic-model workspace"
```

7. Inspect the saved target before any later SDM creation work.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\inspect-next-target.ps1 -TargetKey juju-demo-sdm
```

8. Build the semantic-model spec and request locally before applying any live write.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\orchestrate-authenticated-to-sdm.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -TableauNextTargetKey juju-demo-sdm -WorkspaceId 1DyKZ000000kA8f0AE -ModelApiName Juju_Demo_Semantic -ModelLabel 'Juju Demo Semantic' -SkipAuthAppDeploy -SkipUpload
```

9. Apply the semantic model live through the supported semantic-layer REST path when the manifest, workspace, and active DLOs are validated.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\orchestrate-authenticated-to-sdm.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -TableauNextTargetKey juju-demo-sdm -WorkspaceId 1DyKZ000000kA8f0AE -ModelApiName Juju_Demo_Semantic -ModelLabel 'Juju Demo Semantic' -SkipAuthAppDeploy -SkipUpload -ApplySemanticModel
```

10. Use this playbook's roadmap sections to decide whether the next action belongs in immediate manual preparation, design, or new automation work. Keep any still-unwrapped API inspection in `tmp/` until a stable local wrapper exists for that surface.

## What Can Be Done Immediately

These are repo-native actions you can take now without inventing a new platform:

1. Validate the Salesforce org alias and Data Cloud alias split is correct for the target org.
2. Validate Data Cloud ingestion health using the existing PowerShell scripts.
3. Capture the live workspace inventory with `scripts/tableau/list-next-workspaces.ps1`.
4. Generate a semantic-model spec from the manifest, CSV field profiles, and active Data Lake Object identities.
5. Capture the live semantic-model inventory with `scripts/tableau/list-next-semantic-models.ps1`.
6. Save a minimal non-secret target in `notes/registries/tableau-next-targets.json` with `scripts/tableau/register-next-target.ps1`.
7. Re-run `scripts/tableau/inspect-next-target.ps1` before any later creation work.
8. Use `scripts/tableau/upsert-next-semantic-model.ps1` to generate or apply the semantic model from a saved target and manifest-backed spec.
9. Keep temporary payload experiments in `tmp/` only for surfaces that are not yet wrapped.

## What Still Needs Design

These decisions should be made before adding new scripts:

1. Auth surface: decide whether Tableau Next write operations should use the standard org alias, the Data Cloud alias, or a specific per-target override.
2. Object mapping contract: decide whether later SDM creation should persist manifest-derived object mappings more explicitly in the Tableau Next target registry, or continue deriving them at runtime from the manifest plus active streams.
3. Inspection output: define any additional wrapper shape needed beyond the current direct semantic-model definition inspection and validation endpoints.
4. Cleanup contract: define what a safe teardown means for semantic models, visualizations, and dashboards created for demo use.

## What Still Needs New Automation

These capabilities are still missing entirely from this repo:

1. Visualization and dashboard discovery wrappers tied to semantic models.
2. Teardown helpers for semantic models, visualizations, dashboards, and related demo assets.
3. Local troubleshooting guidance based on real PowerShell script failures and API responses.

## Current Boundary

- The fully proven live publish path is saved Tableau Next target plus manifest-backed spec through `scripts/tableau/upsert-next-semantic-model.ps1` or `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1 -ApplySemanticModel`.
- The narrower ad hoc object-only path using `-ObjectApiName` without a manifest-backed spec is still less proven and should be treated as secondary until its required request-shape differences are folded back into the helper.

## Recommended Implementation Order

1. Add inspection playbooks and troubleshooting notes using the real wrapper outputs.
2. Add visualization and dashboard wrappers after semantic-model creation has been validated across stable datasets.
3. Add teardown last, once the creation model and asset naming rules are understood.

## Validation

- The Data Cloud target can still upload or list recent successful jobs.
- The org aliases needed for the semantic-model session are known and reusable.
- `register-next-target.ps1` can save a validated workspace-first target without adding secrets to tracked files.
- `inspect-next-target.ps1` can confirm the saved workspace still exists and any pinned semantic model still resolves.
- The operator has a written field and metric plan tied to stable Data Cloud objects.
- No secrets were added to tracked files while preparing the semantic-model work.

## Failure Modes

- Data Cloud ingestion is still unstable, so semantic-model work starts on a moving target.
- The org alias used for Salesforce access is not the alias that can resolve the required downstream access context.
- A saved Tableau Next target points at a workspace that has been renamed in human-visible fields or no longer exists.
- A pinned semantic-model id no longer exists in the saved workspace.
- The team jumps directly to dashboard generation before semantic-model inspection exists.

## Cleanup or Rollback

- Remove temporary payload files from `tmp/` if they are no longer needed.
- Remove any incorrect target rows from `notes/registries/tableau-next-targets.json`.
- Stop after the planning phase if ingestion stability regresses; fix Data Cloud first, then resume semantic-model work.