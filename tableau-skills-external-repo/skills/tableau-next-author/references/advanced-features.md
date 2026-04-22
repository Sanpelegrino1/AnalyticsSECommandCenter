# Advanced Features: Calculated Fields

> **Back to main skill:** [SKILL.md](SKILL.md)

Create calculated measurements and dimensions on semantic models to extend your data model with custom formulas.

## Overview

Calculated fields allow you to:
- Create custom metrics from existing measures (e.g., win rates, percentages)
- Create custom dimensions from existing fields (e.g., bucketing, boolean flags)
- Use Tableau formula language for complex calculations
- Reference calculated fields in visualizations immediately after creation

## Calculated Measurements

Calculated measurements support two aggregation approaches depending on whether your expression contains aggregation functions.

### Approach 1: Aggregation in Expression (UserAgg)

When the expression contains aggregation functions (SUM, AVG, COUNTD, etc.), the system automatically uses `aggregationType: "UserAgg"` and `level: "AggregateFunction"`:

```bash
# Expression WITH aggregation function → auto UserAgg
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Won_Count]) / SUM([Total_Count])" \
  --aggregation Sum  # Will be auto-converted to UserAgg
```

**Example expressions:**
- `"SUM([Won_Count]) / SUM([Total_Count])"` → Win rate percentage
- `"AVG([Amount]) / AVG([Quantity])"` → Average price per unit
- `"COUNTD([Account_Id])"` → Unique account count

### Approach 2: Explicit Aggregation (Sum/Avg/etc.)

When the expression does NOT contain aggregation functions, use explicit aggregation type with `level: "Row"`:

```bash
# Expression WITHOUT aggregation function → explicit Sum
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --type measurement \
  --name Total_Sales_clc \
  --label "Total Sales" \
  --expression "IF [Is_Won] THEN [Quantity]*[Price] END" \
  --aggregation Sum  # Uses explicit Sum aggregation
```

**Example expressions:**
- `"IF [Is_Won] THEN [Quantity]*[Price] END"` → Conditional calculation (then aggregated)
- `"[Amount] * 1.1"` → Apply multiplier (then aggregated)
- `"DATEDIFF('day', [Created_Date], [Close_Date])"` → Date difference (then aggregated)

### Aggregation Handling

The system automatically detects if your expression contains aggregation functions:

- **With aggregation in expression**: Uses `UserAgg` + `AggregateFunction` level
  - Example: `"expression": "SUM([Amount])"`
  - Result: `aggregationType: "UserAgg"`, `level: "AggregateFunction"`

- **Without aggregation in expression**: Uses explicit aggregation type + `Row` level
  - Example: `"expression": "IF [Won] THEN [Amount] END"` with `aggregationType: "Sum"`
  - Result: `aggregationType: "Sum"`, `level: "Row"`

## Calculated Dimensions

Create custom dimensions for grouping and filtering:

```bash
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --type dimension \
  --name Deal_Size_Bucket_clc \
  --label "Deal Size" \
  --expression "IF [Amount] < 10000 THEN 'Small' ELSEIF [Amount] < 50000 THEN 'Medium' ELSE 'Large' END"
```

**Example expressions:**
- `"IF [Amount] < 10000 THEN 'Small' ELSEIF [Amount] < 50000 THEN 'Medium' ELSE 'Large' END"` → Value bucketing
- `"[Stage] = 'Closed Won'"` → Boolean flag
- `"UPPER([Region])"` → Text transformation
- `"DATEPART('month', [Close_Date])"` → Date part extraction

## Template-Based Creation (Recommended)

Use pre-built templates for common calculations:

```bash
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --template win_rate \
  --template-args '{"won_field": "Stage_Won_Count", "total_field": "Stage_Total_Count"}' \
  --name Win_Rate_clc \
  --label "Win Rate"
```

### Available Templates

| Template | Description | Example Expression |
|----------|-------------|-------------------|
| `win_rate` | Ratio calculation | `SUM([Won]) / SUM([Total])` |
| `days_between` | Date difference | `DATEDIFF('day', [Start], [End])` |
| `bucket_amount` | Value bucketing | `IF [Amount] < 10000 THEN 'Small' ELSEIF [Amount] < 50000 THEN 'Medium' ELSE 'Large' END` |
| `is_equal` | Boolean check | `[Stage] = 'Closed Won'` |
| `count_distinct` | Unique count | `COUNTD([Field])` |
| `percentage_of_total` | Percent of total | `SUM([Field]) / TOTAL(SUM([Field]))` |

## Formula Syntax

**Language:** Tableau formula language (aggregations, date functions, conditionals, LOD expressions)

**Field references:** Use `[FieldName]` or `[ObjectName].[FieldName]` format

**Examples:**
- `[Amount]` → Field reference
- `[Opportunity].[Amount]` → Qualified field reference
- `SUM([Amount])` → Aggregation function
- `IF [Stage] = 'Won' THEN [Amount] END` → Conditional
- `DATEDIFF('day', [Created_Date], [Close_Date])` → Date function

