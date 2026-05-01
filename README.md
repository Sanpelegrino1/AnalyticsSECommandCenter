# AnalyticsSECommandCenter

This repository is a Windows-first operations workspace for repeated Salesforce and Tableau Cloud work. It is designed to reduce login friction, keep repeated demo-org setup fast, and give future agents a stable path instead of re-deriving the workflow every time.

## What this workspace does

- Keeps Salesforce org auth alias-driven and browser-first.
- Supports repeatable Salesforce Data Cloud CSV uploads through the Ingestion API bulk job flow.
- Keeps Tableau Cloud interaction scripted and repeatable with PAT auth stored only in local environment files or user environment variables.
- Adds a repo-native Slack integration surface for shared MCP connectivity and future Slack-side deployment work without mixing in Slack admin setup.
- Exposes common operations through VS Code tasks and PowerShell wrappers.
- Maintains a starter skill bank and a rule for extracting repeated workflows into durable skills.
- Includes a machine bootstrap script so the same repo can be cloned onto another Windows machine and set up with minimal manual work.

## Day-to-day entry points

Use one of these first:

1. Open `AnalyticsSECommandCenter.code-workspace` in VS Code.
2. Run the task `Bootstrap: Audit workspace machine`.
3. Fill in `.env.local` if you need Tableau Cloud automation.
4. Use the tasks or scripts below for daily work.

Primary operational entry points:

- `scripts/bootstrap/setup-workspace.ps1`
- `playbooks/publish-data.md`
- `scripts/salesforce/login-web.ps1`
- `skills/new-org-data-cloud-to-sdm.md`
- `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1`
- `scripts/salesforce/list-orgs.ps1`
- `scripts/salesforce/set-default-org.ps1`
- `scripts/salesforce/run-soql.ps1`
- `scripts/salesforce/retrieve-metadata.ps1`
- `scripts/salesforce/deploy-metadata.ps1`
- `scripts/salesforce/data-cloud-upload-csv.ps1`
- `scripts/salesforce/data-cloud-create-manifest-streams.ps1`
- `scripts/salesforce/data-cloud-upload-manifest.ps1`
- `scripts/salesforce/data-cloud-list-jobs.ps1`
- `scripts/tableau/auth-status.ps1`
- `scripts/tableau/list-projects.ps1`
- `scripts/tableau/list-content.ps1`
- `scripts/tableau/publish-file.ps1`
- `slack/README.md`
- `skills/INDEX.md`

## Auth strategy

### Salesforce

Use `sf org login web` through `scripts/salesforce/login-web.ps1`.

- The browser flow handles authentication.
- Salesforce CLI stores auth material locally in its own secure auth store.
- This repo stores only non-secret metadata in `notes/registries/salesforce-orgs.json`.
- Reuse aliases aggressively. That is the main friction reducer.
- Keep standard org-access aliases separate from Data Cloud publishing aliases.

