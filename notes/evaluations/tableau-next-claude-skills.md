# Evaluation: `Tableau-Next-Claude-Skills`

Date: 2026-04-17
Status: Snapshot-based evaluation
Source inspected: local snapshot at `C:\Users\andrew.hill\AppData\Local\Temp\1\Tableau-Next-Claude-Skills`

## Repository overview and intended audience

`Tableau-Next-Claude-Skills` is not just a skill bank. It is a Claude-first demo-builder repository aimed at Tableau Solutions Engineers. It contains two automation tracks:
- Tableau Next demo generation in Salesforce Data Cloud.
- Tableau Pulse demo generation in Tableau Cloud.

The operating model is interactive AI orchestration plus Python scripts, with machine-local secret files, Mac-centric runtime assumptions, and direct API authoring for Salesforce Data Cloud, Tableau Next, Tableau Pulse, and Tableau Cloud.

That differs from this workspace's Windows-first, PowerShell-first, task-backed, registry-backed model documented in `README.md`.

## Inventory by folder and capability area

### Root files

#### `README.md`
- Type: doc
- Purpose: end-user entry point for the Tableau Next demo builder.
- Execution model: open the repo in Claude Code, run setup conversationally, then invoke slash commands.
- Required tools and runtime assumptions: Claude Code, Python 3.10+, Mac terminal assumptions.
- Auth and secret handling assumptions: `next_orgs.json` contains local credentials and must never be committed.
- Specialization: Claude-specific, Python-specific, Tableau Next-specific, Data Cloud-specific.
- Local overlap: partial overlap with `README.md`, local Tableau/Data Cloud playbooks, and skill docs.
- Recommendation: referenced only.
- Rationale: useful framing, but the repo-level operating model conflicts with this workspace.

#### `CLAUDE.md`
- Type: skill
- Purpose: defines persona, onboarding, environment, naming rules, and operating instructions for Claude.
- Execution model: loaded as Claude repo instructions.
- Required tools and runtime assumptions: Claude Code, Python, Tableau Cloud, Salesforce APIs.
- Auth and secret handling assumptions: expects `tableau_config.json` and local secret files in the project folder.
- Specialization: strongly Claude-specific, plus Python-, Tableau Cloud-, and Tableau Next-specific.
- Local overlap: partial overlap with `.github/copilot-instructions.md`, `skills/INDEX.md`, and local prompts.
- Recommendation: adapted here.
- Rationale: contains reusable workflow knowledge but should not be copied directly as an agent control file.

#### `PEER_SETUP.md`
- Type: playbook
- Purpose: manual first-time setup for a peer user.
- Execution model: human-guided setup with connected app creation, OAuth, Data Cloud connector creation, config-file creation, and Claude command loading.
- Required tools and runtime assumptions: Mac, Python 3.13 path, Salesforce CLI optional, curl.
- Auth and secret handling assumptions: requires connected app client secret and refresh token stored in `next_config.json`.
- Specialization: Python-specific, Mac-specific, Tableau Next-specific, Data Cloud-specific.
- Local overlap: partial overlap with `playbooks/set-up-command-center-connected-app.md`, `playbooks/set-up-data-cloud-ingestion-target.md`, and the auth sections of `README.md`.
- Recommendation: adapted here.
- Rationale: setup flow is relevant, but secret handling and platform assumptions are misaligned.

#### `next_config.template.json`
- Type: template
- Purpose: local credential template for Tableau Next and Data Cloud demo automation.
- Execution model: copy to `next_config.json` and fill in secrets.
- Required tools and runtime assumptions: JSON config consumed by Python.
- Auth and secret handling assumptions: stores client secret, refresh token, and Data Cloud domain locally in the project folder.
- Specialization: Python-specific, Tableau Next-specific, Data Cloud-specific.
- Local overlap: partial overlap with local env strategy and registry model.
- Recommendation: left alone.
- Rationale: this repo should keep secrets in `.env.local` or CLI stores, not repo-local JSON credential files.