## Expression Validation

The system validates function names in expressions using a comprehensive Tableau function reference (based on Tableau Prep). Invalid functions are caught before API submission with helpful suggestions.

### Supported Function Categories

**Aggregation:**
- `SUM`, `AVG`, `COUNT`, `COUNTD`, `MIN`, `MAX`, `MEDIAN`, `STDEV`, `VAR`

**Date:**
- `DATE`, `DATEDIFF`, `DATEPART`, `DATETRUNC`, `DAY`, `MONTH`, `YEAR`, `TODAY`, `NOW`

**String:**
- `CONTAINS`, `LEFT`, `RIGHT`, `UPPER`, `LOWER`, `TRIM`, `REPLACE`, `SPLIT`

**Logical:**
- `IF/THEN/ELSE`, `CASE/WHEN/THEN`, `AND`, `OR`, `NOT`, `ISNULL`, `IFNULL`

**Math:**
- `ROUND`, `ABS`, `CEILING`, `FLOOR`, `SQRT`, `POWER`, `LOG`, `LN`

**LOD (Level of Detail):**
- `FIXED`, `INCLUDE`, `EXCLUDE`

**Window:**
- `RANK`, `ROW_NUMBER`, `LOOKUP`, `RUNNING_AVG`, `RUNNING_SUM`

## API Naming Rules

**Important:** API name must:
- End with `_clc` suffix (e.g., `Win_Rate_clc`)
- Not contain double underscores (`__`)
- Be unique within the SDM

**Examples:**
- ✅ `Win_Rate_clc`
- ✅ `Deal_Size_Bucket_clc`
- ❌ `Win_Rate` (missing `_clc`)
- ❌ `Win__Rate_clc` (double underscore)

## Using Calculated Fields in Visualizations

After creating a calculated field, it immediately appears in SDM discovery and can be used in visualizations.

### Field Definition for Calculated Fields

**Calculated measurements:**
```json
"F2": {
  "type": "Field",
  "displayCategory": "Continuous",
  "role": "Measure",
  "objectName": null,  // Always null for _clc fields
  "fieldName": "Win_Rate_clc",  // Full apiName including _clc
  "function": "UserAgg"  // Read from SDM aggregationType
}
```

**Calculated dimensions:**
```json
"F1": {
  "type": "Field",
  "displayCategory": "Discrete",
  "role": "Dimension",
  "objectName": null,  // Always null for _clc fields
  "fieldName": "Deal_Size_Bucket_clc",  // Full apiName including _clc
  "function": null
}
```

### Critical Rules

1. **Always read `aggregationType` from SDM**: Never assume `"Sum"` — read it from `semanticCalculatedMeasurements[]` in the SDM response
2. **Use `objectName: null`**: Calculated fields always use `null` for `objectName`
3. **Use full `apiName`**: Include the `_clc` suffix in `fieldName`
4. **Match `function` to `aggregationType`**: Use the exact value from SDM (e.g., `"UserAgg"`, `"Sum"`, `"Min"`)

### Example: Using Calculated Field

**1. Create calculated field:**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Model \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Won_Count]) / SUM([Total_Count])" \
  --aggregation Sum
```

**2. Discover SDM to get aggregationType:**
```bash
python scripts/discover_sdm.py --sdm Sales_Model --json
```

**3. Use in visualization:**
```json
"F2": {
  "type": "Field",
  "displayCategory": "Continuous",
  "role": "Measure",
  "objectName": null,
  "fieldName": "Win_Rate_clc",
  "function": "UserAgg"  // From SDM aggregationType
}
```

## Common Patterns

### Win Rate Calculation

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Model \
  --template win_rate \
  --template-args '{"won_field": "Stage_Won_Count", "total_field": "Stage_Total_Count"}' \
  --name Win_Rate_clc \
  --label "Win Rate"
```

### Deal Size Bucketing

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Model \
  --type dimension \
  --name Deal_Size_Bucket_clc \
  --label "Deal Size" \
  --expression "IF [Amount] < 10000 THEN 'Small' ELSEIF [Amount] < 50000 THEN 'Medium' ELSE 'Large' END"
```

### Days to Close

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Model \
  --template days_between \
  --template-args '{"start_field": "Created_Date", "end_field": "Close_Date"}' \
  --name Days_to_Close_clc \
  --label "Days to Close"
```

### Percentage of Total

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Model \
  --template percentage_of_total \
  --template-args '{"field": "Amount"}' \
  --name Amount_Percent_of_Total_clc \
  --label "Amount % of Total"
