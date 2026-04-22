# Semantic Authoring API Reference

Complete REST API documentation for creating calculated fields, dimensions, and metrics on Semantic Data Models.

## Base URL

All endpoints use the base URL:
```
https://{instance}.salesforce.com/services/data/v66.0
```

Where `{instance}` is your Salesforce instance (e.g., `myorg` for `myorg.salesforce.com`)

**Important:** Semantic authoring endpoints do NOT use `minorVersion` query parameter (unlike visualization/dashboard endpoints).

## Authentication

All requests require Bearer token authentication:

```bash
-H "Authorization: Bearer {access_token}"
-H "Content-Type: application/json"
```

**Getting an Access Token (using SF CLI):**
```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

**Required Permissions:**
- View Semantic Models
- Create/Edit Semantic Models

---

## Discovery Endpoints

### List Semantic Models

Get all semantic models available to the authenticated user.

**Endpoint:** `GET /ssot/semantic/models`

**Request:**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Response:**
```json
{
  "semantic_models": [
    {
      "id": "0FKxx0000000001",
      "apiName": "Sales_Cloud12_backward",
      "label": "Sales Analytics",
      "description": "Sales performance metrics and trends",
      "dataspace": "default",
      "categories": ["Sales"],
      "createdDate": "2024-01-15T10:30:00Z",
      "lastModifiedDate": "2024-02-20T14:45:00Z"
    }
  ],
  "count": 1
}
```

### Get Semantic Model Definition

Retrieve complete structure of a semantic model including objects, dimensions, measurements, and metrics.

**Endpoint:** `GET /ssot/semantic/models/{sdmApiNameOrId}`

**Request:**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Response Structure:**
```json
{
  "id": "0FKxx0000000001",
  "apiName": "Sales_Cloud12_backward",
  "label": "Sales Analytics",
  "dataspace": "default",
  "semanticDataObjects": [
    {
      "apiName": "Opportunity_TAB_Sales_Cloud",
      "label": "Opportunities",
      "semanticDimensions": [
        {
          "apiName": "Region",
          "label": "Region",
          "fieldName": "Region__c",
          "dataType": "Text",
          "objectName": "Opportunity_TAB_Sales_Cloud"
        }
      ],
      "semanticMeasurements": [
        {
          "apiName": "Amount",
          "label": "Amount",
          "fieldName": "Amount",
          "dataType": "Number",
          "aggregationType": "Sum",
          "decimalPlace": 2,
          "objectName": "Opportunity_TAB_Sales_Cloud"
        }
      ]
    }
  ],
  "calculatedMeasurements": [
    {
      "apiName": "Total_Revenue_clc",
      "label": "Total Revenue",
      "expression": "SUM([Amount])",
      "aggregationType": "Sum",
      "dataType": "Number"
    }
  ],
  "calculatedDimensions": [
    {
      "apiName": "Deal_Size_Category_clc",
      "label": "Deal Size Category",
      "expression": "IF [Amount] > 100000 THEN 'Large' ELSE 'Small' END",
      "dataType": "Text"
    }
  ],
  "semanticMetrics": [
    {
      "apiName": "Total_Revenue_mtc",
      "label": "Total Revenue",
      "measurementReference": {
        "calculatedFieldApiName": "Total_Revenue_clc"
      },
      "timeDimensionReference": {
        "tableFieldReference": {
          "fieldApiName": "Close_Date",
          "tableApiName": "Opportunity_TAB_Sales_Cloud"
        }
      },
      "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"]
    }
  ]
}
```

---

## Creation Endpoints

### Create Calculated Measurement

Create a calculated measurement field on an SDM.

**Endpoint:** `POST /ssot/semantic/models/{{modelName}}/calculated-measurements`

**Request body:**
```json
{
  "apiName": "Total_Revenue_clc",
  "label": "Total Revenue",
  "expression": "SUM([Amount])",
  "aggregationType": "Sum",
  "dataType": "Number",
  "decimalPlace": 2,
  "description": "Total revenue from all opportunities"
}
```

**curl example:**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/calculated-measurements" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Total_Revenue_clc",
    "label": "Total Revenue",
    "expression": "SUM([Amount])",
    "aggregationType": "Sum",
    "dataType": "Number",
    "decimalPlace": 2
  }'
```

**Required fields:**
- `apiName` (must end with `_clc`, no double underscores)
- `label`
- `expression` (Tableau formula)
- `aggregationType` (Sum, Avg, Min, Max, Count, UserAgg)
- `dataType` (Number, Text, Date, Boolean)

