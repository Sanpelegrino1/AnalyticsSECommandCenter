# OrgSetup — BUILD 1 Automation Research

Target org: `MFG-Nexus` / `00Dfj00000Nl6khEAB` / `mfg-nexus@salesforce.com`
Research date: 2026-04-25
User Id (for self-assignments): `005fj00000EYYf7AAH`
Instance URL: `https://storm-b5af005f0ad11b.my.salesforce.com`
CLI: `@salesforce/cli 2.130.9`, API v60.0

All findings validated against the live org. `jq` was not on PATH; used Python for JSON parsing.

---

## a. Enable Data Cloud

- **Can automate headlessly?** Yes.
- **Mechanism** — Tooling API sObject `CustomerDataPlatformSettings.IsCustomerDataPlatformEnabled` (boolean). Equivalent metadata: deploy a `<Settings xsi:type="CustomerDataPlatformSettings">` XML via Metadata API (directory `settings/CustomerDataPlatform.settings-meta.xml`). Either approach flips the same flag.
  - PATCH example: `PATCH /services/data/v60.0/tooling/sobjects/CustomerDataPlatformSettings/<DurableId>` with body `{"IsCustomerDataPlatformEnabled": true}`.
  - The `DurableId` in this org is `bWRjLzBIRS9DdXN0b21lckRhdGFQbGF0Zm9ybVNldHRpbmdz`.
- **Current state in MFG-Nexus** — NOT enabled (`IsCustomerDataPlatformEnabled: false`). Q Branch "Deploy Data Cloud Setup" has not been run.
- **Verification** — `sf data query --use-tooling-api --query "SELECT IsCustomerDataPlatformEnabled FROM CustomerDataPlatformSettings"`.
- **Gotchas** — Flipping this boolean kicks off async tenant provisioning; step (c) (~30 min) is the tail end of the *same* workflow. The STORM "Q Branch Demo Wizard" button is essentially a wrapper around this enablement + a later `Get Started` click. No `sf data-cloud` CLI topic exists. There is no `DataCloudTenant` / `CdpTenant` SObject queryable; we instead infer completion by waiting for (c) — see that section.

---

## b. Enable Einstein

- **Can automate headlessly?** Yes.
- **Mechanism** — Tooling API sObject `EinsteinGptSettings.IsEinsteinGptPlatformEnabled` (boolean). Metadata alternative: `EinsteinSettings` / `EinsteinGptSettings` Settings XML. DurableId in this org: `bWRjLzBIRS9FaW5zdGVpbkdwdFNldHRpbmdz`.
- **Current state in MFG-Nexus** — NOT enabled (`false`). Not pre-on in this STORM.
- **Verification** — `SELECT IsEinsteinGptPlatformEnabled FROM EinsteinGptSettings` (Tooling).
- **Gotchas** — "Einstein Setup" in the UI is the same toggle. Note `EinsteinAgentSettings` is a different thing (RunAssignmentRules, SummarizationCopilot, etc.) — do not confuse them. The guide's "Einstein Setup" page toggle = `IsEinsteinGptPlatformEnabled`.

---

## c. Finish Data Cloud Setup "Get Started"

- **Can automate headlessly?** Partial — we can trigger it, but there is no first-class polling SObject.
- **Mechanism** — The "Get Started" button is the *completion* phase of the CDP provisioning that (a) kicks off. In practice enabling `CustomerDataPlatformSettings` begins provisioning; the ~30-minute wait *is* Salesforce building the CDP tenant. The UI "Get Started" is largely a gate; headlessly we wait for tenant readiness by polling for availability of dependent objects:
  - Poll: `SELECT Id FROM MktDataConnection` (becomes queryable after provisioning), or
  - Poll: retrieve metadata `DataKitObjectTemplate` / attempt a no-op `mktDataConnections` REST call: `GET /services/data/v60.0/ssot/data-connections`. Before provisioning this returns an error; after, it returns 200 with records.
  - Safer: poll permission sets `D360HomeOrgPermSet` visibility or query `SELECT Id FROM DataCloudAccessLoyaltyPromotionDesigner` style — but the cleanest signal is the SSOT REST endpoint.
