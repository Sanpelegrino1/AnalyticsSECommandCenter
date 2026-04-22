# Tableau Next Package & Deploy API Reference

Quick reference for API endpoints. Use when constructing curl commands or debugging API calls.

## Table of Contents

- [Authentication](#authentication)
- [Dashboards](#dashboards)
- [Deployment](#deployment)
- [Request/Response Schemas](#requestresponse-schemas)
- [Error Codes](#error-codes)

---

## Authentication

All API requests (except OAuth flows) require:

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <SF_ACCESS_TOKEN>` |
| `X-Instance-Url` | Yes | `https://yourorg.my.salesforce.com` |
| `X-Client-Id` | No | Team identifier for metrics |
| `Content-Type` | Yes (POST) | `application/json` |

**Get token**: `sf org display --target-org myorg --json | jq -r '.result.accessToken'`

---

## Dashboards

### GET /api/v1/dashboards/list

List all Tableau Next dashboards in the authenticated org.

**Response**: `{ "dashboards": [ { "id", "apiName", "label", ... } ] }`

### POST /api/v1/dashboards/package

Package a dashboard and its dependencies into portable JSON.

**Request**:
```json
{ "dashboard_api_name": "Sales_Dashboard" }
```

**Response**:
```json
{
  "package_data": { "templateId", "apiVersion", "components", "requirements" },
  "filename": "Sales_Dashboard_package.json"
}
```

**Errors**: 401 (auth), 404 (dashboard not found), 500 (packaging failed)

---

## Deployment

### GET /api/v1/deployment/workspaces

List workspaces in the target org. Use before deploy when choosing `existing` workspace.

### GET /api/v1/deployment/semantic-models

List SDMs in the target org. Use before deploy when mapping to `existing` SDM.

### POST /api/v1/deployment/validate-package

Validate a package against the target org without deploying.

**Request**: Same as deploy (`DeploymentRequest`). See below.

### POST /api/v1/deployment/deploy

Deploy a package. Returns `job_id` for async deployment. Use `dry_run: true` for sync validation.

**Request** (DeploymentRequest):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| package_data | object | Yes | From package response |
| workspace_choice | string | Yes | `"create"` or `"existing"` |
| workspace_label | string | If create | Label for new workspace |
| workspace_api_name | string | If existing | API name of workspace |
| sdm_choice | string | Yes | `"create"` or `"existing"` |
| sdm_api_name | string | Yes | SDM API name |
| dependency_map | object | No | Field mapping for existing SDM |
| dry_run | boolean | No | If true, validate only |
| skip_validation | boolean | No | Skip pre-deploy checks |

**Response** (async): `{ "job_id", "status", "message" }`

**Response** (dry_run): `{ "status": "dry_run_complete", "valid", "errors", "warnings", "message" }`

### GET /api/v1/deployment/deploy/status/{job_id}

Poll deployment status. Poll every 5-10 seconds.

**Response**: `{ "status": "pending"|"running"|"completed"|"failed", "steps", "workspace_api_name", "workspace_url", "error" }`

---

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 401 | Invalid/expired token | `sf org login web --alias <org>` |
| 404 | Dashboard not found | List dashboards, verify API name |
| 422 | Validation error | Check request body against schema |
| 500 | Server error | Retry; check service health |

---

## Rate Limits

No API-level rate limiting. Respect Salesforce limits. Recommended: max 10 concurrent deployments per org.
