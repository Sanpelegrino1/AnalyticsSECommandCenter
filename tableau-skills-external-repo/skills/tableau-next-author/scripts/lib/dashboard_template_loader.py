"""Load and customize dashboard templates from the collection.

Loads production dashboard templates (F_layout, Z_Layout, etc.) and replaces
widget sources with actual visualization/metric/filter names.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dashboard_patterns import deduplicate_filter_defs

# Path to dashboard templates (relative to project root)
# Try project root first, fallback to old location for backward compatibility
_SCRIPT_DIR = Path(__file__).parent.parent.parent  # Go up from scripts/lib/ to project root
TEMPLATE_DIR = _SCRIPT_DIR / "templates" / "dashboards"
if not TEMPLATE_DIR.exists():
    # Fallback to old location
    TEMPLATE_DIR = Path.home() / ".cursor" / "skills" / "tableau-next-author" / ".cursor" / "tabnext-tools-main" / "collection" / "dashboard_template"


def load_dashboard_template(template_name: str) -> Optional[Dict[str, Any]]:
    """Load a dashboard template JSON file.
    
    Args:
        template_name: Template name (e.g., "F_layout", "Z_Layout", "Performance_Overview_Full_Page")
    
    Returns:
        Dashboard JSON dict or None if not found
    """
    # Map common names to file names
    name_map = {
        "f_layout": "F_layout.json",
        "z_layout": "Z_Layout.json",
        "performance_overview": "Performance_Overview_Full_Page.json",
        "c360_full": "C360_Metrics_Full_View.json",
        "c360_half": "C360_Metrics_Half.json",
        "c360_vertical": "C360_Metrics_Vertical_View.json",
    }
    
    file_name = name_map.get(template_name.lower(), f"{template_name}.json")
    template_path = TEMPLATE_DIR / file_name
    
    if not template_path.exists():
        return None
    
    with open(template_path, 'r') as f:
        return json.load(f)


def recommend_viz_slot_mapping(
    visualization_specs: List[Dict[str, Any]],
    pattern: str = "f_layout"
) -> Dict[str, str]:
    """Recommend which visualization should go in which template slot based on chart type.
    
    Args:
        visualization_specs: List of viz specs with 'name' and 'template' (chart type)
        pattern: Dashboard pattern name (default: "f_layout")
    
    Returns:
        Dict mapping slot names to viz names, e.g. {"visualization_1": "Sales_Trend", "visualization_3": "Pipeline_Funnel"}
    
    Slot characteristics for f_layout:
    - visualization_1: Large top-right (47x55) - Best for trend charts, main overview
    - visualization_2-4: Small bottom (23x37 each) - Good for category charts, funnels, donuts
    - visualization_5: Large bottom (68x53) - Good for detailed tables, multi-series charts
    """
    if pattern != "f_layout":
        # For other patterns, just use order
        return {}
    
    slot_mapping = {}
    
    # Chart type priorities for slot assignment
    # Priority 1: Large top-right (visualization_1) - best for trends
    trend_templates = ["trend_over_time", "multi_series_line"]
    
    # Priority 2: Small slots (visualization_2-4) - good for funnels, donuts, bars
    small_chart_templates = ["conversion_funnel", "market_share_donut", "revenue_by_category"]
    
    # Priority 3: Large bottom (visualization_5) - good for tables, detailed views
    large_bottom_templates = ["top_n_leaderboard", "heatmap_grid", "dot_matrix"]
    
    # Track which slots are used
    used_slots = set()
    small_slots = ["visualization_2", "visualization_3", "visualization_4"]
    small_slot_idx = 0
    
    # First pass: assign trend charts to visualization_1
    for viz_spec in visualization_specs:
        viz_name = viz_spec.get("name", "")
        template = viz_spec.get("template", "").lower()
        
        if template in trend_templates and "visualization_1" not in used_slots:
            slot_mapping["visualization_1"] = viz_name
            used_slots.add("visualization_1")
            break
    
    # Second pass: assign small charts to small slots
    for viz_spec in visualization_specs:
        viz_name = viz_spec.get("name", "")
        template = viz_spec.get("template", "").lower()
        
        if template in small_chart_templates and small_slot_idx < len(small_slots):
            slot = small_slots[small_slot_idx]
            if slot not in used_slots:
                slot_mapping[slot] = viz_name
                used_slots.add(slot)
                small_slot_idx += 1
    
    # Third pass: assign large bottom charts
    for viz_spec in visualization_specs:
        viz_name = viz_spec.get("name", "")
        template = viz_spec.get("template", "").lower()
        
        if template in large_bottom_templates and "visualization_5" not in used_slots:
            slot_mapping["visualization_5"] = viz_name
            used_slots.add("visualization_5")
            break
    
    # Fill remaining slots in order for any unassigned visualizations
    all_slots = ["visualization_1", "visualization_2", "visualization_3", "visualization_4", "visualization_5"]
    slot_idx = 0
    
    for viz_spec in visualization_specs:
        viz_name = viz_spec.get("name", "")
        if viz_name not in slot_mapping.values():
            while slot_idx < len(all_slots) and all_slots[slot_idx] in used_slots:
                slot_idx += 1
            if slot_idx < len(all_slots):
                slot_mapping[all_slots[slot_idx]] = viz_name
                used_slots.add(all_slots[slot_idx])
                slot_idx += 1
    
    return slot_mapping


def get_sdm_id(sdm_name: str) -> Optional[str]:
    """Get SDM ID from SDM API name.
    
    Args:
        sdm_name: SDM API name
        
    Returns:
        SDM ID if found, None otherwise
    """
    try:
        from .sf_api import get_credentials, sdm_detail_endpoint, sf_get
        token, instance = get_credentials()
        data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
        if data and isinstance(data, dict):
            return data.get("id")
    except Exception:
        # Silently fail - sdm_id is optional
        pass
    return None


def replace_placeholders_recursive(
    obj: Any,
    placeholders: Dict[str, str]
) -> Any:
    """Recursively replace placeholders in a JSON structure.
    
    Args:
        obj: JSON object (dict, list, or primitive)
        placeholders: Dict mapping placeholder names to replacement values
                      e.g., {"{{SDM_API_NAME}}": "Sales_Cloud12_backward"}
    
    Returns:
        Object with placeholders replaced
    """
    if isinstance(obj, dict):
        return {k: replace_placeholders_recursive(v, placeholders) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_placeholders_recursive(item, placeholders) for item in obj]
    elif isinstance(obj, str):
        # Replace placeholders in string values
        result = obj
        for placeholder, replacement in placeholders.items():
            if placeholder in result:
                result = result.replace(placeholder, replacement)
        return result
    else:
        return obj


def generate_smart_text_content(
    visualization_name: str,
    chart_type: Optional[str] = None,
    text_widget_type: str = "header"
) -> List[Dict[str, Any]]:
    """Generate smart text content for text widgets based on visualization context.
    
    Args:
        visualization_name: Visualization API name (e.g., "Sales_Trend_Over_Time")
        chart_type: Optional chart type (e.g., "trend_over_time", "conversion_funnel")
        text_widget_type: Type of text widget ("header", "subheader", "section")
    
    Returns:
        List of content items for text widget parameters
    """
    # Convert API name to readable title
    # "Sales_Trend_Over_Time" -> "Sales Trend Over Time"
    readable_title = visualization_name.replace("_", " ")
    
    # Chart type to description mapping
    chart_descriptions = {
        "trend_over_time": "Trend Analysis",
        "conversion_funnel": "Pipeline Analysis",
        "revenue_by_category": "Revenue Breakdown",
        "market_share_donut": "Market Share",
        "top_n_leaderboard": "Top Performers",
        "geomap_location_only": "Geographic Analysis",
        "geomap_points": "Geographic Analysis",
        "geomap_advanced": "Geographic Analysis",
        "flow_sankey": "Flow Analysis",
        "flow_simple": "Flow Analysis",
        "flow_simple_measure_on_marks": "Flow Analysis",
        "flow_sankey_measure_on_marks": "Flow Analysis",
        "flow_package_base": "Flow Analysis",
        "flow_package_single_color": "Flow Analysis",
        "flow_package_link_color_nodes_color": "Flow Analysis",
        "flow_package_colors_variations": "Flow Analysis",
        "flow_package_three_level": "Flow Analysis",
    }
    
    if text_widget_type == "header":
        # Main title (large, bold)
        description = chart_descriptions.get(chart_type, "Analysis") if chart_type else ""
        return [
            {
                "attributes": {"size": "20px", "color": "#03234d"},
                "insert": readable_title
            },
            {"insert": "\n"},
            {
                "attributes": {"color": "#5c5c5c", "size": "14px"},
                "insert": description if description else "Performance Overview"
            },
            {"attributes": {"align": "left"}, "insert": "\n"}
        ]
    elif text_widget_type == "subheader":
        # Small subheader
        return [
            {
                "attributes": {"color": "#2e2e2e", "size": "18px"},
                "insert": readable_title
            },
            {"attributes": {"align": "left"}, "insert": "\n"}
        ]
    elif text_widget_type == "section":
        # Section divider
        return [
            {
                "attributes": {"color": "#03234d", "size": "24px"},
                "insert": readable_title
            },
            {"insert": "\n"},
            {
                "attributes": {"color": "#5c5c5c", "size": "14px"},
                "insert": "Section Subheader"
            },
            {"attributes": {"align": "left"}, "insert": "\n"}
        ]
    else:
        return [
            {
                "attributes": {"color": "#03234d", "size": "18px"},
                "insert": readable_title
            },
            {"attributes": {"align": "left"}, "insert": "\n"}
        ]


def customize_dashboard_template(
    template: Dict[str, Any],
    name: str,
    label: str,
    workspace_name: str,
    visualization_names: Optional[List[str]] = None,
    visualization_slot_map: Optional[Dict[str, str]] = None,
    visualization_specs: Optional[List[Dict[str, Any]]] = None,
    metric_names: Optional[List[str]] = None,
    filter_defs: Optional[List[Dict[str, Any]]] = None,
    sdm_name: Optional[str] = None,
    sdm_id: Optional[str] = None,
    text_content_overrides: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Customize a dashboard template with actual widget sources.
    
    Args:
        template: Template dashboard JSON
        name: Dashboard API name
        label: Dashboard display label
        workspace_name: Workspace API name
        visualization_names: List of visualization API names (will replace visualization_1, visualization_2, etc. in order)
        visualization_slot_map: Optional dict mapping slot names to viz names, e.g. {"visualization_1": "Sales_Trend", "visualization_3": "Pipeline_Funnel"}
                      If provided, overrides visualization_names ordering
        metric_names: List of metric API names (will replace metric_1, metric_2, etc.)
        filter_defs: List of filter definitions with fieldName, objectName, dataType
        sdm_name: SDM API name (required for filters/metrics)
        sdm_id: SDM ID (optional, but recommended for metrics)
    
    Returns:
        Customized dashboard JSON ready to POST
    """
    # Create a deep copy to avoid modifying the template
    dashboard = json.loads(json.dumps(template))
    
    # Auto-fetch SDM ID if not provided but sdm_name is available
    if sdm_name and not sdm_id:
        sdm_id = get_sdm_id(sdm_name)
    
    # Build placeholder replacement map
    placeholders = {}
    if sdm_name:
        placeholders["{{SDM_API_NAME}}"] = sdm_name
    if sdm_id:
        placeholders["{{SDM_ID}}"] = sdm_id
    if workspace_name:
        placeholders["{{WORKSPACE_API_NAME}}"] = workspace_name
    
    # Add visualization name placeholders ({{VIZ_1}}, {{VIZ_2}}, etc.)
    visualization_names = visualization_names or []
    for i, viz_name in enumerate(visualization_names, start=1):
        placeholders[f"{{{{VIZ_{i}}}}}"] = viz_name
        placeholders[f"{{{{VISUALIZATION_{i}}}}}"] = viz_name
    
    # Add metric name placeholders ({{METRIC_1}}, {{METRIC_2}}, etc.)
    metric_names = metric_names or []
    for i, metric_name in enumerate(metric_names, start=1):
        placeholders[f"{{{{METRIC_{i}}}}}"] = metric_name
    
    # Replace all placeholders recursively throughout the dashboard FIRST
    # This handles any placeholder strings anywhere in the template
    if placeholders:
        dashboard = replace_placeholders_recursive(dashboard, placeholders)
    
    # Update basic fields (these override any placeholders)
    dashboard["name"] = name
    dashboard["label"] = label
    dashboard["workspaceIdOrApiName"] = workspace_name
    
    # Remove readonly fields that will be set by API or are not supported in POST
    readonly_fields = [
        "id", "url", "createdBy", "createdDate", "lastModifiedBy", 
        "lastModifiedDate", "permissions", "customViews", "templateSource"
    ]
    for field in readonly_fields:
        dashboard.pop(field, None)
    
    # Remove readonly fields from widgets (id, status)
    # Also clean up source objects - they should only have "name", not "id", "type", "label"
    widgets = dashboard.get("widgets", {})
    for widget_key, widget in widgets.items():
        if isinstance(widget, dict):
            widget.pop("id", None)
            widget.pop("status", None)
            # Clean source objects - remove readonly fields, keep only name
            if "source" in widget and isinstance(widget["source"], dict):
                source_name = widget["source"].get("name")
                if source_name:
                    widget["source"] = {"name": source_name}
                else:
                    widget.pop("source", None)
    
    # Remove readonly fields from layouts (id)
    layouts = dashboard.get("layouts", [])
    for layout in layouts:
        layout.pop("id", None)
        pages = layout.get("pages", [])
        for page in pages:
            page.pop("id", None)
            # Remove readonly fields from page widgets
            page_widgets = page.get("widgets", [])
            for pw in page_widgets:
                if isinstance(pw, dict):
                    pw.pop("id", None)
    
    widgets = dashboard.get("widgets", {})
    visualization_names = visualization_names or []
    metric_names = metric_names or []
    filter_defs = filter_defs or []
    
    # Deduplicate filters to prevent using the same field twice
    filter_defs = deduplicate_filter_defs(filter_defs)
    
    # Replace visualization sources
    # Visualizations need source at widget level (like build_dashboard does)
    viz_widgets = [k for k in widgets.keys() if k.startswith("visualization_")]
    viz_widgets.sort()  # Sort to ensure consistent ordering
    
    if visualization_slot_map:
        # Use explicit slot mapping if provided (AI can specify which viz goes where)
        for widget_key in viz_widgets:
            if widget_key in visualization_slot_map:
                widget = widgets[widget_key]
                widget["source"] = {"name": visualization_slot_map[widget_key]}
    else:
        # Fallback to ordered list matching (visualization_1 → first, visualization_2 → second, etc.)
        visualization_names = visualization_names or []
        for i, widget_key in enumerate(viz_widgets):
            if i < len(visualization_names):
                widget = widgets[widget_key]
                # Replace source completely - must ONLY contain "name", not "type", "id", or "label"
                widget["source"] = {"name": visualization_names[i]}
    
    # Replace metric sources
    metric_widgets = [k for k in widgets.keys() if k.startswith("metric_")]
    metric_widgets.sort()
    for i, widget_key in enumerate(metric_widgets):
        widget = widgets[widget_key]
        # Ensure widget has required structure
        if "parameters" not in widget:
            widget["parameters"] = {}
        if "metricOption" not in widget["parameters"]:
            widget["parameters"]["metricOption"] = {}
        
        if i < len(metric_names) and metric_names[i]:
            # Set SDM name in metricOption (override any placeholders that weren't replaced)
            if sdm_name:
                widget["parameters"]["metricOption"]["sdmApiName"] = sdm_name
            # Add sdmId if provided (optional but may help with DataSourceError)
            if sdm_id:
                widget["parameters"]["metricOption"]["sdmId"] = sdm_id
            
            # Ensure metricOption has layout structure (like build_dashboard does)
            if "layout" not in widget["parameters"]["metricOption"]:
                widget["parameters"]["metricOption"]["layout"] = {}
            if "componentVisibility" not in widget["parameters"]["metricOption"]["layout"]:
                widget["parameters"]["metricOption"]["layout"]["componentVisibility"] = {
                    "chart": True,
                    "value": True,
                    "title": True,
                    "details": True,
                    "comparison": True,
                    "insights": False,
                }
            
            # Ensure receiveFilterSource exists
            if "receiveFilterSource" not in widget["parameters"]:
                widget["parameters"]["receiveFilterSource"] = {"filterMode": "all", "widgetIds": []}
            
            # Replace source at widget level (required, like build_dashboard does)
            # Source must ONLY contain "name", not "type" or "id" or "label"
            # Completely replace any existing source object
            widget["source"] = {"name": metric_names[i]}
        else:
            # If no metric name, ensure widget still has proper structure but no source
            if sdm_name:
                widget["parameters"]["metricOption"]["sdmApiName"] = sdm_name
            widget.pop("source", None)
    
    # Replace filter sources
    filter_widgets = [k for k in widgets.keys() if k.startswith("filter_")]
    filter_widgets.sort()
    for i, widget_key in enumerate(filter_widgets):
        if i < len(filter_defs):
            filter_def = filter_defs[i]
            widget = widgets[widget_key]
            # Ensure widget has required structure
            if "parameters" not in widget:
                widget["parameters"] = {}
            if "filterOption" not in widget["parameters"]:
                widget["parameters"]["filterOption"] = {}
            
            # Update filterOption with actual field data
            widget["parameters"]["filterOption"]["fieldName"] = filter_def.get("fieldName", "")
            # Preserve None for calculated fields (don't default to empty string)
            object_name = filter_def.get("objectName")
            widget["parameters"]["filterOption"]["objectName"] = object_name if object_name is not None else None
            widget["parameters"]["filterOption"]["dataType"] = filter_def.get("dataType", "Text")
            widget["parameters"]["filterOption"]["selectionType"] = filter_def.get("selectionType", "multiple")
            
            # Ensure required filter parameters exist
            if "viewType" not in widget["parameters"]:
                widget["parameters"]["viewType"] = "list"
            if "isLabelHidden" not in widget["parameters"]:
                widget["parameters"]["isLabelHidden"] = False
            if "receiveFilterSource" not in widget["parameters"]:
                widget["parameters"]["receiveFilterSource"] = {"filterMode": "all", "widgetIds": []}
            
            # Add source field (required for filters, like build_dashboard does)
            if sdm_name:
                widget["source"] = {"name": sdm_name}
            
            # Update label if provided
            if "label" in filter_def:
                widget["label"] = filter_def["label"]
    
    # Update text widgets with smart titles based on visualizations
    # Map text widgets to their associated visualizations based on layout positions
    # For f_layout:
    # - text_1: Above visualization_1 (large top-right)
    # - text_2: Section divider (between metrics and bottom visualizations)
    # - text_6, text_7, text_8: Above visualization_2, 3, 4 (small bottom slots)
    
    # Build reverse mapping: viz name -> slot name
    slot_to_viz = {}
    if visualization_slot_map:
        slot_to_viz = {v: k for k, v in visualization_slot_map.items()}
    else:
        for i, viz_name in enumerate(visualization_names or [], start=1):
            slot_to_viz[viz_name] = f"visualization_{i}"
    
    # Build viz name -> chart type mapping from specs
    viz_to_chart_type = {}
    if visualization_specs:
        for spec in visualization_specs:
            viz_name = spec.get("name", "")
            chart_type = spec.get("template", "")
            if viz_name:
                viz_to_chart_type[viz_name] = chart_type
    
    # Update text widgets
    text_widget_mappings = {
        "text_1": ("visualization_1", "header"),  # Main header above large viz
        "text_2": (None, "section"),  # Section divider (no specific viz)
        "text_6": ("visualization_2", "subheader"),  # Above small viz 2
        "text_7": ("visualization_3", "subheader"),  # Above small viz 3
        "text_8": ("visualization_4", "subheader"),  # Above small viz 4
    }
    
    for text_widget_name, (viz_slot, text_type) in text_widget_mappings.items():
        if text_widget_name not in widgets:
            continue
        
        # Check for explicit override first
        if text_content_overrides and text_widget_name in text_content_overrides:
            widgets[text_widget_name]["parameters"]["content"] = text_content_overrides[text_widget_name]
            continue
        
        # Generate smart content based on associated visualization
        if viz_slot:
            # Find viz name for this slot
            viz_name = None
            if visualization_slot_map and viz_slot in visualization_slot_map:
                viz_name = visualization_slot_map[viz_slot]
            elif visualization_names:
                slot_num = int(viz_slot.split("_")[1])
                if slot_num <= len(visualization_names):
                    viz_name = visualization_names[slot_num - 1]
            
            if viz_name:
                chart_type = viz_to_chart_type.get(viz_name)
                content = generate_smart_text_content(viz_name, chart_type, text_type)
                widgets[text_widget_name]["parameters"]["content"] = content
        elif text_type == "section":
            # Section divider - use dashboard label or generic text
            section_title = label or "Details"
            widgets[text_widget_name]["parameters"]["content"] = [
                {
                    "attributes": {"color": "#03234d", "size": "24px"},
                    "insert": section_title
                },
                {"insert": "\n"},
                {
                    "attributes": {"color": "#5c5c5c", "size": "14px"},
                    "insert": "Performance Breakdown"
                },
                {"attributes": {"align": "left"}, "insert": "\n"}
            ]
    
    return dashboard
