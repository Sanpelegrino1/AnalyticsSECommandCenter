# Scripts Guide

> **Back to main skill:** [SKILL.md](SKILL.md)

Instead of manually assembling JSON, use the helper scripts in `scripts/`. They eliminate the most common API errors by generating valid payloads programmatically.

## Script Location & Setup

### Finding Scripts

**IMPORTANT for AI Agents**: When you need to run scripts, follow these steps:

1. **Locate the skill directory:**
   - Skill is installed at: `~/.cursor/skills/tableau-next-author/`
   - Scripts are located at: `~/.cursor/skills/tableau-next-author/scripts/`

2. **Change to skill directory before running scripts:**
   ```bash
   cd ~/.cursor/skills/tableau-next-author
   python3 scripts/generate_viz.py [args...]
   ```

3. **Or use absolute paths:**
   ```bash
   python3 ~/.cursor/skills/tableau-next-author/scripts/generate_viz.py [args...]
   ```

### Python Environment Setup

**Python executable detection:**
- Try `python3` first, fallback to `python`
- Scripts require Python 3.8+ with `requests` library
- Check with: `python3 --version` (should be 3.8+)

**Install dependencies:**
```bash
pip3 install requests
```

**If scripts fail:**
- Verify script exists: `ls ~/.cursor/skills/tableau-next-author/scripts/generate_viz.py`
- Install dependencies: `pip3 install requests`
- Check Python version: `python3 --version`

## Discovery Scripts

### discover_sdm.py

Discover available Semantic Data Models and their fields.

**List all SDMs:**
```bash
python scripts/discover_sdm.py --list
```

**Get SDM details:**
```bash
python scripts/discover_sdm.py --sdm {{SDM_NAME}}
```

**Get machine-readable JSON:**
```bash
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json > sdm_fields.json
```

**Example agent workflow:**
```bash
# Navigate to skill directory
cd ~/.cursor/skills/tableau-next-author

# Discover SDM fields
python3 scripts/discover_sdm.py --sdm Sales_Model --json > sdm_fields.json
```

The script outputs:
- Available dimensions (with data types)
- Available measures (with aggregation types)
- Calculated fields (`_clc` suffix)
- Metrics (`_mtc` suffix)

## Generation Scripts

### generate_viz.py

Generate visualization JSON with validation.

**Basic usage:**
```bash
python scripts/generate_viz.py \
  --chart-type bar \
  --name "Revenue_by_Region" --label "Revenue by Region" \
  --sdm-name Sales_Model --sdm-label "Sales" \
  --workspace-name My_WS --workspace-label "My WS" \
  --columns F1 --rows F2 \
  --field F1 role=Dimension fieldName=Region objectName=Opportunity \
  --field F2 role=Measure fieldName=Amount objectName=Opportunity function=Sum \
  --encoding F2 type=Label \
  --style backgroundColor=#1A1A1A --style fontColor=#FFFFFF \
  -o viz.json
```

**With validation:**
```bash
python3 scripts/generate_viz.py \
  --chart-type donut \
  --name Pipeline_Donut \
  --label "Pipeline by Stage" \
  --sdm-name Sales_Model --sdm-label "Sales" \
  --workspace-name My_WS --workspace-label "My Workspace" \
  --columns F1 \
  --field F1 role=Dimension fieldName=Stage objectName=Opportunity \
  --field F2 role=Measure fieldName=Amount objectName=Opportunity function=Sum \
  --encoding F1 type=Color \
  --encoding F2 type=Angle \
  --validate \
  -o viz.json
```

**Style overrides:**

| Key | Default | Controls |
|-----|---------|----------|
| `backgroundColor` | `#FFFFFF` | `style.shading.backgroundColor` |
| `bandingColor` | `#E5E5E5` | `style.shading.banding.rows.color` |
| `fontColor` | `#2E2E2E` | All 7 `style.fonts.*.color` entries |
| `fontSize` | `13` | All `style.fonts.*.size` entries |
| `actionableHeaderColor` | `#0250D9` | `style.fonts.actionableHeaders.color` |
| `lineColor` | `#C9C9C9` | All 4 `style.lines.*.color` entries |
| `fit` | *(chart default)* | `style.fit` |

Supported chart types: `bar`, `line`, `donut`, `scatter`, `table`, `funnel`, `heatmap`, `dot_matrix`.

### generate_dashboard.py

Generate dashboard JSON with filters, metrics, and multi-page support.

**Basic usage:**
```bash
python scripts/generate_dashboard.py \
  --name "Sales_Dashboard" --label "Sales Dashboard" \
  --workspace-name My_WS --sdm-name Sales_Model \
  --title "Sales Performance" \
  --viz Revenue_by_Region --viz Pipeline_Donut \
  --filter fieldName=Account_Industry objectName=Opportunity dataType=Text \
  --metric Total_Revenue_mtc sdmName=Sales_Model \
  --style backgroundColor=#1A1A1A \
  --page "Overview" --page "Details" \
  -o dashboard.json
```