**Optional fields:**
- `description`
- `decimalPlace` (for Number type, default 2)

**Response:**
```json
{
  "id": "0Fmxx0000000001",
  "apiName": "Total_Revenue_clc",
  "label": "Total Revenue",
  "success": true
}
```

### Create Calculated Dimension

Create a calculated dimension field on an SDM.

**Endpoint:** `POST /ssot/semantic/models/{{modelName}}/calculated-dimensions`

**Request body:**
```json
{
  "apiName": "Deal_Size_Category_clc",
  "label": "Deal Size Category",
  "expression": "IF [Amount] > 100000 THEN 'Large' ELSEIF [Amount] > 50000 THEN 'Medium' ELSE 'Small' END",
  "dataType": "Text",
  "description": "Categorizes deals by size"
}
```

**curl example:**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/calculated-dimensions" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Deal_Size_Category_clc",
    "label": "Deal Size Category",
    "expression": "IF [Amount] > 100000 THEN '\''Large'\'' ELSEIF [Amount] > 50000 THEN '\''Medium'\'' ELSE '\''Small'\'' END",
    "dataType": "Text"
  }'
```

**Required fields:**
- `apiName` (must end with `_clc`, no double underscores)
- `label`
- `expression` (Tableau formula)
- `dataType` (Text, Date, Boolean)

**Optional fields:**
- `description`

**Note:** Dimensions don't require `aggregationType` (only measurements do).

### Create Semantic Metric

Create a semantic metric on an SDM. Metrics reference existing calculated fields.

**Endpoint:** `POST /ssot/semantic/models/{{modelName}}/metrics`

**Request body (basic):**
```json
{
  "apiName": "Total_Revenue_mtc",
  "label": "Total Revenue",
  "aggregationType": "UserAgg",
  "measurementReference": {
    "calculatedFieldApiName": "Total_Revenue_clc"
  },
  "timeDimensionReference": {
    "tableFieldReference": {
      "fieldApiName": "Close_Date",
      "tableApiName": "Opportunity_TAB_Sales_Cloud"
    }
  },
  "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
  "filters": [],
  "isCumulative": false,
  "isGoalEditingBlocked": false
}
```

**curl example:**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/metrics" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Total_Revenue_mtc",
    "label": "Total Revenue",
    "aggregationType": "UserAgg",
    "measurementReference": {
      "calculatedFieldApiName": "Total_Revenue_clc"
    },
    "timeDimensionReference": {
      "tableFieldReference": {
        "fieldApiName": "Close_Date",
        "tableApiName": "Opportunity_TAB_Sales_Cloud"
      }
    },
    "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
    "filters": [],
    "isCumulative": false,
    "isGoalEditingBlocked": false
  }'
```

**Required fields:**
- `apiName` (must end with `_mtc`, no double underscores)
- `label`
- `aggregationType` (typically `UserAgg`)
- `measurementReference.calculatedFieldApiName` (must exist on SDM)
- `timeDimensionReference` (field + table for time-based analysis)
- `timeGrains` (array of: "Day", "Week", "Month", "Quarter", "Year")

**Optional fields:**
- `description`
- `additionalDimensions` (for breakdown analysis)
- `insightsSettings` (auto-generated if not provided)
- `filters`
- `isCumulative` (default false)
- `isGoalEditingBlocked` (default false)
- `sentiment` (SentimentTypeUpIsGood, SentimentTypeUpIsBad, SentimentTypeNone)

**Request body (with additional dimensions):**
```json
{
  "apiName": "Revenue_by_Region_mtc",
  "label": "Revenue by Region",
  "aggregationType": "UserAgg",
  "measurementReference": {
    "calculatedFieldApiName": "Total_Revenue_clc"
  },
  "timeDimensionReference": {
    "tableFieldReference": {
      "fieldApiName": "Close_Date",
      "tableApiName": "Opportunity_TAB_Sales_Cloud"
    }
  },
  "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
  "additionalDimensions": [
    {
      "tableFieldReference": {
        "fieldApiName": "Region",
        "tableApiName": "Opportunity_TAB_Sales_Cloud"
      }
    }
  ],
  "insightsSettings": {
    "insightTypes": [
      {"enabled": true, "type": "TopContributors"},
      {"enabled": true, "type": "TrendChangeAlert"},
      {"enabled": true, "type": "BottomContributors"}
    ],
    "insightsDimensionsReferences": [
      {
        "tableFieldReference": {
          "fieldApiName": "Region",
          "tableApiName": "Opportunity_TAB_Sales_Cloud"
        }
      }
    ],
    "pluralNoun": "regions",
    "singularNoun": "region",
    "sentiment": "SentimentTypeUpIsGood"
  },
  "filters": [],
  "isCumulative": false,
  "isGoalEditingBlocked": false
}
```

