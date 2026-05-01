# Deterministic Dataset Publisher

One script. One dataset directory. One org. SDM published end to end.

## Problem

The current path from "I have a dataset folder" to "the SDM is live in the org" chains together 8+ PowerShell scripts. A single run in the last session took ~2 hours and required the operator to:

- Run auth twice (standard + Data Cloud) with OAuth timeouts
- Manually edit `salesforce-orgs.json` to add `dataCloudClientId`
- Manually edit `.env.local` to clear `DATACLOUD_SALESFORCE_ALIAS` so the refresh-token path wins
- Diagnose a `$ErrorActionPreference=Stop` + sf CLI stderr warning interaction
- Diagnose a strict-mode `objectEndpoint` property access bug
- Diagnose a registry preflight failure caused by `ObjectNamePrefix` mismatch between registration and stream bootstrap
- Re-register targets three separate times with different flag combinations
- Discover that the orchestrator wiped `.env.local` mid-run
- Find an existing SDM from a failed half-run and switch to Update mode
- Pass `-WhatIf:$false` / `-Confirm:$false` / both, none of which worked — ended up invoking via `& scriptname` to bypass `ShouldProcess` propagation from `Import-CommandCenterEnv`

None of this should be operator work. The inputs are "a directory and an org choice." Everything else is derivable.

## Objective

```
pwsh scripts/publish-dataset.ps1 -DatasetPath "Demos/<folder>"
```

Picks an org interactively, deploys CommandCenterAuth if absent, authenticates Data Cloud if absent, registers targets, bootstraps streams, uploads CSVs, creates/updates the SDM, validates it, writes a state JSON, exits.

Wall-clock target: < 3 minutes for an idempotent re-run, < 15 minutes for a cold run.

## Non-goals

- Replacing underlying scripts. We call them. We fix only the bugs that block determinism.
- Tableau Server publish (`.tdsx` → workbook). Stops at SDM.
- LLM / agent work. Plain script.
- New registry formats.

## Derivation rules

All naming flows from `manifest.datasetName` (or dataset folder name if absent). Nothing is asked of the user except the target org.

| Artifact | Rule | Example |
|---|---|---|
| `datasetKey` | kebab-slug(datasetName), max 60 chars | `sunrun-direct-pay-command-center2` |
| `sourceName` | `<shortSlug>_ingest_api`, max 40 chars | `sunrun_direct_pay_ingest_api` |
| `targetKeyPrefix` | shortSlug, max 12 chars, `[a-z0-9_]` | `sdp` |
| `objectNamePrefix` | **same value as targetKeyPrefix** (bug from session) | `sdp` |
| `modelApiName` | PascalCase + `_Semantic` | `SunrunDirectPayCommandCenter2_Semantic` |
| `modelLabel` | datasetName as-is | `Sunrun Direct Pay Command Center2` |
| `workspaceDeveloperName` | PascalCase + underscores | `Sunrun_Direct_Pay_Command_Center2` |
| `workspaceLabel` | datasetName | `Sunrun Direct Pay Command Center2` |
| `tableauNextTargetKey` | `<targetKeyPrefix>-sdm` | `sdp-sdm` |

Short slug rule: first letter of each word in `datasetName`, concatenated, lowercased, truncated to 12 chars. Collision detection checks existing registries; if collision, append numeric suffix `-2`, `-3`, etc. Persisted in a new field on the dataset's first Data Cloud target so subsequent runs reuse it deterministically.

Table definitions come from `manifest.tables[]`. `fileName` falls back to `<tableName>.csv` if missing. If `manifest.tables` is absent (older schema), enumerate CSVs in the directory and synthesize a minimal `tables` array.

## Phases

Script runs these in order. Each phase logs `[phase] start ... done (Ns)`. Failures exit non-zero and write a readiness blocker to the state JSON.