#### `next_setup.py`
- Type: script
- Purpose: interactive first-time setup for connected app auth, OAuth capture, Data Cloud token validation, connector discovery, and `next_config.json` creation.
- Execution model: interactive Python script with browser launch and local callback server.
- Required tools and runtime assumptions: Python `requests`, localhost callback, browser launch.
- Auth and secret handling assumptions: captures a refresh token and writes it to `next_config.json`.
- Specialization: Python-specific, Tableau Next-specific, Data Cloud-specific.
- Local overlap: partial overlap with `scripts/salesforce/setup-command-center-connected-app.ps1`, `scripts/salesforce/data-cloud-login-web.ps1`, and related playbooks.
- Recommendation: adapted here.
- Rationale: the workflow logic is valuable, but the implementation should be translated into PowerShell and the current secret model.

#### `next_teardown.py`
- Type: script
- Purpose: discovers and deletes demo assets in safe order: dashboards, visualizations, semantic model, workspace, and optional Data Cloud assets.
- Execution model: interactive Python teardown with confirmation gates.
- Required tools and runtime assumptions: Python `requests`, Salesforce REST APIs.
- Auth and secret handling assumptions: uses refresh-token configuration from `next_config.json`.
- Specialization: Python-specific, Tableau Next-specific, Data Cloud-specific.
- Local overlap: no strong equivalent in this repo.
- Recommendation: recreated here.
- Rationale: this fills a real workflow gap: deterministic cleanup for Tableau Next demo assets.

#### `requirements.txt`
- Type: config
- Purpose: Python dependency manifest.
- Execution model: `pip install -r requirements.txt`.
- Required tools and runtime assumptions: Python, pandas, numpy, `tableauserverclient`, `tableauhyperapi`, `requests`.
- Auth and secret handling assumptions: none directly.
- Specialization: Python-specific.
- Local overlap: no direct equivalent because this repo is not Python-centric.
- Recommendation: referenced only.
- Rationale: useful only if specific scripts are selectively ported.

#### `.gitignore`
- Type: config
- Purpose: excludes secrets, generated outputs, and local memory.
- Execution model: Git hygiene.
- Required tools and runtime assumptions: none.
- Auth and secret handling assumptions: explicitly excludes `tableau_config.json`, `next_config.json`, `next_orgs.json`, private keys, and generated scripts/guides.
- Specialization: none.
- Local overlap: partial overlap with secret-handling conventions in `README.md`.
- Recommendation: adapted here.
- Rationale: useful as a checklist of artifacts to avoid tracking if Tableau Next support is added.

### Claude command files

#### `.claude/commands/build-next-demo.md`
- Type: skill
- Purpose: end-to-end specification for building Tableau Next demos through Claude, including org selection, credential setup, data design, Data Cloud ingestion, semantic model creation, metrics, visualizations, dashboards, clone mode, concierge optimization, and post-build guidance.
- Execution model: slash command driving Claude to generate and run code.
- Required tools and runtime assumptions: Claude Code, Python 3.13, `requests`, `pandas`, `numpy`, `pyyaml`, Salesforce/Data Cloud/Tableau Next APIs.
- Auth and secret handling assumptions: reads `next_orgs.json` or `next_config.json`.
- Specialization: strongly Claude-specific, Python-specific, Tableau Next-specific, Data Cloud-specific.
- Local overlap: no direct equivalent; partial overlap with local Data Cloud auth and upload skills.
- Recommendation: adapted here.
- Rationale: high-value domain knowledge, but too tied to Claude slash-command behavior and local Python generation.

#### `.claude/commands/build-pulse-demo.md`
- Type: skill
- Purpose: end-to-end Tableau Pulse demo generation with Hyper creation, Tableau Cloud publishing, Pulse metric definitions, groups, and subscriptions.
- Execution model: slash command driving Claude-generated Python.
- Required tools and runtime assumptions: Claude Code, Python, `tableauhyperapi`, `tableauserverclient`, Tableau Cloud REST/Pulse APIs.
- Auth and secret handling assumptions: reads `tableau_config.json` with PAT secret.
- Specialization: Claude-specific, Python-specific, Tableau Cloud-specific.
- Local overlap: partial overlap with `scripts/tableau/publish-file.ps1`, `skills/publish-or-inspect-tableau-content.md`, and `skills/tableau-cloud-auth-bootstrap.md`.
- Recommendation: deferred or largely left alone.
- Rationale: interesting, but this workspace is not currently organized around Pulse metric-authoring automation.

