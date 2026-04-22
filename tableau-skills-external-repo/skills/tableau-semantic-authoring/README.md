# Tableau Semantic Authoring

Enrich Semantic Data Models with calculated fields, dimensions, and metrics for Tableau Next. The semantic layer lives in Data 360.

## Quick Start

```bash
# 1. Discover available SDMs
python scripts/discover_sdm.py --list

# 2. Inspect SDM structure
python scripts/discover_sdm.py --sdm Sales_Cloud12_backward --json

# 3. Create calculated field when you need reusable semantic logic
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Won_Count]) / SUM([Total_Count])" \
  --aggregation UserAgg

# 4. Create metric referencing the calculated field
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Win_Rate_mtc \
  --label "Win Rate" \
  --calculated-field Win_Rate_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud

# 5. For a scoped variant of an existing metric, prefer metric-native filters.
# First inspect the live metric JSON, then pass its filter objects through unchanged.
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Win_Rate_Last_60_Days_mtc \
  --label "Win Rate Last 60 Days" \
  --calculated-field Win_Rate_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud \
  --filters-file metric-filters.json
```

## What This Skill Does

- **Discover** — List SDMs and inspect field definitions
- **Create calculated fields** — Add custom business logic (measurements and dimensions)
- **Create metrics** — Build time-based KPIs for Tableau Next dashboards
- **Create scoped metric variants** — Apply metric-native filters without forcing new calculated fields
- **Validate** — Check Tableau expressions before POSTing

## When to Use

Use this skill **before** building Tableau Next dashboards when you need:
- Custom business logic (win rates, conversion rates, weighted pipelines)
- Categorical dimensions derived from other fields
- Reusable metrics across multiple dashboards
- Standardized business definitions on the semantic layer
- Scoped variants of existing metrics such as last-N-days, current-quarter, or filtered business slices

## Scripts & Bundling

Scripts are **shared with the tableau-next-author skill** via symlinks in `scripts/`. This skill must be installed alongside `tableau-next-author` for scripts to work.

**Verify installation:**
```bash
python scripts/lib/verify_paths.py
```

If you see "Missing scripts", ensure both skills are present in `skills/` and symlinks exist. **Fallback:** run scripts directly from tableau-next-author:
```bash
python ../tableau-next-author/scripts/discover_sdm.py --list
```

## Prerequisites

- Salesforce CLI (`sf`) authenticated to org with semantic model access
- Python 3.8+ with `requests` library
- `jq` for JSON parsing
- tableau-next-author skill installed (provides shared scripts)

**Quick setup:**
```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

## Common Use Cases

### Create a Win Rate Metric

```bash
# Step 1: Create calculated field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Won_Count]) / SUM([Total_Count])" \
  --aggregation UserAgg

# Step 2: Create metric
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Win_Rate_mtc \
  --label "Win Rate" \
  --calculated-field Win_Rate_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

### Create a Metric with Breakdown Dimensions

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

### Create a Scoped Variant of an Existing Metric

Use this when the user wants the same metric definition with a date or business filter applied.

1. Inspect the existing live metric and copy its `filters` array.
2. Reuse the same measurement reference.
3. Pass the filter objects to `create_metric.py` with `--filter-json` or `--filters-file`.

Do not add a new `_clc` field unless the user explicitly wants reusable semantic logic beyond the metric itself.

### Create a Categorical Dimension

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Deal_Size_Category_clc \
  --label "Deal Size Category" \
  --expression "IF [Amount] > 100000 THEN 'Large' ELSEIF [Amount] > 50000 THEN 'Medium' ELSE 'Small' END"
```

## Next Steps

After enriching the semantic layer:
- **Build visualizations** — Use `tableau-next-author` skill
- **Build dashboards** — Reference metrics in Tableau Next dashboard KPI widgets

## Documentation

See [SKILL.md](SKILL.md) for complete documentation including:
- Discovery workflow
- Calculated field patterns
- Metric design best practices
- Tableau function reference
- Common errors and fixes