1. **Load & derive** — parse manifest, compute all derived names, show the user a one-screen summary ("publishing X to Y, creating Z, N tables"), prompt "Continue? [Y/n]" (skippable via `-NonInteractive`).
2. **Select org** — if `-OrgAlias` not passed, show numbered menu from `salesforce-orgs.json` + "add new org" option. "Add new" prompts for alias and instance URL, runs `login-web.ps1`, persists to registry.
3. **Verify Salesforce CLI session** — if `sf org display --target-org <alias>` fails or token is expired, run `login-web.ps1`.
4. **Ensure CommandCenterAuth** — query the org for the External Client App by name. If absent, invoke `setup-command-center-connected-app.ps1`. After deploy, compute `CommandCenterAuth<orgId>` client ID and upsert it into `salesforce-orgs.json` under the alias.
5. **Ensure Data Cloud auth** — attempt refresh-token exchange using the org-specific client ID. If it fails with `invalid_scope` or no refresh token is stored, run `data-cloud-login-web.ps1 -UseManualOAuth` (opens browser once). Persist resulting refresh token + exchange URL to `.env.local`. **Force `DATACLOUD_SALESFORCE_ALIAS` to empty** so the refresh-token path wins over the CLI session (session bug).
6. **Ensure ingest connector** — probe `/services/data/v62.0/ssot/connections?connectorType=IngestApi` for a connector matching derived `sourceName`. If absent, call `data-cloud-generate-ingest-metadata.ps1` to write `ExternalDataConnector` + `DataConnectorIngestApi` meta-xml under `salesforce/generated/<sourceName>/`, then `sf project deploy start --metadata-dir <that path> --target-org <alias>`, then poll the connections endpoint until present (cap 60s). **This is the step that blocked manual runs historically.** Metadata type is confirmed public (see `Org Setup/build1-automation-research.md:198`).
7. **Register manifest targets** — call `data-cloud-register-manifest-targets.ps1` with both `-TargetKeyPrefix` and `-ObjectNamePrefix` set to the same derived shortSlug, plus the tenant endpoint looked up from an existing target on the same connector or from the Data Cloud token exchange response.
8. **Bootstrap streams** — call `data-cloud-create-manifest-streams.ps1`. Idempotent by design (reuses compatible schemas).
9. **Re-register targets with live object names** — call the register script a second time so `objectName` and `objectEndpoint` match what stream bootstrap produced. (This is how the preflight check in `data-cloud-upload-manifest.ps1` stops complaining.)
10. **Upload CSVs** — call `data-cloud-upload-manifest.ps1` without `-WaitForCompletion` (default async). The ingest jobs take ~60s each and run in parallel on the Data Cloud side; waiting is a latency tax we don't need for the SDM step, which only needs `ACTIVE` DLOs.
11. **Ensure Tableau Next workspace** — query for `workspaceDeveloperName`. If exactly one match, use it. If none, create via `create-next-workspace.ps1`. If multiple, fail with the candidate list.
12. **Register Tableau Next target** — upsert `<targetKeyPrefix>-sdm` into `tableau-next-targets.json` with the workspace ID.
13. **Build semantic model spec** — call `build-manifest-semantic-model-spec.ps1`.
14. **Apply the model** — call `upsert-next-semantic-model.ps1 -Apply`. Invoke via `& scriptname` (not `-File`) so `ShouldProcess` behaves (session bug). Action = Auto so it creates on first run, updates on subsequent runs.
15. **Validate** — call `ssot/semantic/models/<apiName>/validate`. Write state JSON with `isValid`, phase timings, blockers, applied model ID, and relationship API names.

## State JSON shape

Written to `tmp/<datasetKey>-publish-state.json`:

```json
{
  "generatedAt": "...",
  "datasetPath": "...",
  "datasetName": "...",
  "orgAlias": "...",
  "derived": { "datasetKey": "...", "sourceName": "...", "targetKeyPrefix": "...", ... },
  "phases": [
    { "name": "selectOrg", "status": "ok", "elapsedSec": 0.1 },
    { "name": "commandCenterAuth", "status": "already-deployed", "elapsedSec": 1.2 },
    ...
  ],
  "tablesUploaded": [ { "tableName": "project", "jobId": "...", "state": "UploadComplete" }, ... ],
  "semanticModel": { "apiName": "...", "id": "...", "isValid": true, "relationshipApiNames": [...] },
  "totalElapsedSec": 47.3,
  "blockers": []
}
```

## Auth flow (the part that hurt last time)

