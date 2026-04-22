---
name: tableau-next-author
description: Build business-focused Tableau Next dashboards with clear storytelling, meaningful visualizations, and user-centric design. Expert guidance on chart selection, layout patterns, and dashboard UX. Use when creating visualizations, building dashboards, or authoring Tableau Next content.
license: MIT
compatibility: Requires Salesforce CLI (sf), Python 3.8+, jq. Authenticated Salesforce org with Tableau Next creator access, read access to the semantic model in Data 360 (former Data Cloud).
metadata:
  author: alaviron
  version: "1.1"
  api-major-version: "v66.0"
  api-minor-version: "12"
allowed-tools: Bash(sf:*) Bash(python:*) Bash(curl:*) Read Write
---

# Tableau Next Dashboard Building Expertise

Build insightful, story-driven dashboards that answer business questions and drive action. This skill emphasizes dashboard design principles, visual storytelling, and user experience over technical API mechanics.

## Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| Design a dashboard narrative | [Dashboard Design Principles](#dashboard-design-principles) |
| Create a dashboard right now | [AI-Driven Workflow](#ai-driven-dashboard-creation-workflow) |
| Choose the right chart type | [Chart Type Decision Matrix](#chart-type-decision-matrix) |
| Ensure dashboard quality | [Dashboard Quality Checklist](#dashboard-quality-checklist) |
| Use automation scripts | [Script Cheat Sheet](#script-cheat-sheet) |
| Fix an API error | [Common Errors](#common-errors-quick-fix-table) |
| Copy full JSON templates | [references/chart-catalog.md](references/chart-catalog.md) (includes quick start examples) |
| Format numbers/currency in viz | [references/format-patterns.md](references/format-patterns.md) |
| Understand API endpoints | [API Endpoints](#api-endpoints-quick-reference) |

## Dashboard Design Principles

**CRITICAL**: You are a dashboard building expert, not just an API caller. Every dashboard must tell a clear business story with meaningful visualizations.

### Think Like a Business User

Before selecting charts or writing code, ask:
- **What question does this dashboard answer?** (e.g., "Are sales improving?", "Which regions perform best?")
- **What action should the user take after viewing it?** (e.g., "Focus on underperforming regions", "Investigate pipeline bottlenecks")
- **Can a non-technical user understand every label?** (e.g., "Revenue by Industry" ✅ vs "Account_Industry_2" ❌)

### Naming Best Practices

**CRITICAL: Always Use SDM Field Labels**

**Rules:**
1. **Always use SDM field labels** (from `sdm_fields[field_name]["label"]`), not technical field names
2. **Strip technical suffixes** (`_Clc`, `_mtc`, `_MTC`, `_CLC`) from display names
3. Use business-friendly names: `"Sales_Trend_Over_Time"` ✅ not `"Trend_1"` ❌
4. Use clear labels: `"Revenue by Industry"` ✅ not `"Account_Industry_2"` ❌
5. Make labels actionable (e.g., "Sales Performance by Region" not just "Sales by Region")

**Examples:**
- ✅ `"Sales_Trend_Over_Time"` → Clear, descriptive API name
- ✅ `"Revenue by Industry"` → User-friendly display label (uses SDM label)
- ❌ `"Pipeline_Generation_Clc_Trend"` → Technical suffix exposed
- ❌ `"Viz_1"` → Generic, meaningless

### Visual Storytelling Flow

Every great dashboard follows a narrative structure:

1. **Start with KPIs** (What matters most?)
   - Key metrics at top/left (F-pattern layout)
   - Answer: "What's our current state?"

2. **Show trends** (Are we improving?)
   - Temporal charts early in flow
   - Answer: "How are we performing over time?"

3. **Break down by dimensions** (Where is performance strong/weak?)
   - Category comparisons, stacked bars, heatmaps
   - Answer: "Which segments/categories drive results?"

4. **Reveal correlations** (What drives success?)
   - Scatter plots, multi-measure comparisons
   - Answer: "What factors correlate with performance?"

### Visual Hierarchy Principles

- **F-pattern layout**: Metrics left sidebar, visualizations follow eye movement (top-left → right → down)
- **Z-pattern layout**: Metrics top row, visualizations zigzag down
- **Progressive disclosure**: Overview → Detail → Action
- **Color consistency**: Use colors meaningfully (e.g., red = problem, green = success)
- **White space**: Don't overcrowd - let insights breathe

### Meaningful Questions Framework

Each visualization should answer a specific business question:

| Chart Type | Business Question | Example |
|------------|------------------|---------|
| Line Chart | "How are we trending over time?" | "Sales Performance Over Time" |
| Bar Chart | "Which categories perform best?" | "Revenue by Product Line" |
| Stacked Bar | "What's the composition breakdown?" | "Revenue by Region and Product Type" |
| Heatmap | "Where are the hotspots?" | "Sales Performance by Region and Quarter" |
| Scatter Plot | "What correlates with success?" | "Deal Size vs Win Rate by Stage" |
| Donut Chart | "What's our market share?" | "Revenue Distribution by Customer Segment" |
| Map (points) | "Where are values distributed geographically?" | "Revenue by Store Location" |
| Flow (Sankey) | "How does volume flow between two dimensions?" | "Orders from Product Family to Store" |

## Color Encoding Best Practices

**CRITICAL**: Color encoding is **AUTOMATIC** for most templates when 2+ dimensions are available. Templates automatically add Color encoding + legend.

**Template-specific requirements:**
- **`stacked_bar_by_dimension`**: Must use `stack_dim` in `fields` (NOT `color_dim`) - this creates the stacking
- **Other templates**: Use `color_dim` for color encoding (optional, auto-added when available)
  - Bar charts: Auto-adds `color_dim` with second dimension
  - Line charts: Auto-adds `color_dim` to create multi-series line charts
  - Scatter plots: Auto-adds `color_dim` for category grouping
  - Donut charts: Automatically includes Color encoding
  - Heatmaps: Automatically uses Color(measure) encoding
  - Funnel charts: Auto-adds `color_dim` for category breakdown
  - **Map**: `geomap_location_only` = MapPosition only (no encodings); `geomap_points` = Color(measure) + Label(dimension); `geomap_advanced` = Label(dim) + Color + Label + Size on **duplicate** measure fields (F3/F4/F5). Marks may be **Circle**, **Square**, or **Text** (`marks.panes.type`). Basemap is usually `style.background`: `{"type": "Map", "styleName": "light"}`.
  - **Flow (package parity, `New_Dashboard1_package (4).json`)**: `flow_package_base` / `flow_package_single_color` (measure-first **F1=link**, **F2/F3=levels**); `flow_package_link_color_nodes_color` (link **Color** + nodes **Color**, with **F4** defined); `flow_package_colors_variations`; `flow_package_three_level` (needs `--level3`). Empty dashboard packages may ship `"visualizations": {}`—use a **full** export to verify shapes.
  - **Flow (legacy levels-first)**: `flow_simple`, `flow_simple_measure_on_marks` (**Size** on nodes), `flow_sankey`, `flow_sankey_measure_on_marks`. Overrides: `flow_link_legend_visible`, `flow_node_size_legend_visible`, `flow_uniform_fill`, etc.

**Manual override:**
- You can manually specify `color_dim` at top level (not inside `fields`) if you want a specific dimension
- Colors work WITH automatic sorting (doesn't interfere)

## MANDATORY Workflow for Dashboard Creation

**CRITICAL**: When creating dashboards, ALWAYS follow this workflow in order. Templates are MANDATORY for both visualizations and dashboards. **Narrative design is REQUIRED** - never skip it.

### AI-Driven Dashboard Creation Workflow

**The AI should:**
1. **Parse user intent** - Extract: dashboard type, org, SDM, workspace, dashboard name
2. **Design the narrative** - **REQUIRED**: Plan the story before selecting charts:
   - What business questions must this dashboard answer?
   - What's the logical flow? (KPIs → Trends → Breakdowns → Correlations)
   - What should each visualization be named? (business-friendly, not technical)
   - Which dimensions are meaningful to users? (not technical IDs)
   - What actions should users take based on insights?
   - **NEVER skip this step** - narrative design ensures business value
3. **Decide which visualizations to create** - Based on dashboard narrative and SDM fields
   - Select diverse chart types that tell a complete story
   - `color_dim` is automatic for most templates (see Color Encoding section)
4. **Create visualization specs JSON** - Specify template, name, label, and field mappings
   - Use business-friendly names: `"Sales_Trend_Over_Time"` not `"Trend_1"`
   - Use clear labels: `"Sales Performance by Product Line"` not `"Sales_Trend"`
   - **CRITICAL**: Always use SDM field labels, not technical field names (see Naming Best Practices section)
   - **CRITICAL**: Template-specific field requirements:
     - `stacked_bar_by_dimension` → Must use `stack_dim` in `fields` (NOT `color_dim`)
     - Other templates → Use `color_dim` for color encoding
   - `color_dim` is optional for most templates (system auto-adds when available)
5. **Call generic script** - Pass specs to `create_dashboard.py`

**⚠ WARNING**: The `--auto-generate-viz` flag bypasses narrative design and should be avoided for production dashboards. It's provided for quick prototyping only. Always design the narrative first, then create visualization specs manually.

**Example AI workflow:**
```python
# 1. Parse user request: "create a Sales Dashboard on org GDO_TEST_001 using SDM Sales_Cloud12_backward"

# 2. Design the narrative:
#    Business Questions:
#    - "How are sales trending over time?" → Multi-series line chart
#    - "Which stages have the most revenue?" → Bar chart by stage
#    - "What's our revenue breakdown by industry?" → Stacked bar or heatmap
#    - "Which industries correlate with deal size?" → Scatter plot
#    Flow: KPIs (metrics) → Trends → Breakdowns → Correlations

# 3. Discover SDM fields and determine pattern requirements
sdm_fields = discover_sdm_fields("Sales_Cloud12_backward")
# Pattern will likely be f_layout (requires 6 filters, 3 metrics, 5 visualizations)

# 4. Select fields (PREFER CLC fields):
#    - Prefer fields ending in _clc or _Clc when available
#    - Use recommend_diverse_chart_types() which automatically prioritizes CLC fields
#    - Or manually select: prefer "Pipeline_Generation_Clc" over "Pipeline_Generation"

# 5. Generate filters (6 for f_layout, with correct objectName lookup):
filter_field_names = [
    "Account_Industry",
    "Opportunity_Stage",
    "Opportunity_Type",
    "Account_Type",
    "Close_Date",
    "Region"
]
filters = []
for field_name in filter_field_names:
    field_def = sdm_fields[field_name]
    filters.append({
        "fieldName": field_name,
        "objectName": field_def.get("objectName"),  # CORRECT: Look up from SDM
        "dataType": field_def.get("dataType", "Text")
    })

# 6. Use recommend_diverse_chart_types() to get diverse, colorful visualizations
dashboard_spec = {
    "org": "GDO_TEST_001",
    "sdm_name": "Sales_Cloud12_backward",
    "workspace_name": "TEST_SKILL",
    "dashboard_name": "Sales_Dashboard",
    "visualizations": [
        {
            "template": "multi_series_line",
            "name": "Sales_Trend_Over_Time",  # Business-friendly name
            "label": "Sales Performance by Product Line",  # Clear, actionable label
            "fields": {"date": "Close_Date", "measure": "Total_Amount"},
            "color_dim": "Opportunity_Type"  # Meaningful dimension
        },
        {
            "template": "revenue_by_category",
            "name": "Revenue_by_Stage",  # Descriptive API name
            "label": "Revenue by Opportunity Stage",  # User-friendly label
            "fields": {"category": "Opportunity_Stage", "amount": "Total_Amount"},
            "color_dim": "Opportunity_Type"  # Adds color encoding + legend (works WITH automatic sorting)
        },
        {
            "template": "revenue_by_category",
            "name": "Revenue_by_Industry",  # Clear, business-focused name
            "label": "Revenue by Industry",  # Simple, understandable label
            "fields": {"category": "Account_Industry", "amount": "Total_Amount"},
            "color_dim": "Account_Type"  # Always add color_dim when 2+ dimensions available
        }
    ],
    "filters": filters  # Use filters generated with correct objectName lookup
}

# 2. Save specs to JSON file
with open("viz_specs.json", "w") as f:
    json.dump(dashboard_spec, f, indent=2)

# 3. Call script
subprocess.run([
    "python", "scripts/create_dashboard.py",
    "--org", dashboard_spec["org"],
    "--sdm", dashboard_spec["sdm_name"],
    "--workspace", dashboard_spec["workspace_name"],
    "--name", dashboard_spec["dashboard_name"],
    "--viz-specs", "viz_specs.json"
])
```

**The script handles:**
- Authentication to org
- Workspace creation/verification
- SDM field discovery and validation
- Visualization creation using templates (with automatic sorting, colors, legends from test harness)
- Metric discovery from SDM
- Dashboard pattern auto-selection
- Dashboard creation and POST

**CRITICAL**: Use `create_dashboard.py` for ALL dashboard types (sales, marketing, HR, finance, etc.). This is the ONLY script needed - domain-specific scripts are deprecated.


### Field Selection Best Practices

**CRITICAL**: Always select meaningful dimensions, NOT ID fields. **PREFER CLC (calculated) fields** when available.

**Why avoid ID fields:**
- ID fields (Account_Id, Contact_Id, etc.) have thousands of unique values
- Visualizations become unreadable with too many categories
- ID fields don't provide business insights

**Field selection priority (automatically handled by `recommend_diverse_chart_types()`):**
1. **Highest priority** (score +15): **CLC fields** (`*_clc`, `*_Clc`) - Calculated fields are business-ready
2. **High priority** (score +10): Industry, Type, Stage, Status, Region, Segment, Category, Group, Class, Tier, Level, Phase
3. **Medium priority** (score +5): Country, State, Territory, Department, Division, Account, Opportunity, Product, Service
4. **Lower priority** (score +2): Name fields (Account_Name, Product_Name, etc.)
5. **Avoid** (score -5): Description, Comment, Note, Detail, Text (generic fields)
6. **Never use**: ID fields (automatically filtered out)

**The `recommend_diverse_chart_types()` function automatically:**
- Filters out ID fields (`_id`, `_ids`, etc.)
- Scores dimensions by relevance using `_score_dimension_relevance()`
- Selects the most meaningful fields using `_select_best_dimensions()`
- Avoids using the same dimension multiple times when possible

**When manually creating visualization specs:**
- **ALWAYS prefer CLC fields** when available (e.g., `Pipeline_Generation_Clc` over `Pipeline_Generation`)
- Use fields like `Account_Industry`, `Opportunity_Stage`, `Account_Type`, `Region`
- Avoid fields like `Account_Id`, `Contact_Id`, `Opportunity_Id`
- Prefer categorical fields with 5-50 unique values over fields with thousands of values

**Example: Prefer CLC fields:**
```python
# GOOD: Prefer CLC calculated fields
"measure": "Pipeline_Generation_Clc"  # Calculated field (+15 priority)
"category": "Opportunity_Stage_Clc"     # Calculated dimension (+15 priority)

# ACCEPTABLE: Use regular fields if no CLC available
"measure": "Total_Amount"               # Regular field
"category": "Opportunity_Stage"         # Regular field
```

**CRITICAL: CLC Fields with UserAgg Aggregation**

CLC (calculated) fields with `aggregationType: "UserAgg"` are correctly configured in the SDM and must NEVER be overridden by aggregation inference logic.

**Why this matters:**
- CLC fields with UserAgg contain aggregation functions in their expressions (e.g., `SUM([Field]) / COUNT([Field])`)
- UserAgg is the correct aggregation type for calculated measures
- The `_infer_aggregation_type()` function checks field names for keywords like "rate", "probability", etc. and would incorrectly override UserAgg to Avg
- **UserAgg is always preserved** - the system checks for UserAgg before applying any aggregation inference

**How it works:**
- The `_infer_aggregation_type()` function returns `None` (no override) when it detects UserAgg
- Field building logic explicitly checks for UserAgg before calling aggregation inference
- Both main field building (lines 828-835) and measure_values field building (lines 910-916) preserve UserAgg

**Example:**
- `Scrap_Rate_clc` with `aggregationType: "UserAgg"` → Preserves UserAgg (not overridden to Avg)
- Regular field `Scrap_Rate` without UserAgg → Gets Avg aggregation (correct inference)

## Learning from Real Dashboards

Based on analysis of 25 production dashboard packages (142 visualizations):

### Chart Type Distribution
- **Most common**: `stacked_bar_by_dimension` (42%), `market_share_donut` (17%), `revenue_by_category` (14%), `scatter_correlation` (12%)
- **By industry**:
  - **Sales**: 54% stacked bars, 19% donut charts, 11% unknown patterns
  - **Marketing**: 27% bar charts, 27% donut charts, 27% stacked bars
  - **Key Account Management**: 83% stacked bars, 17% bar charts
  - **Healthcare**: 40% scatter plots, 30% stacked bars, 20% bar charts
  - **Other**: 48% stacked bars, 14% donut charts, 10% scatter plots

### Dashboard Pattern Distribution
- **f_layout**: 50% (executive dashboards with KPIs)
- **z_layout** and **performance_overview**: common for operational and time-nav layouts
- **unknown**: 32% (custom layouts not matching standard patterns)

### Filter Selection Patterns
- Most common filter fields: `Account` (12%), `Date` (8%)
- Common sales filters: `Account Industry`, `Account Type`, `Opportunity Type`, `Close Date`, `Created Date`
- Average filters per dashboard: ~4-5 filters
- Filter fields are dimensions (not measures)

### Naming Patterns
- **Business-friendly**: 88.7% use descriptive names (e.g., "Sales_Trend_Over_Time", "Open_Pipe_by_Region")
- **Generic**: 11.3% use generic names (e.g., "Whitespace", placeholder names)
- **Technical**: Very few expose technical suffixes in names (good practice)

### Key Insights
- **Stacked bars dominate**: 42% of visualizations use stacked bars, indicating strong preference for part-to-whole breakdowns
- **Donut charts popular**: 17% use donut charts for distribution visualization
- **Color encoding common**: Most stacked bars include color dimensions (automatic in templates)
- **Business-friendly naming**: 89% follow naming best practices
- **Pattern diversity**: Sales dashboards favor stacked bars; Healthcare uses more scatter plots for correlation analysis

### Using Learned Patterns vs Decision Matrix

**CRITICAL**: Learned patterns are preferences, not constraints.

**Priority order:**
1. **Decision matrix first**: Field pattern → chart type (e.g., 2 Dimensions + 2 Measures → `dot_matrix`)
2. **Learned patterns second**: When multiple valid options exist, prefer common patterns
3. **Diversity matters**: Don't always default to most common pattern - use appropriate chart type for the question

**Examples:**
- 2 Dimensions + 2 Measures → Use `dot_matrix` (even if not in training data) ✅
- 2 Dimensions + Measure → Prefer `stacked_bar_by_dimension` (common) over `heatmap_grid` (less common) when both are valid
- 1 Dimension + 2+ Measures → Use `bar_multi_measure` (correct for pattern) even if not seen in training ✅

**Missing from training data but still valid:**
- `dot_matrix` - Use for 2 dimensions + 2 measures
- `heatmap_grid` - Use for 2 dimensions + 1 measure (alternative to stacked bar)
- `bar_multi_measure` - Use for 1 dimension + 2+ measures
- `top_n_leaderboard` - Use for detailed tables with multiple dimensions + measures
- `geomap_*`, `flow_package_*`, `flow_simple`, `flow_sankey`, … — Maps need lat/lon; package Flow templates use **two or three** level dimensions + link measure; `flow_package_three_level` adds `level3` in `viz_specs.fields`

### Filter Generation Best Practices

**CRITICAL**: Always generate the correct number of filters based on dashboard pattern requirements.

**Dashboard Pattern Filter Requirements:**
- `f_layout`: **6 filters** (exact requirement)
- `z_layout`: **6 filters** (exact requirement)
- `performance_overview`: **3 filters** (exact requirement)

**How to generate filters correctly:**

1. **Determine dashboard pattern first** (or use auto-select logic):
   - If metrics + visualizations → likely `f_layout` or `z_layout` when counts match (6 filters each)
   - If visualizations only → often `z_layout` when you also supply the required metrics
   - Metrics-only boards without charts are not supported by `create_dashboard.py` (add at least one visualization)

2. **Select dimension fields** from SDM (not measures - filters must be dimensions):
   - Use fields that appear in visualizations (for consistency)
   - Prefer fields with good labels (business-friendly)
   - Avoid ID fields (too many unique values)

3. **Look up objectName from SDM fields** (NEVER guess):
   ```python
   # CORRECT: Look up objectName from sdm_fields
   field_def = sdm_fields[field_name]
   object_name = field_def.get("objectName")  # May be None for calculated fields
   data_type = field_def.get("dataType", "Text")
   
   filter_def = {
       "fieldName": field_name,
       "objectName": object_name,  # From SDM, not guessed
       "dataType": data_type
   }
   ```

4. **Generate correct number of filters**:
   ```python
   # Example: For f_layout pattern (requires 6 filters)
   filter_fields = [
       "Account_Industry",
       "Opportunity_Stage", 
       "Opportunity_Type",
       "Account_Type",
       "Close_Date",  # Date fields work as filters
       "Region"
   ]
   
   filters = []
   for field_name in filter_fields[:6]:  # Ensure exactly 6
       field_def = sdm_fields[field_name]
       filters.append({
           "fieldName": field_name,
           "objectName": field_def.get("objectName"),  # Correct lookup
           "dataType": field_def.get("dataType", "Text")
       })
   ```

**Common mistakes to avoid:**
- ❌ Guessing object names (e.g., assuming `Account_Industry` belongs to `Opportunity_TAB_Sales_Cloud`)
- ❌ Using wrong number of filters (e.g., 3 filters for `f_layout` which needs 6)
- ❌ Using measure fields as filters (filters must be dimensions)
- ❌ Not looking up objectName from `sdm_fields[field_name]["objectName"]`

**Filter Label Enrichment:**

Filters in `viz_specs.json` are automatically enriched with `objectName`, `dataType`, and `label` from SDM field definitions.

**How it works:**
- When filters are loaded from `viz_specs.json`, they only need `fieldName`
- After discovering SDM fields, the system automatically enriches filters with:
  - `objectName`: From SDM field definition (None for calculated fields like `_clc`)
  - `dataType`: From SDM field definition (defaults to "Text" if missing)
  - `label`: From SDM field definition, or cleaned field name as fallback
- If a field is not found in the SDM, validation will fail with actionable error messages
- Existing values in filter definitions are preserved (not overwritten)

**Example filter definitions:**

```json
{
  "filters": [
    {
      "fieldName": "Primary_Industry"
      // objectName, dataType, and label will be auto-enriched from SDM
    },
    {
      "fieldName": "Opportunity_Stage",
      "label": "Custom Label"
      // objectName and dataType auto-enriched, label preserved
    },
    {
      "fieldName": "Days_to_Close_clc"
      // objectName will be None (calculated field), dataType and label auto-enriched
    }
  ]
}
```

**Best practice:**
- **Only include `fieldName`** in `viz_specs.json` filters - let the system enrich from SDM
- Optionally include `label` if you want custom display names
- The system validates that all filter fields exist in the SDM before dashboard creation
- If a field is not found, you'll get an error listing unresolved filters and suggestions

### Step-by-Step Dashboard Creation Process (Manual - for reference)

**1. Discover Available SDMs**
```bash
python scripts/discover_sdm.py --list
# Or via API: GET /services/data/v66.0/ssot/semantic/models
```
- List all available Semantic Data Models
- Review SDM labels and descriptions
- Identify SDMs relevant to the use case

**2. Select the Best SDM**
```bash
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json
```
- Get detailed SDM definition with all fields
- Verify required dimensions and measures exist
- Check for calculated fields (`_clc`) and metrics (`_mtc`)

**3. Choose Dashboard Template/Pattern**
- Review available dashboard patterns:
  - `f_layout` — Executive dashboards with KPIs
  - `z_layout` — Operational dashboards (metrics top row, Z-pattern vizzes)
  - `performance_overview` — Performance dashboards with time navigation
- **Select pattern based on use case and requirements**

**4. Create Visualizations Using Templates (MANDATORY)**
- For each visualization needed:
  - Use `apply_viz_template.py` with `--auto-select` and `--auto-match` when possible
  - Or explicitly choose template from [references/templates-guide.md](references/templates-guide.md) based on data pattern
  - **NEVER manually build visualization JSON** — always use templates
- Create all visualizations BEFORE creating the dashboard
- Note the API names of created visualizations (needed for dashboard)

**5. Create Dashboard Using Pattern (MANDATORY)**
```bash
# Auto-select pattern (recommended)
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
- Use `--auto-select-pattern` to automatically choose the best pattern
- Reference previously created visualizations by API name
- **NEVER manually build dashboard JSON** — always use patterns

**6. POST Dashboard to API**
```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/dashboards?minorVersion=12" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

### Why This Order Matters

- **SDM First**: Ensures you know what data is available before designing
- **Pattern Selection**: Dashboard layout drives which visualizations are needed
- **Templates Required**: Both visualization and dashboard templates ensure API compliance and quality
- **Visualizations Before Dashboard**: Dashboard references visualization API names, so they must exist first

See [references/workflow.md](references/workflow.md) for detailed workflow documentation.

## Chart Type Decision Matrix

When selecting a chart type, use this decision matrix based on data characteristics and business questions:

| Business Question | Data Pattern | Field Combination | Recommended Chart Type | Template |
|------------------|--------------|------------------|----------------------|----------|
| **"How are we performing over time?"** | Trend over time | 1 Date Dimension + 1 Measure | Line Chart | `trend_over_time` |
| **"How do trends compare across categories?"** | Multi-series trend | 1 Date Dimension + 1 Measure + 1 Dimension | Multi-Series Line Chart | `multi_series_line` |
| **"Which categories perform best?"** | Comparison/Ranking | 1 String Dimension + 1 Measure | Horizontal Bar Chart (sorted descending) | `revenue_by_category` |
| **"What's our market composition?"** (< 5 slices) | Part-to-Whole | 1 Dimension (< 5 unique values) + 1 Measure | Donut Chart | `market_share_donut` |
| **"What's our market composition?"** (≥ 5 slices) | Part-to-Whole | 1 Dimension (≥ 5 unique values) + 1 Measure | Bar Chart | `revenue_by_category` |
| **"What's the breakdown by two dimensions?"** | Part-to-Whole with Breakdown | 2 Dimensions + 1 Measure | **Stacked Bar Chart** | `stacked_bar_by_dimension` |
| **"How do multiple measures compare?"** | Multi-Measure Comparison | 1 Dimension + 2+ Measures | Side-by-Side Bar Chart | `bar_multi_measure` |
| **"Where are the performance hotspots?"** | Two-dimensional analysis | 2 Dimensions + 1 Measure | Heatmap | `heatmap_grid` |
| **"What correlates with success?"** | Correlation | 2 Continuous Measures | Scatter Plot | `scatter_correlation` |
| **"What's the conversion funnel?"** | Funnel/Stage Analysis | 1 Stage Dimension + 1 Measure | Funnel Chart | `conversion_funnel` |
| **"What's the multi-dimensional view?"** | Two-dimensional analysis | 2 Dimensions + 2 Measures | Dot Matrix | `dot_matrix` |
| **"What are the detailed rankings?"** | Detailed Table | Multiple Dimensions + Measures | Table (sorted) | `top_n_leaderboard` |
| **"Where is it on the map?"** | Geographic | Lat + Lon + Measure + Label dimension | Map (points) | `geomap_points` |
| **"How does volume flow A → B?"** | Flow between categories | 2–3 Dimensions + Measure (link width) | Sankey / Flow | Prefer **`flow_package_*`** for exports matching `New_Dashboard1_package (4).json`; legacy **`flow_sankey`** / **`flow_simple_*`** for older F-key ordering |

**Rules with Business Context:**
- **Never use Pie Chart** — Use Donut Chart instead (better for < 5 slices)
- **Bar Charts**: Automatically sorted descending by measure + auto color encoding when 2+ dimensions available
- **Line Charts**: Year + Month hierarchy AUTOMATIC (DatePartYear + DatePartMonth) + auto color encoding
- **Date + Measure + Dimension** → Use Multi-Series Line Chart (`multi_series_line`) to compare trends across categories
- **2 Dimensions + 1 Measure** → Prefer Stacked Bar Chart (`stacked_bar_by_dimension`) - **requires `stack_dim` in fields** (NOT `color_dim`)
- **1 Dimension + 2+ Measures** → Use Side-by-Side Bar Chart (`bar_multi_measure`)
- **2 Measures** → Use Scatter Plot with Detail + Color encodings
- **2 Dimensions + 2 Measures** → Use Dot Matrix
- **Category < 5 values** → Prefer Donut Chart
- **Use diverse chart types** - Don't default to basic bars when stacked bars, heatmaps, or scatter plots are more appropriate

See [references/templates-guide.md](references/templates-guide.md) for complete decision matrix with examples.

## Template Quick Reference

**CRITICAL**: Always use visualization templates instead of manually building visualization JSON. Templates ensure proper field structure, encodings, sorting, and API compliance.

**Available templates (aligned with test harness patterns):**
- `revenue_by_category` — Bar chart (dimension vs measure) - **Automatically sorted descending + automatic color_dim (default) + legend (test harness pattern)**
- `stacked_bar_by_dimension` — **Stacked bar chart** - **2 dimensions + measure, part-to-whole with breakdown + legend**
- `bar_multi_measure` — **Side-by-side bar chart** - **1 dimension + 2+ measures, comparing multiple measures**
- `trend_over_time` — Line chart (date vs measure) - **Year + Month hierarchy AUTOMATIC (DatePartYear + DatePartMonth) + automatic color_dim (default) + legend (test harness pattern)**
- `multi_series_line` — **Multi-series line chart** - **Date + measure + color_dim, comparing trends across categories + legend**
- `market_share_donut` — Donut chart distribution - **Color + Angle + Label encodings + legend (test harness pattern)**
- `top_n_leaderboard` — Table sorted by measure
- `conversion_funnel` — Funnel chart by stage - **Automatic sorting + automatic color_dim (default) + legend (test harness pattern)**
- `scatter_correlation` — Scatter plot (measure vs measure) - **Detail + Color encodings + legend (test harness pattern)**
- `heatmap_grid` — Heatmap (2 dimensions + measure) - **Color(measure) + Label(measure) + Size(measure) + legend (test harness pattern)**. Fields: col_dim, row_dim, measure (aliases: x_dimension, y_dimension).
- `dot_matrix` — **Dot matrix chart** - **2 dimensions + 2 measures, Color(measure) + Size(measure) + legend (test harness pattern)**
- `geomap_location_only` — **Map** - **latitude + longitude only; empty encodings; Circle**
- `geomap_points` — **Map (points)** - **latitude + longitude + measure + label dimension; MapPosition; Color + Label**
- `geomap_advanced` — **Map** - **latitude + longitude + label dimension + one measure (triplicated for Color, Label, Size); diverging palette on color measure**
- `flow_package_base` / `flow_package_single_color` — **Package minimal flow** — measure-first keys; single-color uses `flow_uniform_fill` (`#F9E3B6`)
- `flow_package_link_color_nodes_color` — **Package “measure on marks”** — link Color (dup measure) + nodes Color (dup level2, **F4** defined)
- `flow_package_colors_variations` — first-level bar Color (dup level1), link Color, nodes Color (dup level2)
- `flow_package_three_level` — three dimensions + link Color on duplicate measure; `--level3`
- `flow_simple` / `flow_simple_measure_on_marks` / `flow_sankey` / `flow_sankey_measure_on_marks` — **Legacy** levels-first layouts (node **Size** variants differ from package Color-on-marks)

**Create from template (with color encoding):**
```bash
python scripts/apply_viz_template.py \
  --template revenue_by_category \
  --sdm Sales_Model \
  --category Region \
  --amount Total_Amount \
  --color-dim Opportunity_Type \
  --name Revenue_by_Region \
  --label "Revenue by Region" \
  --workspace My_Workspace \
  --post
```

**Note**: `color_dim` is automatic for most templates (see Color Encoding section). For `stacked_bar_by_dimension`, use `--stack-dim` (NOT `--color-dim`).

**Auto-select chart type:**
```bash
python scripts/apply_viz_template.py \
  --sdm Sales_Model \
  --date Close_Date \
  --measure Total_Amount \
  --auto-select \
  --auto-match \
  --name Sales_Trend_Over_Time \
  --label "Sales Performance Over Time" \
  --workspace My_Workspace \
  --post
```

**⚠ WARNING**: The `--auto-generate-viz` flag in `create_dashboard.py` bypasses narrative design workflow:
- It auto-generates visualization specs without narrative planning
- Names may contain technical suffixes if SDM labels are missing
- Use only for quick prototyping, not production dashboards
- Always prefer manual `viz_specs.json` creation with narrative design

See [references/templates-guide.md](references/templates-guide.md) for complete template catalog.

## Dashboard Pattern Quick Reference

**CRITICAL**: Always use dashboard patterns/templates instead of manually building dashboard JSON.

**Available patterns:**
1. **`f_layout`** — Metrics in left sidebar, visualizations in F-pattern
   - Requirements: **6 filters, 3 metrics, 5 visualizations** (exact)
   - REQUIRES metrics
2. **`z_layout`** — Metrics in top row, visualizations in Z-pattern
   - Requirements: **6 filters, 6 metrics, 5 visualizations** (exact)
   - REQUIRES metrics
3. **`performance_overview`** — Large metric left, smaller metrics right, time navigation
   - Requirements: **3 filters, 5 metrics (1 primary + 4 secondary), 5 visualizations** (exact)
   - REQUIRES metrics (primary_metric mandatory)

**Auto-select pattern:**
```bash
python scripts/generate_dashboard_pattern.py \
  --auto-select-pattern \
  --name {{DASHBOARD_NAME}} \
  --workspace-name {{WORKSPACE}} \
  --sdm-name {{SDM_NAME}} \
  --viz {{VIZ_1}} {{VIZ_2}} ... \
  --metrics {{METRIC_1}} {{METRIC_2}} ... \
  -o dashboard.json
```

Auto-select logic:
- **Exact slot match** → `f_layout`, `z_layout`, or `performance_overview`
- **Other metric + viz mixes** → `f_layout` (default)
- **Metrics only** → `f_layout` (`create_dashboard.py` still requires ≥1 visualization in specs)
- **Visualizations only** → `z_layout` (still supply metrics for a valid dashboard)

See [references/templates-guide.md](references/templates-guide.md) for complete pattern documentation.

## Script Cheat Sheet

**Script location:** `~/.cursor/skills/tableau-next-author/scripts/`

**Generic Dashboard Creation (AI-driven):**
```bash
# AI creates viz_specs.json, then calls:
python scripts/create_dashboard.py \
  --org {{ORG_ALIAS}} \
  --sdm {{SDM_NAME}} \
  --workspace {{WORKSPACE_NAME}} \
  --name {{DASHBOARD_NAME}} \
  --viz-specs viz_specs.json
```

**Visualization Spec Format (viz_specs.json) - COLOR ENCODINGS ARE AUTOMATIC:**

**NOTE**: `color_dim` is now **AUTOMATIC** - the system auto-adds it when templates support it and 2+ dimensions are available. You can optionally specify `color_dim` at the top level (not inside `fields`) if you want a specific dimension. Colors work WITH automatic sorting - charts are still sorted descending by measure, colors add visual distinction.

```json
{
  "visualizations": [
    {
      "template": "multi_series_line",
      "name": "Sales_Trend_Over_Time",  // Business-friendly API name
      "label": "Sales Performance by Product Line",  // Clear, actionable label
      "fields": {"date": "Close_Date", "measure": "Total_Amount"},
      "color_dim": "Opportunity_Type"  // Adds multi-series colors + legend
    },
    {
      "template": "revenue_by_category",
      "name": "Revenue_by_Stage",  // Descriptive name
      "label": "Revenue by Opportunity Stage",  // User-friendly label
      "fields": {"category": "Opportunity_Stage", "amount": "Total_Amount"},
      "color_dim": "Opportunity_Type"  // Adds colors + legend, sorting still works
    },
    {
      "template": "conversion_funnel",
      "name": "Pipeline_Funnel",  // Clear purpose
      "label": "Sales Pipeline by Stage",  // Business terminology
      "fields": {"stage": "Opportunity_Stage", "count": "Total_Amount"},
      "color_dim": "Opportunity_Type"
    },
    {
      "template": "market_share_donut",
      "name": "Revenue_Distribution_by_Type",  // Descriptive name
      "label": "Revenue Distribution by Opportunity Type",  // Clear label
      "fields": {"category": "Opportunity_Type", "amount": "Total_Amount"}
    },
    {
      "template": "scatter_correlation",
      "name": "Deal_Size_vs_Win_Rate",  // Business-focused name
      "label": "Deal Size vs Win Rate by Stage",  // Explains correlation
      "fields": {"x_measure": "Total_Amount", "y_measure": "Probability", "category": "Opportunity_Stage"}
    },
    {
      "template": "stacked_bar_by_dimension",
      "name": "Revenue_by_Stage_and_Type",  // Descriptive name
      "label": "Revenue by Stage and Type",  // Clear label
      "fields": {"category": "Opportunity_Stage", "stack_dim": "Opportunity_Type", "amount": "Total_Amount"}
      // NOTE: stacked_bar_by_dimension REQUIRES stack_dim (NOT color_dim)
    },
    {
      "template": "geomap_location_only",
      "name": "Store_Locations",
      "label": "Store locations",
      "fields": {"latitude": "Latitude", "longitude": "Longitude"}
    },
    {
      "template": "geomap_points",
      "name": "Revenue_by_Location",
      "label": "Revenue by store location",
      "fields": {
        "latitude": "Latitude",
        "longitude": "Longitude",
        "measure": "Total_Amount_clc",
        "label_dim": "Store_Name"
      }
    },
    {
      "template": "geomap_advanced",
      "name": "Map_Color_Size",
      "label": "Map with color and size",
      "fields": {
        "latitude": "Latitude",
        "longitude": "Longitude",
        "measure": "Total_Amount_clc",
        "label_dim": "Store_Name"
      }
    },
    {
      "template": "flow_package_base",
      "name": "Base_Flow",
      "label": "Base flow (package shape)",
      "fields": {
        "level1": "Product_Family1",
        "level2": "Store_Type",
        "link_measure": "Total_Orders_clc"
      }
    },
    {
      "template": "flow_package_three_level",
      "name": "Flow_Three_Dims",
      "label": "Three-level flow",
      "fields": {
        "level1": "Store_Type",
        "level2": "Region",
        "level3": "Status1",
        "link_measure": "Total_Amount_clc"
      }
    },
    {
      "template": "flow_sankey",
      "name": "Product_to_Store_Flow",
      "label": "Volume from product family to store (legacy levels-first)",
      "fields": {
        "level1": "Product_Family1",
        "level2": "Store_Name",
        "link_measure": "Total_Amount_clc"
      }
    }
  ],
  "filters": [
    {"fieldName": "Account_Industry", "objectName": "Opportunity_TAB_Sales_Cloud", "dataType": "Text"}
  ]
}
```

**Key points:**
- **Template-specific field requirements**:
  - `stacked_bar_by_dimension` → Must use `stack_dim` in `fields` (NOT `color_dim`)
  - Other templates → Use `color_dim` for color encoding (optional, auto-added when available)
- **`color_dim` is AUTOMATIC** - system auto-adds when templates support it and 2+ dimensions available
- **Year+Month hierarchy is AUTOMATIC** for line charts - no manual config needed
- **Sorting is automatic** for bar charts and funnels (descending by measure)
- **Use `recommend_diverse_chart_types()`** to get diverse, colorful visualizations
- **For stacked bars**: Use `stacked_bar_by_dimension` with `stack_dim` in fields (NOT `color_dim`)

**Discovery:**
```bash
python scripts/discover_sdm.py --list
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json
```

**Create visualization with template (RECOMMENDED):**
```bash
python scripts/apply_viz_template.py \
  --template revenue_by_category \
  --sdm Sales_Model \
  --category Region \
  --amount Total_Amount \
  --color-dim Opportunity_Type \
  --name Revenue_by_Region \
  --label "Revenue Performance by Region" \
  --workspace My_Workspace \
  --post
```

**Generate dashboard pattern (for manual dashboard creation):**
```bash
python scripts/generate_dashboard_pattern.py \
  --pattern f_layout \
  --name Sales_Dashboard \
  --workspace-name My_WS \
  --sdm-name Sales_Model \
  --viz Revenue_Bar Pipeline_Funnel \
  --metrics Total_Revenue_mtc \
  -o dashboard.json
```

**Note**: For production dashboards, use `create_dashboard.py` with `viz_specs.json` instead of manual pattern generation.

**Validate before POST:**
```bash
python scripts/validate_viz.py viz.json
```

**Create calculated field:**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Model \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Won_Count]) / SUM([Total_Count])" \
  --aggregation Sum
```

See [references/scripts-guide.md](references/scripts-guide.md) for detailed script documentation.

## Dashboard Quality Checklist

Before publishing a dashboard, verify it meets these business and UX standards:

### Business Clarity
- [ ] Every visualization has a clear, business-friendly label (e.g., "Sales Performance by Region" not "Account_Region_2")
- [ ] API names are descriptive and meaningful (e.g., `Revenue_by_Stage`, not `Viz_1` or `Trend_1`)
- [ ] No technical jargon (field names, IDs, API names) visible to end users
- [ ] Dashboard tells a coherent story with logical flow (KPIs → Trends → Breakdowns → Correlations)
- [ ] Each chart answers a specific business question
- [ ] Dashboard title clearly states its purpose

### Visual Design
- [ ] Metrics positioned at top/left (F-pattern) showing key KPIs first
- [ ] Trend charts appear early in flow (provides temporal context)
- [ ] Breakdowns follow trends (dimensional analysis after temporal context)
- [ ] Colors used consistently and meaningfully (not random)
- [ ] Visual hierarchy guides the eye naturally (F-pattern or Z-pattern)
- [ ] White space used effectively (not overcrowded)

### User Experience
- [ ] Filters are relevant and clearly labeled with business terminology
- [ ] Each chart has a purpose - user can take action based on insights
- [ ] Dashboard layout matches user's mental model (executive vs operational)
- [ ] Labels use business language, not technical field names
- [ ] Chart types are appropriate for the data and question being answered
- [ ] Dashboard is scannable - key insights visible at a glance

### Technical Quality
- [ ] All visualizations use templates (never manually built JSON)
- [ ] Dashboard uses appropriate pattern (f_layout, z_layout, etc.)
- [ ] Color encodings added when multiple dimensions available
- [ ] Sorting applied where appropriate (bar charts descending by measure)
- [ ] Date hierarchies configured correctly (Year+Month for line charts)

**Remember**: A technically correct dashboard that's confusing to users is a failure. Prioritize clarity and business value over technical perfection.

## Common Errors Quick Fix Table

| Error Message | Quick Fix |
|--------------|-----------|
| `"Value required for [fonts]"` | Include all 7 font definitions in `style.fonts` |
| `"Value required for [range]"` | Add `"range": {"reverse": false}` to `marks.panes` |
| `"Value required for [axis]"` | Add `"axis": {"fields": {}}` to `style` |
| `"encodings can have only measure fields"` | Remove dimension fields from `style.encodings.fields` |
| `"encodings style is required for the <field> field"` | Add field entry to `style.encodings.fields` |
| `"startToMiddleSteps isn't available with sequential palettes"` | Remove `startToMiddleSteps` from 2-color palette |
| `JSON_PARSER_ERROR` (dashboard) | Remove `label` and `type` from `widget.source` |
| `401 Unauthorized` | Refresh token: `sf org display --target-org $SF_ORG --json` |
| `"Semantic model not found"` | Verify SDM name with `discover_sdm.py --list` |

See [references/troubleshooting.md](references/troubleshooting.md) for complete error catalog and solutions.

## Prerequisites

**Easy Authentication (Recommended):**
1. Salesforce CLI installed: `sf` command
2. Authenticated org: `sf org login web --alias myorg`
3. `jq` for JSON parsing: `brew install jq`
4. Python 3.8+ with `requests`: `pip install requests`

**Quick auth setup:**
```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

See [references/authentication.md](references/authentication.md) for complete setup including helper scripts!

## Additional Resources

- **[references/workflow.md](references/workflow.md)** - Step-by-step dashboard creation process
- **[references/templates-guide.md](references/templates-guide.md)** - Complete template catalog and decision matrix
- **[references/scripts-guide.md](references/scripts-guide.md)** - Script usage and automation
- **[references/troubleshooting.md](references/troubleshooting.md)** - Common errors and solutions
- **[references/chart-catalog.md](references/chart-catalog.md)** - Complete chart type library (Vizql, Map, Flow)
- **[references/examples.md](references/examples.md)** - 3 real-world industry examples (Sales, Marketing, HR)
- **[references/api-reference.md](references/api-reference.md)** - Full REST API documentation
- **[references/authentication.md](references/authentication.md)** - Easy auth with SF CLI + helper scripts
- **[references/advanced-features.md](references/advanced-features.md)** - Calculated fields and formulas

---

## Appendix: Technical Reference

### API Endpoints Quick Reference

```
Discovery (no minor version):
GET  /services/data/v66.0/ssot/semantic/models
GET  /services/data/v66.0/ssot/semantic/models/{apiName}

Creation (with minorVersion=12):
POST /services/data/v66.0/tableau/visualizations?minorVersion=12
POST /services/data/v66.0/tableau/dashboards?minorVersion=12
POST /services/data/v66.0/tableau/workspaces
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-measurements
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-dimensions

Retrieval (with minorVersion=12):
GET  /services/data/v66.0/tableau/visualizations/{id}?minorVersion=12
GET  /services/data/v66.0/tableau/dashboards/{id}?minorVersion=12

Update (with minorVersion=12):
PATCH /services/data/v66.0/tableau/visualizations/{id}?minorVersion=12
PATCH /services/data/v66.0/tableau/dashboards/{id}?minorVersion=12
```

**Important:** 
- Base URL: `https://{instance}.salesforce.com`
- Major version: `v66.0` (NOT v65.11)
- Minor version: Query parameter `?minorVersion=12` for Tableau endpoints

See [references/api-reference.md](references/api-reference.md) for complete API documentation.

### Tested Combinations

All combinations below have been validated, POSTed, and round-trip verified against a live org:

| # | Chart | Encodings / What it tests | Result |
|---|-------|---------------------------|--------|
| 1 | Bar | Label(measure) | PASS |
| 2 | Bar | Label + Color(dim) + Sort | PASS |
| 3 | Line | Label(measure), DatePartMonth | PASS |
| 4 | Line | Label + Color(dim) | PASS |
| 5 | Donut | Angle + Color(dim) + Label | PASS |
| 6 | Scatter | Detail(dim) + Color(dim) | PASS |
| 7 | Scatter | Detail(dim) + Color(measure) | PASS |
| 8 | Funnel | Label(measure) | PASS |
| 9 | Funnel | Label + Color(dim) | PASS |
| 10 | Heatmap | Color(measure) + Label | PASS |
| 11 | Dot Matrix | Color(measure) + Size(measure) | PASS |
| 12 | Table | 2 dims + 1 measure | PASS |
| 13 | Bar | `_clc` measure with UserAgg | PASS |
| 14 | Line | `_clc` measure + DatePartMonth | PASS |
| 15 | Donut | `_clc` measure + `_clc` dimension | PASS |
| 16 | Bar | MeasureValues/MeasureNames (side-by-side) | PASS |
| 17 | Dashboard | 2-widget dashboard + text header | PASS |
| 18 | Dashboard | Filter + metric + 2 vizzes | PASS |
| 19 | PATCH | POST → GET → strip read-only → PATCH | PASS |
| 20 | Bar | Custom bg/font/line colors | PASS |
| 21 | Dashboard | 2-page layout + nav buttons | PASS |
| 22 | Calculated Field | Create _clc measurement | PASS |
| 23 | Calculated Field | Create _clc dimension | PASS |
| 33 | Metric | Create _mtc metric on SDM | PASS |
| 34 | Metric | Create _mtc metric (ratio) | PASS |
| 35 | Metric | Create _mtc metric using template | PASS |
| 36 | Dashboard | Dashboard with metric widget using _mtc | PASS |
| 37 | Map | geomap_points: MapPosition + Circle + validate() | PASS |
| 38 | Flow | flow_package_* + legacy flow_* + validate(); optional `strict_encoding_field_refs` | PASS |
