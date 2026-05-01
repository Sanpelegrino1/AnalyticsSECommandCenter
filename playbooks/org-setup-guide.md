# Org Setup Automation Guide

**Scripts:** `scripts/salesforce/org-setup/`
**Orchestrators:** `run-kickoff.ps1` → *(wait ~30 min)* → `run-resume.ps1`

---

## Overview

This automation brings a fresh Salesforce org to a fully configured Tableau Next + Data Cloud + Agentforce state in two phases. Phase 1 starts the slow async work (Data Cloud provisioning) while you still have momentum. Phase 2 finishes everything once provisioning is done.

Every step is **idempotent** — safe to rerun. Failed steps emit warnings into the end-of-run summary rather than killing the whole pipeline. A state file at `notes/org-setup-state/<alias>.json` tracks what has been completed, skipped, or warned.

---

## Milestones at a Glance

```
KICKOFF  (~5 min to run, then 30 min waiting)
  ├─ [a]  Enable Data Cloud               ← starts 30 min async provisioning
  ├─ [b]  Enable Einstein
  ├─ [d]  Deploy permission set + PSG
  ├─ [e]  Self-assign PSG to running user
  └─ [*]  Deploy CommandCenterAuth app    ← OPTIONAL: -WithConnectedApp

      ... wait ~30 min for Data Cloud to provision ...

RESUME   (~5 min to run)
  ├─ [c]  Poll until Data Cloud is live
  ├─ [f]  Enable Tableau Next + Agentforce toggles (dynamic)
  ├─ [g]  Feature Editor flags            ← MANUAL STEPS required (no API)
  ├─ [h]  Enable org-level dark mode      ← per-user step still manual
  ├─ [k]  Create + activate Analytics & Visualization agent
  ├─ [l]  Grant agent access to permission set
  ├─ [m]  Create Heroku PostgreSQL connector  ← OPTIONAL: -WithHeroku
  ├─ [n]  Deploy Reckless Analyst agent   ← OPTIONAL: -WithRecklessAgent
  └─ [o]  Register PACE + PACE-NEXUS Tableau Cloud sites
```

---

## Optional Feature Flags

| Flag | Script param | What it does |
|------|-------------|--------------|
| Data Cloud publish auth | `-WithConnectedApp` on **kickoff** | Deploys the `CommandCenterAuth` external client app. Only needed if this org will receive Data Cloud CSV uploads from Command Center. |
| Heroku PostgreSQL connector | `-WithHeroku` on **resume** | Creates the shared PACE curriculum Heroku PostgreSQL external data connector in Data Cloud. Only needed for orgs following the PACE lab guide. |
| Reckless Analyst agent | `-WithRecklessAgent` on **resume** | Deploys a custom Agentforce Employee agent ("Reckless Analyst") that appears in the Concierge sidebar dropdown. Not installed by default — only for demo orgs where you want the custom analytics agent experience. |

---

## Prerequisites

Before running either script:

1. **PowerShell** — 5.1+ on Windows, `pwsh` on macOS/Linux
2. **Salesforce CLI (`sf`)** — if missing, the scripts will prompt to auto-install via `winget` (Windows) or `brew` (macOS)
3. **Org registered** — the target org must be authenticated with `sf` and registered in `notes/registries/salesforce-orgs.json`
4. **Repo metadata present** — `salesforce/force-app/main/default/` must contain the `Access_Analytics_Agent` permset and `Tableau_Next_Admin_PSG` PSG (both ship in this repo)

---

## Usage

