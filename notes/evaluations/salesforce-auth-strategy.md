# Salesforce Auth Strategy

This note was archived during repo cleanup. See `recycling-bin/2026-04-21-repo-cleanup/notes/evaluations/salesforce-auth-strategy.md` for the staged historical copy.
# Salesforce Auth Strategy Evaluation

## Question

What is the best authentication model for this workspace when agents need both:

- normal Salesforce org access for Setup, metadata, SOQL, and browser-open workflows
- Data Cloud publishing access for Ingestion API uploads

## Short Answer

Use two distinct auth contexts for the same org:

1. A standard Salesforce CLI web-login alias for normal org work.
2. A repo-owned External Client App login for Data Cloud publishing.

Do not reuse the same alias for both roles.

## Recommended Model

### Primary interactive model

- Keep one alias for standard org access created through `scripts/salesforce/login-web.ps1`.
- Keep a second alias for Data Cloud publishing created through `scripts/salesforce/data-cloud-login-web.ps1` against the repo-owned `CommandCenterAuth` app.
- Point Data Cloud upload scripts at the Data Cloud alias through `DATACLOUD_SALESFORCE_ALIAS` or the `salesforceAlias` field in `notes/registries/data-cloud-targets.json`.

Example naming:

- `STORM_TABLEAU_NEXT` for normal org access
- `STORM_TABLEAU_NEXT_DC` for Data Cloud publishing

### Why this is the best fit for this repo

- Standard `sf org login web` sessions work well for Setup navigation, metadata retrieval and deploy, SOQL, and general browser-open flows.
- The repo-owned `CommandCenterAuth` app has the scopes needed for Data Cloud token exchange, including `CDPIngest`.
- The current `DataCloud.Common.ps1` logic can already reuse a Salesforce CLI session from a specified alias and exchange it for a Data Cloud access token.
- Using separate aliases prevents one login from breaking or replacing the other workflow.

## What Was Validated

### Standard org auth works for normal Salesforce access

- `scripts/salesforce/login-web.ps1` against the org My Domain succeeds.
- This is the right path for Setup, metadata, and general interactive Salesforce work.

### Repo-owned Data Cloud auth works for token exchange

- The repo-owned `CommandCenterAuth` External Client App deploys successfully.
- A Salesforce CLI session created with that app can exchange through `/services/a360/token` and return a valid Data Cloud tenant token.

### One alias should not serve both roles

Reusing the same alias for both auth models causes operational problems:

- the alias registry intent becomes ambiguous
- the general org session can be replaced by the Data Cloud-scoped session
- browser-open and Setup flows can behave differently after the alias is repointed to the custom client app
- troubleshooting becomes harder because the same alias no longer means one consistent auth mode

## Recommended Priority Order

### 1. Preferred

Salesforce CLI session reuse from a dedicated Data Cloud alias.

Why:

- no secrets need to live in tracked files
- no refresh token parsing is required for day-to-day work
- works with the repo-owned External Client App
- integrates directly with the existing PowerShell scripts

### 2. Acceptable fallback

Refresh-token flow from `.env.local` using `DATACLOUD_CLIENT_ID`, `DATACLOUD_CLIENT_SECRET` if required, and `DATACLOUD_REFRESH_TOKEN`.

Use this when:

- browser login is not feasible
- the agent is running in a more automated or unattended context
- the Salesforce CLI session cannot be relied on

### 3. Emergency-only fallback

Direct `DATACLOUD_ACCESS_TOKEN` plus `DATACLOUD_TENANT_ENDPOINT`.

Use this only for short-lived troubleshooting or constrained automation because it is brittle and expires quickly.

## Operational Guidance

Dependency chain for the preferred interactive Data Cloud path:

1. Log in with `scripts/salesforce/login-web.ps1` using the normal org alias.
2. Deploy `CommandCenterAuth` with `scripts/salesforce/setup-command-center-connected-app.ps1` using that normal org alias.
3. Complete any remaining manual Salesforce Setup and Data Cloud Setup work for the org.
4. Log in with `scripts/salesforce/data-cloud-login-web.ps1` using the separate Data Cloud alias.
5. Validate with `scripts/salesforce/data-cloud-get-access-token.ps1 -AsJson` and confirm `tokenSource`.

### For normal org tasks

Use:

- `scripts/salesforce/login-web.ps1`
- `scripts/salesforce/open-org.ps1`
- `scripts/salesforce/retrieve-metadata.ps1`
- `scripts/salesforce/deploy-metadata.ps1`

### For Data Cloud publishing

Use:

- `scripts/salesforce/setup-command-center-connected-app.ps1`
- `scripts/salesforce/data-cloud-login-web.ps1`
- `scripts/salesforce/data-cloud-get-access-token.ps1`
- `scripts/salesforce/data-cloud-upload-csv.ps1`
- `scripts/salesforce/data-cloud-upload-manifest.ps1`

Operator note:

- `setup-command-center-connected-app.ps1 -LaunchLogin` should be given a dedicated `-DataCloudAlias` and should not reuse the normal org alias.
- When validation succeeds, `data-cloud-get-access-token.ps1 -AsJson` shows the active auth source through `tokenSource` and the resolved dedicated alias through `salesforceAlias`.

### Registry guidance

- `notes/registries/salesforce-orgs.json` should keep both aliases if both are in use.
- `notes/registries/data-cloud-targets.json` should store the Data Cloud alias in each target's `salesforceAlias` field.
- The default Salesforce alias does not need to be the Data Cloud alias.

## What Not To Do

- Do not overwrite the standard org alias with the Data Cloud auth app login.
- Do not make refresh-token env auth the default for interactive use.
- Do not rely on pre-existing org-owned connected apps or external client apps outside this repo.
- Do not store secrets in tracked files.

## Final Recommendation

For this workspace, the best auth architecture is:

- standard browser-login alias for general Salesforce work
- separate Data Cloud publishing alias backed by the repo-owned `CommandCenterAuth` External Client App
- CLI session reuse as the first-choice Data Cloud token source
- refresh-token env configuration as fallback only

This is the most stable model for agents because it preserves normal Salesforce ergonomics while still enabling Data Cloud publishing through a repeatable, repo-owned path.