# Set Up Command Center Auth App

## Purpose

Create and reuse a repo-owned external client app so Command Center agents can bootstrap Salesforce CLI and Data Cloud auth from a known, documented path.

This playbook assumes the repo does not reuse any pre-existing external client app already found in an org.

The current default path generates a per-org `CommandCenterAuth` client id during deployment so a second org does not reuse a stale consumer key and trip cross-org OAuth blocking.

## Inputs

- Standard Salesforce org alias used for deployment and Setup access
- Separate Data Cloud alias used only for CommandCenterAuth login and token exchange
- Existing browser-based Salesforce auth to the org

## Prerequisites

- The user is already logged into the org with Salesforce CLI.
- The org allows external client app metadata deployment.
- The user has permission to deploy external client app metadata and manage External Client Apps.
- Salesforce Data Cloud is provisioned in the org.
- The login user can self-authorize OAuth apps and request `cdp_ingest_api`.
- Localhost callback auth used by Salesforce CLI is allowed by the org's session and network controls.
- The operator can complete one browser authorization for the dedicated Data Cloud alias, or copy the redirected localhost callback URL back into the script if the local listener times out.

## New Org Settings To Confirm

- External Client Apps are available in Setup and deployable via metadata.
- Data Cloud is enabled.
- An Ingestion API connector exists. For a new org, prefer the generic shared name `command_center_ingest_api`.
- If you want Command Center to create the streams, the operator knows the manifest path, source name, and object naming scheme that should be provisioned.
- The target object's tenant endpoint, source name, object name, and object endpoint are known and will be registered in `notes/registries/data-cloud-targets.json`.
- The deploying/admin user can authorize the `CommandCenterAuth` app.

## Exact Steps

1. Log into the org with the normal Salesforce alias if that has not already been done.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\login-web.ps1 -Alias STORM_TABLEAU_NEXT -InstanceUrl https://your-domain.my.salesforce.com
```

2. Deploy the repo-owned auth app with the normal org alias.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\setup-command-center-connected-app.ps1 -TargetOrg STORM_TABLEAU_NEXT
```

Expected result:

- The script deploys `CommandCenterAuth` into the target org.
- The script derives an org-specific Data Cloud client id from the org id.
- The script stores that non-secret client id in `notes/registries/salesforce-orgs.json` for the target alias.

3. If you want to bootstrap Data Cloud auth immediately, launch browser auth with a separate Data Cloud alias.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\setup-command-center-connected-app.ps1 -TargetOrg STORM_TABLEAU_NEXT -DataCloudAlias STORM_TABLEAU_NEXT_DC -LaunchLogin
```

4. If you already deployed the app earlier, you can run the Data Cloud login directly.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-login-web.ps1 -Alias STORM_TABLEAU_NEXT_DC -InstanceUrl https://your-domain.my.salesforce.com -ValidateAfterLogin
```

Default behavior now uses Salesforce CLI web login with the org-specific `CommandCenterAuth` client id, so the dedicated Data Cloud alias becomes a normal CLI session instead of depending on a repo-managed localhost callback listener.

If the browser flow reaches the login and consent page but the local callback listener times out, rerun the same command with the redirected localhost URL:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-login-web.ps1 -Alias STORM_TABLEAU_NEXT_DC -CallbackUrl "http://localhost:1718/OauthRedirect?code=...&state=..." -ValidateAfterLogin
```

Use that callback form only when you intentionally choose the manual fallback path or need to resume a previously timed-out manual OAuth attempt. The script saves the pending PKCE verifier and state under `tmp/data-cloud-oauth/<alias>.json` so the callback rerun reuses the original browser session instead of generating a mismatched verifier.

5. Validate the post-login token exchange and confirm which auth source is being used.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\salesforce\data-cloud-get-access-token.ps1 -AsJson
```

Expected result:

- `tokenSource` should normally be `salesforce-cli-session` for the dedicated Data Cloud alias.
- `salesforceAlias` should match the dedicated Data Cloud alias, not the standard org alias.
- `salesforce-cli-session` is the preferred interactive path.
- Refresh-token values in `.env.local` remain fallback only.
- `notes/registries/salesforce-orgs.json` should contain the target org alias with `dataCloudClientId` populated.

