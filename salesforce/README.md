# Pulse Assistant Salesforce DX Workspace

This folder contains the Salesforce-specific workspace assets that were moved out of the app root during repo cleanup.

This repo now includes a standard Salesforce DX project scaffold for working against existing orgs from VS Code with the modern Salesforce CLI (`sf`). The setup is optimized for practical source retrieval, editing, diffing, deployment, and org interaction without forcing a scratch-org-first workflow.

Active DSB prompt authoring does not live in this workspace. The current runtime prompt source of truth is repo-local under `Vertex Agent Prompt Templates/`. The retired Apex prompt-runtime gateway assets were moved under `Salesforce Apex Legacy - No Longer Used/`, and the old prompt-template workflow scripts plus prompt-template metadata mirrors were removed, so this workspace stays focused on broader non-legacy Salesforce DX tasks.

It is intentionally org-first and metadata-first:

- retrieve metadata from an existing org into source format
- edit metadata locally in VS Code
- deploy source back to an org
- diff and review changes in Git and VS Code
- open the org quickly from the CLI

It does not pretend that every Salesforce experience is better in code than in Setup. Some assets remain partially UI-driven, and those boundaries are called out below.

## What Was Created

- `sfdx-project.json` for a standard DX source project
- `force-app/main/default` as the primary source-format folder
- `manifest/package.xml` for broad org-first retrieval and deployment
- `scripts/*.ps1` helper scripts for common workflows
- `package.json` scripts for the same workflows
- `.vscode/extensions.json` and `.vscode/settings.json` for a minimal VS Code setup

## Legacy Separation

The repo now keeps the retired Salesforce/Apex LLM workflow under `Salesforce Apex Legacy - No Longer Used/`.

That legacy area contains:

- Apex prompt gateway classes and prompt-job object metadata
- prompt-flow assets tied to the retired Apex runtime
- mirrored Salesforce-backed prompt bodies and older prompt sources

Removed during retirement cleanup:

- prompt publish and prompt-retrieval scripts
- retrieved `GenAiPromptTemplate` metadata mirrors
- production prompt-template snapshot folders

Use that folder only for audits, rollback planning, or explicit retirement cleanup work.

## Prerequisites

Install these before using the workspace:

1. Salesforce CLI (`sf`)
2. Visual Studio Code
3. Salesforce Extension Pack for VS Code
4. Git

Windows install examples:

```powershell
winget install Salesforce.cli
winget install Microsoft.VisualStudioCode
winget install Git.Git
```

Cross-platform notes:

- macOS: use Homebrew or the official Salesforce installer.
- Linux: use the official Salesforce CLI install instructions for your distro.

Verify the CLI:

```powershell
sf --version
sf plugins
```

## Project Layout

```text
.
salesforce/
├─ force-app/
│  └─ main/
│     └─ default/
├─ manifest/
│  └─ package.xml
├─ scripts/
├─ sfdx-project.json
└─ README.md
```

## Authentication

### Web login

Use browser login for normal interactive development against an existing org.

PowerShell:

```powershell
.\scripts\auth-web.ps1 -Alias MY_SANDBOX_ALIAS -InstanceUrl https://YOUR_MY_DOMAIN_OR_LOGIN_HOST -SetDefault
```

NPM script:

```powershell
npm run auth:web
```

The package script contains placeholders. Replace `MY_SANDBOX_ALIAS` and `https://YOUR_MY_DOMAIN_OR_LOGIN_HOST` before relying on it for daily use, or use the PowerShell script with parameters.

Examples for real org URLs:

- Production or developer edition: `https://login.salesforce.com`
- Sandbox via My Domain: `https://YOUR_DOMAIN--YOUR_SANDBOX.sandbox.my.salesforce.com`
- My Domain production: `https://YOUR_DOMAIN.my.salesforce.com`

### Device login

This workspace includes an `auth:device` placeholder only as a documented boundary. The current documented modern `sf org login` command set exposes `web`, `jwt`, `sfdx-url`, and `access-token` login flows; it does not document a general `sf org login device` flow for standard org auth in the same command family.

Use one of these instead:

- `sf org login web` for interactive development
- `sf org login sfdx-url` for secure reusable auth URLs handled outside source control
- `sf org login jwt` for CI or non-interactive automation

### Display authenticated org details

```powershell
.\scripts\org-display.ps1 -TargetOrg MY_SANDBOX_ALIAS -Verbose
```

```powershell
npm run org:display
```

## Retrieving Metadata

### Retrieve the broad workspace manifest

This is the main org-first retrieval flow.

```powershell
.\scripts\retrieve-all.ps1 -TargetOrg MY_SANDBOX_ALIAS
```

```powershell
npm run retrieve:all
```

### Retrieve a specific manifest

```powershell
.\scripts\retrieve-manifest.ps1 -TargetOrg MY_SANDBOX_ALIAS -ManifestPath manifest/package.xml
```

```powershell
npm run retrieve:manifest -- --target-org MY_SANDBOX_ALIAS --manifest manifest/package.xml
```

### Retrieval strategy notes

