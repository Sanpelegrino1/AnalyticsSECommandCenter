# Templates & Patterns Guide

> **Back to main skill:** [SKILL.md](SKILL.md)

**CRITICAL**: Always use visualization templates and dashboard patterns instead of manually building JSON. Templates ensure proper field structure, encodings, sorting, and API compliance.

## When to Use Templates

Templates are **MANDATORY** for both visualizations and dashboards. They provide:

- **Proper field structure**: Correct `displayCategory`, `role`, `function` values
- **API compliance**: All required fields included (fonts, lines, encodings, etc.)
- **Production quality**: Automatic sorting, hierarchies, formatting
- **Error prevention**: Eliminates the most common API validation errors

**NEVER manually build visualization or dashboard JSON** — always use templates.

## Visualization Template Catalog

### List Available Templates

```bash
python scripts/apply_viz_template.py --list-templates
```

### Preview Template Requirements

```bash
python scripts/apply_viz_template.py --preview revenue_by_category
```

### Available Templates

| Template | Chart Type | Description | Best For |
|---------|-----------|-------------|----------|
| `revenue_by_category` | Bar | Dimension vs measure | **Automatically sorted descending by measure + automatic color_dim (default) + legend (test harness pattern)** |
| `stacked_bar_by_dimension` | Stacked Bar | Dimension vs measure, stacked by second dimension | **Part-to-whole comparisons with breakdown** - Automatically sorted descending, includes legend |
| `trend_over_time` | Line | Date vs measure | **Year + Month hierarchy AUTOMATIC (DatePartYear + DatePartMonth) + automatic color_dim (default) + legend (test harness pattern)** |
| `multi_series_line` | Multi-Series Line | Date + measure + color_dim | **Comparing trends across categories** - Year + Month hierarchy automatic, includes legend |
| `market_share_donut` | Donut | Distribution chart | **Color + Angle + Label encodings + legend (test harness pattern)** |
| `top_n_leaderboard` | Table | Sorted by measure | Detailed breakdowns |
| `conversion_funnel` | Funnel | Stage analysis | **Automatic sorting + automatic color_dim (default) + legend (test harness pattern)** |
| `funnel_color_dim` | Funnel | Funnel with Color encoding by dimension | Funnel with category breakdown (use `conversion_funnel` with `color_dim` instead) |
| `scatter_correlation` | Scatter | Measure vs measure | **Detail + Color encodings + legend (test harness pattern)** |
| `scatter_color_meas` | Scatter | Scatter with Color encoding by measure | Scatter with measure-based coloring |
| `heatmap_grid` | Heatmap | 2 dimensions + measure | **Color(measure) + Label(measure) + Size(measure) + legend (test harness pattern)** |
| `heatmap_label_size` | Heatmap | With Label and Size encodings | Enhanced heatmap |
| `dot_matrix` | Dot Matrix | 2 dimensions + color + size measures | **Two-dimensional analysis with intensity and magnitude** |
| `bar_multi_measure` | Side-by-Side Bar | Multiple measures using MeasureValues | Comparing multiple measures (complex) |
| `line_detail_encoding` | Line | Line with Detail encoding | Breaking down by dimension |
| `kpi_single_value` | Text | Single metric | Single value display |
| `geomap_location_only` | Map | Lat/lon MapPosition only; no measure encodings | Plot locations only |
| `geomap_points` | Map | MapPosition + measure (Color) + dimension (Label) | Geographic distribution |
| `geomap_advanced` | Map | MapPosition + dim + measure ×3 encodings (Color, Label, Size) | Rich map (color, size, labels) |
| `flow_package_base` | Flow / Sankey | Measure-first **F1=link**; empty encodings | `New_Dashboard1_package (4)` `Base_Flow` |
| `flow_package_single_color` | Flow / Sankey | Same + uniform `#F9E3B6` fills | `Base_Flow_single_color_all_nodes` |
| `flow_package_link_color_nodes_color` | Flow / Sankey | Link Color (dup measure) + nodes Color (dup L2; **F4** defined) | `Copy_of_Base_Flow_*_measure_on_marks` |
| `flow_package_colors_variations` | Flow / Sankey | L1 bar Color (dup L1) + link + nodes Color | `Base_Flow_colors_variations_measure_on_marks` |
| `flow_package_three_level` | Flow / Sankey | Three level dims + link Color (dup measure) | `Base_Flow_colors_variations_measure_on_marks1` |
| `flow_simple` | Flow / Sankey | Legacy: **F1/F2** levels, **F3** link; no encodings | Older skill default |
| `flow_simple_measure_on_marks` | Flow / Sankey | Legacy + node **Size** (not package Color-on-marks) | Alternate pattern |
| `flow_sankey` | Flow / Sankey | Legacy: link Color + level-2 bar Color | Older full-color flow |
| `flow_sankey_measure_on_marks` | Flow / Sankey | Legacy + node **Size** | Alternate pattern |

