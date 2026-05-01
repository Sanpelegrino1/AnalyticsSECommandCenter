# Run Authenticated To SDM

## Purpose

Run the repo-native authenticated onboarding-to-SDM path with one orchestration command, capture a machine-readable readiness state, and stop early when org setup, permissions, or platform limits still block full automation.

## Inputs

- Manifest path
- Standard Salesforce org alias
- Dedicated Data Cloud alias for the same org
- Shared Data Cloud source name and naming prefix inputs for the manifest dataset
- Tableau Next workspace selector or saved target key
- Semantic-model API name and label
- Optional selected manifest tables if you want a narrower run

## Prerequisites

- The user can authenticate to the Salesforce org with Salesforce CLI.
- Data Cloud is licensed and provisioned if the manifest path will be exercised past auth and target registration.
- The manifest is the intended source of truth for the dataset.
- The manifest join graph and publish-contract relationships are accurate for the dataset you want to model.

## Exact Steps

1. Authenticate to the standard Salesforce org alias first.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\login-web.ps1 -Alias STORM_TABLEAU_NEXT -InstanceUrl https://your-domain.my.salesforce.com -SetDefault
```

2. Run the orchestration entry point.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\orchestrate-authenticated-to-sdm.ps1 -ManifestPath '.\Demos\Sunrun Demo\manifest.json' -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -SourceName sunrun_ingest_api -TargetKeyPrefix sunrun -ObjectNamePrefix sunrun2 -TableauNextTargetKey juju-demo-sdm -WorkspaceDeveloperName Juju_Demo -ModelApiName Juju_Demo_Semantic -ModelLabel 'Juju Demo Semantic'
```

3. Read the emitted readiness state under `tmp/<dataset>-authenticated-to-sdm-state.json`.

4. Add `-ApplySemanticModel` when you want the orchestration to create the semantic model and publish manifest relationships live through the supported semantic-layer REST endpoints.

5. Review the emitted semantic-model spec and request artifacts in `tmp/` when you want to inspect the generated field and relationship mapping before or after live apply.

6. Treat the current zero-touch boundary precisely: the path is proven after a usable standard Salesforce CLI session exists. It is not yet a proven one-browser cold-start for a brand-new org because connector creation is still outside repo control.

## Fast Split Path

Use this when stream bootstrap is ready but the dedicated Data Cloud alias still blocks upload, or when you want a deterministic SDM build from a manifest without rerunning the full orchestration.

1. Register manifest targets with `scripts/salesforce/data-cloud-register-manifest-targets.ps1`.
2. Bootstrap streams and DLOs with `scripts/salesforce/data-cloud-create-manifest-streams.ps1`.
3. Register or reuse a Tableau Next workspace target with `scripts/tableau/register-next-target.ps1`.
4. Build the manifest-based semantic-model spec from the live provisioning report with `scripts/salesforce/build-manifest-semantic-model-spec.ps1`.
5. Apply the model with `scripts/tableau/upsert-next-semantic-model.ps1 -Apply`.

This split path now supports older manifest shapes that only provide top-level `tables` and `joinPaths`; the normalizer will synthesize `files`, `publishContract.relationships`, and a root table automatically.

## Readiness Classifications

- `ReadyForFullAutomation`: the current run encountered no repo-local blockers and the supported semantic-model path is ready to apply.
- `ReadyThroughDryRunOnly`: the orchestration completed repo-local discovery and request generation, but the current run intentionally stopped before live semantic-model apply.
- `BlockedByOrgConfiguration`: the org is missing required setup such as the Data Cloud connector or stable workspace routing criteria.
- `BlockedByPermission`: the current user or alias lacks required auth or scope access.
- `BlockedByExternalApiLimitation`: the remaining blocker is a platform surface the repo still cannot prove or control, such as a missing Tableau Next REST capability outside semantic-model and relationship authoring.

## Validation

- The orchestration writes a machine-readable state file.
- Manifest-backed Data Cloud targets refresh without manual registry edits.
- Stream bootstrap reports reused or created streams plus `ACTIVE` DLO status.
- Tableau Next target resolution either reuses a saved target or registers one from live workspace discovery.
- The semantic-model spec and request outputs exist when the Tableau Next phase is reached.
- When `-ApplySemanticModel` is used, the state file shows an applied model id and persisted semantic relationships.

## Failure Modes

- The org can authenticate but cannot deploy or verify `CommandCenterAuth`.
- Data Cloud auth cannot resolve `cdp_ingest_api` scope for the dedicated alias.
- The Ingestion API connector does not exist in the org.
- Multiple Tableau Next workspaces are visible and no stable selector was provided.
- The manifest join contract does not match the active Data Lake Object field set.
- Older manifests omit `fileName` per table. The repo now falls back to `<tableName>.csv`, but mismatched on-disk file names will still break stream bootstrap.

## Cleanup or Rollback

- Remove or correct any wrong local request payloads under `tmp/`.
- Re-register the Tableau Next target if the workspace routing changed.
- Rerun the orchestration after fixing org setup or permissions; the Data Cloud manifest phases are designed to be idempotent.