```powershell
# ── PHASE 1: KICKOFF ──────────────────────────────────────────────────────────

# Standard kickoff
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-kickoff.ps1 -Alias MFG-Nexus

# Kickoff + also deploy the CommandCenterAuth connected app
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-kickoff.ps1 -Alias MFG-Nexus -WithConnectedApp

# ── (wait ~30 min) ────────────────────────────────────────────────────────────

# Optional: monitor Data Cloud provisioning in a separate window without blocking
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/05-wait-for-data-cloud.ps1 -Alias MFG-Nexus

# ── PHASE 2: RESUME ───────────────────────────────────────────────────────────

# Standard resume
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus

# Resume + skip the Data Cloud poll (if you already confirmed it's live)
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus -NoWait

# Resume + Heroku connector
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus -WithHeroku

# Resume + Reckless Analyst agent
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus -WithRecklessAgent

# Resume with all optional flags
powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus -WithHeroku -WithRecklessAgent
```

---

## Phase 1: Kickoff — Step by Step

### Step a — Enable Data Cloud
**Script:** `01-enable-data-cloud.ps1`

Deploys `Settings:CustomerDataPlatform` with `enableCustomerDataPlatform=true` via the Metadata API. This is the only supported headless path — the Tooling API PATCH on this settings object returns a 500.

This call kicks off approximately 30 minutes of async tenant provisioning on Salesforce's backend. The script returns immediately after the deploy succeeds. Nothing downstream can run until provisioning completes, which is why the flow is split into two phases.

**Idempotency:** Queries `CustomerDataPlatformSettings.IsCustomerDataPlatformEnabled` first. If already `true`, logs a noop and exits.

---

### Step b — Enable Einstein
**Script:** `02-enable-einstein.ps1`

Deploys `Settings:EinsteinGpt` with three flags set to `true`:

- `enableEinsteinGptPlatform` — the master "Turn on Einstein" toggle
- `enableAIModelBeta` — enables Beta Generative AI Models
- `enableEinsteinGptAllowUnsafePTInputChanges` — allows unsafe changes to prompt templates (required for customisation)

Einstein must be on before Agentforce agents can be created in step k. This step also indirectly covers step (i) from the PACE guide.

**Idempotency:** The deploy is a no-op server-side if all three flags are already true.

---

### Steps d + e — Deploy Permission Set and PSG
**Script:** `03-deploy-permsets-and-psg.ps1`

Deploys two metadata components from the repo:

- **`Access_Analytics_Agent` (PermissionSet)** — grants access to run the Analytics and Visualization Agentforce agent. Users without this permset cannot see the agent.
- **`Tableau_Next_Admin_PSG` (PermissionSetGroup)** — bundles eight standard permsets required for Tableau Next admin access: `CopilotSalesforceUser`, `CopilotSalesforceAdmin`, `CDPAdmin`, `TableauEinsteinAdmin`, `TableauUser`, `TableauEinsteinAnalyst`, `TableauSelfServiceAnalyst`, `SlackElevateUser`.

These eight standard permsets must already exist in the target org. They ship with STORM pre-enablement.

---

### Step e (completion) — Self-Assign PSG
**Script:** `04-assign-psg-to-self.ps1`

Assigns the `Tableau_Next_Admin_PSG` to the currently authenticated user. Permission Set Groups are asynchronously recalculated after deploy, so this script first polls until the PSG reaches `Status = Updated` (up to 5 minutes by default) before inserting the `PermissionSetAssignment` record.

**Idempotency:** Checks for an existing assignment before inserting.

---

### Optional — Deploy CommandCenterAuth Connected App
**Script:** `11-deploy-connected-app.ps1`
**Flag:** `-WithConnectedApp` on `run-kickoff.ps1`

Deploys the `CommandCenterAuth` external client app, which is the OAuth credential store used by Command Center to authenticate Data Cloud CSV upload sessions. Only required if this org will be used as a Data Cloud publish target. Not part of the standard PACE BUILD 1 guide.

After this deploys, follow `playbooks/set-up-command-center-connected-app.md` to complete the auth wiring (the DataCloudAlias and LaunchLogin steps cannot be automated).

---

## The Wait

After kickoff completes, Data Cloud is provisioning in the background. This takes approximately 30 minutes. You can:

- Walk away and come back
- Run `05-wait-for-data-cloud.ps1` in a separate terminal to monitor readiness without blocking your session
- Or pass `-NoWait` to `run-resume.ps1` if you have separately confirmed Data Cloud is live

Do not run `run-resume.ps1` until Data Cloud is ready — steps f through n require it.

---

## Phase 2: Resume — Step by Step

### Step c — Poll for Data Cloud Readiness
**Script:** `05-wait-for-data-cloud.ps1`

Polls `GET /services/data/v60.0/ssot/data-connections` at 60-second intervals until the endpoint returns a success response, indicating that the Data Cloud tenant is fully provisioned and the `MktDataConnection` sObject is available. Times out after 60 minutes by default.

This is the gating step for everything that follows. If it times out, re-run resume after additional wait.

---

### Steps f + i — Enable Tableau Next and Agentforce Toggles
**Script:** `06-enable-tableau-next.ps1`

This is the most complex step. Rather than hardcoding a fixed list of toggle names (which changes with every Salesforce release), the script uses a dynamic "flip everything" approach:

1. **Static seed list:** Always targets `Bot`, `EinsteinCopilot`, `EinsteinAgent`, `AgentPlatform`, `Analytics`
2. **Dynamic discovery:** Enumerates all Settings metadata records in the org and adds any whose name contains "Tableau", "Concierge", or "Semantic" — these only appear after Data Cloud provisioning
3. **Retrieves** current state of all target records via Metadata API
4. **Identifies** every field named `enable*` that is currently `false`
5. **Skips** a hardcoded list of license-gated fields (e.g. `enableCrmaDataCloudIntegration`, `enableSnowflakeOutputConnector`) that would cause deploy failures on demo orgs
6. **Deploys each Settings record individually** — so if one fails (e.g. Tableau Next isn't fully provisioned yet), the others still succeed

Failures per-record are logged as warnings, not hard failures. The end-of-run summary tells you exactly which records failed and which fields to enable manually in Setup.

The `Bot` record's `enableBots` flag is the master Agentforce toggle — this is what makes `BotDefinition` a valid sObject and allows agents to be created in step k.

---

### Step g — Data Cloud Feature Editor Flags
**Script:** `07-enable-feature-manager-flags.ps1`

**This step cannot be automated.** The Data Cloud Feature Editor (previously called Feature Manager) has no public REST endpoint, no Tooling sObject, and no Metadata API surface. This is a known gap.

The script emits one warning per target feature into the run summary, each with manual instructions. Features that require manual enablement:

- **Semantic Authoring AI** — required for building Semantic Data Models
- **Connectors (Beta)** — required for additional data source connectors
- **Accelerated Data Ingest** — required for high-throughput CSV ingestion
- **Code Extension** — for custom Data Cloud code extensions
- **Content Tagging** — for AI-powered content classification

**Where to go in Setup:** Search for "Feature" in Setup Quick Find. The page may be labelled "Feature Manager" or "Feature Editor" depending on your org's release.

---

### Step h — Enable Org-Level Dark Mode
**Script:** `12-enable-dark-mode.ps1`

Deploys `Settings:UserInterface` with `enableSldsV2` and `enableSldsV2DarkModeInCosmos` set to `true`. This unlocks dark mode as an available option across the org.

**Manual follow-up required:** Salesforce does not expose a public API for the per-user dark mode selection. After this step, each user must click their profile avatar → Appearance → Dark to switch their own session. The run summary always includes this reminder.

---

### Step k — Create and Activate Analytics and Visualization Agent
**Script:** `08-create-analytics-agent.ps1`

Creates the OOTB Salesforce "Analytics and Visualization" Agentforce agent using `sf agent create --spec` with a hand-authored spec YAML. The spec defines three topics: Data Analysis, Data Alert Management, and Data Pro.

After creation, activates the agent with `sf agent activate`. If the first activation attempt fails, the script automatically attempts a deactivate + reactivate cycle before falling back to a warning.

**Dependency:** Requires step f to have enabled `Bot.enableBots`. If `BotDefinition` is not yet a valid sObject (Einstein or Agentforce not yet enabled), the step gracefully skips with a warning rather than failing.

**Idempotency:** Queries `BotDefinition WHERE DeveloperName = 'Analytics_and_Visualization'` before acting.

---

### Step l — Grant Agent Access via Permission Set
**Script:** `09-grant-agent-access.ps1`

Wires the `Access_Analytics_Agent` permission set to the `Analytics_and_Visualization` bot via a `SetupEntityAccess` insert. This is the mechanism that makes the agent visible to users who hold that permset.

Without this step, the agent exists and is active, but no user can see it — the Agentforce Concierge sidebar filters agents based on `SetupEntityAccess` grants.

The script uses the Tooling API directly (inserting a data sObject) rather than modifying the PermissionSet metadata XML, because the `agentAccesses` element name varies across API versions and is not reliably deployable via Metadata API in all org configurations.

**Idempotency:** Queries `SetupEntityAccess WHERE ParentId = [psId] AND SetupEntityId = [botId]` before inserting.

---

### Optional — Create Heroku PostgreSQL Connector
**Script:** `10-create-heroku-connector.ps1`
**Flag:** `-WithHeroku` on `run-resume.ps1`

Creates a Data Cloud external data connector pointing at the shared Heroku PostgreSQL instance used by the PACE curriculum. POSTs to `/services/data/v60.0/ssot/external-data-connectors` with the connector type, host, port, database, and credentials.

This step is best-effort — the endpoint is not officially documented. If the POST fails, the script logs a manual fallback instruction pointing to the PACE guide (lines 177–192) for the credentials.

**Idempotency:** Queries `MktDataConnection WHERE Name = 'Heroku_PostgreSQL'` before acting.

---

### Optional — Deploy Reckless Analyst Agent
**Script:** `13-deploy-reckless-analyst-agent.ps1`
**Flag:** `-WithRecklessAgent` on `run-resume.ps1`

Deploys a custom Agentforce **Employee Agent** ("Reckless Analyst") that appears in the Concierge sidebar alongside the default agent. This is a demo-oriented agent designed for decisive, answer-first analytics Q&A over Tableau Next semantic models.

This step uses the **authoring-bundle publish path** — the only CLI path that produces an `InternalCopilot` (Employee Agent) type, which is required to appear in the Concierge sidebar dropdown. The standard `sf agent create --spec` path always produces an `ExternalCopilot` (Service Agent), which will never appear in the sidebar regardless of permissions.

The step performs four actions:

1. **Publishes** `Reckless_Analyst_Employee` via `sf agent publish authoring-bundle --skip-retrieve` from the repo's existing `.agent` source
2. **Activates** the published version with `sf agent activate`
3. **Deploys** the `Reckless_Analyst_Access` permission set from repo source
4. **Wires** `SetupEntityAccess` to bind the permset to the bot, and **assigns** the permset to the running user

After this step, the running user will see "Reckless Analyst" in the Concierge agent switcher dropdown immediately (a full session re-auth clears any cache).

**Idempotency:** Checks for existing `BotDefinition` before publishing, and for existing `SetupEntityAccess` before inserting.

---

### Step o — Register Tableau Cloud Sites
**Script:** `14-register-tableau-sites.ps1`

Registers the two shared PACE Tableau Cloud sites on the Salesforce side by inserting `TableauHostMapping` records (site URL + LUID). This is the Salesforce-side site registry only — it does not configure any authentication trust.

The two sites registered are:

| Site | UrlMatch | SiteLuid |
|------|----------|---------|
| PACE | `prod-uswest-c.online.tableau.com/pace` | `5a81db69-14f1-42c7-b6a5-65ec087bf57d` |
| PACE-NEXUS | `prod-uswest-c.online.tableau.com/pace-nexus` | `6901a397-fe8d-4795-83a0-7a6e7685434f` |

**Tableau-side trust setup is manual and required.** Each Salesforce org that wants to view dashboards from either site must be registered as a trusted issuer on that site's Tableau Connected App (Direct Trust) — this happens in Tableau Cloud, not Salesforce, and needs Tableau admin credentials. This script does **not** automate it; hardcoding a PAT into a shared org-setup script is not acceptable. The step always emits a warning reminding the user to complete the Tableau-side setup for each new org.

**Idempotency:** Queries `TableauHostMapping WHERE UrlMatch = <url>` before inserting each record. Safe to rerun.

---

## After the Scripts Complete

The run summary printed at the end of `run-resume.ps1` lists every warning and completed step. Items that always require manual follow-up:

| What | Where in Setup |
|------|----------------|
| Feature Editor flags (5 features) | Data Cloud Setup → Feature Editor / Feature Manager |
| Per-user dark mode | Profile avatar → Appearance → Dark |
| CommandCenterAuth final auth wiring | Follow `playbooks/set-up-command-center-connected-app.md` |
| Tableau Cloud Connected App trust (PACE + PACE-NEXUS) | In Tableau Cloud, update each site's Connected App to trust this Salesforce org's EntityId. Requires Tableau admin. |

Once warnings are cleared you are at the "ready to connect data and build Semantic Data Models" milestone — the end of PACE BUILD 1.

---

## State File

`notes/org-setup-state/<alias>.json` persists the outcome of every step:

```json
{
  "alias": "MFG-Nexus",
  "completed": ["a-enable-data-cloud", "b-enable-einstein", "..."],
  "warnings": [
    {
      "step": "g-feature-editor",
      "feature": "Semantic Authoring AI",
      "message": "Enable manually: Data Cloud > Feature Editor..."
    }
  ],
  "log": [...]
}
```

Rerunning either orchestrator is safe — completed steps become noops, and the warning list only includes warnings from the current run.

---

## Individual Step Reference

| Guide step | Script | Mechanism | Hard failure? |
|-----------|--------|-----------|--------------|
| a | `01-enable-data-cloud.ps1` | Metadata deploy `Settings:CustomerDataPlatform` | Yes |
| b | `02-enable-einstein.ps1` | Metadata deploy `Settings:EinsteinGpt` | Yes |
| d + e | `03-deploy-permsets-and-psg.ps1` | Metadata deploy `PermissionSet` + `PermissionSetGroup` | Yes |
| e | `04-assign-psg-to-self.ps1` | `PermissionSetAssignment` insert, polls PSG status | Yes |
| c + j | `05-wait-for-data-cloud.ps1` | Poll `GET /ssot/data-connections` | Yes (timeout) |
| f + i | `06-enable-tableau-next.ps1` | Retrieve + flip `enable*` fields, per-record deploy | Warning per record |
| g | `07-enable-feature-manager-flags.ps1` | No API — emits 5 manual warnings | Warning only |
| h | `12-enable-dark-mode.ps1` | Metadata deploy `Settings:UserInterface` | Warning |
| k | `08-create-analytics-agent.ps1` | `sf agent create` + `sf agent activate` | Warning |
| l | `09-grant-agent-access.ps1` | `SetupEntityAccess` insert via REST | Warning |
| m *(opt)* | `10-create-heroku-connector.ps1` | POST `/ssot/external-data-connectors` | Warning |
| *(opt)* | `11-deploy-connected-app.ps1` | Delegates to `setup-command-center-connected-app.ps1` | Hard |
| n *(opt)* | `13-deploy-reckless-analyst-agent.ps1` | `sf agent publish authoring-bundle` + permset deploy + `SetupEntityAccess` | Warning |
| o | `14-register-tableau-sites.ps1` | `TableauHostMapping` REST inserts (PACE + PACE-NEXUS sites) | Warning |
