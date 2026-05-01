# Build a Custom Agentforce Employee Agent (CLI end-to-end)

## Purpose

Create a new custom Agentforce **Employee Agent** from scratch in a target Salesforce org, wire it with actions, grant a user access to it, and confirm it appears in the Concierge agent switcher sidebar alongside the org's default agent.

This playbook documents the path that actually works end-to-end. It is the only CLI path in the Salesforce CLI today that produces an Employee-type (`InternalCopilot`) agent. The legacy `sf agent create --spec` path produces a `ExternalCopilot` / `EinsteinServiceAgent`, which **will not appear in the Concierge Employee Agent switcher** regardless of how permissions are granted. That distinction is the single most load-bearing fact in this playbook.

## Inputs

- Target org alias (e.g., `MFG-Nexus`) with Salesforce CLI auth
- An agent API name (snake_case, no leading underscore, no `__`, ≤80 chars, e.g., `Reckless_Analyst_Employee`)
- An agent display label (e.g., `Reckless Analyst`)
- A role prompt (the agent's `system.instructions`)
- A user who should see the agent in the Concierge sidebar (typically the running user)

## Prerequisites

- The target org has Agentforce enabled and `BotDefinition` is a valid sObject.
- The user has a profile or permission set with `Manage AI Agents` or `Customize Application`.
- The VS Code **Salesforce Agentforce / Agent Script Language Client** extensions are installed locally — the language server catches most script errors before `sf agent validate`.
- `sf` CLI is on at least plugin-agent 1.7.0 (supports AiAuthoringBundle).

## Why this works when the other CLI paths don't

There are three CLI-reachable paths to create an agent. Only one produces an Employee Agent:

| Path | Result type | Shows in Concierge sidebar? |
| --- | --- | --- |
| `sf agent create --spec <yaml>` | `ExternalCopilot` / Service Agent | No |
| Hand-authored `Bot` + `GenAiPlannerBundle` metadata, `sf project deploy` | `ExternalCopilot` / Service Agent (type is locked at creation, `BotType can't be updated`) | No |
| **`sf agent generate authoring-bundle` → `sf agent validate authoring-bundle` → `sf agent publish authoring-bundle`** | **`InternalCopilot` / Employee Agent** (when `agent_type: "AgentforceEmployeeAgent"` is set in the `.agent` script) | **Yes** |

Bot type is immutable after creation, so picking the wrong path means starting over. Always use the authoring-bundle path for a sidebar-eligible agent.

## Step 1 — Scaffold the authoring bundle

From the repo's `salesforce/` directory:

```bash
sf agent generate authoring-bundle \
  --target-org <alias> \
  --name "<Display Label>" \
  --api-name <Api_Name> \
  --no-spec \
  --force-overwrite
```

This creates:

- `force-app/main/default/aiAuthoringBundles/<Api_Name>/<Api_Name>.agent` — the Agent Script file
- `force-app/main/default/aiAuthoringBundles/<Api_Name>/<Api_Name>.bundle-meta.xml` — the wrapper metadata

`--no-spec` skips the LLM-based topic generator (which requires a server-side prompt template that isn't reliably present in every org). The script starts as boilerplate and you edit it by hand — deterministic, reviewable, and survives across orgs.

## Step 2 — Edit the `.agent` script

Open `<Api_Name>.agent` and set:

```agentscript
system:
    instructions: "<role prompt as a single-line double-quoted string>"
    messages:
        welcome: "<first-turn greeting>"
        error: "<one-line generic error message>"

config:
    developer_name: "<Api_Name>"
    agent_type: "AgentforceEmployeeAgent"   # REQUIRED — produces InternalCopilot
    agent_label: "<Display Label>"
    description: "<one-sentence agent description>"
```

### Script rules that cost us hours the first time

- `system.instructions` must be a **plain double-quoted string**. The `->` / `|` template form compiles in `reasoning.instructions:` but **not** here — it will fail validation with `Expected a string or template`.
- Indentation is **4 spaces, never tabs**. Mixed indentation breaks the parser silently.
- Identifiers (`developer_name`, topic names, variable names): letters/numbers/underscores only, begin with a letter, no trailing underscore, no `__`.
- `agent_type` enum accepts `AgentforceServiceAgent`, `AgentforceEmployeeAgent`, `SalesEinsteinCoach`. Anything else fails validation.

Declare page-context variables so the agent receives the current app/record context:

```agentscript
variables:
    currentAppName: mutable string
        description: "Salesforce Application Name."
    currentObjectApiName: mutable string
        description: "The API name of the Salesforce object the user is viewing."
    currentPageType: mutable string
        description: "Type of Salesforce Page."
    currentRecordId: mutable string
        description: "The ID of the record on the user's screen."
```

Add topics with a `start_agent` router:

```agentscript
start_agent topic_selector:
    label: "Topic Selector"
    description: "Route every turn to the best-fit topic."
    reasoning:
        instructions: ->
            | Route to the best-fit topic. Never refuse -- if nothing else fits, route to <default_topic>.
        actions:
            go_to_default: @utils.transition to @topic.<default_topic>
```

Each `topic <name>:` block needs `label`, `description`, and a `reasoning:` block. Add `actions:` under both the topic (to declare) and `reasoning:` (to invoke). See Step 3 for the action pattern.

## Step 3 — Wire real actions (charts, record lookups, etc.)

Agent Script uses a **two-level action system**:

- **Topic-level `actions:`** — DECLARE the action (with `target:`, `inputs:`, `outputs:`)
- **Reasoning-level `actions:`** — INVOKE the action (via `@actions.<name>`)

Target formats take the form `<type>://<DeveloperName>`:

| Protocol | What it calls |
| --- | --- |
| `flow://` | Autolaunched Flow |
| `apex://` | Apex class with `@InvocableMethod` |
| `standardInvocableAction://` | Built-in Salesforce action (see below) |
| `prompt://` or `generatePromptResponse://` | Prompt Template |

### Finding the right target for Tableau Next / Data Cloud actions

"Analyze Metric" and "Summarize Dashboard" are NOT `standardInvocableAction` directly — they're GenAiFunctions that wrap specific targets. To find the real target, query the tooling API:

```bash
sf data query --target-org <alias> \
  --query "SELECT DeveloperName, InvocationTargetType, InvocationTarget FROM GenAiFunctionDefinition WHERE DeveloperName LIKE '<prefix>%'" \
  --use-tooling-api
```

Confirmed real targets in a Tableau-Next-enabled org:

| Function | Real target |
| --- | --- |
| `Analyze Metric` | `flow://sfdc_dqa__AnalyzeMetric` |
| `Summarize Dashboard` | `standardInvocableAction://summarizeDashboard` |

Wire them into topic actions like this:

```agentscript
topic decisive_data_qa:
    label: "Decisive Data Q&A"
    description: "Default topic for metric and dashboard questions."

    actions:
        analyze_metric:
            description: "Analyzes a Tableau Next semantic metric and returns the real metric visualization."
            target: "flow://sfdc_dqa__AnalyzeMetric"
        summarize_dashboard:
            description: "Summarizes a Tableau Next dashboard and returns the embedded dashboard visualization."
            target: "standardInvocableAction://summarizeDashboard"

    reasoning:
        instructions: ->
            | Answer directly. For any metric question, call analyze_metric to return a real viz. For dashboard questions, call summarize_dashboard.
        actions:
            invoke_analyze_metric: @actions.analyze_metric
                description: "Pull and visualize a specific Tableau Next metric"
            invoke_summarize_dashboard: @actions.summarize_dashboard
                description: "Pull and visualize a Tableau Next dashboard"
```

## Step 4 — Validate

```bash
cd salesforce
sf agent validate authoring-bundle \
  --target-org <alias> \
  --api-name <Api_Name>
```

Warnings like "unused variable" are fine — page-context variables are bound by the hosting surface at runtime, not in-script. Only fix hard errors.

## Step 5 — Publish and activate

```bash
sf agent publish authoring-bundle \
  --target-org <alias> \
  --api-name <Api_Name> \
  --skip-retrieve
```

Use `--skip-retrieve`. Without it, the post-publish metadata retrieve occasionally 500s with `Metadata retrieval failed:` even though the publish itself succeeded. `--skip-retrieve` sidesteps that entirely.

Then activate:

```bash
sf agent activate --target-org <alias> --api-name <Api_Name>
```

Verify type:

```bash
sf data query --target-org <alias> \
  --query "SELECT Id, DeveloperName, Type FROM BotDefinition WHERE DeveloperName = '<Api_Name>'"
```

Expected: `Type: InternalCopilot`. If it comes back as `ExternalCopilot`, check that `agent_type: "AgentforceEmployeeAgent"` is in the script's `config:` block.

## Step 6 — Grant user access via permission set

The Concierge Employee Agent switcher filters on **both** type (`InternalCopilot`) **and** explicit permset-granted bot access. Without the permset grant, the agent is invisible to the picker even when the user has the right profile.

Create a permission set with an `<agentAccesses>` entry:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <agentAccesses>
        <agentName><Api_Name></agentName>
        <enabled>true</enabled>
    </agentAccesses>
    <description>Grants access to run the <Display Label> Agentforce agent.</description>
    <hasActivationRequired>false</hasActivationRequired>
    <label><Display Label> Access</label>
</PermissionSet>
```

Save as `salesforce/force-app/main/default/permissionsets/<Api_Name>_Access.permissionset-meta.xml`, deploy, assign:

```bash
cd salesforce
sf project deploy start --target-org <alias> \
  --metadata "PermissionSet:<Api_Name>_Access" \
  --api-version 66.0

sf org assign permset --target-org <alias> \
  --name <Api_Name>_Access
```

Verify the grant landed:

```bash
sf data query --target-org <alias> \
  --query "SELECT Parent.Name, SetupEntityId FROM SetupEntityAccess WHERE SetupEntityType = 'BotDefinition' AND Parent.Name = '<Api_Name>_Access'"
```

Expected: one row where `SetupEntityId` matches the Bot ID from Step 5. Zero rows means the permset was deployed but the `<agentAccesses>` block didn't take — usually a stale XML or a typo in `agentName`.

## Step 7 — Confirm sidebar visibility

Hard-refresh the target org's browser tab (full logout-login if possible, incognito is cleanest). Open the Concierge sidebar. The new agent should appear in the **"Select Agent"** dropdown alongside the default agent.

If it doesn't appear:

- Confirm `Type: InternalCopilot` on the BotDefinition. `ExternalCopilot` will never surface here.
- Confirm the active BotVersion status: `SELECT DeveloperName, Status FROM BotVersion WHERE BotDefinition.DeveloperName = '<Api_Name>'`. Need at least one `Active` row.
- Confirm `SetupEntityAccess` row exists per the verify query in Step 6.
- Confirm the user has the permset assigned: `SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username = '<username>' AND PermissionSet.Name = '<Api_Name>_Access'`.

If all four are true and it still doesn't appear, the cache hasn't refreshed. Full session reauth (not just browser refresh) almost always fixes it.

## Reference: manual equivalent in Setup UI

Per Salesforce Help's **Manage Employee Agent Access** page (the authoritative doc):

> From Setup, in the Quick Find box, enter Permission Sets, and then select Permission Sets.
> Select a permission set or profile.
> Edit the Enabled Agent Access settings.
> Select the Agentforce Employee agents that you want to give users access to and then click Save.

The metadata `<agentAccesses>` block we deploy in Step 6 writes to the same underlying `SetupEntityAccess` table that the Enabled Agent Access UI edits. Either path works.

## What NOT to do

- Do not use `sf agent create --spec <yaml>` if you need a sidebar-eligible agent. It always produces `ExternalCopilot`, and `BotType` is immutable after creation — you cannot flip it later.
- Do not add `<agentAccesses>` entries to managed permsets (e.g., `CopilotSalesforceUser`). Managed permsets are not retrievable/modifiable via Metadata API in most orgs.
- Do not skip the activate step. A published-but-inactive bot does not appear in the sidebar even when all permissions are correct.
- Do not edit the `.agent` script while the agent is active if you plan to republish. Deactivate first; active bots reject plugin/bundle updates (`Can't edit an active bot version`).

## Outputs

- A `BotDefinition` row with `Type = InternalCopilot`
- An active `BotVersion`
- A `GenAiPlannerBundle` wired to the bot
- An `AiAuthoringBundle` containing the editable `.agent` script (source of truth for future updates)
- A permission set with `<agentAccesses>` entry, assigned to at least one user
- A `SetupEntityAccess` row binding permset → bot

Re-running the playbook against the same org with the same `--api-name` is idempotent for script edits: `sf agent publish authoring-bundle` creates a new BotVersion rather than duplicating the bot. The permset step is also idempotent.