**Multi-page:** Pass `--page` twice+ to auto-generate nav buttons and distribute vizzes across pages.

**Containers:** `--container col=0 row=20 colspan=48 rowspan=2 borderColor=#1B96FF pageIndex=0`.

### generate_dashboard_pattern.py

Generate dashboard JSON using production-ready patterns.

**Auto-select pattern (recommended):**
```bash
python scripts/generate_dashboard_pattern.py \
  --auto-select-pattern \
  --name {{DASHBOARD_NAME}} \
  --workspace-name {{WORKSPACE}} \
  --sdm-name {{SDM_NAME}} \
  --viz {{VIZ_1}} {{VIZ_2}} ... \
  --metrics {{METRIC_1}} {{METRIC_2}} ... \
  --filter fieldName={{FIELD}} objectName={{OBJECT}} dataType={{TYPE}} \
  -o dashboard.json
```

**Explicit pattern:**
```bash
python scripts/generate_dashboard_pattern.py \
  --pattern f_layout \
  --name Sales_Dashboard \
  --label "Sales Dashboard" \
  --workspace-name My_WS \
  --sdm-name Sales_Model \
  --title-text "Sales Performance" \
  --metrics Metric1_mtc Metric2_mtc Metric3_mtc \
  --viz Viz1 Viz2 Viz3 Viz4 Viz5 \
  --filter fieldName=Field1 objectName=Obj1 dataType=Text \
  --filter fieldName=Field2 objectName=Obj1 dataType=Text \
  --filter fieldName=Field3 objectName=Obj1 dataType=Text \
  --filter fieldName=Field4 objectName=Obj1 dataType=Text \
  --filter fieldName=Field5 objectName=Obj1 dataType=Text \
  --filter fieldName=Field6 objectName=Obj1 dataType=Text \
  -o dashboard.json
```

**Check pattern requirements:**
```bash
python scripts/generate_dashboard_pattern.py \
  --pattern f_layout \
  --show-requirements
```

**Validate requirements before building:**
```bash
python scripts/generate_dashboard_pattern.py \
  --pattern f_layout \
  --validate-requirements \
  [other args...]
```

See [templates-guide.md](templates-guide.md) for pattern details.

### apply_viz_template.py

Create visualizations from templates (recommended approach).

**List available templates:**
```bash
python scripts/apply_viz_template.py --list-templates
```

**Preview template requirements:**
```bash
python scripts/apply_viz_template.py --preview revenue_by_category
```

**Create from template:**
```bash
python scripts/apply_viz_template.py \
  --template revenue_by_category \
  --sdm Sales_Model \
  --category Region \
  --amount Total_Amount \
  --name Revenue_by_Region \
  --label "Revenue by Region" \
  --workspace My_Workspace \
  --post
```

**Auto-match fields:**
```bash
python scripts/apply_viz_template.py \
  --template revenue_by_category \
  --sdm Sales_Model \
  --auto-match \
  --name Revenue_Bar \
  --workspace My_Workspace \
  --post
```

**Auto-select chart type:**
```bash
python scripts/apply_viz_template.py \
  --sdm Sales_Model \
  --date Close_Date \
  --measure Total_Amount \
  --auto-select \
  --auto-match \
  --name Sales_Trend \
  --workspace My_Workspace \
  --post
```

See [templates-guide.md](templates-guide.md) for template catalog.

## Validation Scripts

### validate_viz.py

Pre-POST validation (catches 16 common API errors).

**Usage:**
```bash
python scripts/validate_viz.py viz.json
```

**Before POSTing:**
```bash
# Generate visualization
python3 scripts/generate_viz.py [args...] -o viz.json

# Validate before POST
python3 scripts/validate_viz.py viz.json

# If validation passes, POST to API
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/visualizations?minorVersion=12" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @viz.json
```

## Calculated Field Scripts

### create_calc_field.py

Create calculated measurements and dimensions on semantic models.

**Calculated measurements** support two aggregation approaches:

**Approach 1: Aggregation in expression (UserAgg)**
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

**Approach 2: Explicit aggregation (Sum/Avg/etc.)**
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

**Calculated dimensions:**
```bash
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --type dimension \
  --name Deal_Size_Bucket_clc \
  --label "Deal Size" \
  --expression "IF [Amount] < 10000 THEN 'Small' ELSEIF [Amount] < 50000 THEN 'Medium' ELSE 'Large' END"
```

**Template-based (recommended):**
```bash
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --template win_rate \
  --template-args '{"won_field": "Stage_Won_Count", "total_field": "Stage_Total_Count"}' \
  --name Win_Rate_clc \
  --label "Win Rate"
```

**Common templates:**