The three auth modes in `DataCloud.Common.ps1`:
1. `DATACLOUD_ACCESS_TOKEN` direct (not used here)
2. Salesforce CLI session via `DATACLOUD_SALESFORCE_ALIAS`
3. Refresh-token exchange via `DATACLOUD_CLIENT_ID` + `DATACLOUD_REFRESH_TOKEN`

Mode 2 is evaluated before mode 3. Mode 2 fails when the CLI session was obtained via the standard DX connected app (no `cdp_ingest_api` scope). Mode 3 works when the refresh token was obtained via `CommandCenterAuth`. The session bug was: both were set, mode 2 ran first, failed, and error propagation bailed before mode 3 was tried.

**Fix in this script:** unset `DATACLOUD_SALESFORCE_ALIAS` in the child process environment for all phases that exchange into Data Cloud. Don't touch `.env.local` — just don't inherit that var. Mode 3 becomes the only path, and it's the one with `cdp_ingest_api` scope.

Secondary fix: if mode 3 fails with `invalid_scope`, run `data-cloud-login-web.ps1 -UseManualOAuth` once. Browser opens, user logs in, script captures code, exchanges for refresh token, writes to `.env.local`, retries. This is the only interactive prompt that cannot be eliminated (the platform requires a human at the OAuth consent screen the first time per org).

## Org identity

CommandCenterAuth's client ID embeds the org ID: `CommandCenterAuth<orgId18>`. After deploy, we read org ID from `sf org display --json` and compute the expected client ID. If it differs from what was stored in `salesforce-orgs.json`, update the registry.

## Idempotency checklist

Each phase must be safe to re-run.

- Targets: `data-cloud-register-manifest-targets.ps1` already upserts.
- Streams: `data-cloud-create-manifest-streams.ps1` already reuses compatible schemas.
- Upload: CSVs don't need to be idempotent at the stream level for this script to be deterministic — a second run creates another bulk job. If the user wants to skip, add `-SkipUpload` flag.
- Workspace: create-or-reuse.
- Model: `upsert-next-semantic-model.ps1` already supports Create/Update via `-Action Auto`.
- Validation: read-only.

## Bugs to fix in-place (minimum scope)

Each fix is a one-line or one-block change.

1. **`data-cloud-create-manifest-streams.ps1` line 409–412** — already patched this session (use `$updatedTarget.Contains(...)`). Keep.
2. **`DataCloud.Common.ps1` Get-SalesforceCliOrgSession** — set `$env:SF_SKIP_NEW_VERSION_CHECK='true'` before calling `sf` to prevent stderr update warnings tripping strict-mode callers.
3. **`orchestrate-authenticated-to-sdm.ps1`** — no fix. We're replacing its usage, not repairing it.
4. **`upsert-next-semantic-model.ps1`** — no fix. We invoke it via `&` operator to bypass `ShouldProcess` inheritance from `Import-CommandCenterEnv`.

No other upstream changes.

## Known risks, ranked by blast radius

### R1. Data Cloud ingest connector creation — AUTOMATABLE via metadata deploy.
**Update after code review.** I assumed this was manual. It's not. The repo already generates `ExternalDataConnector` + `DataConnectorIngestApi` meta-xml under `salesforce/generated/<sourceName>/` via `scripts/salesforce/data-cloud-generate-ingest-metadata.ps1`, and these deploy cleanly via `sf project deploy start --metadata-dir <path>` (confirmed in `Org Setup/build1-automation-research.md:198` — `ExternalDataConnector` is a public metadata type). The existing fast split path doesn't wire this together end-to-end because stream bootstrap assumes the connector already exists; that's a gap, not a platform limitation.

**Plan update — add phase 6a "Ensure ingest connector":** probe Data Cloud for a connector matching derived `sourceName`. If missing, generate metadata via `data-cloud-generate-ingest-metadata.ps1`, deploy it via `sf project deploy start`, poll `/services/data/v62.0/ssot/connections?connectorType=IngestApi` until the connector appears, then proceed. This turns the cold-start time from "manual Setup click path" to ~60 seconds of deploy + poll. No new manual step for fresh orgs.

### R2. Workspace creation on a fresh org.
`create-next-workspace.ps1` exists but may hit permission errors on orgs that haven't been fully provisioned for Tableau Next. **Mitigation:** detect the specific error and direct the user to run the PACE setup playbook first (`org-setup-tableau-next-pace` skill already exists).