### Reference Files

#### `Reference Files/api-reference.md`
- Type: doc
- Purpose: concrete Tableau Next REST endpoint reference for semantic models, visualizations, and dashboards.
- Execution model: operator or agent reference.
- Required tools and runtime assumptions: Salesforce REST APIs.
- Auth and secret handling assumptions: bearer token access.
- Specialization: Tableau Next-specific.
- Local overlap: no direct equivalent.
- Recommendation: adapted here.
- Rationale: strong candidate for local reference material or playbook appendix.

#### `Reference Files/authentication.md`
- Type: doc
- Purpose: SF CLI-based auth patterns and helper wrappers for Tableau Next API calls.
- Execution model: shell helper and Python helper.
- Required tools and runtime assumptions: `sf` CLI, `jq`, Bash, Python `requests`.
- Auth and secret handling assumptions: derives tokens from existing SF CLI auth.
- Specialization: Salesforce CLI-specific, Unix-leaning, Tableau Next-specific.
- Local overlap: strong conceptual overlap with `scripts/salesforce/login-web.ps1`, `skills/salesforce-org-login-and-alias-registration.md`, and the auth model in `README.md`.
- Recommendation: adapted here.
- Rationale: the auth approach aligns better with this repo than the upstream refresh-token JSON pattern.

#### `Reference Files/workflow.md`
- Type: workflow
- Purpose: required creation workflow for dashboards and visualizations, emphasizing discovery, chart selection, templates, and POST sequence.
- Execution model: procedural guidance.
- Required tools and runtime assumptions: Python helper scripts and Tableau Next API.
- Auth and secret handling assumptions: token-based API access.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: adapted here.
- Rationale: high-value procedural knowledge for future Tableau Next skills or playbooks.

#### `Reference Files/chart-catalog.md`
- Type: doc
- Purpose: working visualization JSON patterns and chart payload structure.
- Execution model: copy/adapt payloads or feed generators.
- Required tools and runtime assumptions: Tableau Next visualization API.
- Auth and secret handling assumptions: none beyond API auth.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: adapted here.
- Rationale: valuable as a source of tested API structure.

#### `Reference Files/templates-guide.md`
- Type: doc
- Purpose: catalog of visualization templates and dashboard patterns, with selection rules and automation guidance.
- Execution model: use generator scripts instead of hand-building JSON.
- Required tools and runtime assumptions: Python template scripts.
- Auth and secret handling assumptions: none beyond API auth.
- Specialization: Tableau Next-specific, Python-specific.
- Local overlap: no equivalent.
- Recommendation: adapted here.
- Rationale: one of the strongest selective-adoption targets.

#### `Reference Files/scripts-guide.md`
- Type: doc
- Purpose: explains helper scripts such as `discover_sdm.py`, `generate_viz.py`, `generate_dashboard.py`, and template application workflow.
- Execution model: run helper scripts from a skill directory.
- Required tools and runtime assumptions: Python 3.8+, `requests`, skill-install directory assumptions.
- Auth and secret handling assumptions: CLI/token assumptions.
- Specialization: Python-specific, Cursor or Claude skill-install-path-specific.
- Local overlap: no equivalent.
- Recommendation: referenced only.
- Rationale: useful for understanding the intended automation stack, but too coupled to scripts not present in the snapshot and to a different agent platform.

#### `Reference Files/troubleshooting.md`
- Type: doc
- Purpose: common Tableau Next API failures and fixes.
- Execution model: lookup guide during development.
- Required tools and runtime assumptions: Tableau Next payload authoring.
- Auth and secret handling assumptions: none.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: adapted here.
- Rationale: high signal and directly reusable as troubleshooting knowledge.

