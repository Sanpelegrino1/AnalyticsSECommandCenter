# Publish Data Through Command Center

## Purpose

Handle the operator intent "I have data to publish" as one orchestrated workflow that collects only the missing inputs, reuses saved non-secret metadata when available, and drives the repo's Data Cloud and optional Tableau Next publishing surfaces end to end.

## When to use it

- The user has a CSV or manifest-backed dataset and wants the agent to take over the publishing workflow.
- The user wants the agent to ask for only the missing inputs instead of making them navigate scripts, tasks, registries, or playbooks.
- The user may want Data Cloud publication only, or Data Cloud plus Tableau Next semantic-model publication.

## Inputs

- Dataset path: manifest path for multi-table datasets, or CSV path for single-table uploads.
- Standard Salesforce org alias and login URL if the org is not already authenticated.
- Dedicated Data Cloud alias if one already exists; otherwise derive one from the standard alias.
- Publishing scope: Data Cloud only, or Data Cloud plus Tableau Next semantic model.
- Naming inputs only when defaults are unsuitable: source name, target key prefix, object name prefix.
- Tableau Next workspace selector or saved target key only when semantic-model publication is requested.

## Prerequisites

- The user can complete Salesforce browser auth when the org or Data Cloud alias is not already authenticated.
- Data Cloud is provisioned if the workflow should reach stream bootstrap or upload.
- The Ingestion API connector already exists in the target org if live stream bootstrap or upload is required.
- For manifest-backed publication, the manifest is the source of truth for files, keys, and relationships.
- Prefer already-saved registry values, aliases, and local env values over re-asking for the same non-secret inputs.

## Exact steps

1. Determine whether the dataset is manifest-backed or single-CSV, and prefer the manifest path when one exists.
2. Gather only the missing inputs. Reuse saved aliases, target rows, tenant endpoint, and naming prefixes from the registries and local env when they already exist.
3. If the standard Salesforce alias is not authenticated, run `scripts/salesforce/login-web.ps1` or the matching VS Code task first.
4. For manifest-backed Data Cloud publication, run `scripts/salesforce/data-cloud-guided-manifest-setup.ps1` first so the manifest-derived targets are registered and the Data Cloud token exchange is validated.
5. If the live Data Cloud streams and DLOs are not already known to be healthy, run `scripts/salesforce/data-cloud-create-manifest-streams.ps1` to reconcile schemas, streams, and accepted object identities.
6. Run `scripts/salesforce/data-cloud-upload-manifest.ps1` for manifest-backed datasets, or `scripts/salesforce/data-cloud-upload-csv.ps1` for a configured single target.
7. If the user also wants Tableau Next publication, run `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1` after the Data Cloud side is healthy, and use `-ApplySemanticModel` only when the non-apply path is clean or the user explicitly wants live apply.
8. Report back with the exact outputs that matter: registered target keys, resolved tenant endpoint, upload job ids and states, readiness classification, and any blockers that still require org-side action.
9. Persist the non-secret outcomes so retries are cheaper: reuse or refresh `notes/registries/data-cloud-targets.json`, Tableau Next targets, and the local env defaults instead of asking for the same values again.

## Validation

- Manifest setup resolves a Data Cloud token and registers one target per manifest table.
- Stream bootstrap reports reused or created streams and `ACTIVE` DLO status when that phase is required.
- Upload jobs reach `JobComplete` or stop with a clear object-level failure.
- If Tableau Next publication is requested, the orchestration state file exists and reports a readiness classification or an applied semantic model plus relationships.
- The agent's summary names the exact next operator action only when repo-local automation is blocked by org setup or permissions.

## Failure modes

- The org or Data Cloud alias is not authenticated, so auth must be completed in the browser.
- The manifest shape is missing required publication metadata. The repo can normalize the newer `publishContract.tables` shape, but it still needs enough table, file, and join information to build targets.
- The Data Cloud Ingestion API connector or live streams do not exist yet in the org.
- The registry is present, but connector-specific `objectEndpoint` values are still missing because the live stream objects have not yet been accepted by Data Cloud.
- Tableau Next workspace routing is ambiguous, or the requested semantic-model publish path still lacks required live org context.

## Cleanup or rollback

- Remove bad local request payloads from `tmp/` if they are no longer useful.
- Refresh manifest-derived target rows by rerunning guided setup instead of manually editing registry fields that should be derived.
- Rerun stream bootstrap if the connector schema or accepted stream object names change.
- If Tableau Next target routing changes, re-register the target instead of editing the saved target by hand.

## Commands and links

- `scripts/salesforce/login-web.ps1`
- `scripts/salesforce/data-cloud-guided-manifest-setup.ps1`
- `scripts/salesforce/data-cloud-create-manifest-streams.ps1`
- `scripts/salesforce/data-cloud-upload-manifest.ps1`
- `scripts/salesforce/data-cloud-upload-csv.ps1`
- `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1`
- `notes/registries/data-cloud-targets.json`
- `notes/registries/tableau-next-targets.json`
- `playbooks/publish-data.md`