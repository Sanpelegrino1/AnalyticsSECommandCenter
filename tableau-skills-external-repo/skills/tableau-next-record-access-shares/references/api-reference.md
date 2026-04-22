# Record Access Shares API Reference

Full types and enums for the Tableau Next Record Access Shares REST API.

## Contents

- [Enums](#enums)
- [Request Types](#request-types)
- [Response Types](#response-types)
- [Full Response Schemas](#full-response-schemas)

## Enums

### SetupObjectAccessTypeEnum

The type of access to the asset.

| Value | Description |
|-------|-------------|
| Editor | Can edit and view assets, add assets to shared workspace |
| Owner | Can create, edit, view, share, and delete assets |
| Viewer | Can view assets only |

### SetupObjectTypeEnum

The type of the object being shared.

| Value | Description |
|-------|-------------|
| AnalyticsWorkspace | Tableau Next workspace |
| AnalyticsDashboard | Dashboard |
| AnalyticsVisualization | Visualization |

### ApplicationDomainEnum

The product domain for the asset.

| Value |
|-------|
| Tableau |

---

## Request Types

### SetupRecordAccessItemInput (POST body item)

Used in `accessRequestItems` for POST.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| accessType | SetupObjectAccessTypeEnum | Yes | Editor, Owner, or Viewer |
| applicationDomain | ApplicationDomainEnum | Yes | Tableau |
| setupObjectType | SetupObjectTypeEnum | Yes | AnalyticsWorkspace, AnalyticsDashboard, or AnalyticsVisualization |
| userOrGroupId | string | Yes | User ID (005...) or ALL_USERS |

### UpdateSetupRecordAccessItemInput (PATCH body item)

Used in `updateSetupRecordAccessItems` for PATCH.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| accessType | SetupObjectAccessTypeEnum | Yes | New access level |
| userOrGroupId | string | Yes | User ID to update |

---

## Response Types

### SetupRecordAccess (recordAccessMappings item)

Returned in GET response.

| Field | Type | Description |
|-------|------|-------------|
| accessType | string | Editor, Owner, or Viewer |
| applicationDomain | string | Tableau |
| createdDate | string | ISO 8601 date |
| userOrGroup | SetupRecordShareUserOrGroup | User details |
| userOrGroupId | string | User or group ID |

### SetupRecordShareUserOrGroup

| Field | Type | Description |
|-------|------|-------------|
| displayName | string | Display name |
| email | string | Email (if user) |
| id | string | User ID |
| profilePhotoUrl | string | Profile photo URL |
| username | string | Username |

### SetupRecordShare (successfulRecordShares item)

Returned in POST/PATCH response for successful shares.

| Field | Type | Description |
|-------|------|-------------|
| accessType | string | Granted access type |
| applicationDomain | string | Tableau |
| createdBy | AnalyticsUser | Creator |
| createdDate | string | ISO 8601 date |
| lastModifiedBy | AnalyticsUser | Last modifier |
| lastModifiedDate | string | ISO 8601 date |
| userOrGroupId | string | User or group ID |

### SetupRecordShareError (failedRecordShares item)

Returned in POST/PATCH response for failed shares.

| Field | Type | Description |
|-------|------|-------------|
| errorCode | string | Error code |
| errorMessage | string | Error description |
| userOrGroupId | string | User or group that failed |

### AnalyticsUser

| Field | Type | Description |
|-------|------|-------------|
| id | string | User ID |
| name | string | Name |
| label | string | Label |
| description | string | Description |
| profilePhotoUrl | string | Profile photo URL |

---

## Full Response Schemas

### GET response (SetupRecordAccessCollection)

```json
{
  "recordAccessMappings": [...],
  "recordId": "1DyHo000000PBboKAG",
  "limit": 50,
  "offset": 0,
  "orderBy": "createddate",
  "sortOrder": "DESC",
  "ownerCount": 1,
  "filterByAccessType": [],
  "filterByRecipientType": [],
  "filterByUserOrGroupId": null
}
```

### POST/PATCH response (SetupRecordShareCollection)

```json
{
  "recordId": "1DyHo000000PBboKAG",
  "setupObjectType": "analyticsworkspace",
  "successfulRecordShares": [...],
  "failedRecordShares": [...]
}
```
