# :blue_book: SE-Command-Center Product Spec

## :sparkles: Product Name

SE-Command-Center

## :dart: Product Summary

SE-Command-Center is the repo-native workflow and operator surface that takes an already authenticated Salesforce operator from stable Data Cloud dataset readiness to a live Tableau Next semantic data model using repeatable PowerShell wrappers, saved Tableau Next targets, manifest-backed object mappings, and semantic-layer REST automation.

This product exists to replace brittle one-off setup and historical Aura-era experimentation with a repeatable, inspectable, and agent-friendly path.

## :boom: Problem Statement

Creating user-ready semantic data models for demo or solution-engineering scenarios is slow and error-prone when operators must:
- rediscover the correct org, Data Cloud, and workspace context each time
- manually infer object names and relationships from live state
- hand-build semantic-model payloads
- rely on outdated unsupported paths and scratch artifacts

The product solves this by making the supported path deterministic, inspectable, and reusable.

## :raising_hands: Target Users

Primary users:
- solution engineers
- demo engineers
- technical sellers
- internal operators maintaining repeatable Tableau Next demo datasets

Secondary users:
- agents working inside this repo
- maintainers cleaning up or extending SDM automation

## :briefcase: Jobs To Be Done

When a dataset is already stable in Data Cloud, the user wants to:
- confirm it is still healthy
- resolve the correct Tableau Next workspace context
- generate a semantic-model request from the manifest and active objects
- apply that semantic model reliably
- validate the result quickly

## :white_check_mark: Goals

- make the manifest-backed SDM creation path the default operator path
- minimize manual workspace and object mapping work
- keep the workflow safe for repeated demo prep
- keep secrets out of tracked files
- keep artifacts understandable enough for handoff and debugging
- preserve a clear distinction between proven paths and secondary paths

## :no_entry_sign: Non-Goals

- full Tableau Next dashboard and visualization lifecycle management
- generalized support for every possible object-only request shape
- secret storage inside the repo
- backward support for historical Aura workflows as a first-class path
- teardown automation for all generated assets

## :building_construction: Scope

In scope:
- Salesforce org auth reuse through CLI aliases
- dedicated Data Cloud alias support when token exchange is required
- manifest-backed Data Cloud target readiness
- saved Tableau Next target registration and inspection
- semantic-model request generation
- semantic-model live apply
- semantic-model validation

Out of scope:
- dashboard authoring
- visualization generation
- semantic-model teardown and lifecycle cleanup beyond manual operator control

## :gear: Core Capabilities

### 1. Context Resolution

The system resolves:
- Salesforce org alias
- Data Cloud alias
- manifest-backed target set
- Tableau Next saved target
- workspace id and semantic-model routing context

### 2. Request Generation

The system can:
- derive semantic-model inputs from manifest-backed dataset structure
- build reusable request/spec artifacts in `tmp/`
- preserve a reviewable intermediate output before live apply

### 3. Live Apply

The system can:
- apply the semantic model through the supported semantic-layer REST path
- persist semantic relationships from the manifest-backed design
- return a model id and validation state

### 4. Inspection And Validation

The system can:
- inspect the saved target before creation
- inspect semantic-model inventory
- inspect a created semantic model directly
- call validation and return a clear validity result

## :map: User Workflow

Typical workflow:

1. Operator confirms Data Cloud ingestion health.
2. Operator confirms saved Tableau Next target and workspace context.
3. Operator generates the semantic-model request from the manifest-backed path.
4. Operator applies the semantic model.
5. Operator validates the created model.
6. Operator hands off the resulting model id and request artifacts.

## :package: Inputs

Required inputs:
- manifest path
- Tableau org alias
- Data Cloud alias when needed
- Tableau Next target key or workspace selector
- model API name
- model label

Derived inputs:
- active Data Cloud object identities
- manifest joins and relationship graph
- workspace routing metadata from the saved target registry

## :outbox_tray: Outputs

Primary outputs:
- semantic-model spec artifact
- semantic-model request artifact
- applied semantic model id
- validation result

Secondary outputs:
- machine-readable orchestration state
- updated operator confidence about dataset readiness and workspace routing

## :card_file_box: Key System Components

Primary scripts:
- `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1`
- `scripts/tableau/upsert-next-semantic-model.ps1`
- `scripts/tableau/inspect-next-target.ps1`
- `scripts/tableau/inspect-next-semantic-model.ps1`
- `scripts/tableau/list-next-semantic-models.ps1`

Primary registries:
- `notes/registries/data-cloud-targets.json`
- `notes/registries/tableau-next-targets.json`

Primary documentation:
- `README.md`
- `playbooks/prepare-tableau-next-semantic-model.md`

## :triangular_ruler: Functional Requirements

### FR1. Alias-Driven Auth Reuse

The product must reuse Salesforce CLI aliases instead of introducing tracked credentials.

### FR2. Manifest-Backed Request Generation

The product must support a manifest-backed request generation path that can emit a local artifact before apply.

### FR3. Saved Target Support

The product must support a saved Tableau Next target as the preferred workspace resolution path.

### FR4. Live Semantic-Model Apply

The product must be able to apply a semantic model through the supported REST-based semantic-layer path.

### FR5. Validation

The product must expose a direct validation result after apply or on demand for an existing model.

### FR6. Inspectability

The product must leave enough output artifacts for operators and agents to understand what happened without re-deriving the full request.

## :shield: Non-Functional Requirements

- predictable Windows-first execution through PowerShell
- safe handling of secrets and auth material
- repeatable operator workflow with minimal branch logic
- readable intermediate artifacts for debugging and handoff
- compatibility with agent-driven operation inside VS Code

## :white_check_mark: Acceptance Criteria

The product is successful when:
- an operator can start from a stable dataset and existing auth
- the system generates a semantic-model request without manual payload authoring
- the live apply returns a semantic model id
- the created model validates successfully
- the operator can inspect the result from repo-native scripts
- the workflow is documented clearly enough for reuse by another operator or agent

## :bar_chart: Success Metrics

Suggested product metrics:
- time from ready dataset to validated semantic model
- number of manual edits required to the request before first successful apply
- number of successful reruns on the same dataset with no registry drift
- rate of failures caused by routing/config issues versus platform issues

## :warning: Known Constraints

- the strongest proven path is saved target + manifest-backed spec
- the object-only path is not yet the preferred default
- dashboard and visualization automation are not part of the current product
- final success still depends on the health of the live Data Cloud dataset and Tableau Next workspace context

## :rotating_light: Risks

- registry drift causes object or workspace mismatch
- manifest join assumptions drift from live DLO structure
- operators use stale scratch artifacts instead of current generated files
- future contributors accidentally revive old Aura-era approaches as if they were supported

## :construction_worker: Operational Guardrails

- treat the recycling-bin area as retired history, not active implementation guidance
- keep only current supported request/spec/state artifacts in the active `tmp/` tree
- prefer saved targets over ad hoc workspace ids where possible
- fix registry truth first before changing request generation logic

## :seedling: Future Enhancements

Reasonable next expansions:
- visualization and dashboard discovery wrappers
- stronger troubleshooting notes tied to real failure outputs
- safer teardown helpers for semantic-model assets
- normalization of the object-only request path until it matches the manifest-backed path more closely

## :memo: Product Positioning

This product should be described internally as:

> a repo-native, manifest-backed, alias-driven path for taking a stable Data Cloud dataset to a validated Tableau Next semantic data model with minimal manual payload work.

## :handshake: Final Product Promise

If the dataset is stable, the target is registered, and auth is already working, SE-Command-Center should let an operator move from readiness check to validated semantic model without falling back to historical unsupported flows.