## Dependency Chain

1. `scripts/salesforce/login-web.ps1` establishes the standard org alias.
2. `scripts/salesforce/setup-command-center-connected-app.ps1` deploys the repo-owned `CommandCenterAuth` metadata.
3. Salesforce Setup must still allow the user to authorize that app and must already have Data Cloud provisioned.
4. `scripts/salesforce/data-cloud-login-web.ps1` stores only local auth values for the separate Data Cloud alias.
5. `scripts/salesforce/data-cloud-get-access-token.ps1` proves the token exchange path works before any upload.

## Validation

- The deploy succeeds for the `ExternalClientApplication` and related `ExtlClntApp*` metadata for `CommandCenterAuth`.
- The external client app appears in Setup under External Client App Manager.
- Browser auth succeeds when using `scripts/salesforce/data-cloud-login-web.ps1` with a dedicated Data Cloud alias.
- Data Cloud token exchange resolves if the org accepts the `cdp_ingest_api` scope.
- `data-cloud-get-access-token.ps1 -AsJson` reports the auth source through `tokenSource`.
- No org-owned external client app metadata from prior work is required.
- A second org does not reuse the same `DATACLOUD_CLIENT_ID` value from an earlier org deployment.

## Manual Setup Still Required

- Confirm the app is visible in External Client App Manager.
- Confirm the OAuth policy allows the intended users to self-authorize the app.
- Confirm Data Cloud is provisioned and the user can grant `cdp_ingest_api`.
- Create or verify the shared Ingestion API connector. For a new org, prefer `command_center_ingest_api` and save it in `notes/registries/salesforce-orgs.json` as `dataCloudSourceName`.
- Deploy any desired generated metadata from `salesforce/generated/<sourceName>/` through the Salesforce metadata workflow if you want that local source pushed into the org.

## What Is Now Automated After Auth Works

- `scripts/salesforce/data-cloud-register-manifest-targets.ps1` can derive stable dataset target rows from a manifest.
- `scripts/salesforce/data-cloud-create-manifest-streams.ps1` can register compatible schemas, create or resolve streams idempotently, wait for `ACTIVE` DLO status, sync registry targets to the live object name and `objectEndpoint`, and emit `salesforce/generated/<sourceName>/provisioning-state.json`.
- `scripts/salesforce/data-cloud-upload-manifest.ps1` can then upload the full manifest dataset once the registry and live stream state are aligned.

## Failure Modes

- External client app deployment is blocked because the org has not opted in to External Client Apps metadata.
- The operator attempts to reuse the normal Salesforce alias for Data Cloud login and overwrites the intended auth split.
- A stale shared `DATACLOUD_CLIENT_ID` is reused across orgs, so Salesforce treats the flow as cross-org OAuth. Rerun `setup-command-center-connected-app.ps1` for that org and use the generated org-specific client id.
- The standard Salesforce CLI alias still returns `invalid_scope` during `/services/a360/token` exchange. That means the normal org alias is not a Data Cloud-capable auth source for that org; use the separate Data Cloud alias backed by `CommandCenterAuth` and finish the browser callback for that alias.
- The org rejects the OAuth settings or policy metadata for `cdp_ingest_api`.
- Data Cloud auth still fails because the org requires additional Data Cloud setup beyond the app itself.
- The browser auth finishes after the local listener timeout. Reuse the redirected localhost callback URL with `-CallbackUrl` instead of starting a fresh browser auth attempt.
- The org is missing the Ingestion API connector, so auth succeeds but manifest stream bootstrap and uploads still fail.
- A live connector schema conflicts with the manifest-derived schema, so manifest stream bootstrap stops before changing the existing connector state.

## Cleanup or Rollback

- Delete the `CommandCenterAuth` external client app metadata from the org if this path is abandoned.
- Remove the local CLI auth alias and reauthorize with a different client app if needed.

## Commands and Links

- `scripts/salesforce/setup-command-center-connected-app.ps1`
- `scripts/salesforce/data-cloud-login-web.ps1`
- `scripts/salesforce/data-cloud-get-access-token.ps1`
- `salesforce/force-app/main/default/externalClientApps/CommandCenterAuth.eca-meta.xml`