Example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\login-web.ps1 -Alias DEMO_FINANCE -InstanceUrl https://login.salesforce.com -Purpose "Finance demo org" -SetDefault
```

### Tableau Cloud

Use PAT auth with local-only configuration.

- Put `TABLEAU_PAT_NAME` and `TABLEAU_PAT_SECRET` in `.env.local` or user environment variables.
- Put only non-secret target metadata in `notes/registries/tableau-targets.json`.
- Each script signs in, performs the requested operation, and signs out.

Example local-only config:

```powershell
TABLEAU_SERVER_URL=https://prod-useast-a.online.tableau.com
TABLEAU_SITE_CONTENT_URL=my-site
TABLEAU_DEFAULT_TARGET=default
TABLEAU_PAT_NAME=your_pat_name
TABLEAU_PAT_SECRET=your_pat_secret
```

### Salesforce Data Cloud

Use the Data Cloud scripts to bootstrap manifest-driven schema and stream provisioning after an admin has created the Ingestion API connector, then use the bulk ingestion scripts for uploads.

Treat the Ingestion API connector as org-scoped shared infrastructure, not dataset-scoped configuration.

- Put Data Cloud secrets only in `.env.local` or user environment variables.
- Store only non-secret connector and object metadata in `notes/registries/data-cloud-targets.json`.
- Store the org's shared publish connector name in `notes/registries/salesforce-orgs.json` as `dataCloudSourceName` once it is known, so future dataset publishes do not guess a connector name from the dataset.
- For a brand new org, the generic shared connector name should be `command_center_ingest_api`.
- The repo supports two local auth patterns: direct `DATACLOUD_ACCESS_TOKEN` injection, or a refresh-token flow that exchanges a Salesforce token for a Data Cloud token.
- The repo-owned auth app is `CommandCenterAuth`; the repo should not depend on pre-existing external client apps from an org.
- Preferred interactive model: use a dedicated Salesforce CLI alias for Data Cloud publishing and let `DataCloud.Common.ps1` reuse that CLI session for token exchange.
- Bootstrap order matters: normal Salesforce login first, then `setup-command-center-connected-app.ps1`, then `data-cloud-login-web.ps1`, then `data-cloud-get-access-token.ps1`.
- Do not overwrite the standard Salesforce org alias with the Data Cloud login. Keep a separate alias such as `ORG_ALIAS_DC` and set `DATACLOUD_SALESFORCE_ALIAS` or the target registry's `salesforceAlias` to that value.
- Data Cloud auth resolution does not inherit `SF_DEFAULT_ALIAS`; the dedicated alias must come from `DATACLOUD_SALESFORCE_ALIAS` or the target registry.
- `setup-command-center-connected-app.ps1 -LaunchLogin` now requires a separate Data Cloud alias and will fail fast if you try to reuse the normal org alias.

Example local-only config:

```powershell
DATACLOUD_DEFAULT_TARGET=orders-demo
DATACLOUD_LOGIN_URL=https://login.salesforce.com
DATACLOUD_CLIENT_ID=your_connected_app_client_id
DATACLOUD_CLIENT_SECRET=your_connected_app_client_secret
DATACLOUD_REFRESH_TOKEN=your_refresh_token
```

The refresh-token values above are fallback-only for unattended or constrained scenarios. The preferred interactive path does not require storing those secrets when the dedicated Data Cloud alias is available in Salesforce CLI.

Recommended alias split for one org:

```powershell
SF_DEFAULT_ALIAS=STORM_TABLEAU_NEXT
DATACLOUD_SALESFORCE_ALIAS=STORM_TABLEAU_NEXT_DC
```

Example upload:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-csv.ps1 -TargetKey orders-demo -CsvPath .\tmp\orders.csv
```

The default upload path now submits the Data Cloud job and returns immediately. Use `-WaitForCompletion:$true` only when you intentionally want blocking validation on one table or one manifest run.

## Machine setup

Run the audit first:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap\setup-workspace.ps1
```

If something required is missing, let the repo install what it can:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap\setup-workspace.ps1 -InstallMissing
```

What the bootstrap verifies:

- Git
- VS Code and `code` CLI
- GitHub Copilot Chat extension
- Salesforce CLI and `sfdx` compatibility path
- Node.js LTS
- Python 3.11+
- `curl.exe`
- A supported JDK for Salesforce VS Code features
- REST, YAML, dotenv, XML, and Markdown support extensions

## Salesforce workflow map

Useful scripts:

- Login and registry update: `scripts/salesforce/login-web.ps1`
- Org registry write: `scripts/salesforce/register-org.ps1`
- Org list: `scripts/salesforce/list-orgs.ps1`
- Default org switch: `scripts/salesforce/set-default-org.ps1`
- Open org or setup surfaces: `scripts/salesforce/open-org.ps1`, `scripts/salesforce/open-setup-surface.ps1`
- SOQL export: `scripts/salesforce/run-soql.ps1`
- Metadata retrieve/deploy: `scripts/salesforce/retrieve-metadata.ps1`, `scripts/salesforce/deploy-metadata.ps1`
- Snapshot aliases: `scripts/salesforce/snapshot-aliases.ps1`