### Quality Features Built-In (Enhanced with Test Harness Patterns)

All templates include production-quality defaults from 40+ proven test cases:

- **Bar charts**: Automatically sorted descending by measure (highest values first) + automatic `color_dim` (default) for Color encoding + legend (test harness pattern)
- **Line charts**: Automatically use Year + Month hierarchy (`DatePartYear` + `DatePartMonth`) for proper time series visualization + automatic `color_dim` (default) for multi-series + legend (test harness pattern)
- **Donut charts**: Color + Angle + Label encodings + legend (test harness pattern)
- **Scatter plots**: Detail + Color encodings + legend (Detail encoding MUST come first, test harness pattern)
- **Funnel charts**: Automatic sorting + automatic `color_dim` (default) for Color encoding + legend (test harness pattern)
- **Heatmaps**: Color(measure) + Label(measure) + Size(measure) encodings + legend (test harness pattern)
- **Maps**: `geomap_location_only` (points only), `geomap_points` (Color + Label), `geomap_advanced` (duplicate measure fields for Color/Label/Size); panes mark type is often **Circle**, also **Square** or **Text** in exports
- **Flow**: Prefer **`flow_package_*`** for **`New_Dashboard1_package (4).json`** (measure-first field ids). Legacy **`flow_simple` / `flow_sankey`** use levels-first F-keys. Dashboard packages may omit viz JSON (`visualizations: {}`); use a full export to confirm shapes.
- All templates include proper styling, encodings, formatting, and required API fields

### Color Encoding (Test Harness Patterns)

**CRITICAL**: Templates automatically add `color_dim` when 2+ dimensions are available (matches test harness pattern). This adds Color encoding + legend automatically. You can still manually specify `color_dim` if you want a specific dimension.

**When to add colors:**
- **Bar charts**: Add `color_dim` when 2+ text dimensions available
- **Line charts**: Add `color_dim` to create multi-series line charts
- **Scatter plots**: Always include `color_dim` for category grouping
- **Funnel charts**: Add `color_dim` for category breakdown

**How to add colors:**

Via CLI:
```bash
python scripts/apply_viz_template.py \
  --template revenue_by_category \
  --sdm Sales_Model \
  --category Region \
  --amount Total_Amount \
  --color-dim Opportunity_Type \
  --name Revenue_by_Region \
  --workspace My_Workspace \
  --post
```

Via viz_specs.json:
```json
{
  "template": "revenue_by_category",
  "name": "Revenue_by_Stage",
  "label": "Revenue by Stage",
  "fields": {"category": "Opportunity_Stage", "amount": "Total_Amount"},
  "color_dim": "Opportunity_Type"
}
```

**What happens automatically (test harness pattern):**
- `color_dim` is automatically detected and added when 2+ dimensions are available
- Color encoding is automatically added to encodings array
- Legend is automatically configured (Right position, visible title)
- Color palette is automatically applied (discrete for dimensions, continuous for measures)
- Chart becomes more informative and visually appealing
- You can still manually specify `color_dim` if you want a specific dimension

