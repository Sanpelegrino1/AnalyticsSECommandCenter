# New Org Data Cloud To SDM

## Purpose

Give agents one repo-native, step-by-step path for taking a new Salesforce org from first auth through Data Cloud ingestion and base Tableau Next semantic-model publication.

This is the default manual when the goal is to do the whole process simply: authenticate, provision or reconcile manifest-backed streams, create DLOs, upload CSV data, and create the base semantic model plus relationships.

## When to use it

- The target Salesforce org is new to this workspace or does not yet have reusable Data Cloud auth state.
- The user wants one end-to-end agent workflow instead of separate auth, ingest, and SDM playbooks.
- The dataset is manifest-backed, or can be made manifest-backed, so the repo can derive targets, relationships, and the semantic-model spec from one source of truth.

## Inputs

- Standard Salesforce org alias, for example `STORM_TABLEAU_NEXT`.
- Salesforce login URL or My Domain URL.
- Dedicated Data Cloud alias, usually `<org alias>_DC`.
- Manifest path for the dataset. This is the preferred and most proven full-path input.
- Optional naming overrides only when defaults are wrong for the org: `SourceName`, `TargetKeyPrefix`, `ObjectNamePrefix`.
- Tableau Next workspace selector or saved target key.
- Semantic-model API name and label.

## Prerequisites

- The workspace machine is already bootstrapped, or the agent can run the bootstrap audit first.
- The target org can authenticate through Salesforce CLI browser login.
- Data Cloud is provisioned in the target org.
- The operator can deploy External Client App metadata and authorize the repo-owned `CommandCenterAuth` app.
- The target org allows `cdp_ingest_api` scope for the intended Data Cloud user.
- A shared Data Cloud Ingestion API connector exists in the org, or the operator can create it in Data Cloud Setup.
- For the simplest full path, the dataset is manifest-backed. The repo's most proven SDM automation path starts from a manifest, not a bare CSV.

## Exact steps

1. Run the machine audit if the workspace or machine is new.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap\setup-workspace.ps1
```

2. Authenticate to the org with the standard Salesforce alias.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\login-web.ps1 -Alias STORM_TABLEAU_NEXT -InstanceUrl https://your-domain.my.salesforce.com -SetDefault
```

3. Deploy the repo-owned `CommandCenterAuth` app and bootstrap the dedicated Data Cloud alias.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\setup-command-center-connected-app.ps1 -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -LaunchLogin
```

4. Validate the Data Cloud token exchange before any stream or upload work.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-get-access-token.ps1 -AsJson
```

The result should show the dedicated Data Cloud alias as `salesforceAlias` and normally `salesforce-cli-session` as `tokenSource`.

5. Confirm the org has one shared Ingestion API connector in Data Cloud Setup.

- For brand-new orgs, the preferred shared connector name is `command_center_ingest_api`.
- `setup-command-center-connected-app.ps1` will save that generic connector name into `notes/registries/salesforce-orgs.json` if the org row does not already have `dataCloudSourceName`.
- If the org uses a different connector name, save that non-secret value in the org registry or pass `-SourceName` explicitly on later commands.

6. Prefer the manifest-backed dataset path for the full workflow.

- If the dataset already has a manifest, continue.
- If the user only has a CSV, the repo can still upload it, but the most proven full SDM path is manifest-backed. For CSV-only work, use `playbooks/set-up-data-cloud-ingestion-target.md` and `scripts/salesforce/data-cloud-upload-csv.ps1`, then stop before SDM or create a manifest-backed dataset first.

7. Run guided manifest setup so the repo registers manifest-derived targets and validates Data Cloud auth in one pass.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-guided-manifest-setup.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -Alias STORM_TABLEAU_NEXT_DC -LoginUrl https://your-domain.my.salesforce.com -SourceName command_center_ingest_api -TargetKeyPrefix sunrun -ObjectNamePrefix sunrun -SetDefault
```

8. Bootstrap or reconcile the manifest streams. This is the step that registers compatible schemas, creates or resolves streams, and waits for active DLOs.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-create-manifest-streams.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT_DC -SourceName command_center_ingest_api -ObjectNamePrefix sunrun
```

9. Review `salesforce/generated/<sourceName>/provisioning-state.json` and confirm the DLOs are `ACTIVE`.

10. Upload the manifest dataset once the registry and live stream state are aligned.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-manifest.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetKeyPrefix sunrun
```

11. Confirm the upload results or inspect failed jobs.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-list-jobs.ps1 -TargetKey sunrun-projects
```

