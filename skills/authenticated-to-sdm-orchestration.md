# Authenticated To SDM Orchestration

## Purpose

Run the repo-native authenticated onboarding-to-SDM path with minimal operator decisions after authentication, and leave behind a machine-readable readiness result.

## Required Inputs

- Manifest path
- Standard Salesforce org alias
- Dedicated Data Cloud alias
- Data Cloud source name and naming prefix inputs
- Tableau Next workspace selector or saved target key
- Semantic-model API name and label

## Prerequisites

- Salesforce CLI auth works for the standard org alias.
- Data Cloud is provisioned if the run should reach stream bootstrap or upload.
- The manifest dataset is the intended source of truth.
- The manifest publish contract accurately describes the relationships that should appear in the semantic model.

## Exact Steps

1. Authenticate to the standard Salesforce org alias.
2. Run `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1` with the manifest, alias, naming, and Tableau Next inputs.
3. Read the emitted readiness state file and classification.
4. Add `-ApplySemanticModel` when you want the orchestration to create the semantic model and publish manifest relationships live through the supported semantic-layer REST endpoints.

## Validation

- The orchestration state file exists.
- Data Cloud target registration, connector preflight, and stream bootstrap complete or return explicit blockers.
- Tableau Next target resolution either reuses a saved target or registers one from discovery.
- Semantic-model spec and request generation succeed when the path reaches Tableau Next.
- Live apply persists the model and the manifest relationships when `-ApplySemanticModel` is used.
- The current repo-native orchestration covers semantic model create or update plus relationship sync only. Calculated fields (`_clc`) and semantic metrics (`_mtc`) are not yet part of this workflow.

## Current Boundary

- Use this orchestration when the goal is to create or update a Tableau Next semantic model from manifest-backed Data Cloud objects and relationships.
- If the goal also includes semantic-layer enrichment such as calculated measurements, calculated dimensions, or dashboard-ready semantic metrics, treat that as a separate follow-on step after model creation.
- The external workspace repo `tableau-skills-external-repo` demonstrates supported REST patterns for `POST /ssot/semantic/models/{modelName}/calculated-measurements`, `calculated-dimensions`, and `metrics` using existing Salesforce CLI auth.

## Failure Modes

- Salesforce auth, Data Cloud auth, or CommandCenterAuth deployment fails.
- The Data Cloud connector is missing.
- Workspace routing is ambiguous.
- Manifest relationships do not match the active Data Lake Object field set.
- The operator expects KPI-ready semantic metrics or calculated fields to exist immediately after orchestration, but the current workflow only publishes the base semantic model and relationships.

## Cleanup or Rollback

- Remove temporary request payloads from `tmp/` if they are no longer needed.
- Re-register the Tableau Next target if the saved workspace changed.
- Rerun the orchestration after org setup or permission fixes; the manifest-backed phases are intended to be rerunnable.
- Add a separate semantic enrichment step if the published model still needs `_clc` or `_mtc` assets before visualization work.