### Create from Template

**Basic usage:**
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

**Auto-match fields** (when field names are obvious):
```bash
python scripts/apply_viz_template.py \
  --template revenue_by_category \
  --sdm Sales_Model \
  --auto-match \
  --name Revenue_Bar \
  --workspace My_Workspace \
  --post
```

The template will search for fields like "Amount", "Revenue", "Total", etc. and match them automatically.

**Auto-select chart type** (uses decision matrix to choose chart type automatically):
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

The system will automatically detect "1 Date Dimension + 1 Measure" and select `trend_over_time` template (Line Chart).

## Chart Type Decision Matrix

When selecting a chart type, use this decision matrix based on data characteristics:

| Data Pattern | Field Combination | Recommended Chart Type | Template |
|--------------|------------------|----------------------|----------|
| **Trend over time** | 1 Date Dimension + 1 Measure | Line Chart | `trend_over_time` |
| **Multi-series trend** | 1 Date Dimension + 1 Measure + 1 Dimension | Multi-Series Line Chart | `multi_series_line` |
| **Comparison/Ranking** | 1 String Dimension + 1 Measure | Horizontal Bar Chart (sorted descending) | `revenue_by_category` |
| **Part-to-Whole (< 5 values)** | 1 Dimension (< 5 unique values) + 1 Measure | Donut Chart | `market_share_donut` |
| **Part-to-Whole (≥ 5 values)** | 1 Dimension (≥ 5 unique values) + 1 Measure | Stacked Bar Chart | `stacked_bar_by_dimension` |
| **Part-to-Whole with Breakdown** | 2 Dimensions + 1 Measure | Stacked Bar Chart | `stacked_bar_by_dimension` |
| **Two-dimensional analysis** | 2 Dimensions + 2 Measures | Dot Matrix | `dot_matrix` |
| **Correlation** | 2 Continuous Measures | Scatter Plot | `scatter_correlation` |
| **Distribution** | 1 Measure only | Bar Chart (histogram-like) | `revenue_by_category` |
| **Multiple Measures** | 2+ Measures | Bar Chart (side-by-side) | `revenue_by_category` |
| **Funnel/Stage Analysis** | 1 Stage Dimension + 1 Measure | Funnel Chart | `conversion_funnel` |
| **Heatmap** | 2 Dimensions + 1 Measure | Heatmap | `heatmap_grid` |
| **Detailed Table** | Multiple Dimensions + Measures | Table (sorted) | `top_n_leaderboard` |
| **Geographic** | Lat + Lon + Measure + label dimension | Map (points) | `geomap_points` |
| **Flow** | 2–3 Dimensions + link measure | Sankey / Flow | **`flow_package_*`** for package (4) parity; **`flow_sankey`** / **`flow_simple`** for legacy ordering |

### Decision Rules

- **Never use Pie Chart** — Use Donut Chart instead (better for < 5 slices)
- **Bar Charts are automatically sorted descending** by measure (templates handle this)
- **Line Charts use Year + Month hierarchy** automatically for better time series visualization
- **Date Dimensions** → Always use Line Chart for trends (templates create Year/Month hierarchy)
- **Stage/Status fields** → Prefer Funnel Chart for flow visualization
- **2 Measures** → Use Scatter Plot to show correlation
- **Multiple Dimensions** → Use Table for detailed breakdowns

### Example Decision Flow

```
IF (1 Date Dimension + 1 Measure):
    → Use trend_over_time template (Line Chart)
ELIF (1 Text Dimension + 1 Measure):
    → Use revenue_by_category template (Bar Chart, sorted descending)
ELIF (1 Dimension + 1 Measure AND < 5 unique values):
    → Use market_share_donut template (Donut Chart)
ELIF (2 Measures):
    → Use scatter_correlation template (Scatter Plot)
ELIF (1 Stage Dimension + 1 Measure):
    → Use conversion_funnel template (Funnel Chart)
ELIF (Latitude + Longitude + Measure + Label dimension on SDM):
    → Use geomap_points (Map)
ELIF (two categorical levels + measure for link strength):
    → Use `flow_simple` or `flow_sankey` (see chart-catalog Flow variant table)
ELSE:
    → Use revenue_by_category template (Bar Chart - most versatile)
```

