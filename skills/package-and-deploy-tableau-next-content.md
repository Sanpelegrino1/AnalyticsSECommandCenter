# Package And Deploy Tableau Next Content

## Purpose

Package Tableau Next dashboards from one Salesforce org and validate or deploy them into another org using the external package-and-deploy toolkit.

## When to use it

Use this when the user wants to export a dashboard package, validate a deployment, migrate dashboards between orgs, or automate Tableau Next promotion through a dev-to-test-to-prod flow.

## Inputs

- Source Salesforce org alias.
- Target Salesforce org alias for validation or deployment.
- Dashboard API name.
- Package file path.
- Workspace and semantic-model deployment choices for the target org.

## Prerequisites

- Salesforce CLI auth works for both source and target orgs.
- The external toolkit exists at `tableau-skills-external-repo/skills/tableau-next-package-deploy`.
- Python dependencies from that skill's `scripts/requirements.txt` are installed.
- The Tableau Next Package and Deploy service is reachable for the current environment.

## Exact steps

1. Fetch source-org auth context with Salesforce CLI.
2. Package the dashboard with `tableau-skills-external-repo/skills/tableau-next-package-deploy/scripts/package_dashboard.py`.
3. Save the returned package JSON under `tmp/` or another deliberate local path.
4. Validate the package against the target org with `validate_package.py` before any deployment.
5. Deploy with `deploy_package.py` only after validation succeeds.
6. Poll or review the async deploy result until it reports success or a concrete failure.

## Validation

- A package JSON file is produced for the requested dashboard.
- Validation succeeds against the target org before deployment.
- Deployment returns a completed job state and the target dashboard resolves in the chosen workspace.

## Failure modes

- The dashboard API name is wrong in the source org.
- Validation fails because the target semantic model, workspace, or permissions do not match the package requirements.
- The async deployment job fails after acceptance and must be inspected from its returned error payload.

## Cleanup or rollback

- Keep package JSON files only if they are intended migration artifacts; otherwise remove them from `tmp/`.
- If deployment creates unwanted target content, remove it from the target org after inspecting the package choices that caused it.

## Commands and links

- `tableau-skills-external-repo/skills/tableau-next-package-deploy/SKILL.md`
- `tableau-skills-external-repo/skills/tableau-next-package-deploy/scripts/package_dashboard.py`
- `tableau-skills-external-repo/skills/tableau-next-package-deploy/scripts/validate_package.py`
- `tableau-skills-external-repo/skills/tableau-next-package-deploy/scripts/deploy_package.py`
