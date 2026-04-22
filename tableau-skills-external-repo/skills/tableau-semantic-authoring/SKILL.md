---
name: tableau-semantic-authoring
description: Enrich Semantic Data Models with calculated fields, dimensions, and metrics for Tableau Next. The semantic layer lives in Data 360. Use when creating calculated measurements (_clc), calculated dimensions (_clc), or semantic metrics (_mtc) on existing SDMs. Trigger before dashboard authoring when custom business logic is needed. Use when the user asks to "create a metric", "add a calculated field", "enrich the semantic model", "validate a Tableau expression", or "discover SDM fields". This skill handles semantic layer enrichment; use tableau-next-author for visualizations and dashboards.
license: Apache-2.0
compatibility: >
  Requires tableau-next-author skill installed (scripts shared via symlinks in scripts/).
  Verify: python scripts/lib/verify_paths.py
  Salesforce CLI (sf), Python 3.8+, jq. Authenticated org with semantic model access.
metadata:
  author: alaviron
  version: "1.0"
  api-version: "v66.0"
allowed-tools: Bash(sf:*) Bash(python:*) Read Write
---

# Semantic Layer Authoring

Enrich Semantic Data Models (SDMs) with calculated fields, dimensions, and metrics. This skill focuses on data modeling—creating reusable business logic on the semantic layer before visualization or dashboard authoring.

## When to Use This Skill

Use this skill when you need to:
- Create calculated measurements or dimensions on an SDM
- Build semantic metrics for Tableau Next dashboard KPI widgets
- Validate Tableau expressions before creating fields
- Discover SDM structure and identify missing fields
- Standardize business logic across dashboards

**Don't use this skill for:** visualizations, dashboards, or Pulse metric definitions (Pulse is Tableau Cloud; those have dedicated skills).

**Trigger examples (SHOULD use this skill):**
- "Create a win rate metric on Sales_Cloud12_backward"
- "Add a calculated field for deal size categories"
- "What fields are available in the Sales model?"
- "Build a metric for revenue by region"
- "Validate this Tableau expression: SUM([Table].[Won]) / SUM([Table].[Total])"
- "Create a dimension that extracts month from Close_Date"

**Don't trigger (use other skills):**
- "Create a bar chart showing revenue by region" → `tableau-next-author`
- "Build a sales dashboard" → `tableau-next-author`
- "Set up a Pulse metric definition" → `tableau-pulse-*` (Tableau Cloud)

## Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| See available SDMs | [Discovery Workflow](#discovery-workflow) |
| Create a calculated field | [Calculated Fields](#calculated-fields) |
| Create a metric | [Semantic Metrics](#semantic-metrics) |
| Validate an expression | [Validation](#validation) |
| Fix common errors | [Common Errors](#common-errors) |
| See script examples | [Script Cheat Sheet](#script-cheat-sheet) |

## Core Concepts

### Calculated Fields vs Metrics

**Calculated Fields (`_clc`):**
- Rich structure: aggregation type, data type, decimal places, expression
- Used directly in visualizations (charts, tables)
- Can be measurements (aggregated) or dimensions (categorical)
- Example: `Win_Rate_clc` with expression `SUM([Table].[Won]) / SUM([Table].[Total])`

**Semantic Metrics (`_mtc`):**
- Lightweight wrappers for dashboard metric widgets
- Usually reference a calculated field via `measurementReference.calculatedFieldApiName`, but can also carry native metric filters
- Include time dimension (`timeDimensionReference`) and time grains (Day, Week, Month, Quarter, Year)
- Support additional dimensions and metric-level filters for breakdown and scoped analysis
- Example: `Win_Rate_mtc` references `Win_Rate_clc` with `Close_Date` as time dimension

**When to use each:**
- Create calc field when you need a reusable formula for visualizations
- Create metric when you need a time-based KPI for Tableau Next dashboard widgets
- If the user asks for a scoped variant of an existing metric, like "last 60 days" or "only won deals", prefer copying the existing metric and changing its native `filters` array.
- Only introduce a new calculated field first when the user explicitly wants reusable semantic logic or the metric truly needs a new formula.

### Scoped Metric Rule

When a user asks for a time-bounded or otherwise filtered variant of an existing metric:
- Inspect the live metric first and copy its current `filters`, `measurementReference`, `timeDimensionReference`, `timeGrains`, and breakdown settings.
- Prefer changing the metric's native `filters` array directly.
- Do not create an intermediate `_clc` field just to force a date window unless the user explicitly asks for a reusable calculated field.
- If the filter schema is unclear, inspect an existing live metric payload and reuse that shape instead of inventing one.

### Naming Conventions

- Calculated fields end with `_clc` (e.g., `Win_Rate_clc`, `Total_Revenue_clc`)
- Metrics end with `_mtc` (e.g., `Win_Rate_mtc`, `Total_Revenue_mtc`)
- No double underscores (`__`) anywhere in the name—Salesforce rejects them
- Use descriptive names that communicate business meaning (not `Field_1` or `Metric_2`)

## Discovery Workflow

Before creating fields or metrics, discover what already exists on the SDM.

### List All SDMs

```bash
python scripts/discover_sdm.py --list
```

Returns all semantic models with labels and descriptions. Use this to identify which SDM to enrich.

### Inspect SDM Fields

```bash
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json
```

Returns complete SDM structure including:
- Semantic data objects (tables)
- Semantic dimensions (categorical fields)
- Semantic measurements (aggregated fields)
- Calculated fields (`_clc`)
- Semantic metrics (`_mtc`)

**What to look for:**
- Missing business logic (e.g., no win rate field but you have won/total counts)
- Field data types and aggregation types (you'll need these when creating calc fields)
- Table names (`objectName`) for dimension/measurement references
- Existing calculated fields that metrics could reference

### Before Creating Fields: Verify Field Names

Always verify field names exist in the SDM before referencing them in expressions.

**Field Reference Rules:**

1. **Table fields** (semanticMeasurements/semanticDimensions): MUST use qualified syntax `[TableName].[FieldName]`
2. **Calculated fields** (_clc suffix): Use unqualified syntax `[FieldName]` (they're model-level, not table-specific)

```bash
# 1. Discover SDM fields first
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json

# 2. Check available fields in the JSON output
# - semanticDataObjects[].objectName (table) and .semanticMeasurements/.semanticDimensions (table fields)
# - calculatedMeasurements/calculatedDimensions (model-level calc fields)

# 3. Use correct syntax based on field type
[Opportunity_TAB_Sales_Cloud].[Amount]   # Correct - table field (qualified)
[Total_Revenue_clc]                      # Correct - calculated field (unqualified)
[Amount]                                  # Wrong - table field must be qualified
[Opportunity_TAB_Sales_Cloud].[Total_Revenue_clc] # Wrong - calc fields are model-level, not table-specific
```

**Common errors:**
- Using unqualified names for table fields (they must be qualified)
- Using qualified names for calculated fields (they're model-level, cannot be qualified)
- Referencing field names without checking SDM output (apiName may be `Amount`, `Amount1`, etc. depending on joins)
- Referencing fields that don't exist in the SDM

## Calculated Fields

Calculated fields add custom business logic to the semantic layer. They're reusable across visualizations and can be measurements (aggregated) or dimensions (categorical).

### Creating Calculated Measurements

Measurements are aggregated numeric fields (sum, average, count, etc.).

**Basic example:**

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Amount])" \
  --aggregation Sum
```

**Ratio example (win rate):**

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Won_Count]) / SUM([Opportunity_TAB_Sales_Cloud].[Total_Count])" \
  --aggregation UserAgg
```

**Why `UserAgg` for ratios:** The expression already includes aggregation functions (`SUM`). Using `Sum` or `Avg` would add another aggregation layer on top, producing incorrect results. `UserAgg` preserves the expression's aggregation logic.

### Creating Calculated Dimensions

Dimensions are categorical fields used for grouping and filtering.

**DATEPART returns numbers:** DATEPART and DATEDIFF return numeric values. For dimensions, wrap in STR() to convert to text. For measurements (to calculate averages or sums), use without STR() and specify aggregation type.

**Example (extracting month from date for grouping):**

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Close_Month_clc \
  --label "Close Month" \
  --expression "STR(DATEPART('month', [Opportunity_TAB_Sales_Cloud].[Close_Date]))"
```

**Example (conditional logic):**

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Deal_Size_Category_clc \
  --label "Deal Size Category" \
  --expression "IF [Opportunity_TAB_Sales_Cloud].[Amount] > 100000 THEN 'Large' ELSEIF [Opportunity_TAB_Sales_Cloud].[Amount] > 50000 THEN 'Medium' ELSE 'Small' END"
```

### Aggregation Types

When creating measurements, choose the correct aggregation type based on how the field should behave in visualizations:

| Aggregation | Use When | Example |
|-------------|----------|---------|
| `Sum` | Additive values (revenue, count) | `SUM([Table].[Amount])` |
| `Avg` | Average needed (rates, percentages when raw values available) | `AVG([Table].[Close_Days])` |
| `UserAgg` | Expression already includes aggregation | `SUM([Table].[Won]) / SUM([Table].[Total])` |
| `Min` | Minimum value | `MIN([Table].[Close_Date])` |
| `Max` | Maximum value | `MAX([Table].[Amount])` |
| `Count` | Row count | `COUNT([Table].[Opportunity_Id])` |

**Critical:** Don't guess aggregation types. If uncertain, inspect the SDM first to see how similar fields are configured, or use `UserAgg` when your expression already includes aggregation functions.

### Common Expression Patterns

**Time calculations:**
```tableau
DATEDIFF('day', [Table].[Created_Date], [Table].[Close_Date])
```

**Conditional aggregation:**
```tableau
SUM(IF [Table].[Stage] = 'Closed Won' THEN [Table].[Amount] ELSE 0 END)
```

**String manipulation:**
```tableau
UPPER([Table].[Account_Name])
LEFT([Table].[Opportunity_Name], 10)
```

**Null handling:**
```tableau
IFNULL([Table].[Amount], 0)
```

See [references/tableau-functions.md](references/tableau-functions.md) for complete function reference.

## Semantic Metrics

Before creating a new metric, decide whether the request is:
- A new reusable business formula: create or reuse a calculated field, then create the metric.
- A scoped variant of an existing metric: keep the same measurement reference and use native metric filters.

For scoped variants, inspect an existing live metric first, then pass the filter objects through unchanged with `create_metric.py --filter-json` or `--filters-file`.

Metrics are lightweight wrappers for Tableau Next dashboard KPI widgets. They reference existing calculated fields and include time dimension configuration.

### Creating a Basic Metric

**Prerequisite:** Create the calculated field first. Metrics reference calculated fields by API name, so the calc field must exist before the metric can be created.

```bash
# Step 1: Create calculated field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Amount])" \
  --aggregation Sum

# Step 2: Create metric referencing it
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Total_Revenue_mtc \
  --label "Total Revenue" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

### Metric with Additional Dimensions

Additional dimensions enable breakdown analysis (e.g., "Revenue by Region" or "Top contributors by Industry").

```bash
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Revenue_by_Region_mtc \
  --label "Revenue by Region" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud \
  --additional-dimension "Region:Opportunity_TAB_Sales_Cloud" \
  --additional-dimension "Industry:Account_TAB_Sales_Cloud"
```

Format: `fieldApiName:tableApiName` (repeat `--additional-dimension` for multiple dimensions).

**When additional dimensions are provided, the system automatically generates `insightsSettings`** with enabled insight types (TopContributors, TrendChangeAlert, BottomContributors, etc.) and maps the dimensions to `insightsDimensionsReferences`.

### Metric Structure

Metrics include:
- `measurementReference.calculatedFieldApiName` — references the calc field
- `timeDimensionReference` — field + table for time-based analysis
- `timeGrains` — defaults to `["Day", "Week", "Month", "Quarter", "Year"]`
- `additionalDimensions` — optional breakdown dimensions
- `insightsSettings` — auto-generated when additional dimensions exist
- `isCumulative` — set to `true` for cumulative metrics (default `false`)
- `sentiment` — `SentimentTypeUpIsGood`, `SentimentTypeUpIsBad`, or `SentimentTypeNone`

See [references/metric-design.md](references/metric-design.md) for design patterns.

## Validation

### Validate Expressions Before Creating Fields

Dry-run mode shows the payload without POSTing:

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Won]) / SUM([Opportunity_TAB_Sales_Cloud].[Total])" \
  --aggregation UserAgg \
  --dry-run
```

Review the JSON output to verify:
- Expression syntax is correct
- Field references exist in the SDM (check with `discover_sdm.py`)
- Aggregation type matches the expression
- API name follows conventions (`_clc`, no `__`)

### Supported Tableau Functions

The system validates function names against supported Tableau functions. Common categories:

- **Aggregation:** `SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, `COUNTD`
- **Date:** `DATEPART`, `DATEDIFF`, `DATEADD`, `NOW`, `TODAY`
- **String:** `LEFT`, `RIGHT`, `MID`, `UPPER`, `LOWER`, `CONTAINS`, `SPLIT`
- **Logic:** `IF`, `CASE`, `IFNULL`, `ISNULL`, `ZN`
- **Math:** `ABS`, `ROUND`, `CEILING`, `FLOOR`, `POWER`, `SQRT`

See [references/tableau-functions.md](references/tableau-functions.md) for complete list.

## Script Cheat Sheet

**Discovery:**
```bash
# List all SDMs
python scripts/discover_sdm.py --list

# Inspect SDM structure
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json
```

**Calculated Fields:**
```bash
# Create measurement
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --type measurement \
  --name {{FIELD_NAME}}_clc \
  --label "{{Display Label}}" \
  --expression "{{TABLEAU_FORMULA}}" \
  --aggregation {{Sum|Avg|UserAgg|Min|Max|Count}}

# Create dimension
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --type dimension \
  --name {{FIELD_NAME}}_clc \
  --label "{{Display Label}}" \
  --expression "{{TABLEAU_FORMULA}}"

# Dry-run (show payload without POSTing)
python scripts/create_calc_field.py ... --dry-run
```

**Metrics:**
```bash
# Create basic metric
python scripts/create_metric.py \
  --sdm {{SDM_NAME}} \
  --name {{METRIC_NAME}}_mtc \
  --label "{{Display Label}}" \
  --calculated-field {{CALC_FIELD_NAME}}_clc \
  --time-field {{TIME_FIELD}} \
  --time-table {{TABLE_NAME}}

# Create metric with breakdown dimensions
python scripts/create_metric.py \
  --sdm {{SDM_NAME}} \
  --name {{METRIC_NAME}}_mtc \
  --label "{{Display Label}}" \
  --calculated-field {{CALC_FIELD_NAME}}_clc \
  --time-field {{TIME_FIELD}} \
  --time-table {{TABLE_NAME}} \
  --additional-dimension "{{FIELD}}:{{TABLE}}" \
  --additional-dimension "{{FIELD2}}:{{TABLE2}}"

# Dry-run
python scripts/create_metric.py ... --dry-run
```

**Script Location:**
Scripts are symlinked from `tableau-next-author/scripts/` (shared). Run `python scripts/lib/verify_paths.py` to verify scripts are accessible. Ensure both skills are installed in `skills/`.

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `API name cannot contain double underscores` | Name includes `__` | Remove `__`: `Field__Name` → `Field_Name` |
| `API name must end with '_clc'` | Missing suffix | Add `_clc`: `Win_Rate` → `Win_Rate_clc` |
| `Invalid function 'SUMIF'` | Function not supported in Tableau | Use `SUM(IF ... THEN ... END)` instead |
| `Field 'Amount' not found` | Field doesn't exist in SDM | Run `discover_sdm.py` to verify field name |
| `Validation error: aggregationType required` | Missing `--aggregation` flag | Add `--aggregation Sum` (or appropriate type) |
| `measurementReference.calculatedFieldApiName not found` | Calc field doesn't exist yet | Create calc field first, then metric |
| `401 Unauthorized` | Token expired | Refresh: `sf org display --target-org $SF_ORG` |

## Prerequisites

**Easy Authentication (Recommended):**
1. Salesforce CLI: `sf` command installed
2. Authenticated org: `sf org login web --alias myorg`
3. `jq` for JSON parsing: `brew install jq` (macOS) or `apt install jq` (Linux)
4. Python 3.8+ with `requests`: `pip install requests`

**Quick auth setup:**
```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

Scripts automatically use these environment variables.

## API Endpoints

```
Discovery (no minor version):
GET  /services/data/v66.0/ssot/semantic/models
GET  /services/data/v66.0/ssot/semantic/models/{sdmName}

Creation (no minor version):
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-measurements
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-dimensions
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/metrics
```

**Authentication:** All requests require `Authorization: Bearer {token}` header.

See [references/api-reference.md](references/api-reference.md) for complete API documentation.

## Best Practices

### Prefer CLC Fields Over Raw Fields

When creating fields, prefer calculated fields (`_clc`) even for simple formulas. This centralizes business logic and makes it reusable.

**Example:**
```bash
# Instead of using raw [Table].[Amount] everywhere, create:
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Amount])" \
  --aggregation Sum
```

### Use Meaningful Names

API names should communicate business meaning, not generic identifiers.

**Good:**
- `Win_Rate_clc`
- `Total_Revenue_mtc`
- `Deal_Size_Category_clc`

**Bad:**
- `Field_1_clc`
- `Metric_2_mtc`
- `Calc_Field_clc`

### Two-Step Workflow for Metrics

Create the calculated field first, then the metric. Metrics reference calc fields by API name in `measurementReference.calculatedFieldApiName`, so attempting to create a metric before its calc field exists will fail with a "Field not found" error.

### Test Fields Before Creating Metrics

After creating a calc field, verify it works in a visualization (using `tableau-next-author` skill) before creating a metric. This catches expression errors early.

**Verification steps after field/metric creation:**
1. **Confirm existence:** Run `discover_sdm.py --sdm {{NAME}} --json` and search for your API name in the response
2. **Check API response:** POST response includes `apiName` and `success: true` on successful creation
3. **Test in visualization:** Create a simple chart using the calc field, or reference the metric in a dashboard widget
4. **Validate calculations:** Compare output values against manual calculations to verify expression logic

### Read Aggregation Types from SDM

Don't assume aggregation types—inspect the SDM to see how similar fields are configured. Use `discover_sdm.py --sdm {{NAME}} --json` and look at `aggregationType` for existing measurements.

## Real-World Patterns

The following patterns are learned from analyzing 25+ production dashboard packages. Use these as guidance when designing your own fields and metrics.

**See also:** [references/lintao-aggregations.md](references/lintao-aggregations.md) for time-based aggregation patterns (snapshot sums, annualization, DATEDIFF) and 40+ composite KPI formulas from finance/banking domains.

### Metric Design Patterns

**Additional Dimensions:**
- Sales metrics typically include 4–5 breakdown dimensions: Account_Name, Opportunity_Type, Account_Industry, Account_Type, Full_Name
- Choose dimensions that enable meaningful "Top contributors" and "Top detractors" insights
- Avoid using too many dimensions (5+ can dilute insights)

**Time Dimension Selection:**
- Pipeline/forecast metrics → Use `Created_Date` (when opportunity entered pipeline)
- Revenue/closed metrics → Use `Close_Date` (when deal closed)
- Process metrics → Use event date (when action occurred)

**Insights Settings (common pattern):**
```json
{
  "insightTypes": [
    {"enabled": false, "type": "TopContributors"},
    {"enabled": false, "type": "ComparisonToExpectedRangeAlert"},
    {"enabled": true, "type": "TrendChangeAlert"},
    {"enabled": true, "type": "BottomContributors"},
    {"enabled": true, "type": "ConcentratedContributionAlert"},
    {"enabled": true, "type": "TopDrivers"},
    {"enabled": true, "type": "TopDetractors"},
    {"enabled": true, "type": "CurrentTrend"}
  ]
}
```

TopContributors and ComparisonToExpectedRangeAlert are often disabled; trend-based insights are enabled.

**Plural/Singular Nouns:**
Often left empty (`""`) in production packages, but can improve readability when specified (e.g., `"calls"`, `"opportunities"`).

### Calculated Field Patterns

**Ratios → UserAgg:**
```tableau
SUM([Table].[Won_Count]) / SUM([Table].[Total_Count])
```
Always use `aggregationType: UserAgg` when expression includes aggregation functions.

**Conditional Aggregation → UserAgg:**
```tableau
SUM(IF [Table].[Stage] = 'Closed Won' THEN [Table].[Amount] ELSE 0 END)
```
Or referencing a calculated field (unqualified):
```tableau
SUM(IF NOT [Is_Open_Opportunity_clc] THEN [OpportunityLineItem_TAB_Sales_Cloud].[Product_Quantity]*[OpportunityLineItem_TAB_Sales_Cloud].[List_Price_Amount] END)
```

**Referencing Other Calc Fields:**
```tableau
SUM([Total_Sales_clc])/[Total_Closed_Opportunities_Amount_clc]
```
Valid to reference other calculated fields in expressions. Calculated fields are model-level and use unqualified syntax `[FieldName_clc]`. Table fields require qualified syntax `[Table].[Field]`.

**Weighted Calculations:**
```tableau
SUM(FLOAT([Probability_clc] * [Table].[Quantity]*[Table].[Price]))
```
Use FLOAT() for probability-weighted values.

**LOD (Level of Detail) Expressions:**
```tableau
{ FIXED [Table].[Fiscal_Quarter] : SUM([Table].[Quota_USD]) }
```
FIXED expressions compute aggregations at specific dimension levels, independent of other dimensions in the view. Common uses:
- Quota allocation across time periods
- Percent of total calculations
- Running totals or cumulative metrics
- Comparing values across different granularities

LOD syntax: `{ FIXED [Table].[dimension] : aggregation_function([Table].[measure]) }`

### Dimension Patterns

**Tiering by Thresholds:**
```tableau
IF [Table].[CSAT] >= 60 THEN "Tier 1"
ELSEIF [Table].[CSAT] <= 20 THEN "Tier 3 - Escalated"
ELSE "Tier 2"
END
```

**Mapping with CASE:**
```tableau
CASE [Table].[Call_Reason]
  WHEN "Benefits Inquiry" THEN "General Platform Issues"
  WHEN "Billing Question" THEN "Regulatory Document Upload Issues"
  ELSE [Table].[Call_Reason]
END
```

**Boolean Flags:**
```tableau
If [Table].[Type]="Self" then "Site User" else "Participant" end
```

**Referencing Calculated Fields in Dimensions:**
```tableau
IF [Is_Open_Opportunity_clc] THEN 'Open' ELSEIF [Is_Won_Opportunity_clc] THEN 'Won' ELSE 'Lost' END
```
Calculated fields use unqualified syntax. Table fields require `[TableName].[FieldName]`:
```tableau
[HLS_Call_Center_Dataverse].[Member_CSAT]
```

### Industry-Specific Patterns

**Sales:**
- Win_Rate_clc, Conversion_Rate_clc, Pipeline_Generation_clc
- Weighted_Pipeline_Value_clc (probability * amount)
- Sales_Cycle_Won_clc (time between Created_Date and Close_Date)
- Quota_Per_Fiscal_Quarter_clc (FIXED LOD for quota allocation)

**Service:**
- Average_Time_To_Close_clc (UserAgg)
- CSAT_clc, Volume_clc (UserAgg)
- Reopen_Rate_clc (ratio)

**HR:**
- Headcount_clc, Turnover_Rate_clc
- Employee tiering by age ranges or seniority

**Healthcare:**
- Call volume, wait times
- Tiering by CSAT or priority
- Channel mapping (Portal, Call, Email, etc.)

### Reference Examples

**Tableau Next (modern platform):**
- `Sales_Cloud12_package.json` in `.cursor/tabnext-tools-main/collection/`
- Contains full semantic model with calc measurements, dimensions, and metrics
- Shows production-ready insightsSettings, additionalDimensions, and expression patterns

**Lintao Linpack (legacy acquisition - advanced patterns):**
- [references/lintao-aggregations.md](references/lintao-aggregations.md) — Time-based aggregation patterns (native Tableau), composite KPI formulas, color semantics
- 40+ production dashboard templates across Finance, Banking, Sales, HR domains
- Time-based aggregations (snapshot sums, annualization), lifecycle tracking (new/lost counts via LOD), period-constrained calculations

## Next Steps

After enriching the semantic layer:
- **Create visualizations:** Use `tableau-next-author` skill to build charts with your new calc fields
- **Build dashboards:** Reference metrics in Tableau Next dashboard KPI widgets

---

## Reference Files

- [references/tableau-functions.md](references/tableau-functions.md) — Complete Tableau function reference
- [references/field-types.md](references/field-types.md) — Measurements vs dimensions deep dive
- [references/metric-design.md](references/metric-design.md) — Metric design patterns and examples
- [references/lintao-aggregations.md](references/lintao-aggregations.md) — Lintao Linpack aggregations, KPI formulas, color semantics (from acquisition)
- [references/api-reference.md](references/api-reference.md) — Full REST API documentation