## Dashboard Pattern Catalog

**CRITICAL**: Always use dashboard patterns/templates instead of manually building dashboard JSON. Dashboard patterns ensure proper layout, widget structure, and API compliance.

### Available Dashboard Patterns

Use `generate_dashboard_pattern.py` script with one of these production-ready patterns:

#### 1. `f_layout` — Executive Dashboard

- **Best for:** Executive dashboards with KPIs prominently displayed
- **Layout:** Metrics stacked vertically on left, vizzes in F-reading pattern
- **REQUIRES metrics** - Do not use if no metrics available

**Widget Requirements:**
- **Filters**: 6 slots (top row, columns 33-72, distributed)
- **Metrics**: 3 slots (left sidebar, columns 1-22, stacked vertically)
- **Visualizations**: 5 slots
  - Slot 1: Large top-right visualization (columns 25-71, rows 3-57)
  - Slots 2-4: 3 small visualizations below (columns 1-23, 25-47, 49-70, rows 60-96)
  - Slot 5: Large bottom visualization (columns 2-69, rows 98-150)

**Usage:**
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

**Check requirements:**
```bash
python scripts/generate_dashboard_pattern.py \
  --pattern f_layout \
  --show-requirements
```

**Validate before building:**
```bash
python scripts/generate_dashboard_pattern.py \
  --pattern f_layout \
  --validate-requirements \
  [other args...]
```

#### 2. `z_layout` — Operational Dashboard

- **Best for:** Operational dashboards with metrics at top
- **Layout:** Metrics horizontally across top, vizzes in Z-reading pattern
- **REQUIRES metrics** - Do not use if no metrics available

**Widget Requirements:**
- **Filters**: **6 slots** (exact, top row, distributed)
- **Metrics**: **6 slots** (exact, top row)
- **Visualizations**: **5 slots** (exact, Z-pattern)

**Usage:**
```bash
python scripts/generate_dashboard_pattern.py \
  --pattern z_layout \
  --name Operations_Dashboard \
  --workspace-name My_WS \
  --sdm-name Sales_Model \
  --title-text "Operations Overview" \
  --viz Viz1 Viz2 Viz3 Viz4 Viz5 \
  --filter fieldName=Field1 objectName=Obj1 dataType=Text \
  --filter fieldName=Field2 objectName=Obj1 dataType=Text \
  --filter fieldName=Field3 objectName=Obj1 dataType=Text \
  --filter fieldName=Field4 objectName=Obj1 dataType=Text \
  --filter fieldName=Field5 objectName=Obj1 dataType=Text \
  --filter fieldName=Field6 objectName=Obj1 dataType=Text \
  --metrics Metric1_mtc Metric2_mtc Metric3_mtc Metric4_mtc Metric5_mtc Metric6_mtc \
  -o dashboard.json
```

#### 3. `performance_overview` — Performance Dashboard

- **Best for:** Performance dashboards with time-based navigation
- **Layout:** Primary metric large on left, secondary metrics on right, time period navigation
- **REQUIRES metrics** - primary_metric is mandatory

**Widget Requirements:**
- **Filters**: **3 slots** (top row)
- **Metrics**: **5 slots** (1 primary + 4 secondary, primary large left, secondary smaller right)
- **Visualizations**: **5 slots** (distributed)
- **Pages**: Multiple (time-based navigation, e.g., "Week", "Month", "Day")

