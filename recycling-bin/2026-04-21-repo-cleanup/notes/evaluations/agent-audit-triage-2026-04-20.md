# Agent Audit Triage - 2026-04-20

## Purpose

Consolidate the completed board handoffs and follow-up audits from the current implementation run into one short triage artifact.

Primary source: [CommandCenter TODO.md](../../CommandCenter%20TODO.md)

## Verified Working

- CommandCenterAuth deployment is currently reusable again. The earlier repo-local metadata path defect is stale, and the latest board evidence shows `setup-command-center-connected-app.ps1 -TargetOrg STORM_TABLEAU_NEXT` deploying successfully.
- Data Cloud auth resolution is reusable for the Sunrun targets through `salesforce-token-exchange` with the dedicated Data Cloud alias model.
- Manifest target registration is deterministic and refreshes the `sunrun-*` target rows while preserving org-specific values.
- CSV inspection, schema inference, and ingest metadata generation now share one path and produce predictable generated output under `salesforce/generated/`.
- Upload behavior is materially hardened. Retry, inspect, abort guidance, and stale `objectEndpoint` fallback behavior are present and the operator messaging was corrected during audit.
- Tableau Next preparation docs are now bounded correctly as planning and discovery-prep only, not implemented automation.

## Open Issues By Class

### Code Defects

- `scripts/salesforce/data-cloud-create-manifest-streams.ps1` still appears to miss at least one pre-existing ACTIVE stream before attempting create. Current board evidence points to the live `projects` path where `sunrun2_projects` already exists, but the resolver does not match the accepted live stream name before create.

### Stale Registry Or Config

- `notes/registries/data-cloud-targets.json` still lacks a saved connector-specific `objectEndpoint` for at least `sunrun-projects`, so uploads continue to rely on generic object lookup when the registry should already know the live endpoint.
- Some older board notes describing a local CommandCenterAuth path failure are now stale and should not be used for prioritization.

### Live Data Cloud Org-State Problems

- The org already contains live stream and connector state that constrains reconciliation, including the existing `sunrun2_projects` object and ACTIVE stream naming that the bootstrap must respect.
- Previous `409 CONFLICT` upload failures were tied to live ingest job state. Later board evidence indicates that blocker cleared, so it should be treated as transient org state rather than an active product bug unless it reappears.
- Connector creation, some stream uniqueness rules, and final live object acceptance still depend on the current Data Cloud org state rather than repo-local code alone.

## Priority Triage

1. Fix existing-stream resolution in `scripts/salesforce/data-cloud-create-manifest-streams.ps1`.
2. Capture and persist the live `objectEndpoint` values for the Sunrun targets in `notes/registries/data-cloud-targets.json`.
3. Rerun the smallest realistic single-table `projects` bootstrap and upload path after step 1 and step 2.

## Recommended Single Owner

Assign one owner to the manifest stream bootstrap path first.

Why this is the highest-value next blocker:

- It is the clearest remaining repo-local defect.
- It sits ahead of successful repeatable uploads for the `projects` table.
- It separates code repair from org-state noise better than another broad multi-phase rerun.

## Deferred Work

- Add mocked script-level regression coverage for upload fallback and timeout messaging.
- Design Tableau Next read-only discovery wrappers before any registry or setup automation work.