# Publish Data

## Purpose

Use one operator-facing workflow when you have data to publish and want Command Center to drive the Data Cloud path for you, with optional Tableau Next semantic-model publication after the dataset is live.

## When to use it

- You have a manifest-backed dataset or a CSV and want the agent to orchestrate the publishing workflow.
- You want the repo to reuse saved aliases and registry values instead of manually re-entering setup state.

## Inputs

- Dataset path: manifest path or CSV path.
- Salesforce org alias and login URL if not already authenticated.
- Dedicated Data Cloud alias if one already exists.
- Whether the outcome is Data Cloud only, or Data Cloud plus Tableau Next semantic model.
- Naming overrides only if the defaults derived from the manifest are wrong for this org.

## Prerequisites

- The target org can authenticate through Salesforce CLI browser login.
- Data Cloud is provisioned if the workflow needs stream bootstrap or upload.
- The Ingestion API connector already exists in the org if you want live stream creation or upload.

## Exact steps

1. Tell the agent: "I have data to publish" and provide the dataset path.
2. Let the agent collect only the missing inputs such as alias, login URL, or naming overrides.
3. For manifest-backed datasets, let the agent run guided manifest setup first.
4. Let the agent run stream bootstrap when the live Data Cloud stream state is not already known to be healthy.
5. Let the agent run the upload path.
6. If you also want Tableau Next publication, let the agent continue into authenticated-to-SDM orchestration after the Data Cloud side is healthy.

## Validation

- Manifest-backed targets are registered.
- Token exchange succeeds.
- Upload jobs complete or return a clear blocker.
- If Tableau Next publication is requested, the readiness state or applied model result is captured.

## Failure modes

- Missing auth.
- Missing Data Cloud connector or stream objects.
- Manifest metadata is incomplete for automated registration.
- Tableau Next workspace or publish routing is still ambiguous.

## Cleanup or rollback

- Remove temporary payload artifacts from `tmp/` if they are no longer needed.
- Rerun guided setup or stream bootstrap instead of manually editing manifest-derived registry values.

## Commands and links

- `scripts/salesforce/data-cloud-guided-manifest-setup.ps1`
- `scripts/salesforce/data-cloud-create-manifest-streams.ps1`
- `scripts/salesforce/data-cloud-upload-manifest.ps1`
- `scripts/salesforce/data-cloud-upload-csv.ps1`
- `scripts/salesforce/orchestrate-authenticated-to-sdm.ps1`
- `skills/publish-data-through-command-center.md`