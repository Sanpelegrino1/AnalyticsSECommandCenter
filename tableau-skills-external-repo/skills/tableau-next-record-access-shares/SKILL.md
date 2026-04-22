---
name: tableau-next-record-access-shares
description: Shares Tableau Next workspaces, dashboards, and visualizations via the Record Access Shares REST API. Use when the user wants to share assets, grant access, make workspaces public, share with ALL_USERS, list who has access, update or remove shares, or automate sharing in Tableau Next.
license: MIT
compatibility: Requires Salesforce CLI (sf), jq. Authenticated Salesforce org with Tableau Next access.
allowed-tools: Bash(sf:org*) Bash(curl:*) Read Write
---

# Tableau Next Record Access Shares

Use this skill when the user discusses sharing Tableau Next workspaces, dashboards, or visualizations; granting access; making assets public or restricted; or automating sharing via API.

## Authentication

**CRITICAL**: Use curl with exported credentials. Do NOT use `sf api request` or `sf api request get` (invalid/beta).

1. Export token and instance:
```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

2. Use curl for all API calls: `curl -H "Authorization: Bearer $SF_TOKEN" "${SF_INSTANCE}/services/data/v64.0/..."`

## Record ID

`recordId` is the Salesforce ID of the asset (workspace, dashboard, or visualization).

**Get workspace IDs:**
```
GET /tableau/workspaces?limit=50&offset=0
```
Response includes `id`, `name`, `label` per workspace. Workspace IDs typically start with `1Dy` (AnalyticsWorkspace).

**Get dashboard IDs:**
```
GET /tableau/dashboards?limit=50&offset=0
```
Response includes `id`, `name`, `label` per dashboard. Dashboard IDs typically start with `0Tr` (AnalyticsDashboard). Note: this endpoint follows the same pattern as workspaces/visualizations but is not yet officially documented in the Tableau Next REST API docs.

**Get visualization IDs:**
```
GET /tableau/visualizations?limit=50&offset=0
```
Response includes `id`, `name`, `label` per visualization. Visualization IDs typically start with `1AK` (AnalyticsVisualization).

**userOrGroupId**: Use a User ID (`005...`) or `ALL_USERS` for org-wide sharing. `ALL_USERS` works in practice even though docs mention "users only."

## How to share a workspace

1. Get the workspace `recordId`: `GET /tableau/workspaces?limit=50` → use `id` from the response.
2. POST to create shares: `POST /tableau/records/{recordId}/shares` with `accessRequestItems`.
3. Check `failedRecordShares` in the response; retry or fix for any failures.

## Endpoints Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/tableau/records/{recordId}/shares` | List shares |
| POST | `/tableau/records/{recordId}/shares` | Create shares |
| PATCH | `/tableau/records/{recordId}/shares` | Update shares |
| DELETE | `/tableau/records/{recordId}/shares/{userOrGroupId}` | Remove one user's access |
| DELETE | `/tableau/records/{recordId}/shares` | Remove all shares |

## GET — List shares

```
GET /tableau/records/{recordId}/shares?limit=50&offset=0&orderBy=createddate&sortOrder=DESC&userOrGroupId={id}
```

**Query params**: `limit`, `offset`, `orderBy`, `sortOrder` (asc/desc), `userOrGroupId` (filter by user)

**Response**: `recordAccessMappings[]` with `accessType`, `applicationDomain`, `createdDate`, `userOrGroup`, `userOrGroupId`

## POST — Create shares

```
POST /tableau/records/{recordId}/shares
Content-Type: application/json
```

**Body** (no wrapper — `accessRequestItems` at top level):
```json
{
  "accessRequestItems": [
    {
      "accessType": "Editor",
      "applicationDomain": "Tableau",
      "setupObjectType": "AnalyticsWorkspace",
      "userOrGroupId": "ALL_USERS"
    }
  ]
}
```

**Enums**:
- `accessType`: `Editor`, `Owner`, `Viewer` (capitalized)
- `setupObjectType`: `AnalyticsWorkspace`, `AnalyticsDashboard`, `AnalyticsVisualization`
- `applicationDomain`: `Tableau`

**Response**: `successfulRecordShares[]`, `failedRecordShares[]` (check for errors)

## PATCH — Update shares

```
PATCH /tableau/records/{recordId}/shares
Content-Type: application/json
```

**Body**:
```json
{
  "updateSetupRecordAccessItems": [
    {
      "accessType": "Editor",
      "userOrGroupId": "005Ho00000LqtX0IAJ"
    }
  ]
}
```

**Response**: Same as POST — `successfulRecordShares[]`, `failedRecordShares[]`

## DELETE — Remove access

**Single user:**
```
DELETE /tableau/records/{recordId}/shares/{userOrGroupId}
```

**All shares:**
```
DELETE /tableau/records/{recordId}/shares
```

## Examples

### Get workspace IDs
```bash
curl "${SF_INSTANCE}/services/data/v64.0/tableau/workspaces?limit=50" \
  -H "Authorization: Bearer $SF_TOKEN"
```

### Share workspace with everyone (viewer)
```bash
curl -X POST "${SF_INSTANCE}/services/data/v64.0/tableau/records/1DyHo000000PBboKAG/shares" \
  -H "Authorization: Bearer $SF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accessRequestItems": [
      {
        "accessType": "Viewer",
        "applicationDomain": "Tableau",
        "setupObjectType": "AnalyticsWorkspace",
        "userOrGroupId": "ALL_USERS"
      }
    ]
  }'
```

### Share with specific user (editor)
```json
{
  "accessRequestItems": [
    {
      "accessType": "Editor",
      "applicationDomain": "Tableau",
      "setupObjectType": "AnalyticsWorkspace",
      "userOrGroupId": "005Ho00000LqtX0IAJ"
    }
  ]
}
```

### Get current shares
```bash
curl "${SF_INSTANCE}/services/data/v64.0/tableau/records/1DyHo000000PBboKAG/shares?limit=50" \
  -H "Authorization: Bearer $SF_TOKEN"
```

### Update access from Viewer to Editor
```json
{
  "updateSetupRecordAccessItems": [
    {
      "accessType": "Editor",
      "userOrGroupId": "005Ho00000LqtX0IAJ"
    }
  ]
}
```

## Workspace sharing behavior

Sharing a workspace grants access to its contents. Users with workspace access see dashboards and visualizations in that workspace. Referenced assets in other workspaces still require their own shares.

## Error handling

- **POST/PATCH**: Inspect `failedRecordShares` in the response for `errorCode`, `errorMessage`, `userOrGroupId`
- **401**: Refresh JWT or re-authenticate
- **404**: Invalid `recordId` or `userOrGroupId`

### Partial success (POST/PATCH)

When some shares succeed and others fail, the response contains both arrays. Check `failedRecordShares` and handle per-item errors (e.g. invalid user ID, permission denied).

## Reference

For full type definitions, enum values, and response schemas when building typed clients or debugging responses, see [references/api-reference.md](references/api-reference.md).
