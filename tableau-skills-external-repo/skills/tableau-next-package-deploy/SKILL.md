---
name: tableau-next-package-deploy
description: Packages Tableau Next dashboards from source Salesforce orgs and deploys them to target orgs using the Tableau Next Package & Deploy API. Handles migration workflows, pre-deployment validation, and async job tracking. Use when migrating dashboards between orgs, automating dashboard deployments, packaging dashboards for distribution, or when the user mentions "package this dashboard", "deploy dashboard to org", "migrate dashboards", "export dashboard package", or CI/CD automation.
license: MIT
compatibility: Requires Salesforce CLI (sf) for token auth, Python 3.8+ with requests for wrapper scripts, jq for token extraction in bash. Authenticated Salesforce org with Tableau Next access. API base defaults to https://next-package-deploy.demo.tableau.com/api (override via TABNEXT_API_BASE).
metadata:
  author: alaviron
  version: "1.0"
allowed-tools: Bash(sf:*) Bash(python:*) Bash(curl:*) Read Write
---

# Tableau Next Package & Deploy

Package dashboards from a source org and deploy them to target orgs. Use direct API calls or bundled Python scripts with Salesforce CLI tokens.

## Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| Package a dashboard | [Package Workflow](#package-workflow) |
| Deploy a package | [Deploy Workflow](#deploy-workflow) |
| Validate before deploy | [Validation Workflow](#validation-workflow) |
| Get auth token | [Authentication](#authentication) |
| Choose workflow | [Workflow Selection](#workflow-selection) |
| API reference | [references/api-guide.md](references/api-guide.md) |
| Real-world examples | [references/examples.md](references/examples.md) |

---

## Authentication

The API uses **Salesforce access tokens** (pass-through auth). Each request needs:

```
Authorization: Bearer <SF_ACCESS_TOKEN>
X-Instance-Url: https://yourorg.my.salesforce.com
X-Client-Id: your-team-id (optional)
```

### Get Token (Recommended for Scripts/CI)

Use Salesforce CLI — no manual copy/paste:

```bash
# Get token and instance URL for an org
TOKEN=$(sf org display --target-org myorg --json | jq -r '.result.accessToken')
INSTANCE_URL=$(sf org display --target-org myorg --json | jq -r '.result.instanceUrl')
```

If `jq` is unavailable: `sf org display --target-org myorg --verbose` shows the Access Token in plain text.

**Decision**: Use token auth for scripts, CI, and automation. Use OAuth web flow (browser login to the service) for interactive use only.

**Trigger**: Use for packaging, deploying, migrating dashboards. Do not use for: creating new dashboards from scratch (use tableau-next-author), sharing access (use tableau-next-record-access-shares), or enriching semantic models (use tableau-semantic-authoring).

---

## Workflow Selection

**Triggers**: Package, deploy, migrate, export dashboard, CI/CD automation. **Does not trigger**: Building new dashboards (use tableau-next-author), sharing workspaces (use tableau-next-record-access-shares), enriching semantic models (use tableau-semantic-authoring).

| User intent | Workflow | Key action |
|-------------|----------|------------|
| Export/save dashboard from org | Package | Run package workflow on source org |
| Deploy package JSON to org | Deploy | Run deploy workflow on target org |
| Check if deployment will succeed | Validate | Run validation first, then deploy if valid |
| List dashboards before packaging | Package | Call list endpoint or use `--list` in script |
| Migrate dev → QA → prod | Package + Deploy | Package from source, deploy to each target |

**Does not apply**: Building new dashboards from scratch (use tableau-next-author). Sharing workspaces/dashboards (use tableau-next-record-access-shares).

---

## Package Workflow

1. **Get credentials** for the source org:
   ```bash
   TOKEN=$(sf org display --target-org source-org --json | jq -r '.result.accessToken')
   INSTANCE=$(sf org display --target-org source-org --json | jq -r '.result.instanceUrl')
   ```

2. **List dashboards** (if unsure of API name):
   ```bash
   curl -s -X GET "$API_BASE/v1/dashboards/list" \
     -H "Authorization: Bearer $TOKEN" \
     -H "X-Instance-Url: $INSTANCE" \
     -H "Content-Type: application/json"
   ```

3. **Package the dashboard**:
   ```bash
   curl -s -X POST "$API_BASE/v1/dashboards/package" \
     -H "Authorization: Bearer $TOKEN" \
     -H "X-Instance-Url: $INSTANCE" \
     -H "Content-Type: application/json" \
     -d '{"dashboard_api_name": "Sales_Dashboard"}'
   ```

4. **Save** the `package_data` from the response to `tableauNext/{DashboardName}_package.json`.

**Or use the script**: Run `scripts/package_dashboard.py` — it fetches the token via `sf` and saves the package.

---

## Deploy Workflow

1. **Get credentials** for the target org (same token pattern as package).

2. **Validate first** — use `dry_run: true` in the deploy payload or run `scripts/validate_package.py`. This catches permission issues, duplicate names, and missing fields before deployment.

3. **Deploy**:
   ```bash
   curl -s -X POST "$API_BASE/v1/deployment/deploy" \
     -H "Authorization: Bearer $TOKEN" \
     -H "X-Instance-Url: $INSTANCE" \
     -H "Content-Type: application/json" \
     -d @deploy_payload.json
   ```

   Deploy payload structure (see [references/api-guide.md](references/api-guide.md)):
   - `package_data`: object from package JSON
   - `workspace_choice`: `"create"` or `"existing"`
   - `workspace_label`: required if create
   - `workspace_api_name`: required if existing
   - `sdm_choice`: `"create"` or `"existing"`
   - `sdm_api_name`: required

4. **Poll status**: Response returns `job_id`. Poll `GET /api/v1/deployment/deploy/status/{job_id}` every 5-10 seconds until `status` is `completed` or `failed`.

**Or use the script**: Run `scripts/deploy_package.py` — it polls automatically and reports workspace/dashboard URLs.

---

## Validation Workflow

Validate before deploying to catch errors early:

- **Dry run**: Add `"dry_run": true` to the deploy payload. Returns validation result without deploying.
- **Validate package endpoint**: `POST /api/v1/deployment/validate-package` with a `DeploymentRequest` body.
- **Validate requirements**: `POST /api/v1/deployment/validate-requirements` — check package dependencies against an existing SDM.

**Or use the script**: Run `scripts/validate_package.py` with org alias and package file.

---

## Best Practices

- **Validate before deploy** — use dry run or validate endpoint in production. Skips wasted deployment time.
- **List dashboards first** — API names may differ from labels. Use `GET /api/v1/dashboards/list` to confirm.
- **Unique SDM names** — when creating, append a timestamp suffix to avoid conflicts across deployments.
- **Polling interval** — poll deploy status every 5-10 seconds. Faster polling adds no value and may hit rate limits.
- **Package naming** — save as `{DashboardName}_package.json` for clarity.

---

## Anti-patterns

- Don't deploy to production without validation.
- Don't hardcode tokens — fetch via `sf org display` or env vars.
- Don't poll status every 1 second.
- Don't assume dashboard API names — list first.

---

## Scripts

Scripts live in `scripts/`. Run them from the skill directory or with the full path.

| Script | Purpose |
|--------|---------|
| `package_dashboard.py` | Package a dashboard from source org; saves JSON |
| `deploy_package.py` | Deploy a package to target org; polls until complete |
| `validate_package.py` | Validate package against target org; no deploy |

**Dependencies**: `pip install requests` (Python scripts).

See [references/examples.md](references/examples.md) for CLI one-liners and migration scenarios.

---

## Error Handling

| HTTP | Meaning | Action |
|------|---------|--------|
| 401 | Invalid/expired token | Refresh: `sf org login web --alias myorg` |
| 404 | Dashboard not found | List dashboards, verify API name |
| 422 | Validation error | Check request body against schema |
| 500 | Server error | Retry; check service health |

When deployment fails: check the `error` field in the status response. Common causes — missing permissions, duplicate SDM name, field not found in target SDM.