**Usage:**
```bash
python scripts/generate_dashboard_pattern.py \
  --pattern performance_overview \
  --name Performance_Dashboard \
  --workspace-name My_WS \
  --sdm-name Sales_Model \
  --primary-metric Total_Revenue_mtc \
  --secondary-metrics Win_Rate_mtc Pipeline_Count_mtc Avg_Deal_Size_mtc Conversion_Rate_mtc \
  --viz Viz1 Viz2 Viz3 Viz4 Viz5 \
  --filter fieldName=Field1 objectName=Obj1 dataType=Text \
  --filter fieldName=Field2 objectName=Obj1 dataType=Text \
  --filter fieldName=Field3 objectName=Obj1 dataType=Text \
  --pages "Week" "Month" "Day" \
  -o dashboard.json
```

**Note:** You must provide exactly 1 primary metric and 4 secondary metrics (5 total). The primary metric will be displayed large on the left, with 4 secondary metrics on the right.

### Pattern-Specific Arguments

- **f_layout/z_layout**: `--title-text "Dashboard Title"`
- **performance_overview**: `--primary-metric Total_Revenue_mtc --secondary-metrics Win_Rate_mtc Pipeline_Count_mtc --pages "Week" "Month" "Day"`

### Auto-Select Pattern

Use `--auto-select-pattern` to automatically choose the best pattern:

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

Auto-select logic (see `lib/dashboard_patterns.auto_select_pattern`):
- **Exact slot match** → `f_layout`, `z_layout`, or `performance_overview` when counts align
- **Metrics + visualizations (other counts)** → `f_layout` (F-layout JSON tolerates padding)
- **Metrics only** → `f_layout` (note: `create_dashboard.py` still requires at least one visualization in viz-specs)
- **Visualizations only** → `z_layout` (Z-layout still expects metrics on the SDM for a valid board)

### Why Patterns Are Mandatory

- **Proper widget structure**: Patterns ensure all widgets have correct `source.name` format (no `id`, `label`, or `type`)
- **Correct layout structure**: Patterns include required `style.widgetStyle` and `layouts[].style` with proper spacing
- **Multi-page support**: Patterns automatically generate navigation buttons and distribute widgets across pages
- **Filter integration**: Patterns correctly configure filter widgets with SDM references
- **Metric widgets**: Patterns properly configure metric widgets with `metricOption.sdmApiName`
- **Tested and validated**: All patterns are tested against live Salesforce orgs

### Alternative: Use Python Function

```python
from lib.templates import build_dashboard_from_pattern, FilterDef, MetricDef, VizDef, PageDef

dash = build_dashboard_from_pattern(
    name="Sales_Dashboard",
    label="Sales Dashboard",
    workspace_name="My_Workspace",
    pattern="f_layout",  # or "z_layout", "performance_overview"
    viz_defs=[VizDef("Revenue_Bar"), VizDef("Pipeline_Funnel")],
    filter_defs=[FilterDef("Account_Industry", "Opportunity", "Text")],
    metric_defs=[MetricDef("Total_Revenue_mtc", "Sales_SDM")],
    sdm_name="Sales_SDM",
    title_text="Sales Performance"  # For f_layout/z_layout
)
```

**NEVER manually build dashboard JSON** — always use patterns to ensure API compliance and proper structure.

## Production Enhancements

For professional, user-friendly visualizations, templates include:

- **Better data visibility**: Mark labels shown directly on charts
- **Enhanced styling**: Row banding (`#E5E5E5`) for consistency
- **More interactive elements**: Color encoding, tooltips, and reference lines

See [chart-catalog.md](chart-catalog.md) for complete copy-paste templates (all chart types, including color encoding, sort orders, and currency formatting). See [format-patterns.md](format-patterns.md) for visualization format configuration (currency, percentage, time duration).

## Full JSON Templates

For complete JSON templates ready to copy-paste, see [chart-catalog.md](chart-catalog.md).

## Related Documentation

- [workflow.md](workflow.md) - Step-by-step dashboard creation process
- [scripts-guide.md](scripts-guide.md) - Script usage and automation
- [troubleshooting.md](troubleshooting.md) - Common errors and solutions
- [chart-catalog.md](chart-catalog.md) - Complete JSON templates