## Data Cloud workflow map

Useful scripts:

- Deploy the repo-owned auth app and optionally launch auth: `scripts/salesforce/setup-command-center-connected-app.ps1`
- Browser login with a custom Data Cloud-scoped connected app: `scripts/salesforce/data-cloud-login-web.ps1`
- Target registry write: `scripts/salesforce/data-cloud-register-target.ps1`
- Manifest-based target registry write: `scripts/salesforce/data-cloud-register-manifest-targets.ps1`
- Auth check without exposing tokens by default: `scripts/salesforce/data-cloud-get-access-token.ps1`
- CSV inspection and preflight: `scripts/salesforce/data-cloud-inspect-csv.ps1`
- Manifest schema draft for operator review: `scripts/salesforce/data-cloud-generate-schema.ps1`
- Manifest-to-metadata generation into a reviewable local folder: `scripts/salesforce/data-cloud-generate-ingest-metadata.ps1`
- Manifest bootstrap that reuses the same schema inference before live schema and stream registration, DLO activation checks, registry sync, and local provisioning-state output: `scripts/salesforce/data-cloud-create-manifest-streams.ps1`
- Manifest-and-provisioning-report semantic-model spec builder for already-bootstrapped datasets: `scripts/salesforce/build-manifest-semantic-model-spec.ps1`
- Bulk CSV upload and optional wait: `scripts/salesforce/data-cloud-upload-csv.ps1`
- Manifest-based batch upload: `scripts/salesforce/data-cloud-upload-manifest.ps1`
- Job list, job detail, and cleanup: `scripts/salesforce/data-cloud-list-jobs.ps1`, `scripts/salesforce/data-cloud-get-job.ps1`, `scripts/salesforce/data-cloud-abort-job.ps1`

Schema inference now has two roles:

- `data-cloud-generate-schema.ps1` remains the standalone review helper for operators.
- `data-cloud-create-manifest-streams.ps1` uses the same shared CSV validation and field inference path automatically as part of the bootstrap flow.

Predictable generated paths:

- `data-cloud-generate-schema.ps1` defaults to `salesforce/generated/<dataset-or-manifest-name>/<dataset-or-manifest-name>-ingestion-api-schema.yaml`.
- `data-cloud-generate-ingest-metadata.ps1` defaults to `salesforce/generated/<sourceName>/` so the generated metadata is reviewable before deployment.
- Pass `-OutputPath` or `-OutputRoot` only when you intentionally want a different review or deployment location.

New org prerequisites that must be true before this workflow will work:

1. Salesforce Data Cloud is provisioned in the org.
2. External Client App metadata deployment is allowed in the org.
3. The operator can deploy metadata and manage External Client Apps.
4. The repo-owned `CommandCenterAuth` external client app is deployed.
5. The app's OAuth policy allows self-authorization for the users who will log in.
6. The login user can authorize scopes that include `cdp_ingest_api`.
7. A shared Data Cloud Ingestion API connector exists for the org.
8. The tenant endpoint and source name are known, and the generated or live object names can be recorded in `notes/registries/data-cloud-targets.json`.
9. If you plan to upload immediately, connector-specific `objectEndpoint` values must either already be in the registry or be discoverable by the manifest stream bootstrap.
10. If the org uses additional security controls, localhost callback auth for Salesforce CLI must be allowed.

Expected operating model:

Phase 1: bootstrap the org once.

