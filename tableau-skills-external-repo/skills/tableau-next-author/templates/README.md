# Dashboard Templates

This directory contains production-ready dashboard templates that can be loaded and customized with actual visualizations, metrics, and filters.

## Location

Templates are stored in `templates/dashboards/` and loaded by `scripts/lib/dashboard_template_loader.py`.

## Available Templates

- **F_layout.json** - Metrics in left sidebar, visualizations in F-pattern
- **Z_Layout.json** - Metrics in top row, visualizations in Z-pattern  
- **Performance_Overview_Full_Page.json** - Large metric left, smaller metrics right, time navigation
- **C360_Metrics_Full_View.json** - Customer 360 metrics full view layout
- **C360_Metrics_Half.json** - Customer 360 metrics half view layout
- **C360_Metrics_Vertical_View.json** - Customer 360 metrics vertical layout

## Usage

```python
from lib.dashboard_template_loader import load_dashboard_template, customize_dashboard_template

# Load a template
template = load_dashboard_template("f_layout")

# Customize with actual widgets
dashboard = customize_dashboard_template(
    template=template,
    name="My_Dashboard",
    label="My Dashboard",
    workspace_name="My_Workspace",
    visualization_names=["Viz1", "Viz2"],
    metric_names=["Metric1", "Metric2"],
    filter_defs=[
        {"fieldName": "Region", "objectName": "Opportunity", "dataType": "Text"}
    ],
    sdm_name="Sales_Model"
)
```

## Template Structure

Templates are cleaned production dashboards with:
- Read-only fields removed (id, url, createdBy, etc.)
- Widget sources cleaned (only "name" field, no id/type/label)
- Layout structure preserved
- Ready for customization and POST

## Adding New Templates

1. Export a dashboard from Salesforce (GET from API)
2. Clean it using `scripts/lib/dashboard_template_loader.py` logic:
   - Remove readonly fields
   - Clean widget sources
   - Remove layout/page IDs
3. Save to `templates/dashboards/` with descriptive name
4. Update `dashboard_template_loader.py` name_map if needed
