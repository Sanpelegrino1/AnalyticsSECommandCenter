# AnalyticsSECommandCenter

This repository is a Windows-first operations workspace for repeated Salesforce and Tableau Cloud work. It is designed to reduce login friction, keep repeated demo-org setup fast, and give future agents a stable path instead of re-deriving the workflow every time.

## What this workspace does

- Keeps Salesforce org auth alias-driven and browser-first.
- Supports repeatable Salesforce Data Cloud CSV uploads through the Ingestion API bulk job flow.
- Keeps Tableau Cloud interaction scripted and repeatable with PAT auth stored only in local environment files or user environment variables.
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
- `scripts/salesforce/login-web.ps1`
- `scripts/salesforce/list-orgs.ps1`
- `scripts/salesforce/set-default-org.ps1`
- `scripts/salesforce/run-soql.ps1`
- `scripts/salesforce/retrieve-metadata.ps1`
- `scripts/salesforce/deploy-metadata.ps1`
- `scripts/salesforce/data-cloud-upload-csv.ps1`
- `scripts/salesforce/data-cloud-upload-manifest.ps1`
- `scripts/salesforce/data-cloud-list-jobs.ps1`
- `scripts/tableau/auth-status.ps1`
- `scripts/tableau/list-projects.ps1`
- `scripts/tableau/list-content.ps1`
- `scripts/tableau/publish-file.ps1`
- `skills/INDEX.md`

## Auth strategy

### Salesforce

Use `sf org login web` through `scripts/salesforce/login-web.ps1`.

- The browser flow handles authentication.
- Salesforce CLI stores auth material locally in its own secure auth store.
- This repo stores only non-secret metadata in `notes/registries/salesforce-orgs.json`.
- Reuse aliases aggressively. That is the main friction reducer.

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

Use the Data Cloud bulk ingestion scripts for CSV uploads after an admin has created the Ingestion API connector and data stream.

- Put Data Cloud secrets only in `.env.local` or user environment variables.
- Store only non-secret connector and object metadata in `notes/registries/data-cloud-targets.json`.
- The repo supports two local auth patterns: direct `DATACLOUD_ACCESS_TOKEN` injection, or a refresh-token flow that exchanges a Salesforce token for a Data Cloud token.

Example local-only config:

```powershell
DATACLOUD_DEFAULT_TARGET=orders-demo
DATACLOUD_LOGIN_URL=https://login.salesforce.com
DATACLOUD_CLIENT_ID=your_connected_app_client_id
DATACLOUD_CLIENT_SECRET=your_connected_app_client_secret
DATACLOUD_REFRESH_TOKEN=your_refresh_token
```

Example upload:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-upload-csv.ps1 -TargetKey orders-demo -CsvPath .\tmp\orders.csv
```

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
- GitHub Copilot and Copilot Chat extensions
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

- Target registry write: `scripts/salesforce/data-cloud-register-target.ps1`
- Manifest-based target registry write: `scripts/salesforce/data-cloud-register-manifest-targets.ps1`
- Auth check without exposing tokens by default: `scripts/salesforce/data-cloud-get-access-token.ps1`
- CSV inspection and preflight: `scripts/salesforce/data-cloud-inspect-csv.ps1`
- Bulk CSV upload and optional wait: `scripts/salesforce/data-cloud-upload-csv.ps1`
- Manifest-based batch upload: `scripts/salesforce/data-cloud-upload-manifest.ps1`
- Job list and job detail: `scripts/salesforce/data-cloud-list-jobs.ps1`, `scripts/salesforce/data-cloud-get-job.ps1`

Expected operating model:

1. Create the Ingestion API connector and download the object endpoints in Data Cloud.
2. Create the Ingestion API data stream for the target object.
3. Register the non-secret target metadata in `notes/registries/data-cloud-targets.json`.
4. Put the auth secrets in `.env.local` or user environment variables.
5. Inspect the CSV.
6. Upload the CSV and wait for `JobComplete` or handle `Failed`.
7. For multi-table datasets, generate one target per manifest table and run the manifest upload script.

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
- `playbooks/data-cloud-upload-csv.md`
- `playbooks/upload-manifest-dataset-to-data-cloud.md`
- `playbooks/set-up-data-cloud-ingestion-target.md`
- `playbooks/rotate-tableau-pat.md`
- `prompts/new-machine-setup.md`
- `prompts/extract-skill-from-repeated-workflow.md`
