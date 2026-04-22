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

## Still Semi-Automated

- If multiple Tableau Next workspaces are visible and no stable selector or saved target exists, the system still needs a workspace-routing choice instead of guessing.
- Semantic-model request generation is automated, but live apply remains dry-run-first by design until the write contract is proven and explicit Aura inputs are available for the session.
- Semantic-model field design and object-set choice can now be manifest-derived, but human curation may still produce a better semantic model than the default all-selected-object request.

## Blocked By Org Setup Or Permissions

- Data Cloud connector creation is still an org setup step. The repo can validate connector existence and fail early, but it still does not create the connector automatically.
- Data Cloud auth still requires a dedicated alias or another valid token-exchange path with `cdp_ingest_api` scope.
- External Client App deployment still depends on org support for `CommandCenterAuth` metadata deployment and user rights to deploy it.
- Live SDM apply still requires a current explicit Aura session context, token, and cookies tied to the active org session.

## Blocked By External Platform Or API Constraints

- The repo still does not own a stable public Tableau Next semantic-model create or update API. The current write path is an inferred Aura action, so live apply cannot yet be classified as fully proven automation.
- Connector-specific Data Cloud ingest route behavior is still connector and org dependent, so generic object lookup remains part of the resilient upload path.
- The repo still does not have stable platform-backed wrappers for visualization or dashboard relationships beyond semantic-model inventory.

## Current Closest Real Meaning Of Zero-Touch After Authentication

After authenticating to the Salesforce org and, when required, the dedicated Data Cloud alias, the repo can now run through manifest target refresh, connector and stream reconciliation, upload execution, Tableau Next workspace targeting, direct semantic-model inspection, and SDM request generation without manual registry edits, manual object-name derivation, or manual request-payload construction.

## Current Boundary

The current highest-value remaining gap is not broad wiring. It is proving and productizing the live Tableau Next semantic-model write contract beyond the inferred Aura surface so the orchestration can move from `ReadyThroughDryRunOnly` to `ReadyForFullAutomation`.