#### `Reference Files/examples.md`
- Type: doc
- Purpose: real-world example builds extracted from production-style deployments.
- Execution model: study and adapt sample payloads and workflow.
- Required tools and runtime assumptions: `curl` and Tableau Next APIs.
- Auth and secret handling assumptions: bearer token access.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: adapted here.
- Rationale: good source material for future local examples or test fixtures.

#### `Reference Files/format-patterns.md`
- Type: doc
- Purpose: number and formatting conventions for Tableau Next visualizations.
- Execution model: apply in visualization payload formatting.
- Required tools and runtime assumptions: Tableau Next API formatting JSON.
- Auth and secret handling assumptions: none.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: adapted here.
- Rationale: useful supporting reference once Tableau Next authoring exists locally.

### Dashboard example templates

#### `Reference Files/Dashboard Examples/README.md`
- Type: doc
- Purpose: explains the dashboard template JSON set and intended customization flow.
- Execution model: template selection guidance.
- Required tools and runtime assumptions: Python dashboard template loader.
- Auth and secret handling assumptions: none.
- Specialization: Tableau Next-specific, Python-specific.
- Local overlap: no equivalent.
- Recommendation: adapted here.
- Rationale: useful if dashboard templating is brought into this repo.

#### `Reference Files/Dashboard Examples/F_layout.json`
- Type: template
- Purpose: executive dashboard layout.
- Execution model: loaded and customized programmatically.
- Required tools and runtime assumptions: Tableau Next dashboard API.
- Auth and secret handling assumptions: none.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: referenced only initially.
- Rationale: useful as a design specimen, but raw JSON should not be imported before local tooling exists.

#### `Reference Files/Dashboard Examples/Z_Layout.json`
- Type: template
- Purpose: Z-pattern dashboard layout.
- Execution model: programmatic customization.
- Required tools and runtime assumptions: Tableau Next dashboard API.
- Auth and secret handling assumptions: none.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: referenced only initially.
- Rationale: same as above.

#### `Reference Files/Dashboard Examples/Performance_Overview_Full_Page.json`
- Type: template
- Purpose: performance overview dashboard layout.
- Execution model: programmatic customization.
- Required tools and runtime assumptions: Tableau Next dashboard API.
- Auth and secret handling assumptions: none.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: referenced only initially.
- Rationale: useful reference, but not a direct import target.

#### `Reference Files/Dashboard Examples/C360_Metrics_Full_View.json`
- Type: template
- Purpose: customer-360 metrics dashboard layout.
- Execution model: programmatic customization.
- Required tools and runtime assumptions: Tableau Next dashboard API.
- Auth and secret handling assumptions: none.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: referenced only initially.
- Rationale: same as above.

#### `Reference Files/Dashboard Examples/C360_Metrics_Half.json`
- Type: template
- Purpose: half-width customer-360 dashboard layout.
- Execution model: programmatic customization.
- Required tools and runtime assumptions: Tableau Next dashboard API.
- Auth and secret handling assumptions: none.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: referenced only initially.
- Rationale: same as above.

#### `Reference Files/Dashboard Examples/C360_Metrics_Vertical_View.json`
- Type: template
- Purpose: vertical customer-360 dashboard layout.
- Execution model: programmatic customization.
- Required tools and runtime assumptions: Tableau Next dashboard API.
- Auth and secret handling assumptions: none.
- Specialization: Tableau Next-specific.
- Local overlap: no equivalent.
- Recommendation: referenced only initially.
- Rationale: same as above.

## Comparison against this repo's current workflow model

What this repo already does well:
- Salesforce login and alias management.
- Data Cloud upload workflows and registry-backed targets.
- Tableau Cloud auth, listing, inspection, and publishing.
- Windows-first PowerShell automation.
- Explicit secret separation via local env plus tracked non-secret registries.
- Durable playbook and skill extraction model.

Where the upstream repo is stronger:
- Tableau Next asset creation guidance.
- Semantic model authoring details.
- Visualization and dashboard template knowledge.
- Cleanup or teardown workflows.
- Troubleshooting for Tableau Next API payloads.
- Example payload and reference library.

Where this repo is stronger:
- Operational hygiene.
- Cross-machine repeatability on Windows.
- Auth normalization around Salesforce CLI and registries.
- Separation between automation, playbooks, and tracked metadata.