```

## Troubleshooting

**Field not appearing in SDM discovery:**
- Wait a few seconds after creation (SDM may need to refresh)
- Verify field was created: Check API response for success
- Re-run discovery: `python scripts/discover_sdm.py --sdm {{SDM_NAME}}`

**Expression validation errors:**
- Check function names match supported list
- Verify field references use correct syntax: `[FieldName]` or `[ObjectName].[FieldName]`
- Check for typos in field names

**Aggregation type errors:**
- Always read `aggregationType` from SDM discovery response
- Don't assume `"Sum"` — it could be `"UserAgg"`, `"Min"`, etc.
- Use `objectName: null` for calculated fields

**API name errors:**
- Ensure name ends with `_clc`
- Remove double underscores (`__`)
- Check name is unique within SDM

## Semantic Metrics

Semantic metrics (`_mtc`) are simpler than calculated measurements - they provide a lightweight way to create aggregated metrics on SDMs for use in dashboard metric widgets.

### What Are Metrics vs Calculated Measurements?

**Semantic Metrics (`_mtc`):**
- Reference calculated fields via `measurementReference.calculatedFieldApiName`
- Require `timeDimensionReference` for time-based analysis
- Include `timeGrains` (Day, Week, Month, Quarter, Year)
- Designed for dashboard metric widgets with time dimension support
- Structure: `aggregationType`, `measurementReference`, `timeDimensionReference`, `timeGrains`

**Calculated Measurements (`_clc`):**
- Rich structure: includes `aggregationType`, `dataType`, `decimalPlace`, `level`, `expression`, etc.
- Designed for use in visualizations
- More configuration options for visualization needs
- Contain the actual formula/expression

### When to Use Metrics vs Calculated Fields

**Use Metrics (`_mtc`) when:**
- Creating KPIs for dashboard metric widgets
- You need time-based analysis (metrics include time dimension)
- You want to wrap an existing calculated field with time dimension support

**Use Calculated Measurements (`_clc`) when:**
- Creating fields for visualizations
- You need specific aggregation types, data types, or decimal places
- You need more control over how the field behaves in charts
- You're building the base calculation that metrics will reference

### Creating Metrics

**Workflow:** Create calculated field first, then create metric referencing it.

**Step 1: Create calculated field**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Amount])" \
  --aggregation Sum
```

**Step 2: Create metric referencing calculated field**
```bash
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Total_Revenue_mtc \
  --label "Total Revenue" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

**Example: Win Rate Metric**
```bash
# 1. Create win rate calculated field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Won_Count]) / SUM([Total_Count])" \
  --aggregation Sum

# 2. Create metric referencing it
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Win_Rate_mtc \
  --label "Win Rate" \
  --calculated-field Win_Rate_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

**Note:** Templates (sum, avg, win_rate, etc.) are for creating calculated fields, not metrics. Metrics always reference existing calculated fields.

### Additional Dimensions and Insights

Metrics support additional dimensions for breakdown analysis and insights generation. When you add additional dimensions, the system automatically generates `insightsSettings` with insights types enabled.

**Adding additional dimensions:**
```bash
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Revenue_by_Account_mtc \
  --label "Revenue by Account" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud \
  --additional-dimension Account_Id:Account_TAB_Sales_Cloud \
  --additional-dimension Account_Industry:Account_TAB_Sales_Cloud
```

**What this enables:**
- Breakdown analysis by the specified dimensions
- Automatic insights generation (TopContributors, TopDrivers, TrendChangeAlert, etc.)
- Insights dimensions references matching the additional dimensions

**Note:** Additional dimensions are optional. Metrics work fine without them, but adding dimensions enables richer analysis capabilities.

### Using Metrics in Dashboards

After creating a metric, it immediately appears in SDM discovery and can be used in dashboard metric widgets:

```python
from lib.templates import MetricDef

metric_defs = [
    MetricDef(
        metric_api_name="Total_Revenue_mtc",
        sdm_api_name="Sales_Cloud12_SDM_1772196180"
    )
]

# Use in dashboard
dashboard = build_dashboard(
    name="Sales_Dashboard",
    metric_defs=metric_defs,
    # ... other args
)
```

### API Naming Rules

**Important:** API name must:
- End with `_mtc` suffix (e.g., `Total_Revenue_mtc`)
- Not contain double underscores (`__`)
- Be unique within the SDM

**Examples:**
- ✅ `Total_Revenue_mtc`
- ✅ `Win_Rate_mtc`
- ❌ `Total_Revenue` (missing `_mtc`)
- ❌ `Total__Revenue_mtc` (double underscore)

### Troubleshooting

**Metric not appearing in SDM discovery:**
- Wait a few seconds after creation (SDM may need to refresh)
- Verify metric was created: Check API response for success
- Re-run discovery: `python scripts/discover_sdm.py --sdm {{SDM_NAME}}`

**Expression validation errors:**
- Check function names match supported list
- Verify field references use correct syntax: `[FieldName]` or `[ObjectName].[FieldName]`
- Check for typos in field names

**API name errors:**
- Ensure name ends with `_mtc`
- Remove double underscores (`__`)
- Check name is unique within SDM

## Related Documentation

- [scripts-guide.md](scripts-guide.md) - Script usage for creating calculated fields and metrics
- [workflow.md](workflow.md) - Using calculated fields in visualizations
- [templates-guide.md](templates-guide.md) - Visualization templates that use calculated fields
- [troubleshooting.md](troubleshooting.md) - Common errors and solutions