1. Log into Salesforce with `scripts/salesforce/login-web.ps1` using the standard org alias.
2. Deploy the repo-owned auth app with `scripts/salesforce/setup-command-center-connected-app.ps1` using that standard org alias.
3. In Salesforce Setup, confirm the app is visible and that the intended users can authorize it.
4. In Data Cloud Setup, create or validate one shared Ingestion API connector for the org.
5. Save that connector name in `notes/registries/salesforce-orgs.json` as `dataCloudSourceName` for the org alias so later dataset publishes can reuse it automatically.
6. Log into `scripts/salesforce/data-cloud-login-web.ps1` with a separate Data Cloud alias backed by `CommandCenterAuth`.

Phase 2: publish any new dataset through that shared connector.

1. Register the non-secret target metadata in `notes/registries/data-cloud-targets.json`.
2. Run `scripts/salesforce/data-cloud-get-access-token.ps1 -AsJson` and confirm the reported `tokenSource` and `salesforceAlias`.
3. Inspect the CSV, or for a manifest dataset generate the review schema and review metadata locally.
4. Run `scripts/salesforce/data-cloud-create-manifest-streams.ps1` to create or reuse streams and wait for `ACTIVE` DLOs.
5. For Tableau Next, build the semantic-model spec from `salesforce/generated/<sourceName>/provisioning-state.json` with `scripts/salesforce/build-manifest-semantic-model-spec.ps1`, then apply it with `scripts/tableau/upsert-next-semantic-model.ps1 -Apply`.

Manifest compatibility notes:

- The manifest normalizer now supports both the newer nested publish-contract shape and older top-level `tables` plus `joinPaths` manifests.
- If an older manifest omits `fileName`, the repo assumes `<tableName>.csv` in the manifest directory.
4. For a manifest dataset, run `scripts/salesforce/data-cloud-create-manifest-streams.ps1` to register compatible schemas, create or reconcile streams, wait for `ACTIVE` DLO status, sync matching registry targets, and emit `salesforce/generated/<sourceName>/provisioning-state.json`.
5. Upload the CSV and wait for `JobComplete` or handle `Failed`.

When a script needs `SourceName`, it should prefer this order:

1. Explicit `-SourceName` passed by the operator.
2. `DATACLOUD_SOURCE_NAME` from local environment.
3. `dataCloudSourceName` saved for the org in `notes/registries/salesforce-orgs.json`.
4. A previously registered manifest target for the same dataset.
5. A unique live Ingest API connector discovered in the org.
6. Only then a dataset-derived fallback, and only when no better org-scoped signal exists.

Storm still uses the legacy connector name `sunrun_ingest_api`, which is why its org registry overrides the generic default. That name is historical state, not the naming standard for new orgs.

Example browser login plus immediate validation:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-login-web.ps1 -Alias STORM_TABLEAU_NEXT_DC -InstanceUrl https://your-domain.my.salesforce.com -ValidateAfterLogin
```

To bootstrap the repo-owned auth app first:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\setup-command-center-connected-app.ps1 -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -LaunchLogin
```

If you want a single operator-facing reference for this sequence, use `playbooks/set-up-command-center-connected-app.md`.

What a fresh org still needs configured outside this repo:

- Data Cloud enabled and licensed.
- External Client App Manager available and deployment of External Client App metadata allowed.
- Ingestion API connector created in Data Cloud Setup.
- Any metadata deployment of the generated local source, if you want the contents of `salesforce/generated/<sourceName>/` pushed into the org through the Salesforce metadata workflow.
- User permissions that allow Data Cloud ingestion operations and app authorization.
- Network and session controls that do not block the localhost OAuth callback used by Salesforce CLI.

The underlying Salesforce DX project stays in `salesforce/` and the new wrappers are deliberately thin so the existing metadata workflow remains intact.

## Tableau workflow map

Useful scripts:

- Register or validate a Tableau target: `scripts/tableau/auth-bootstrap.ps1`
- Auth status: `scripts/tableau/auth-status.ps1`
- Set default target: `scripts/tableau/set-target.ps1`
- List projects: `scripts/tableau/list-projects.ps1`
- List content: `scripts/tableau/list-content.ps1`
- Inspect content: `scripts/tableau/inspect-content.ps1`
- Publish workbook or datasource: `scripts/tableau/publish-file.ps1`
- Snapshot target registry: `scripts/tableau/snapshot-targets.ps1`

