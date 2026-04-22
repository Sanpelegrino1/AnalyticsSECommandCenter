# Authenticated To SDM Gap Report - 2026-04-20

## Purpose

Record the current repo-local automation boundary for the authenticated user -> Data Cloud bootstrap -> Tableau Next semantic-model path.

## Now Fully Automated After Authentication

- `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1` can verify standard Salesforce auth, deploy or re-verify `CommandCenterAuth`, refresh manifest-derived Data Cloud targets, validate Data Cloud token exchange, preflight the Ingestion API connector, reconcile live streams, and emit a machine-readable readiness state.
- Manifest-backed Data Cloud target rows are deterministic and refresh without manual registry edits.
- Stream bootstrap reuses compatible live schemas and ACTIVE streams, captures accepted object identities, and preserves or refreshes connector-specific `objectEndpoint` values.
- Upload execution is repo-native through the current Data Cloud scripts, including job inspection and resilient fallback behavior.
- Tableau Next workspace inventory, semantic-model inventory, target registration, target inspection, direct semantic-model inspection, and semantic-model request generation are repo-native.
- A saved Tableau Next target can now be registered from a stable workspace selector such as `WorkspaceDeveloperName`, not only a manually copied workspace id.
- Live semantic-model create, relationship publish, direct model detail inspection, and model validation are now repo-native through the supported semantic-layer REST endpoints plus the current helper and orchestration surfaces.

## Still Semi-Automated

- If multiple Tableau Next workspaces are visible and no stable selector or saved target exists, the system still needs a workspace-routing choice instead of guessing.
- The closest fully proven publish path is saved target plus manifest-backed spec. The narrower object-only helper path without a manifest-backed spec still has a smaller unproven request-shape gap.
- Semantic-model field design and object-set choice can now be manifest-derived, but human curation may still produce a better semantic model than the default generated request.

## Blocked By Org Setup Or Permissions

- Data Cloud connector creation is still an org setup step. The repo can validate connector existence and fail early, but it still does not create the connector automatically.
- Data Cloud auth still requires a dedicated alias or another valid token-exchange path with `cdp_ingest_api` scope.
- External Client App deployment still depends on org support for `CommandCenterAuth` metadata deployment and user rights to deploy it.
- A standard Salesforce CLI org alias still has to exist first. The orchestration is proven after that auth boundary, not yet as a brand-new-org one-browser cold start.

## Blocked By External Platform Or API Constraints

- Connector-specific Data Cloud ingest route behavior is still connector and org dependent, so generic object lookup remains part of the resilient upload path.
- The repo still does not have stable platform-backed wrappers for visualization or dashboard relationships beyond semantic-model inventory.
- Data Cloud connector creation still remains outside repo control in the current org model.

## Current Closest Real Meaning Of Zero-Touch After Authentication

After a usable standard Salesforce CLI org session exists and, when required, the dedicated Data Cloud alias can resolve through token exchange or login bootstrap, the repo can now run through manifest target refresh, connector and stream reconciliation, upload execution, Tableau Next workspace targeting, direct semantic-model inspection, semantic-model publish, relationship publish, and model validation without manual registry edits, manual object-name derivation, or manual request-payload construction.

## Current Boundary

The current highest-value remaining gap is no longer broad wiring. It is closing the narrower object-only semantic-model create gap so ad hoc `-ObjectApiName` publishing is as reliable as the already proven manifest-backed spec path.