## Assets that are strong candidates for selective adoption

1. Authentication patterns from `Reference Files/authentication.md`, adapted to Salesforce CLI aliases and PowerShell wrappers.
2. Tableau Next workflow and reference material from `workflow.md`, `api-reference.md`, `chart-catalog.md`, `templates-guide.md`, `troubleshooting.md`, and `format-patterns.md`.
3. A new teardown workflow inspired by `next_teardown.py`.
4. A new Tableau Next setup playbook derived from `PEER_SETUP.md` and `next_setup.py`, but using this repo's secret strategy.
5. A future local skill or playbook for Tableau Next semantic-model and dashboard authoring, extracting domain guidance from `build-next-demo.md` without keeping the Claude-specific command format.

## Assets that should not be adopted as-is

1. `CLAUDE.md` and `.claude/commands/*.md` as command files.
2. `next_config.template.json` and the `next_config.json` secret-file pattern.
3. `next_setup.py` as a direct implementation.
4. `build-pulse-demo.md` as a near-term target.
5. Raw dashboard JSON templates as imported assets before local generator or wrapper tooling exists.

## Missing capabilities in this repo that the upstream repo highlights

1. Tableau Next setup and auth playbook.
2. Tableau Next API reference or helper wrappers.
3. Semantic model discovery and inspection tooling.
4. Visualization and dashboard creation guidance or generators.
5. Tableau Next teardown and cleanup tooling.
6. Troubleshooting notes for Tableau Next API payload errors.
7. Optional example or template library for dashboard layouts.

## Recommended phased adoption plan

1. Phase 1: add documentation only.
   - Create a Tableau Next playbook and a concise reference pack under `playbooks/` or a new reference area.
   - Base it on the upstream authentication, workflow, troubleshooting, and API reference docs.
   - Rewrite for PowerShell, Windows, and Salesforce CLI alias usage.

2. Phase 2: add one setup path.
   - Create a PowerShell-based Tableau Next setup workflow analogous to `playbooks/set-up-command-center-connected-app.md` and `scripts/salesforce/data-cloud-login-web.ps1`.
   - Keep secrets in `.env.local` or CLI stores, not JSON config files.

3. Phase 3: add teardown.
   - Recreate the core value of `next_teardown.py` as a local cleanup script and playbook.

4. Phase 4: add discovery helpers.
   - Introduce thin wrappers for semantic-model listing and inspection, and optionally workspace, visualization, and dashboard listing.

5. Phase 5: add authoring references, not full auto-build.
   - Extract the tested rules around field descriptions, metric design, insight types, formatting, and dashboard patterns into local skills or playbooks before attempting a full demo-builder.

6. Phase 6: decide later on generator tooling.
   - Only after the above proves useful should this repo consider Python helpers or JSON generators for Tableau Next assets.

## Documentation updates this repo would eventually need if adoption happens

1. Add a Tableau Next workflow section to `README.md`.
2. Add Tableau Next playbooks under `playbooks/`.
3. Add Tableau Next skills to `skills/INDEX.md` if those workflows become repeated enough.
4. Consider a new registry or an extension of existing registries if non-secret Tableau Next target metadata needs tracking.

## Reject or defer list

Reject:
- Direct import of upstream command files.
- Direct import of secret-bearing config patterns.
- Replacing this repo's auth model with refresh-token JSON files.
- Mac-specific setup instructions.

Defer:
- Pulse automation.
- Python generator stack.
- Raw dashboard template import.
- Full AI-driven end-to-end demo builder.

## Risks of wholesale import or submodule use

- Secret-handling regression.
- Platform mismatch.
- Overcoupling to Claude-specific workflows.
- Pulling in a Python-first architecture into a PowerShell-first repo.
- Expanding scope into Pulse and full demo generation before the core Tableau Next plumbing exists locally.

## Decision

Selectively mine the upstream repo for Tableau Next knowledge, not for its execution model. The best near-term work is documentation, setup normalization, and teardown. The wrong move is importing the Claude commands or the credential-file pattern.
