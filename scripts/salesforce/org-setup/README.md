# OrgSetup — Tableau Next PACE BUILD 1

Automates BUILD 1 of `Org Setup/Tableau Next PACE Setup.txt` against a fresh Salesforce org. Scope stops at the line *"You are now ready to start connecting to data and building out your Semantic Data Model!"* — BUILDs 2–4 are training content, not automation.

## Two-phase flow

Data Cloud provisioning takes ~30 min. The flow is split so the session can be paused:

1. **Kickoff** (`run-kickoff.ps1`) — enables Data Cloud + Einstein, deploys permission sets, self-assigns the PSG. Returns immediately; Data Cloud provisioning runs async in the background.
2. *(wait ~30 min — walk away)*
3. **Resume** (`run-resume.ps1`) — polls for Data Cloud readiness, then enables Tableau Next, creates the Analytics agent, grants permset access, and (opt-in) sets up the Heroku connector.

State lives in `notes/org-setup-state/<alias>.json`. Each script is idempotent, so reruns are safe.

## Prereqs

- PowerShell (5.1+ on Windows, `pwsh` on macOS/Linux).
- Salesforce CLI (`sf`). If missing, the orchestrators prompt `Install Salesforce CLI now? (y/n)` and auto-install via `winget` (Windows) or `brew` (macOS). On Linux, follow the manual link in the prompt. Admin elevation is requested automatically on Windows if the non-elevated install fails.
- Target org registered in `notes/registries/salesforce-orgs.json`.
- Target metadata files present under `salesforce/force-app/main/default/` — the `Access_Analytics_Agent` permset and `Tableau_Next_Admin_PSG` PSG ship in this repo.

## Usage

```powershell
# Phase 1 — starts Data Cloud provisioning, creates permsets/PSG, self-assigns
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-kickoff.ps1 -Alias MFG-Nexus

# Phase 1 + also deploy CommandCenterAuth (if this org will publish to Data Cloud)
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-kickoff.ps1 -Alias MFG-Nexus -WithConnectedApp

# (Optional) monitor Data Cloud readiness without blocking resume
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/05-wait-for-data-cloud.ps1 -Alias MFG-Nexus -TimeoutMinutes 60

# Phase 2 — after Data Cloud is live, finishes Tableau Next + agent + access grant
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus

# Phase 2 with the optional Heroku PostgreSQL connector
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus -WithHeroku

# Phase 2 with the Reckless Analyst custom Employee agent (Concierge sidebar)
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus -WithRecklessAgent

# All optional flags together
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus -WithHeroku -WithRecklessAgent

```

Dark mode is always enabled at the org level by `run-resume.ps1`; the run summary always reminds the user to pick "Dark" from their profile avatar menu (per-user selection has no public API).

## Step map

| Guide | Script | Mechanism |
|-------|--------|-----------|
| a     | `01-enable-data-cloud.ps1`            | Tooling PATCH `CustomerDataPlatformSettings.IsCustomerDataPlatformEnabled` |
| b, i  | `02-enable-einstein.ps1`              | Tooling PATCH `EinsteinGptSettings.IsEinsteinGptPlatformEnabled` |
| c, j  | `05-wait-for-data-cloud.ps1`          | Poll GET `/services/data/v60.0/ssot/data-connections` |
| d     | `03-deploy-permsets-and-psg.ps1`      | `sf project deploy start --metadata PermissionSet:Access_Analytics_Agent` |
| e     | `03-deploy-permsets-and-psg.ps1` + `04-assign-psg-to-self.ps1` | PSG metadata deploy + `PermissionSetAssignment` insert |
| f, i  | `06-enable-tableau-next.ps1`          | Dynamic: retrieve target Settings records (Bot, EinsteinCopilot, EinsteinAgent, AgentPlatform, Analytics, plus any `*Tableau*`/`*Concierge*`) and flip every `enable*=false` to `true`. Per-record deploy with warning-on-failure. |
| g     | `07-enable-feature-manager-flags.ps1` | Data Cloud Feature Editor has no public API surface today. Script emits one warning per target feature (Semantic Authoring AI, Connectors (Beta), Accelerated Data Ingest, Code Extension, Content Tagging) for manual completion in Setup. |
| h     | `12-enable-dark-mode.ps1`             | Deploy `UserInterface` settings (`enableSldsV2` + `enableSldsV2DarkModeInCosmos`). Opt-in `-Dark` on resume emits a per-user follow-up reminder. |
| k     | `08-create-analytics-agent.ps1`       | `sf agent create` + `sf agent activate` |
| l     | `09-grant-agent-access.ps1`           | Tooling `SetupEntityAccess` insert |
| m     | `10-create-heroku-connector.ps1`      | POST `/services/data/v60.0/ssot/external-data-connectors` (opt-in via `-WithHeroku`) |
| extra | `11-deploy-connected-app.ps1`         | Deploy CommandCenterAuth external client app (opt-in via `-WithConnectedApp` on kickoff). Not a BUILD 1 step — adds Data Cloud publish auth. See playbooks/set-up-command-center-connected-app.md. |
| n     | `13-deploy-reckless-analyst-agent.ps1` | Publish `Reckless_Analyst_Employee` via authoring-bundle path, deploy + assign `Reckless_Analyst_Access` permset, wire `SetupEntityAccess`. Opt-in via `-WithRecklessAgent`. Produces an `InternalCopilot` agent visible in the Concierge sidebar dropdown. Not installed by default — only for orgs where the custom analytics agent experience is desired. |
| o     | `14-register-tableau-sites.ps1`        | Registers the PACE and PACE-NEXUS Tableau Cloud sites via `TableauHostMapping` REST inserts (`SiteLuid` + `UrlMatch` + `HostType`). Salesforce-side only. Always emits a warning that Tableau-side Direct Trust setup (registering this org as a trusted issuer on each site's Connected App) is manual and requires Tableau admin credentials — not automated here because this script is shared and can't embed a PAT. |

## Warnings + summary

Tolerant steps never fail the whole run — they call `Add-OrgSetupWarning` when a specific feature toggle can't be flipped, and `run-resume.ps1` prints a summary of every warning at the end. Example:

```
=== OrgSetup Summary ===
Alias:    MFG-Nexus
Completed: a-enable-data-cloud, b-enable-einstein, ...

!!! 2 warning(s) during this run !!!
  - [g-feature-manager] [Code Extension] Feature not found in list. Enable manually in Setup > Feature Manager.
  - [h-dark-mode] [User dark mode] Dark Mode Enabled at org level. Click your profile avatar > Appearance > Dark ...
```

Warnings persist in the state file (`notes/org-setup-state/<alias>.json` under `warnings`) so you can review them later too. Rerunning `run-resume.ps1` is safe — already-enabled items are NOOPs and only current-run warnings print in the summary.

See `Org Setup/build1-automation-research.md` for the full pre-automation research notes.

## State file

`notes/org-setup-state/<alias>.json`:

```json
{
  "alias": "MFG-Nexus",
  "createdUtc": "2026-04-25T...",
  "updatedUtc": "2026-04-25T...",
  "completed": ["a-enable-data-cloud", "b-enable-einstein", ...],
  "skipped":   ["f-enable-tableau-next"],
  "log": [
    { "step": "a-enable-data-cloud", "outcome": "completed", "message": "...", "timestamp": "..." },
    ...
  ]
}
```