## Tableau Next semantic-model status

This repo now has Tableau Next workspace discovery, semantic-model inspection, and a supported semantic-model helper that can build and apply manifest-driven models through the public semantic-layer REST APIs.

## Authenticated-to-SDM orchestration

This repo now has a cross-phase orchestration surface at `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1`.

What it automates after authentication:

- Verifies standard Salesforce auth and deploys or re-verifies `CommandCenterAuth`.
- Refreshes manifest-derived Data Cloud targets without manual registry edits.
- Validates Data Cloud token exchange, connector availability, stream reconciliation, accepted object identities, and connector-specific `objectEndpoint` capture.
- Optionally uploads the manifest or selected manifest tables.
- Resolves or registers a Tableau Next target from live workspace discovery.
- Inspects a pinned semantic model when one exists.
- Builds a manifest-driven semantic-model spec from live workspace context, CSV field profiles, and active Data Lake Object identities.
- Creates or updates the semantic model through `/services/data/v66.0/ssot/semantic/models`.
- Creates or updates manifest relationships through `/services/data/v66.0/ssot/semantic/models/{modelApiName}/relationships`.
- Emits a machine-readable readiness state with one of these classifications:
	`ReadyForFullAutomation`, `ReadyThroughDryRunOnly`, `BlockedByOrgConfiguration`, `BlockedByPermission`, `BlockedByExternalApiLimitation`.

Default current boundary:

- The authenticated-to-SDM path is repo-native through supported semantic-model create and relationship apply.
- Data Cloud connector creation is still outside repo control and remains an org-setup prerequisite.

Current closest real meaning of zero-touch after authentication:

- After a usable standard Salesforce CLI session exists, the repo can refresh manifest-backed targets, validate Data Cloud token exchange, reconcile streams, derive stable DLO identities, resolve or register the Tableau Next target, generate the SDM payload, and apply the semantic model plus relationships without manual registry edits or hand-built request payloads.
- This is not yet proven as a cold-start one-browser-auth experience for a brand-new org because the standard Salesforce org alias must already exist, and Data Cloud connector creation still remains outside repo control.

Current stance:

- Treat Tableau Next as a layer that starts only after Salesforce Data Cloud ingestion is stable for the dataset and org.
- Reuse the existing Salesforce CLI alias model, local-only secret handling, and registry-backed metadata patterns instead of importing the upstream Claude or Python workflow.
- Use `playbooks/prepare-tableau-next-semantic-model.md` as the local starter workflow and roadmap for what can be done now, what still needs design, and what still needs new automation.

Available read-only wrappers today:

- `scripts/tableau/list-next-workspaces.ps1`
- `scripts/tableau/list-next-semantic-models.ps1`
- `scripts/tableau/register-next-target.ps1`
- `scripts/tableau/inspect-next-target.ps1`
- `scripts/tableau/inspect-next-semantic-model.ps1`
- `scripts/tableau/upsert-next-semantic-model.ps1`
- `notes/registries/tableau-next-targets.json`

Minimum non-secret Tableau Next target shape:

- `key`: local registry key for the target.
- `targetOrg`: Salesforce alias used for the Tableau Next discovery session.
- `workspaceId`: stable workspace identifier from `list-next-workspaces.ps1`.
- `workspaceDeveloperName`: human-check field from discovery so workspace identity is not just an opaque id.

Optional proven fields:

- `workspaceLabel`: operator-facing label from workspace discovery.
- `semanticModelId`: existing semantic-model id from `list-next-semantic-models.ps1` when you want to inspect or later target an existing model instead of a creation-only workspace.
- `workspaceAssetId`: matching `AnalyticsWorkspaceAsset` id for that existing semantic model.
- `assetUsageType`: current semantic-model usage classification from discovery.

