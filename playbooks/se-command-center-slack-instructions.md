# :compass: SE-Command-Center Instructions

## :dart: What This Is

This is the clean operator writeup for running the current SE-Command-Center path from authenticated Salesforce access to a live Tableau Next semantic data model.

Use this when you want to:
- validate that a dataset is ready for semantic modeling
- generate the semantic-model request from a manifest-backed dataset
- apply the semantic model through the supported REST-based path
- keep the workflow aligned to the current proven implementation instead of older Aura-era experiments

## :white_check_mark: Current Proven Path

The path that is currently proven in this repo is:

1. Salesforce CLI auth is already working for the Tableau Next org.
2. Data Cloud auth can resolve through the dedicated Data Cloud alias when needed.
3. Manifest-backed Data Cloud targets and live DLOs already exist and are healthy.
4. A saved Tableau Next target is registered for the workspace.
5. The semantic model is generated and applied from a manifest-backed spec.

Important:
- The strongest supported path is saved target + manifest-backed spec.
- The narrower object-only path using only `-ObjectApiName` is secondary and should not be treated as the default operator path.
- Do not use old Aura artifacts or old Aura scripts from the recycling-bin staging area.

## :busts_in_silhouette: Intended User

This is written for:
- solution engineers
- demo builders
- operators maintaining repeatable SDM creation for user-facing datasets
- future agents working inside this repo

## :clipboard: Inputs You Need

Before you start, have these ready:
- Salesforce org alias for the Tableau Next org
- dedicated Data Cloud alias for the same org when token exchange is required
- manifest path for the dataset
- Data Cloud target key prefix or already-registered manifest-backed targets
- saved Tableau Next target key
- semantic model API name and label

Example values from the proven Sunrun-style flow:
- Tableau org alias: `STORM_TABLEAU_NEXT`
- Data Cloud alias: `STORM_TABLEAU_NEXT_DC`
- target key: `juju-demo-sdm`
- manifest: `Demos/Sunrun Demo/manifest.json`

## :lock: Guardrails

- Keep secrets out of tracked files.
- Use Salesforce CLI local auth storage for Salesforce auth.
- Use `.env.local` or user environment variables for Data Cloud secrets only when needed.
- Keep standard org aliases separate from Data Cloud aliases.
- Preserve non-secret target metadata in the registries.
- Treat `tmp/` as scratch space only for current supported artifacts.

## :construction: Prerequisites

All of the following should already be true:
- the dataset has already been ingested or is upload-ready
- manifest-backed targets are registered
- the correct Data Cloud connector and streams already exist
- recent ingestion jobs complete successfully
- the Tableau Next workspace is known and registered as a saved target
- the current dataset shape is stable enough to model

You should also confirm:
- the registry points at the correct source name and object names
- the intended joins in the manifest are still correct
- the saved workspace target resolves cleanly

## :rocket: Fast Path

### :one: Confirm Data Cloud Health

Check recent jobs first:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-list-jobs.ps1 -TargetKey sunrun-projects
```

If you need to revalidate the dataset end-to-end, run the manifest upload path intentionally instead of assuming the data is current.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-manifest.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetKeyPrefix sunrun
```

### :two: Confirm Tableau Next Workspace Context

Inspect the saved target:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\inspect-next-target.ps1 -TargetKey juju-demo-sdm
```

If the target does not exist yet, register it only after verifying the workspace from live discovery.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\register-next-target.ps1 -TargetKey juju-demo-sdm -TargetOrg STORM_TABLEAU_NEXT -WorkspaceId 1DyKZ000000kA8f0AE -Purpose "Semantic-model workspace"
```

### :three: Generate The Semantic Model Request

Generate the request locally before live apply:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\orchestrate-authenticated-to-sdm.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -TableauNextTargetKey juju-demo-sdm -WorkspaceId 1DyKZ000000kA8f0AE -ModelApiName Juju_Demo_Semantic -ModelLabel 'Juju Demo Semantic' -SkipAuthAppDeploy -SkipUpload
```

This should emit current request/spec artifacts into `tmp/`.

### :four: Apply The Semantic Model

Apply through the supported semantic-layer path:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\orchestrate-authenticated-to-sdm.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -TableauNextTargetKey juju-demo-sdm -WorkspaceId 1DyKZ000000kA8f0AE -ModelApiName Juju_Demo_Semantic -ModelLabel 'Juju Demo Semantic' -SkipAuthAppDeploy -SkipUpload -ApplySemanticModel
```

Alternative direct helper path:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\upsert-next-semantic-model.ps1 -TargetKey juju-demo-sdm -SpecPath .\tmp\sunrun-demo.semantic-model.spec.json -Apply -Confirm:$false -Json
```

## :mag: What Good Looks Like

Success should look like this:
- the target still resolves
- the request/spec files are generated without drift errors
- a semantic model id is returned after apply
- model detail inspection succeeds
- validation returns `IsValid = true`
- manifest relationships are present on the created model

Useful validation commands:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\list-next-semantic-models.ps1 -TargetOrg STORM_TABLEAU_NEXT -WorkspaceId 1DyKZ000000kA8f0AE -Json
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\inspect-next-semantic-model.ps1 -TargetOrg STORM_TABLEAU_NEXT -SemanticModelId 2SMKZ000000kAfa4AE
```

## :warning: Common Failure Modes

### Dataset problems
- ingestion jobs are not actually healthy
- stream or object names drifted from the registry
- manifest joins do not match the active DLO field set

### Workspace problems
- the saved target points at the wrong workspace
- the workspace exists but the operator is using the wrong org alias

### Semantic-model problems
- the generated request shape is missing required fields for the chosen path
- the operator uses the less-proven object-only path instead of the manifest-backed spec path

## :triangular_flag_on_post: Current Boundary

What is fully supported now:
- saved target registration
- target inspection
- manifest-driven request generation
- manifest-backed semantic-model live apply
- semantic relationship persistence and validation

What is not the default supported operator path:
- old Aura-driven create or update helpers
- recycling-bin historical docs and scripts
- relying on raw scratch files from older validation runs

## :package: Recommended Files To Reuse

Use these active repo files as your source of truth:
- `README.md`
- `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1`
- `scripts/tableau/upsert-next-semantic-model.ps1`
- `scripts/tableau/inspect-next-target.ps1`
- `scripts/tableau/inspect-next-semantic-model.ps1`
- `playbooks/prepare-tableau-next-semantic-model.md`

## :memo: Operator Notes

- Prefer the manifest-backed path for repeatability.
- Keep naming stable for targets and models.
- If the model applies successfully, capture the resulting model id immediately.
- If the request fails, compare the generated request artifact before changing the manifest.
- If a target or registry row is wrong, fix the registry before attempting another live apply.

## :handshake: Handoff Summary Template

Use this when handing the run to another operator or agent:

```text
:white_check_mark: Org alias used: <alias>
:white_check_mark: Data Cloud alias used: <alias>
:white_check_mark: Manifest: <path>
:white_check_mark: Saved target: <key>
:white_check_mark: Request artifact: <path>
:white_check_mark: Applied model id: <id-or-not-applied>
:white_check_mark: Validation result: <valid / invalid / not run>
:warning: Remaining blocker or caveat: <one sentence>
```