| Template | Description | Example |
|----------|-------------|---------|
| `win_rate` | Ratio calculation | `SUM([Won]) / SUM([Total])` |
| `days_between` | Date difference | `DATEDIFF('day', [Start], [End])` |
| `bucket_amount` | Value bucketing | `IF [Amount] < 10000 THEN 'Small' ...` |
| `is_equal` | Boolean check | `[Stage] = 'Closed Won'` |
| `count_distinct` | Unique count | `COUNTD([Field])` |
| `percentage_of_total` | Percent of total | `SUM([Field]) / TOTAL(SUM([Field]))` |

**Note:** API name must end with `_clc` and cannot contain double underscores (`__`). The API validates formula syntax and returns helpful error messages for invalid expressions.

### create_metric.py

Create semantic metrics (`_mtc`) on semantic models. **Metrics reference calculated fields** via `measurementReference` and require a time dimension for time-based analysis.

**Workflow:** First create a calculated field (`_clc`), then create a metric (`_mtc`) that references it.

**Step 1: Create calculated field**
```bash
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Amount])" \
  --aggregation Sum
```

**Step 2: Create metric referencing calculated field**
```bash
python scripts/create_metric.py \
  --sdm {{SDM_NAME}} \
  --name Total_Revenue_mtc \
  --label "Total Revenue" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

**Complete example (Account Count):**
```bash
# 1. Create calculated field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Account_Count_clc \
  --label "Account Count" \
  --expression "COUNTD([Account_TAB_Sales_Cloud].[Account_Id])" \
  --aggregation Sum

# 2. Create metric referencing the calculated field
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Account_Count_mtc \
  --label "Account Count" \
  --calculated-field Account_Count_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

**With additional dimensions (for breakdown analysis):**
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

**Required parameters:**
- `--calculated-field`: API name of calculated field to reference (must exist)
- `--time-field`: Time dimension field API name (e.g., `Close_Date`)
- `--time-table`: Time dimension table API name (e.g., `Opportunity_TAB_Sales_Cloud`)

**Note:** 
- API name must end with `_mtc` and cannot contain double underscores (`__`)
- Metrics wrap calculated fields with time dimension support for dashboard metric widgets
- Templates (sum, avg, win_rate, etc.) are for calculated fields, not metrics

See [advanced-features.md](advanced-features.md) for complete calculated field documentation.

## Test Harness

### test_harness.py

Run integration test harness (optional — verifies all chart types work).

**Usage:**
```bash
python scripts/test_harness.py --sdm {{SDM_NAME}} --cleanup
```

The test harness validates:
- All chart types (Bar, Line, Donut, Scatter, Table, Funnel, Heatmap, Dot Matrix)
- Various encoding combinations
- Calculated fields (`_clc`)
- Dashboard creation
- PATCH updates
- Style overrides

See [SKILL.md](SKILL.md) for the complete tested combinations table.

## Script Error Troubleshooting

**Script not found:**
- Verify script exists: `ls ~/.cursor/skills/tableau-next-author/scripts/{{SCRIPT_NAME}}.py`
- Check you're in the correct directory or using absolute path

**Python version error:**
- Check version: `python3 --version` (should be 3.8+)
- Use `python3` instead of `python` if needed

**Missing dependencies:**
- Install: `pip3 install requests`
- Check: `pip3 list | grep requests`

**Import errors:**
- Ensure you're running from skill directory or using absolute paths
- Check Python path includes script location

**API errors:**
- Verify authentication: `echo $SF_TOKEN`
- Check instance URL: `echo $SF_INSTANCE`
- See [troubleshooting.md](troubleshooting.md) for API-specific errors

## Complete Example Workflow

**Example agent workflow:**
```bash
# Navigate to skill directory
cd ~/.cursor/skills/tableau-next-author

# Discover SDM fields
python3 scripts/discover_sdm.py --sdm Sales_Model --json > sdm_fields.json

# Generate visualization (with validation)
python3 scripts/generate_viz.py \
  --chart-type donut \
  --name Pipeline_Donut \
  --label "Pipeline by Stage" \
  --sdm-name Sales_Model --sdm-label "Sales" \
  --workspace-name My_WS --workspace-label "My Workspace" \
  --columns F1 \
  --field F1 role=Dimension fieldName=Stage objectName=Opportunity \
  --field F2 role=Measure fieldName=Amount objectName=Opportunity function=Sum \
  --encoding F1 type=Color \
  --encoding F2 type=Angle \
  --validate \
  -o viz.json

# Validate before POST
python3 scripts/validate_viz.py viz.json

# POST to API
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/visualizations?minorVersion=12" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @viz.json
```

## Related Documentation

- [workflow.md](workflow.md) - Step-by-step dashboard creation process
- [templates-guide.md](templates-guide.md) - Template catalog and decision matrix
- [troubleshooting.md](troubleshooting.md) - Common errors and solutions
- [advanced-features.md](advanced-features.md) - Calculated fields and formulas
