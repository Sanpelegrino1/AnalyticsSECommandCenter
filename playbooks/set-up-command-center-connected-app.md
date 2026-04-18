# Set Up Command Center Auth App

## Purpose

Create and reuse a repo-owned external client app so Command Center agents can bootstrap Salesforce CLI and Data Cloud auth from a known, documented path.

This playbook assumes the repo does not reuse any pre-existing external client app already found in an org.

## Inputs

- Salesforce org alias
- Existing browser-based Salesforce auth to the org

## Prerequisites

- The user is already logged into the org with Salesforce CLI.
- The org allows external client app metadata deployment.
- The user has permission to deploy external client app metadata and manage External Client Apps.
- Salesforce Data Cloud is provisioned in the org.
- The login user can self-authorize OAuth apps and request `cdp_ingest_api`.
- Localhost callback auth used by Salesforce CLI is allowed by the org's session and network controls.

## New Org Settings To Confirm

- External Client Apps are available in Setup and deployable via metadata.
- Data Cloud is enabled.
- An Ingestion API connector exists.
- A data stream exists for each Data Cloud object you plan to ingest into.
- The target object's tenant endpoint, source name, object name, and object endpoint are known and will be registered in `notes/registries/data-cloud-targets.json`.
- The deploying/admin user can authorize the `CommandCenterAuth` app.

## Exact Steps

1. Deploy the repo-owned auth app.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\setup-command-center-connected-app.ps1 -TargetOrg STORM_TABLEAU_NEXT
```

2. Optionally launch browser auth against the deployed app immediately after deploy.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\setup-command-center-connected-app.ps1 -TargetOrg STORM_TABLEAU_NEXT -LaunchLogin -SetDefault
```

3. If Data Cloud auth is the goal, validate the post-login token exchange.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-get-access-token.ps1 -AsJson
```

## Validation

- The deploy succeeds for the `ExternalClientApplication` and related `ExtlClntApp*` metadata for `CommandCenterAuth`.
- The external client app appears in Setup under External Client App Manager.
- Browser auth succeeds when using `scripts/salesforce/data-cloud-login-web.ps1`.
- Data Cloud token exchange resolves if the org accepts the `cdp_ingest_api` scope.
- No org-owned external client app metadata from prior work is required.

## Failure Modes

- External client app deployment is blocked because the org has not opted in to External Client Apps metadata.
- The org rejects the OAuth settings or policy metadata for `cdp_ingest_api`.
- Data Cloud auth still fails because the org requires additional Data Cloud setup beyond the app itself.
- The org is missing the Ingestion API connector or data stream configuration, so auth succeeds but uploads still fail.

## Cleanup or Rollback

- Delete the `CommandCenterAuth` external client app metadata from the org if this path is abandoned.
- Remove the local CLI auth alias and reauthorize with a different client app if needed.

## Commands and Links

- `scripts/salesforce/setup-command-center-connected-app.ps1`
- `scripts/salesforce/data-cloud-login-web.ps1`
- `salesforce/force-app/main/default/externalClientApps/CommandCenterAuth.eca-meta.xml`