**Note:** `additionalDimensions` can reference either `tableFieldReference` (SDM fields) or `calculatedFieldApiName` (calculated dimensions).

---

## Error Responses

All endpoints return structured error responses:

```json
{
  "error": {
    "code": "INVALID_FIELD",
    "message": "Field 'Amount' not found in semantic model 'Sales_Cloud12_backward'",
    "details": {
      "fieldName": "Amount",
      "availableFields": ["Total_Amount", "Close_Date", "Stage"]
    }
  }
}
```

**Common Error Codes:**
- `INVALID_TOKEN`: Authentication token is invalid or expired
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `RESOURCE_NOT_FOUND`: SDM not found
- `INVALID_FIELD`: Field reference doesn't exist in SDM
- `INVALID_JSON`: Malformed JSON structure
- `VALIDATION_ERROR`: JSON structure valid but business rules violated
- `DUPLICATE_API_NAME`: API name already exists on SDM

---

## Common Validation Rules

### API Name Rules

- Must end with `_clc` (calculated fields) or `_mtc` (metrics)
- Cannot contain double underscores (`__`)
- Must be unique within the SDM
- 1-80 characters, alphanumeric + underscore only

**Valid:**
- `Total_Revenue_clc`
- `Win_Rate_mtc`

**Invalid:**
- `Total__Revenue_clc` (double underscore)
- `Total_Revenue` (missing suffix)
- `Total Revenue_clc` (space not allowed)

### Expression Rules

- Must use valid Tableau functions
- Field references must exist in SDM: `[Field_Name]`
- String literals use single quotes: `'Large'`
- Case-insensitive function names: `SUM`, `Sum`, `sum` all work

### Aggregation Type Rules

- Required for measurements, not for dimensions
- Use `UserAgg` when expression includes aggregation functions
- Don't use `UserAgg` for simple field references

---

## Complete Workflow Example

**Scenario:** Create a win rate metric with regional breakdown.

**Step 1: Discover SDM**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Step 2: Create calculated field (win rate)**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/calculated-measurements" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Win_Rate_clc",
    "label": "Win Rate",
    "expression": "SUM([Won_Count]) / SUM([Total_Count])",
    "aggregationType": "UserAgg",
    "dataType": "Number",
    "decimalPlace": 4
  }'
```

**Step 3: Create metric with regional breakdown**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/metrics" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Win_Rate_by_Region_mtc",
    "label": "Win Rate by Region",
    "aggregationType": "UserAgg",
    "measurementReference": {
      "calculatedFieldApiName": "Win_Rate_clc"
    },
    "timeDimensionReference": {
      "tableFieldReference": {
        "fieldApiName": "Close_Date",
        "tableApiName": "Opportunity_TAB_Sales_Cloud"
      }
    },
    "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
    "additionalDimensions": [
      {
        "tableFieldReference": {
          "fieldApiName": "Region",
          "tableApiName": "Opportunity_TAB_Sales_Cloud"
        }
      }
    ],
    "filters": [],
    "isCumulative": false,
    "isGoalEditingBlocked": false
  }'
```

**Step 4: Verify creation**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

Check response for `calculatedMeasurements` and `semanticMetrics` arrays to verify your new field and metric appear.

---

## Rate Limits

Salesforce API rate limits apply:
- **Standard:** 15,000 API requests per 24 hours per org
- **Unlimited:** 25,000 API requests per 24 hours per org

**Best Practices:**
- Batch field creation when possible
- Cache SDM definitions (they change infrequently)
- Use dry-run mode (`--dry-run` flag) to validate payloads before POSTing

---

## Additional Resources

- [Salesforce Semantic Layer API Docs](https://developer.salesforce.com/docs/data/semantic-layer)
- [OAuth 2.0 Authentication Guide](https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_flows.htm)
- [SKILL.md](../SKILL.md) - Main workflow guide
- [tableau-functions.md](tableau-functions.md) - Complete function reference