- The included `manifest/package.xml` uses broad wildcard retrieval for common metadata-backed assets.
- `GenAiPromptTemplate` is a real Metadata API type, but this repo no longer keeps a repo-local prompt-template metadata mirror for DSB. Treat prompt-template work as historical archaeology unless a new explicit need reintroduces it.
- `CustomField` wildcard behavior can vary in practice by org shape and metadata surface. In day-to-day work, retrieving `CustomObject` metadata is often the more reliable way to bring object fields into source. If your org rejects the `CustomField` wildcard, remove that block and rely on `CustomObject` plus explicit targeted field retrieval.
- Profiles are intentionally omitted by default. Permission Sets are preferred because they are easier to maintain in source control.

If you need to inspect support in your actual org and CLI version:

```powershell
sf org list metadata-types --target-org MY_SANDBOX_ALIAS
sf org list metadata --metadata-type GenAiPromptTemplate --target-org MY_SANDBOX_ALIAS
```

## Deploying Metadata

### Deploy the full DX source tree

```powershell
.\scripts\deploy-all.ps1 -TargetOrg MY_SANDBOX_ALIAS
```

```powershell
npm run deploy:all
```

### Deploy a manifest selection

```powershell
.\scripts\deploy-manifest.ps1 -TargetOrg MY_SANDBOX_ALIAS -ManifestPath manifest/package.xml
```

```powershell
npm run deploy:manifest -- --target-org MY_SANDBOX_ALIAS --manifest manifest/package.xml
```

## Open the Org Quickly

```powershell
.\scripts\org-open.ps1 -TargetOrg MY_SANDBOX_ALIAS
```

```powershell
npm run org:open
```

Open a local Flow directly in Flow Builder:

```powershell
.\scripts\org-open.ps1 -TargetOrg MY_SANDBOX_ALIAS -SourceFile force-app/main/default/flows/YOUR_FLOW.flow-meta.xml
```

## Preview Diffs in VS Code

For day-to-day diffing, use built-in VS Code and Git features:

1. Open Source Control in VS Code.
2. Retrieve metadata from the org.
3. Edit local source under `force-app/main/default`.
4. Use the VS Code Git diff viewer to compare local edits.
5. Use file history or `git diff` for branch-aware review.

Useful commands:

```powershell
git status
git diff
git diff -- force-app/main/default/flows
```

## What Still Requires Salesforce UI

This workspace improves the DX workflow, but it does not replace all admin and builder surfaces.

- Flows: source retrieval and deployment work well, but Flow Builder is still better for some visual authoring and debugging.
- Connected Apps: metadata supports a lot, but some settings and lifecycle operations are still easier or only possible in Setup and App Manager.
- Legacy Prompt Templates: `GenAiPromptTemplate` metadata may still be inspectable in some orgs, but that workflow is historical in this repo and is not the supported path for current DSB prompt edits.
- Permissions: Permission Sets are source-manageable; user assignment still commonly happens through Setup or targeted CLI commands.
- Org settings and security posture: many org-wide settings still need Setup review even when metadata exists.

## Troubleshooting

### `sf` command not found

Install Salesforce CLI and restart your terminal:

```powershell
sf --version
```

### Retrieval fails for a metadata type

Common causes:

- the metadata type is not enabled in the org
- the logged-in user lacks metadata permissions
- the CLI/plugin version does not yet support the type cleanly in source format
- the org feature is enabled in UI but not exposed in Metadata API for that org shape

When this happens:

```powershell
sf org list metadata-types --target-org MY_SANDBOX_ALIAS
sf org list metadata --metadata-type Flow --target-org MY_SANDBOX_ALIAS
```

Then narrow retrieval scope or remove the failing type from `manifest/package.xml`.

### Legacy prompt-template metadata does not retrieve

Check:

- you are intentionally working on historical `GenAiPromptTemplate` metadata rather than current direct-runtime prompts
- Prompt Builder is enabled
- your user has access to Prompt Template management
- your org API version is recent enough

If you only need to change active DSB prompt behavior, stop here and edit the mapped files under `Vertex Agent Prompt Templates/` instead. If you are investigating the retired Apex prompt workflow, switch to `Salesforce Apex Legacy - No Longer Used/` explicitly rather than treating this workspace as the hot path.

### Source tracking confusion

This workspace is designed for manifest-based retrieve and deploy against existing orgs. Do not assume source tracking is available on every org type. It is commonly unavailable or unsuitable for production and many sandboxes.

### Profiles missing

That is intentional. Start with Permission Sets. Add Profile retrieval only if you have a specific proven need.

## Helper Scripts

PowerShell helpers live in `scripts/`:

- `auth-web.ps1`
- `auth-device.ps1`
- `retrieve-all.ps1`
- `retrieve-manifest.ps1`
- `deploy-all.ps1`
- `deploy-manifest.ps1`
- `org-open.ps1`
- `org-display.ps1`

## First-Time Getting Started

Use this exact order the first time:

```powershell
sf --version
.\scripts\auth-web.ps1 -Alias MY_SANDBOX_ALIAS -InstanceUrl https://YOUR_MY_DOMAIN_OR_LOGIN_HOST -SetDefault
.\scripts\org-display.ps1 -TargetOrg MY_SANDBOX_ALIAS
.\scripts\retrieve-all.ps1 -TargetOrg MY_SANDBOX_ALIAS
git status
```

After that, the normal loop is:

1. Retrieve from org.
2. Edit locally in `force-app/main/default`.
3. Review diffs in VS Code or Git.
4. Deploy back with `deploy-all.ps1` or `deploy-manifest.ps1`.