### R3. Interactive browser login on first Data Cloud auth.
Cannot be eliminated — Salesforce OAuth consent requires a human the first time. **Mitigation:** only prompt once per org; persist refresh token so re-runs are silent.

### R4. Dataset name → slug collisions.
Two datasets named "Sales Pipeline" and "Sales Pipeline Q4" would both slug to `salespipeline`. **Mitigation:** before committing a derived slug, check existing targets for conflicts; if found and they belong to a different manifest path, append `-2`. Slug is persisted in the first target's `notes` so subsequent runs of the same dataset are stable.

### R5. `-Apply` + `ShouldProcess` + `Import-CommandCenterEnv` interaction.
`Import-CommandCenterEnv` uses `Set-Item Env:` which respects `$WhatIfPreference`. If the caller sets `-WhatIf`, no env vars load, and the script silently no-ops. **Mitigation:** invoke child scripts via `& 'path\script.ps1' @args` rather than `pwsh -File`, and explicitly do not pass `-WhatIf` through. This is the pattern I used successfully in the session.

### R6. `.env.local` mutation by child scripts.
`data-cloud-login-web.ps1` rewrites `.env.local` on success — including clearing fields it considers stale (`DATACLOUD_REFRESH_TOKEN=''` after a CLI login path). **Mitigation:** snapshot `.env.local` at script start, restore any cleared refresh token + exchange URL at script end if the new values are empty. Alternative: pass auth via environment variables scoped to the child processes and never touch `.env.local` from this script. Preferred path is the alternative — leave `.env.local` alone after the initial login.

### R7. Manifest schema drift.
The session showed that older manifests omit `fileName` per table and newer ones have full `files` / `publishContract.relationships`. **Mitigation:** normalize the manifest at load time (the repo already has a normalizer — `Get-DataCloudManifestInfo`). Fail loud if required fields can't be resolved.

### R8. CLI path on Windows PowerShell 5.1.
Script must run under `powershell.exe` (5.1), not only `pwsh` (7+). Some of the `[ordered]@{}` and null-conditional operators aren't portable. **Mitigation:** test both interpreters; avoid PS7-only syntax.

## Test matrix (manual, not automated in this pass)

| Scenario | Expected | Target run |
|---|---|---|
| Idempotent re-run on `Sunrun Direct Pay Command Center2-downloads` → `STORM_TABLEAU_NEXT` | < 3 min, `isValid: true`, model ID unchanged | first acceptance test |
| Fresh dataset to same org (pick any unused demo) | < 15 min cold, `isValid: true`, new model ID | second acceptance test |
| Missing CommandCenterAuth on a fresh org | auto-deploys, proceeds, no rerun needed | third acceptance test |
| No Data Cloud refresh token in `.env.local` | single browser popup, then silent to completion | implicit in fresh-org test |
| Connector missing in Data Cloud | clean error, clear next step, non-zero exit | sanity check |
| Two workspaces matching derived name | clean error listing both IDs, non-zero exit | sanity check |

## File list

- `docs/plans/deterministic-publish-dataset.md` — this file
- `scripts/publish-dataset.ps1` — new entry point
- `scripts/salesforce/DataCloud.Common.ps1` — one-line `SF_SKIP_NEW_VERSION_CHECK` fix

No new modules, no new common libraries, no registry changes.

## Open questions for Andrew before coding

1. **OK to unset `DATACLOUD_SALESFORCE_ALIAS` at process level rather than clearing it from `.env.local`?** This is cleaner but changes how the repo implicitly routes auth for other scripts called from the same shell.
2. **On a fresh org where CommandCenterAuth is not deployed, is it OK for this script to deploy it automatically without asking?** The connected app touches org-level OAuth policy. Deploy-on-demand is convenient but has a larger blast radius than the rest of the script.
3. **Is the "one interactive prompt per org, then silent" contract acceptable?** Or do you want zero-touch after the org is chosen, with a requirement that refresh tokens be pre-provisioned?
4. **Should `-SkipUpload` be included for the "just rebuild the SDM" case?** Would save ~2 minutes on re-runs where data hasn't changed.

If any of these answers is "no," the script changes in meaningful ways — worth pinning down before I write a single line of PowerShell.