12. Discover the Tableau Next workspace inventory, then register a stable target for the intended workspace.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\list-next-workspaces.ps1 -TargetOrg STORM_TABLEAU_NEXT
powershell -ExecutionPolicy Bypass -File .\scripts\tableau\register-next-target.ps1 -TargetKey sunrun-sdm -TargetOrg STORM_TABLEAU_NEXT -WorkspaceId 1DyKZ000000kA8f0AE -Purpose 'Primary Tableau Next workspace'
```

13. Dry-run the authenticated-to-SDM orchestration first. This builds the semantic-model spec and request from the manifest plus active DLO identities without applying the model yet.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\orchestrate-authenticated-to-sdm.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -TableauNextTargetKey sunrun-sdm -ModelApiName Sunrun_Semantic -ModelLabel 'Sunrun Semantic' -SkipAuthAppDeploy -SkipUpload
```

14. Apply the semantic model once the dry-run state is clean.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\orchestrate-authenticated-to-sdm.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -TableauNextTargetKey sunrun-sdm -ModelApiName Sunrun_Semantic -ModelLabel 'Sunrun Semantic' -SkipAuthAppDeploy -SkipUpload -ApplySemanticModel
```

15. Treat the current SDM boundary precisely.

- This path creates or updates the base semantic model and manifest relationships.
- Calculated fields and semantic metrics are still a separate follow-on step after base model creation.

## Validation

- `data-cloud-get-access-token.ps1 -AsJson` resolves through the dedicated Data Cloud alias.
- `notes/registries/salesforce-orgs.json` contains the org alias plus `dataCloudClientId`, and ideally `dataCloudSourceName`.
- `notes/registries/data-cloud-targets.json` contains one target per manifest table.
- `salesforce/generated/<sourceName>/provisioning-state.json` exists and shows `ACTIVE` DLO status for the provisioned streams.
- Manifest upload returns job ids and terminal states instead of stale-target or missing-auth failures.
- `orchestrate-authenticated-to-sdm.ps1` writes a readiness state file under `tmp/`.
- When `-ApplySemanticModel` is used, the orchestration state reports an applied semantic model and persisted relationships.

## Failure modes

- The normal org alias is reused for Data Cloud auth and the dedicated alias split is lost.
- `CommandCenterAuth` deploys, but the user still cannot authorize `cdp_ingest_api`.
- The Ingestion API connector does not exist in the org, so auth succeeds but stream bootstrap fails.
- The dataset is CSV-only with no manifest, so the simplest full SDM path is not yet available.
- A connector schema already exists but is incompatible with the manifest-derived schema, so stream bootstrap stops instead of mutating the live connector incorrectly.
- Upload jobs fail because the stream objects are stale, incomplete, or not yet `ACTIVE`.
- The Tableau Next workspace routing is ambiguous because no stable target or workspace selector was provided.
- The user expects `_clc` or `_mtc` assets immediately, but the current orchestration publishes only the base model and relationships.

## Cleanup or rollback

- Remove incorrect request payloads from `tmp/`.
- Refresh manifest-derived target rows by rerunning guided manifest setup instead of editing dataset-derived fields by hand.
- Rerun stream bootstrap if the live stream object names or accepted DLO identities change.
- Re-register the Tableau Next target if the workspace selection changes.
- If the workflow stops at SDM dry-run, keep the generated spec and request artifacts for inspection, then rerun with `-ApplySemanticModel` after the blocker is fixed.

## Commands and links

- `scripts/bootstrap/setup-workspace.ps1`
- `scripts/salesforce/login-web.ps1`
- `scripts/salesforce/setup-command-center-connected-app.ps1`
- `scripts/salesforce/data-cloud-login-web.ps1`
- `scripts/salesforce/data-cloud-get-access-token.ps1`
- `scripts/salesforce/data-cloud-guided-manifest-setup.ps1`
- `scripts/salesforce/data-cloud-create-manifest-streams.ps1`
- `scripts/salesforce/data-cloud-upload-manifest.ps1`
- `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1`
- `scripts/tableau/register-next-target.ps1`
- `notes/registries/salesforce-orgs.json`
- `notes/registries/data-cloud-targets.json`
- `notes/registries/tableau-next-targets.json`
- `playbooks/set-up-command-center-connected-app.md`
- `playbooks/guided-data-cloud-manifest-setup.md`
- `playbooks/upload-manifest-dataset-to-data-cloud.md`
- `playbooks/prepare-tableau-next-semantic-model.md`