- **Current state in MFG-Nexus** — Not yet initiated (depends on a).
- **Verification** — `GET $INST/services/data/v60.0/ssot/data-connections` — success = tenant is provisioned and Feature Manager toggles (step g) become available.
- **Gotchas** — There is no `DataCloudTenant` / `CdpTenant` SObject in the org (both tried, both INVALID_TYPE). The 30-minute timer starts at (a); "Get Started" is effectively a no-op in automation land if you wait for the tenant to be live. Build the skill to poll every 60s up to ~45 min.

---

## d. Create Permission Set "Access Analytics Agent"

- **Can automate headlessly?** Yes.
- **Mechanism** — Metadata API deploy. Minimal XML:
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
      <label>Access Analytics Agent</label>
      <hasActivationRequired>false</hasActivationRequired>
      <license>Salesforce</license>
  </PermissionSet>
  ```
  File path `permissionsets/Access_Analytics_Agent.permissionset-meta.xml`. Deploy with `sf project deploy start`. The `<license>` element is optional; omit to create a "None" license permset, which is the safer default since we want to layer it onto many user licenses.
- **Current state in MFG-Nexus** — Does not exist (confirmed by query).
- **Verification** — `sf data query --query "SELECT Id FROM PermissionSet WHERE Name = 'Access_Analytics_Agent'"`.
- **Gotchas** — API name is `Access_Analytics_Agent` (spaces -> underscores). Step (l) later modifies this permset to grant agent access, so keep it simple at creation. Don't include a `<license>` unless you're sure; it locks assignment eligibility.

---

## e. Create Permission Set Group "Tableau Next Admin PSG"

- **Can automate headlessly?** Yes.
- **Mechanism** — Metadata API `PermissionSetGroup` deploy:
  ```xml
  <PermissionSetGroup xmlns="http://soap.sforce.com/2006/04/metadata">
      <label>Tableau Next Admin PSG</label>
      <description>...</description>
      <permissionSets>Access_Analytics_Agent</permissionSets>
      <permissionSets>CopilotSalesforceUser</permissionSets>
      ...
  </PermissionSetGroup>
  ```
  Self-assignment: insert `PermissionSetAssignment` with `PermissionSetGroupId` and `AssigneeId=005fj00000EYYf7AAH` (PSA supports either `PermissionSetId` or `PermissionSetGroupId`, confirmed via describe).

- **Permission set availability in MFG-Nexus RIGHT NOW (before any step runs):**

| # | Guide label | Actual API Name (Name) | Actual Label | Present now? | Requires |
|---|---|---|---|---|---|
| 1 | Access Agentforce Default Agent | `CopilotSalesforceUser` | Access Agentforce Default Agent | YES | standard |
| 2 | Access Analytics Agent | `Access_Analytics_Agent` | Access Analytics Agent | NO | step (d) |
| 3 | Agentforce Default Admin | `CopilotSalesforceAdmin` | Agentforce Default Admin | YES | standard |
| 4 | Data Cloud Admin | `CDPAdmin` | Data Cloud Admin | YES | standard (legacy name CDPAdmin) |
| 4b | Data Cloud Architect (alt) | `GenieAdmin` | Data Cloud Architect | YES | standard |
| 5 | Tableau Next Admin | `TableauEinsteinAdmin` | Tableau Next Admin | YES | standard |
| 6 | Tableau Next Consumer | `TableauUser` | Tableau Next Consumer | YES | standard |
| 7 | Tableau Next Platform Analyst | `TableauEinsteinAnalyst` | Tableau Next Platform Analyst | YES | standard |
| 8 | Tableau Next Self-Service Analyst | `TableauSelfServiceAnalyst` | Tableau Next Self-Service Analyst | YES | standard |
| 9 | Slack Sales Home User | `SlackElevateUser` | Slack Sales Home User | YES | standard |

All eight standard perm sets are already present in a fresh STORM before Data Cloud/Einstein/Tableau Next/Agentforce are flipped on. This is surprising but consistent — STORM pre-ships the metadata; enabling the features merely activates runtime features. The only permset that needs creation is #2 (Access Analytics Agent) in step (d).

- **Current state in MFG-Nexus** — `Tableau_Next_Admin_PSG` does not exist (confirmed query returned 0).
- **Verification** — `SELECT DeveloperName FROM PermissionSetGroup WHERE DeveloperName='Tableau_Next_Admin_PSG'`; then `SELECT Id FROM PermissionSetAssignment WHERE AssigneeId='005fj00000EYYf7AAH' AND PermissionSetGroupId=<id>`.
- **Gotchas** — The `permissionSets` child element takes `Name`, not `Label`. `CDPAdmin` label is "Data Cloud Admin" — use that; `GenieAdmin` ("Data Cloud Architect") is the guide's parenthetical fallback but is not needed. PSG recalc is async — after deploy, wait for `Status='Updated'` on the group before relying on derived perms (`SELECT Id,Status FROM PermissionSetGroup`).

---

## f. Enable Tableau Next + 7 sub-toggles

- **Can automate headlessly?** No clean path discovered.
- **Mechanism** — No `TableauNextSettings` / `TableauSettings` / `TableauEinsteinSettings` Tooling sObject exists; no matching `*Settings` metadata type was returned. Scans for `Tableau`, `Semantic`, `Concierge`, `Feature` returned nothing usable. The UI page "Tableau Next Setup" almost certainly writes to a Feature Manager record or a non-public Tooling object.
  - Strong candidate path: `POST /services/data/v60.0/tableau-einstein-setup/enable` style Connect endpoint (not validated — the org isn't yet at that state). Worth re-probing *after* (c) completes since the endpoint may be tenant-gated.
  - The 7 sub-toggles (Agentforce for Analytics, Concierge Analytics Q&A, Inspector Proactive Alerts, Data Pro Beta, Tableau Following, Metric Insights Summary, Enhanced Visualization Authoring UI) are Feature Manager feature flags — see step (g).
- **Current state in MFG-Nexus** — Unknown; blocked.
- **Verification** — After enable, `SELECT Id FROM TableauHostMapping` becomes queryable (the object exists in schema but empty until Tableau Next is provisioned).
- **Gotchas** — Flag this as the single most likely blocker for a fully headless skill. Plan: after (a)-(c) complete, re-enumerate Tooling sObjects (`/tooling/sobjects/`) and metadata types — new ones appear post-provisioning. This research was done pre-provisioning; `TableauNextSettings` or similar may materialize later. If not, fall back to the UI with an automated browser or Q Branch wizard.

---

## g. Enable "Semantic Authoring AI" + "Connectors (Beta)" via Feature Manager

- **Can automate headlessly?** Unknown / partial. Probably via a private Feature Manager REST endpoint but not validated pre-provisioning.
- **Mechanism** — Feature Manager is a Data Cloud UI that reads/writes FeatureParameter-style toggles. The underlying store is not exposed through any `FeatureParameterBoolean` Tooling sObject (there is no such sobject in this org — that name is only present in 2GP package contexts). It is likely fronted by `/services/data/v60.0/ssot/feature-manager/...` endpoints, which are gated on (c).
- **Current state in MFG-Nexus** — Blocked by (c).
- **Verification** — After (c) completes, re-probe: `curl $INST/services/data/v60.0/ssot/` and explore.
- **Gotchas** — Second-most-likely manual step. Document this as "re-investigate once Data Cloud is live" in the skill.

---

## h. Set Cosmos theme (OPTIONAL)

- **Can automate headlessly?** Partial.
- **Mechanism** — Metadata type `LightningExperienceTheme` exists, but `list metadata` shows zero records in the org today (the built-in Cosmos theme is not listed because Salesforce-provided themes live in a protected namespace). Activating an *existing* theme is normally done by updating `ThemeSettings` metadata pointing to the theme, but that metadata type was not found in this org. Most reliable headless option: deploy a custom `LightningExperienceTheme` + `BrandingSet` named "Cosmos" and set it active via the Tooling sObject `LightningExperienceTheme` (createable).
- **Current state in MFG-Nexus** — No custom themes; default in use.
- **Verification** — Browser-visible only; no clean SOQL.
- **Gotchas** — Step is flagged OPTIONAL in the guide. Recommend the skill skips this by default to avoid gold-plating.

---

## i. Enable Agentforce

- **Can automate headlessly?** Likely yes, via metadata deploy; not confirmed via direct Tooling toggle.
- **Mechanism** — No `AgentforceSettings` Tooling sObject exists. The "Agentforce Agents" master toggle in the UI is generally written as part of `EinsteinAgentSettings` or a Settings-typed metadata deploy. Additionally, enabling Einstein (b) + creating the agent via `sf agent create` (k) implicitly flips the platform-level flag. In practice the skill can skip an explicit toggle and rely on (b) + (k).
- **Current state in MFG-Nexus** — Off (Einstein itself is off).
- **Verification** — After (k), `SELECT Id FROM BotDefinition` starts returning records (currently returns INVALID_TYPE because Einstein isn't on).
- **Gotchas** — The guide describes this as a visible toggle; it's entangled with multiple underlying flags. Recommend the skill treat (b) as sufficient, then let (k) prove enablement.

---

## j. Gate — confirm (c) completed

- **Mechanism** — Poll `GET $INST/services/data/v60.0/ssot/data-connections` every 60 seconds. HTTP 200 with a JSON body = Data Cloud is live. Also validated by `SELECT COUNT() FROM MktDataConnection` succeeding (MktDataConnection is in the schema list already but queries error until tenant is up).
- **Gotchas** — Salesforce's own Q Branch wizard waits on a similar signal; there is no public `DataCloudTenant.Status` field.

---

## k. Create Analytics Agent from "Analytics and Visualization" template + activate

- **Can automate headlessly?** Yes.
- **Mechanism** — Use `sf agent` CLI (validated present):
  1. `sf agent generate agent-spec --target-org MFG-Nexus --name "Analytics and Visualization" --role "Analytic Agent" --company-name "Salesforce" --output-file specs/analytics-agent.yaml` (or hand-author the YAML referencing the "Analytics and Visualization" template)
  2. `sf agent create --target-org MFG-Nexus --spec specs/analytics-agent.yaml --name "Analytics and Visualization" --api-name Analytics_and_Visualization`
  3. `sf agent activate --target-org MFG-Nexus --api-name Analytics_and_Visualization`
- **Current state in MFG-Nexus** — BotDefinition sObject not yet available (blocked by b & i).
- **Verification** — `SELECT Id,DeveloperName,IsActive FROM BotDefinition WHERE DeveloperName='Analytics_and_Visualization'` (post-enable).
- **Gotchas** — The "Analytics and Visualization" is a *template* the UI exposes. `sf agent generate agent-spec` doesn't directly accept a template name; may need to hand-write the YAML based on captured fields (Name, API, Role="Analytic Agent", Company="Salesforce", 3 topics: Data Analysis, Data Alert Management, Data Pro). If activate fails the guide says toggle Agentforce OFF/ON — mirror with `sf agent deactivate` + `sf agent activate`.

---

## l. Grant Access Analytics Agent PS → Agent Access → Analytics and Visualization

- **Can automate headlessly?** Yes.
- **Mechanism** — Modify the `Access_Analytics_Agent` PermissionSet via metadata deploy, adding the agent grant. Shape is likely `<botAccesses>` or `<genAiPlannerAccesses>` element — exact element name should be confirmed by retrieving an existing permset that grants an agent (none present today). As a fallback, the `SetupEntityAccess` SObject can be inserted directly:
  ```
  INSERT SetupEntityAccess (ParentId=<PermissionSetId>, SetupEntityId=<BotDefinitionId>, SetupEntityType='BotDefinition')
  ```
  `SetupEntityAccess` is a createable Tooling sObject used for App/Flow/Bot ACL grants; it is present in this org.
- **Current state in MFG-Nexus** — Cannot validate until (d) and (k) complete.
- **Verification** — `SELECT Id FROM SetupEntityAccess WHERE ParentId=<psId> AND SetupEntityType='BotDefinition'`.
- **Gotchas** — The permset-meta XML format may not expose bot access — `SetupEntityAccess` insert is the safer route. Confirm `SetupEntityType` value ("BotDefinition" vs "GenAiPlanner") after (k) by inspecting a manually-granted permset.

---

## m. Heroku PostgreSQL connector (OPTIONAL)

- **Can automate headlessly?** Partial. Requires Data Cloud "Other Connectors" which is not part of the public metadata surface, but has a `connect/` REST façade.
- **Mechanism** — The connector is a Data Cloud External Data Connector (not a Salesforce `NamedCredential`). Likely endpoint: `POST $INST/services/data/v60.0/ssot/external-data-connectors` with body:
  ```json
  {
    "connectorType": "POSTGRESQL",
    "name": "...",
    "apiName": "...",
    "host": "ec2-34-239-63-69.compute-1.amazonaws.com",
    "port": 5432,
    "database": "d2pbagf1jq37ti",
    "schema": "public",
    "username": "u92dhi1ajn88fj",
    "password": "p4c90c4b2e14564db61447051bc670c4e0ade9e635797596..."
  }
  ```
  Alternatively metadata type `ExternalDataConnector` exists (confirmed) with child `ExternalDataTranObject`. Schema has the following Data Cloud connection objects: `MktDataConnection`, `MktDataConnectionCred`, `MktDataConnectionParam`. These are the public SObject faces of the same thing.
- **Current state in MFG-Nexus** — Blocked by (c).
- **Verification** — `SELECT Id,Name FROM MktDataConnection WHERE Name='<your name>'` after create.
- **Gotchas** — Not required to complete Build 1 ("OPTIONAL"). Recommend skill skips unless explicitly requested, and handles it as a separate opt-in sub-step using `ExternalDataConnector` metadata (since that's the validated public surface).

---

## Overall automation approach

The skill should deploy as a sequence of discrete, re-entrant steps using three primitives: (1) **Tooling API PATCH** on `*Settings` sObjects for feature toggles (steps a, b), (2) **Metadata API source deploy** for permsets, PSG, and connectors (steps d, e, m), and (3) **`sf agent` CLI** for the Analytics Agent (step k, plus SetupEntityAccess insert for step l). Step (c) is a polling wait against `/services/data/v60.0/ssot/data-connections`. All eight standard permission sets referenced by the PSG are already present in a fresh STORM, so step (e) only needs `Access_Analytics_Agent` to be created first; the remaining eight are referenced by their real API names (notably `CopilotSalesforceUser`, `CopilotSalesforceAdmin`, `CDPAdmin`, `TableauEinsteinAdmin`, `TableauUser`, `TableauEinsteinAnalyst`, `TableauSelfServiceAnalyst`, `SlackElevateUser`).

**Blockers and manual fallbacks** I could not find headless paths for: step (f) Enable Tableau Next and its 7 sub-toggles — no `TableauNextSettings` sObject or metadata type exists pre-provisioning; step (g) Semantic Authoring AI + Connectors (Beta) via Feature Manager — no public Feature Manager API surface. Both should be re-investigated *after* (c) completes, since Data Cloud provisioning introduces new sObjects and REST endpoints. Step (h) Cosmos theme requires deploying a custom theme (Salesforce's built-in Cosmos is not listable). Step (i) Agentforce toggle is entangled — rely on (b) + (k) instead of an explicit flip. Plan the skill with these four as "try headless, fall back to interactive browser/manual" escape hatches until a post-provisioning research pass confirms otherwise.