## Slack integration

This repo now has a dedicated Slack integration surface under `slack/`.

Current stance:

- Keep Slack workspace administration, app provisioning, and org-level policy changes in the separate Slack admin repo.
- Use this repo for shared MCP connectivity, operator guidance, and any future repo-native Slack deployment or content-publish helpers.
- Keep Slack secrets and shared server details out of tracked files.

Current entry points:

- `slack/README.md`
- `slack/mcp/README.md`
- `.vscode/mcp.json`

The shared MCP configuration is workspace-scoped so the team can discover the Slack server from this repo, but the actual server URL is supplied through VS Code's MCP input storage on first use rather than being committed.

What still cannot be inferred automatically:

- A stable semantic-model name or richer model detail beyond the asset inventory row.
- Visualization, dashboard, and teardown relationships.

Current write boundary:

- `upsert-next-semantic-model.ps1` owns the local semantic-model spec shape, builds supported semantic-model request bodies from manifest-derived object mappings, and can apply them live.
- Live create uses the supported semantic-model REST endpoint and resolves relationships against the created model's real semantic definition and field API names before writing joins through the child `relationships` resource.
- The helper emits inspectable request artifacts under `tmp/` even when `-Apply` is not requested, so operators can still review the generated body before a live write.

Recommended target validation flow:

1. Discover workspaces with `list-next-workspaces.ps1`.
2. Optionally discover existing semantic models in that workspace with `list-next-semantic-models.ps1`.
3. Register the target with `register-next-target.ps1` using the proven workspace id and optional semantic-model id.
4. Re-run `inspect-next-target.ps1` before any later creation work to confirm the workspace still exists and any pinned semantic model still resolves.
- `scripts/tableau/list-next-semantic-models.ps1`

Missing local automation today:

- Visualization and dashboard discovery wrappers.
- Semantic-model teardown scripts.
- Tableau Next troubleshooting notes grounded in local scripts and error handling.

## Skills system

The workspace skill bank lives in `skills/`.

Rules:

- After two successful runs with substantially the same steps, extract or update a skill.
- On the third run without meaningful variation, use the skill as the default path.
- Skills must remain concrete. If a script or task exists, the skill should reference it rather than restating a hand-built workaround.

Read these first:

- `skills/INDEX.md`
- `skills/RULES.md`
- `.github/copilot-instructions.md`

## Registries and local state

Tracked, non-secret files:

- `notes/registries/salesforce-orgs.json`
- `notes/registries/data-cloud-targets.json`
- `notes/registries/tableau-targets.json`

Ignored local-only files:

- `.env.local`
- `.env`
- `tmp/`

## Recommended first-run sequence on a new machine

1. Clone the repo.
2. Open `AnalyticsSECommandCenter.code-workspace`.
3. Run `Bootstrap: Audit workspace machine`.
4. Run `Bootstrap: Install missing prerequisites` if needed.
5. Copy `.env.example` to `.env.local` if the bootstrap did not already do it.
6. Fill in Tableau settings only if you need Tableau automation.
7. Fill in Data Cloud settings only if you need Data Cloud ingestion automation.
8. Run `Salesforce: Login web and register alias`.
9. Run `Tableau: Auth status` after you set your PAT values.

## Supporting docs

- `playbooks/bootstrap-new-machine.md`
- `playbooks/add-demo-org.md`
- `playbooks/run-authenticated-to-sdm.md`
- `playbooks/set-up-command-center-connected-app.md`
- `playbooks/data-cloud-upload-csv.md`
- `playbooks/upload-manifest-dataset-to-data-cloud.md`
- `playbooks/set-up-data-cloud-ingestion-target.md`
- `notes/evaluations/salesforce-auth-strategy.md`
- `notes/evaluations/README.md`
- `playbooks/rotate-tableau-pat.md`
- `prompts/new-machine-setup.md`
- `prompts/extract-skill-from-repeated-workflow.md`
