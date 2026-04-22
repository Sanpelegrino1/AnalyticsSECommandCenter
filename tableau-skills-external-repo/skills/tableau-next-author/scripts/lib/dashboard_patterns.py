"""Dashboard layout patterns extracted from production templates.

Provides reusable layout patterns (F-layout, Z-layout, performance overview)
with production-quality styling for Tableau Next dashboards.
"""

import sys
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .templates import FilterDef, MetricDef, VizDef, PageDef

# For runtime, we'll use Dict/Any types instead of the dataclass types

# ---------------------------------------------------------------------------
# Pattern Requirements Schema
# ---------------------------------------------------------------------------

PATTERN_REQUIREMENTS = {
    "f_layout": {
        "filters": {"min": 6, "max": 6, "recommended": 6, "slots": 6},
        "metrics": {"min": 3, "max": 3, "recommended": 3, "slots": 3},
        "visualizations": {"min": 5, "max": 5, "recommended": 5, "slots": 5},
        "description": "Executive dashboard: 6 filters top row, 3 metrics left sidebar, 5 visualizations in F-pattern"
    },
    "z_layout": {
        "filters": {"min": 6, "max": 6, "recommended": 6, "slots": 6},
        "metrics": {"min": 6, "max": 6, "recommended": 6, "slots": 6},
        "visualizations": {"min": 5, "max": 5, "recommended": 5, "slots": 5},
        "description": "Operational dashboard: 6 filters top row, 6 metrics top row, 5 visualizations in Z-pattern"
    },
    "performance_overview": {
        "filters": {"min": 3, "max": 3, "recommended": 3, "slots": 3},
        "metrics": {"min": 5, "max": 5, "recommended": 5, "slots": 5},
        "visualizations": {"min": 5, "max": 5, "recommended": 5, "slots": 5},
        "primary_metric": {"required": True},
        "description": "Performance dashboard: 3 filters, 5 metrics (1 primary + 4 secondary), 5 visualizations, time navigation"
    }
}


def get_pattern_requirements(pattern: str) -> Optional[Dict[str, Any]]:
    """Get requirements for a pattern.
    
    Args:
        pattern: Pattern name
        
    Returns:
        Requirements dict or None if pattern not found
    """
    return PATTERN_REQUIREMENTS.get(pattern)


def validate_pattern_requirements(
    pattern: str,
    filters: List[Any],
    metrics: List[str],
    visualizations: List[str],
    **pattern_specific_args
) -> Tuple[bool, List[str]]:
    """Validate that provided widgets match pattern requirements.
    
    Args:
        pattern: Pattern name
        filters: List of filter definitions
        metrics: List of metric API names
        visualizations: List of visualization API names
        **pattern_specific_args: Pattern-specific arguments (e.g., primary_metric)
        
    Returns:
        (is_valid, list_of_warnings)
    """
    if pattern not in PATTERN_REQUIREMENTS:
        return False, [f"Unknown pattern: {pattern}"]
    
    req = PATTERN_REQUIREMENTS[pattern]
    warnings = []
    
    # Validate filters
    filter_count = len(filters)
    if req["filters"]["min"] is not None and filter_count < req["filters"]["min"]:
        warnings.append(f"{pattern} requires at least {req['filters']['min']} filters, got {filter_count}")
    if req["filters"]["max"] is not None and filter_count > req["filters"]["max"]:
        warnings.append(f"{pattern} requires at most {req['filters']['max']} filters, got {filter_count}")
    if req["filters"].get("slots") and filter_count != req["filters"]["slots"]:
        warnings.append(f"{pattern} requires exactly {req['filters']['slots']} filters, got {filter_count}")
    
    # Validate metrics
    metric_count = len(metrics)
    if req["metrics"]["min"] is not None and metric_count < req["metrics"]["min"]:
        warnings.append(f"{pattern} requires at least {req['metrics']['min']} metrics, got {metric_count}")
    if req["metrics"]["max"] is not None and metric_count > req["metrics"]["max"]:
        warnings.append(f"{pattern} requires at most {req['metrics']['max']} metrics, got {metric_count}")
    if req["metrics"].get("slots") and metric_count != req["metrics"]["slots"]:
        warnings.append(f"{pattern} requires exactly {req['metrics']['slots']} metrics, got {metric_count}")
    if req["metrics"].get("slots_per_page") and "metrics_per_page" in pattern_specific_args:
        metrics_per_page = pattern_specific_args["metrics_per_page"]
        if metrics_per_page != req["metrics"]["slots_per_page"]:
            warnings.append(f"{pattern} requires {req['metrics']['slots_per_page']} metrics per page, got {metrics_per_page}")
    if req["metrics"].get("slots_per_row") and "metrics_per_row" in pattern_specific_args:
        metrics_per_row = pattern_specific_args["metrics_per_row"]
        if metrics_per_row != req["metrics"]["slots_per_row"]:
            warnings.append(f"{pattern} requires {req['metrics']['slots_per_row']} metrics per row, got {metrics_per_row}")
    
    # Validate visualizations
    viz_count = len(visualizations)
    if req["visualizations"]["min"] is not None and viz_count < req["visualizations"]["min"]:
        warnings.append(f"{pattern} requires at least {req['visualizations']['min']} visualizations, got {viz_count}")
    if req["visualizations"]["max"] is not None and viz_count > req["visualizations"]["max"]:
        warnings.append(f"{pattern} requires at most {req['visualizations']['max']} visualizations, got {viz_count}")
    if req["visualizations"].get("slots") and viz_count != req["visualizations"]["slots"]:
        warnings.append(f"{pattern} requires exactly {req['visualizations']['slots']} visualizations, got {viz_count}")
    
    # Pattern-specific validation
    if pattern == "performance_overview":
        if "primary_metric" not in pattern_specific_args and not metrics:
            warnings.append("performance_overview requires --primary-metric argument or at least one metric")
    
    return len(warnings) == 0, warnings


def auto_select_pattern(
    metrics: List[str],
    visualizations: List[str],
    filters: List[Any],
) -> Tuple[str, Dict[str, Any]]:
    """Auto-select dashboard pattern based on available widgets.
    
    Logic:
    - Metrics + Visualizations → f_layout, z_layout, or performance_overview when counts match exactly
    - Metrics + Visualizations (other counts) → f_layout when at least one metric and one viz; else f_layout fallback
    - Metrics only, or viz only → f_layout / z_layout fallbacks (callers should supply a valid widget mix)
    
    Args:
        metrics: List of metric API names
        visualizations: List of visualization API names
        filters: List of filter definitions
        
    Returns:
        (pattern_name, pattern_specific_args)
    """
    metric_count = len(metrics)
    viz_count = len(visualizations)
    filter_count = len(filters)
    
    pattern_args: Dict[str, Any] = {}
    
    # Check if we have metrics + visualizations
    if metric_count > 0 and viz_count > 0:
        # Try exact matches first
        f_layout_req = PATTERN_REQUIREMENTS["f_layout"]
        if (f_layout_req["metrics"]["slots"] == metric_count and
            f_layout_req["visualizations"]["slots"] == viz_count and
            f_layout_req["filters"]["slots"] == filter_count):
            return "f_layout", {"title_text": ""}
        
        z_layout_req = PATTERN_REQUIREMENTS["z_layout"]
        if (z_layout_req["metrics"]["slots"] == metric_count and
            z_layout_req["visualizations"]["slots"] == viz_count and
            z_layout_req["filters"]["slots"] == filter_count):
            return "z_layout", {"title_text": ""}
        
        perf_req = PATTERN_REQUIREMENTS["performance_overview"]
        if (perf_req["metrics"]["slots"] == metric_count and
            perf_req["visualizations"]["slots"] == viz_count and
            perf_req["filters"]["slots"] == filter_count and
            metric_count >= 5):
            pattern_args["primary_metric"] = metrics[0]
            pattern_args["secondary_metrics"] = metrics[1:5] if len(metrics) >= 5 else metrics[1:]
            pattern_args["pages"] = ["Week", "Month", "Day"]
            return "performance_overview", pattern_args
        
        # Partial counts: prefer executive F-layout (template tolerates padding).
        return "f_layout", {"title_text": ""}
    
    # Metrics only (no charts): still pick f_layout; create_dashboard requires at least one visualization.
    if metric_count > 0 and viz_count == 0:
        return "f_layout", {"title_text": ""}
    
    # Visualizations only
    if metric_count == 0 and viz_count > 0:
        # Use z_layout (only pattern that handles no metrics)
        # But we need to pad metrics or adjust - z_layout requires 6 metrics
        # Actually, z_layout REQUIRES metrics, so this won't work
        # Fall back to a pattern that doesn't require metrics
        # For now, return z_layout but warn that metrics are needed
        return "z_layout", {"title_text": ""}
    
    # No metrics, no visualizations - invalid
    return "f_layout", {"title_text": ""}  # Default fallback


def deduplicate_filter_defs(filters: List[Any]) -> List[Any]:
    """Remove duplicate filters based on field_name + object_name combination.
    
    Works with both FilterDef dataclass objects and dict-based filter definitions.
    
    Args:
        filters: List of filter definitions (FilterDef objects or dicts)
        
    Returns:
        List of unique filter definitions (first occurrence kept)
    """
    seen = set()
    unique_filters = []
    for fd in filters:
        # Handle both FilterDef objects and dict-based filters
        if hasattr(fd, 'field_name'):
            # FilterDef dataclass
            filter_key = (fd.field_name, fd.object_name)
            field_name = fd.field_name
            object_name = fd.object_name
        else:
            # Dict-based filter
            filter_key = (fd.get("fieldName", ""), fd.get("objectName", ""))
            field_name = filter_key[0]
            object_name = filter_key[1]
        
        if filter_key not in seen:
            seen.add(filter_key)
            unique_filters.append(fd)
        elif field_name:  # Only warn if field_name is not empty
            obj_name = object_name or "None"
            print(f"Warning: Duplicate filter removed: {field_name} ({obj_name})", file=sys.stderr)
    return unique_filters


# ---------------------------------------------------------------------------
# Styling Helpers
# ---------------------------------------------------------------------------

def apply_metric_style(widget: Dict[str, Any]) -> Dict[str, Any]:
    """Apply production metric widget styling.
    
    Args:
        widget: Widget dict to style
        
    Returns:
        Widget dict with metric styling applied
    """
    if "parameters" not in widget:
        widget["parameters"] = {}
    if "widgetStyle" not in widget["parameters"]:
        widget["parameters"]["widgetStyle"] = {}
    
    widget["parameters"]["widgetStyle"].update({
        "borderColor": "#C9C9C9",
        "borderEdges": ["all"],
        "borderRadius": 20,
    })
    return widget


def apply_container_style(widget: Dict[str, Any], border_radius: int = 16) -> Dict[str, Any]:
    """Apply production container widget styling.
    
    Args:
        widget: Widget dict to style
        border_radius: Border radius (default 16)
        
    Returns:
        Widget dict with container styling applied
    """
    if "parameters" not in widget:
        widget["parameters"] = {}
    if "widgetStyle" not in widget["parameters"]:
        widget["parameters"]["widgetStyle"] = {}
    
    widget["parameters"]["widgetStyle"].update({
        "borderColor": "#c9c9c9",
        "borderEdges": ["all"],  # Template uses ["all"] for containers
        "borderRadius": border_radius,
    })
    return widget


def apply_viz_style(widget: Dict[str, Any], border_radius: int = 16) -> Dict[str, Any]:
    """Apply production visualization widget styling.
    
    Args:
        widget: Widget dict to style
        border_radius: Border radius (default 16, can be 12 for some patterns)
        
    Returns:
        Widget dict with visualization styling applied
    """
    if "parameters" not in widget:
        widget["parameters"] = {}
    if "widgetStyle" not in widget["parameters"]:
        widget["parameters"]["widgetStyle"] = {}
    
    widget["parameters"]["widgetStyle"].update({
        "borderColor": "#C9C9C9",
        "borderEdges": [],
        "borderRadius": border_radius,
    })
    return widget


def apply_filter_style(widget: Dict[str, Any]) -> Dict[str, Any]:
    """Apply production filter widget styling.
    
    Args:
        widget: Widget dict to style
        
    Returns:
        Widget dict with filter styling applied
    """
    if "parameters" not in widget:
        widget["parameters"] = {}
    if "widgetStyle" not in widget["parameters"]:
        widget["parameters"]["widgetStyle"] = {}
    
    widget["parameters"]["widgetStyle"].update({
        "backgroundColor": "#f3f3f3",
        "borderEdges": [],
    })
    return widget


def apply_button_style(widget: Dict[str, Any], is_active: bool = False) -> Dict[str, Any]:
    """Apply production button widget styling.
    
    Args:
        widget: Widget dict to style
        is_active: Whether button is in active state
        
    Returns:
        Widget dict with button styling applied
    """
    if "parameters" not in widget:
        widget["parameters"] = {}
    if "widgetStyle" not in widget["parameters"]:
        widget["parameters"]["widgetStyle"] = {}
    
    if is_active:
        widget["parameters"]["widgetStyle"].update({
            "backgroundColor": "#066AFE",
            "borderColor": "#c9c9c9",
            "borderEdges": ["all"],
            "fontColor": "#ffffff",
            "textStyle": [],
        })
    else:
        widget["parameters"]["widgetStyle"].update({
            "borderColor": "#c9c9c9",
            "borderEdges": ["all"],
            "fontColor": "#0250D9",
            "textStyle": [],
        })
    return widget


def apply_text_header_style(widget: Dict[str, Any], size: str = "20px", color: str = "#03234d") -> Dict[str, Any]:
    """Apply production text widget styling for section headers.
    
    Args:
        widget: Widget dict to style
        size: Font size (default "20px")
        color: Font color (default "#03234d")
        
    Returns:
        Widget dict with text header styling applied
    """
    if "parameters" not in widget:
        widget["parameters"] = {}
    if "widgetStyle" not in widget["parameters"]:
        widget["parameters"]["widgetStyle"] = {}
    
    widget["parameters"]["widgetStyle"].update({
        "borderEdges": [],
    })
    
    # Update content if it exists
    if "content" in widget["parameters"]:
        for item in widget["parameters"]["content"]:
            if "attributes" in item:
                item["attributes"]["size"] = size
                item["attributes"]["color"] = color
    
    return widget


# ---------------------------------------------------------------------------
# Layout Pattern Builders
# ---------------------------------------------------------------------------

def build_f_layout_pattern(
    column_count: int,
    metrics: List[str],
    visualizations: List[str],
    filters: List[Any],  # List[FilterDef] - avoiding circular import
    title_text: str,
    sdm_name: str,
    validate: bool = True,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Build F-layout pattern: metrics in left sidebar, visualizations in F-pattern.
    
    Uses EXACT template positions from F_layout.json for deterministic alignment.
    
    Layout slots (exact template positions):
    - Filters: 6 slots (row 1)
      * Columns: 1, 13, 25, 37, 49, 61 (colspan 11/10)
    - Metrics: 3 slots (left sidebar, column 1)
      * Rows: 8, 29, 50 (colspan 22, rowspan 19 each)
    - Visualizations: 5 slots
      * Slot 1: Large top-right (column 24, row 14, colspan 47, rowspan 55)
      * Slots 2-4: 3 small visualizations (columns 1, 25, 49, row 87, colspan 23/22, rowspan 37)
      * Slot 5: Large bottom (column 2, row 128, colspan 68, rowspan 53)
    
    Requirements:
    - Filters: 6 recommended (uses first 6 positions if fewer provided)
    - Metrics: 3 recommended (uses first 3 positions if fewer provided)
    - Visualizations: 5 recommended (uses first 5 positions if fewer provided)
    
    Args:
        column_count: Total columns (typically 72)
        metrics: List of metric API names (recommended: 3)
        visualizations: List of visualization API names (recommended: 5)
        filters: List of filter definitions (recommended: 6)
        title_text: Dashboard title
        sdm_name: SDM API name for filters
        validate: If True, validate requirements and warn if not matching
        
    Returns:
        (widgets_dict, layout_widgets_list)
    """
    if validate:
        is_valid, warnings = validate_pattern_requirements(
            "f_layout", filters, metrics, visualizations
        )
        if warnings:
            for warning in warnings:
                print(f"Warning: {warning}", file=sys.stderr)
    widgets: Dict[str, Any] = {}
    layout_widgets: List[Dict[str, Any]] = []
    
    # Use EXACT template positions from F_layout.json
    # Filters: columns 1, 13, 25, 37, 49, 61 (row 1, colspan 11/10)
    FILTER_POSITIONS = [
        {"column": 1, "colspan": 11},
        {"column": 13, "colspan": 11},
        {"column": 25, "colspan": 11},
        {"column": 37, "colspan": 11},
        {"column": 49, "colspan": 11},
        {"column": 61, "colspan": 10},
    ]
    
    # Metrics: column 1, rows 8, 29, 50 (colspan 22, rowspan 19)
    METRIC_POSITIONS = [
        {"column": 1, "row": 8, "colspan": 22, "rowspan": 19},
        {"column": 1, "row": 29, "colspan": 22, "rowspan": 19},
        {"column": 1, "row": 50, "colspan": 22, "rowspan": 19},
    ]
    
    # Visualization positions from template
    # viz_1: column 24, row 14, colspan 47, rowspan 55
    # viz_2-4: columns 1, 26, 50, row 87, colspan 21-22, rowspan 37
    # viz_5: column 2, row 128, colspan 68, rowspan 53
    VIZ_POSITIONS = [
        {"column": 24, "row": 14, "colspan": 47, "rowspan": 55},  # Large top-right
        {"column": 1, "row": 87, "colspan": 23, "rowspan": 37},   # Small bottom-left
        {"column": 25, "row": 87, "colspan": 23, "rowspan": 37},  # Small bottom-middle
        {"column": 49, "row": 87, "colspan": 22, "rowspan": 37}, # Small bottom-right
        {"column": 2, "row": 128, "colspan": 68, "rowspan": 53},  # Large bottom
    ]
    
    # Title (row 0, column 1, colspan 25, rowspan 5) - not in template but we'll keep it
    title_key = "title"
    widgets[title_key] = {
        "actions": [],
        "name": title_key,
        "type": "text",
        "parameters": {
            "content": [
                {"attributes": {"color": "#042339", "size": "42px"}, "insert": title_text},
                {"attributes": {"align": "left"}, "insert": "\n"},
            ],
            "widgetStyle": {"backgroundColor": "#f3f3f3", "borderColor": "#f3f3f3", "borderEdges": ["all"]},
        },
    }
    layout_widgets.append({"name": title_key, "column": 1, "row": 0, "colspan": 25, "rowspan": 5})
    
    # Filters at top - use exact template positions
    filter_keys: List[str] = []
    if filters:
        filters = deduplicate_filter_defs(filters)
        # Use first N filter positions from template
        for i, fd in enumerate(filters[:6]):  # Max 6 filters
            fkey = f"filter_{i + 1}"
            filter_keys.append(fkey)
            pos = FILTER_POSITIONS[i]
            widgets[fkey] = apply_filter_style({
                "actions": [],
                "name": fkey,
                "type": "filter",
                "label": fd.label or fd.field_name,
                "source": {"name": sdm_name},
                "parameters": {
                    "filterOption": {
                        "dataType": fd.data_type,
                        "fieldName": fd.field_name,
                        "objectName": fd.object_name,
                        "selectionType": fd.selection_type,
                    },
                    "isLabelHidden": False,
                    "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                    "viewType": "list",
                    "widgetStyle": {},
                },
            })
            layout_widgets.append({
                "name": fkey,
                "column": pos["column"],
                "row": 1,  # Template uses row 1
                "colspan": pos["colspan"],
                "rowspan": 5,  # Template uses rowspan 5
            })
    
    # Metrics in left sidebar - use exact template positions
    for i, metric_name in enumerate(metrics[:3]):  # Max 3 metrics
        mkey = f"metric_{i + 1}"
        pos = METRIC_POSITIONS[i]
        widgets[mkey] = apply_metric_style({
            "actions": [],
            "name": mkey,
            "type": "metric",
            "source": {"name": metric_name},
            "parameters": {
                "metricOption": {
                    "sdmApiName": sdm_name,
                    "layout": {
                        "componentVisibility": {
                            "details": True,
                            "title": True,
                            "value": True,
                            "comparison": True,
                            "chart": i == 0,  # First metric shows chart
                            "insights": i == 0,
                        }
                    }
                },
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                "widgetStyle": {},
            },
        })
        layout_widgets.append({
            "name": mkey,
            "column": pos["column"],
            "row": pos["row"],
            "colspan": pos["colspan"],
            "rowspan": pos["rowspan"],
        })
    
    # Containers and text headers from template (must be added before visualizations)
    # Container 1 wraps visualization_1
    if len(visualizations) > 0:
        container1_key = "container_1"
        widgets[container1_key] = apply_container_style({
            "actions": [],
            "name": container1_key,
            "type": "container",
            "parameters": {"widgetStyle": {}},
        })
        layout_widgets.append({
            "name": container1_key,
            "column": 24,
            "row": 8,
            "colspan": 47,
            "rowspan": 61,
        })
        
        # Text header above visualization_1
        text1_key = "text_1"
        widgets[text1_key] = apply_text_header_style({
            "actions": [],
            "name": text1_key,
            "type": "text",
            "parameters": {
                "content": [
                    {"attributes": {"color": "#03234d", "size": "20px"}, "insert": ""},
                    {"attributes": {"align": "left"}, "insert": "\n"},
                ],
                "widgetStyle": {},
            },
        })
        layout_widgets.append({
            "name": text1_key,
            "column": 25,
            "row": 9,
            "colspan": 45,
            "rowspan": 5,
        })
    
    # Section divider text (text_2) - between metrics and bottom visualizations
    if len(visualizations) > 1:
        text2_key = "text_2"
        widgets[text2_key] = apply_text_header_style({
            "actions": [],
            "name": text2_key,
            "type": "text",
            "parameters": {
                "content": [
                    {"attributes": {"color": "#03234d", "size": "20px"}, "insert": ""},
                    {"attributes": {"align": "left"}, "insert": "\n"},
                ],
                "widgetStyle": {},
            },
        })
        layout_widgets.append({
            "name": text2_key,
            "column": 1,
            "row": 73,
            "colspan": 70,
            "rowspan": 6,
        })
    
    # Containers 2-4 wrap visualizations 2-4
    if len(visualizations) > 1:
        for i in range(1, min(4, len(visualizations))):
            container_key = f"container_{i + 1}"
            container_positions = [
                {"column": 1, "row": 83, "colspan": 23, "rowspan": 41},
                {"column": 25, "row": 83, "colspan": 23, "rowspan": 41},
                {"column": 49, "row": 83, "colspan": 22, "rowspan": 41},
            ]
            pos = container_positions[i - 1]
            widgets[container_key] = apply_container_style({
                "actions": [],
                "name": container_key,
                "type": "container",
                "parameters": {"widgetStyle": {}},
            })
            layout_widgets.append({
                "name": container_key,
                "column": pos["column"],
                "row": pos["row"],
                "colspan": pos["colspan"],
                "rowspan": pos["rowspan"],
            })
            
            # Text headers above small visualizations
            text_keys = ["text_6", "text_7", "text_8"]
            text_positions = [
                {"column": 2, "row": 84, "colspan": 22, "rowspan": 3},
                {"column": 26, "row": 84, "colspan": 21, "rowspan": 3},
                {"column": 50, "row": 84, "colspan": 20, "rowspan": 3},
            ]
            text_key = text_keys[i - 1]
            text_pos = text_positions[i - 1]
            widgets[text_key] = apply_text_header_style({
                "actions": [],
                "name": text_key,
                "type": "text",
                "parameters": {
                    "content": [
                        {"attributes": {"color": "#03234d", "size": "20px"}, "insert": ""},
                        {"attributes": {"align": "left"}, "insert": "\n"},
                    ],
                    "widgetStyle": {},
                },
            })
            layout_widgets.append({
                "name": text_key,
                "column": text_pos["column"],
                "row": text_pos["row"],
                "colspan": text_pos["colspan"],
                "rowspan": text_pos["rowspan"],
            })
    
    # Container 5 wraps visualization_5
    if len(visualizations) > 4:
        container5_key = "container_5"
        widgets[container5_key] = apply_container_style({
            "actions": [],
            "name": container5_key,
            "type": "container",
            "parameters": {"widgetStyle": {}},
        })
        layout_widgets.append({
            "name": container5_key,
            "column": 2,
            "row": 126,
            "colspan": 68,
            "rowspan": 57,
        })
    
    # Visualizations in F-pattern - use exact template positions
    for i, viz_name in enumerate(visualizations[:5]):  # Max 5 visualizations
        viz_key = f"visualization_{i + 1}"
        pos = VIZ_POSITIONS[i]
        
        # Determine legend position based on viz position
        if i == 0:
            legend_pos = "Bottom"
        elif i < 4:
            legend_pos = "Top" if i == 1 else "Right"
        else:
            legend_pos = "Right"
        
        widgets[viz_key] = apply_viz_style({
            "actions": [],
            "name": viz_key,
            "type": "visualization",
            "source": {"name": viz_name},
            "parameters": {
                "legendPosition": legend_pos,
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                "widgetStyle": {},
            },
        })
        layout_widgets.append({
            "name": viz_key,
            "column": pos["column"],
            "row": pos["row"],
            "colspan": pos["colspan"],
            "rowspan": pos["rowspan"],
        })
    
    return widgets, layout_widgets


def build_z_layout_pattern(
    column_count: int,
    metrics: List[str],
    visualizations: List[str],
    filters: List[Any],  # List[FilterDef] - avoiding circular import
    title_text: str,
    sdm_name: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Build Z-layout pattern: metrics in top row, visualizations in Z-pattern.
    
    Layout:
    - Row 0-5: Filters (top row)
    - Row 6-24: Metrics in top row (horizontal, 3-4 metrics)
    - Row 25+: Visualizations in Z-pattern (large top-left, smaller forming Z)
    
    Args:
        column_count: Total columns (typically 72)
        metrics: List of metric API names
        visualizations: List of visualization API names
        filters: List of filter definitions
        title_text: Dashboard title
        sdm_name: SDM API name for filters
        
    Returns:
        (widgets_dict, layout_widgets_list)
    """
    widgets: Dict[str, Any] = {}
    layout_widgets: List[Dict[str, Any]] = []
    row = 0
    
    # Filters at top
    filter_keys: List[str] = []
    if filters:
        # Deduplicate filters to prevent using the same field twice
        filters = deduplicate_filter_defs(filters)
        filter_width = (column_count - 2) // len(filters) if filters else 1
        for i, fd in enumerate(filters):
            fkey = f"filter_{i + 1}"
            filter_keys.append(fkey)
            widgets[fkey] = apply_filter_style({
                "actions": [],
                "name": fkey,
                "type": "filter",
                "label": fd.label or fd.field_name,
                "source": {"name": sdm_name},
                "parameters": {
                    "filterOption": {
                        "dataType": fd.data_type,
                        "fieldName": fd.field_name,
                        "objectName": fd.object_name,
                        "selectionType": fd.selection_type,
                    },
                    "isLabelHidden": False,
                    "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                    "viewType": "list",
                    "widgetStyle": {},
                },
            })
            layout_widgets.append({
                "name": fkey,
                "column": 1 + i * filter_width,
                "row": row,
                "colspan": filter_width,
                "rowspan": 5,
            })
        row += 5
    
    # Metrics in top row
    metric_keys: List[str] = []
    if metrics:
        metric_width = (column_count - 2) // len(metrics) if metrics else 1
        metric_row = row
        for i, metric_name in enumerate(metrics):
            mkey = f"metric_{i + 1}"
            metric_keys.append(mkey)
            widgets[mkey] = apply_metric_style({
                "actions": [],
                "name": mkey,
                "type": "metric",
                "source": {"name": metric_name},
                "parameters": {
                    "metricOption": {
                        "sdmApiName": sdm_name,
                        "layout": {
                            "componentVisibility": {
                                "details": True,
                                "title": True,
                                "value": True,
                                "comparison": True,
                                "chart": False,
                                "insights": True,
                            }
                        }
                    },
                    "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                    "widgetStyle": {},
                },
            })
            layout_widgets.append({
                "name": mkey,
                "column": 1 + i * metric_width,
                "row": metric_row,
                "colspan": metric_width,
                "rowspan": 19,
            })
        row += 19
    
    # Title/header
    title_key = "text_title"
    widgets[title_key] = apply_text_header_style({
        "actions": [],
        "name": title_key,
        "type": "text",
        "parameters": {
            "content": [
                {"attributes": {"size": "20px"}, "insert": title_text},
                {"insert": "\n"},
                {"attributes": {"color": "#5c5c5c", "size": "14px"}, "insert": "Section Subheader"},
                {"attributes": {"align": "left"}, "insert": "\n"},
            ],
            "widgetStyle": {"borderColor": "#C9C9C9", "borderEdges": []},
        },
    })
    layout_widgets.append({
        "name": title_key,
        "column": 1,
        "row": row,
        "colspan": 45,
        "rowspan": 5,
    })
    row += 5
    
    # Container for visualizations
    container_key = "container_viz"
    widgets[container_key] = apply_container_style({
        "actions": [],
        "name": container_key,
        "type": "container",
        "parameters": {"widgetStyle": {}},
    })
    layout_widgets.append({
        "name": container_key,
        "column": 1,
        "row": row,
        "colspan": 70,
        "rowspan": 47,
    })
    
    # Large visualization top-left
    viz_row = row + 1
    if visualizations:
        viz1_key = "visualization_1"
        widgets[viz1_key] = apply_viz_style({
            "actions": [],
            "name": viz1_key,
            "type": "visualization",
            "source": {"name": visualizations[0]},
            "parameters": {
                "legendPosition": "Bottom",
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                "widgetStyle": {},
            },
        })
        layout_widgets.append({
            "name": viz1_key,
            "column": 2,
            "row": viz_row,
            "colspan": 70,
            "rowspan": 41,
        })
    
    # Section header for details
    section_row = viz_row + 42
    section_key = "text_section"
    widgets[section_key] = apply_text_header_style({
        "actions": [],
        "name": section_key,
        "type": "text",
        "parameters": {
            "content": [
                {"attributes": {"color": "#03234d", "size": "24px"}, "insert": "Details"},
                {"insert": "\n"},
                {"attributes": {"color": "#2e2e2e", "size": "16px"}, "insert": "Section Subheader"},
                {"attributes": {"align": "left"}, "insert": "\n"},
            ],
            "widgetStyle": {"backgroundColor": "#f3f3f3", "borderEdges": []},
        },
    })
    layout_widgets.append({
        "name": section_key,
        "column": 2,
        "row": section_row,
        "colspan": 70,
        "rowspan": 6,
    })
    
    # Smaller visualizations in Z-pattern
    small_viz_row = section_row + 6
    small_viz_width = 23
    small_viz_height = 37
    
    for i, viz_name in enumerate(visualizations[1:4]):  # Max 3 small vizzes
        viz_key = f"visualization_{i + 2}"
        widgets[viz_key] = apply_viz_style({
            "actions": [],
            "name": viz_key,
            "type": "visualization",
            "source": {"name": viz_name},
            "parameters": {
                "legendPosition": "Top" if i == 0 else "Right",
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                "widgetStyle": {},
            },
        })
        layout_widgets.append({
            "name": viz_key,
            "column": 1 + i * 24,
            "row": small_viz_row,
            "colspan": small_viz_width,
            "rowspan": small_viz_height,
        })
    
    # Large visualization at bottom
    if len(visualizations) > 4:
        viz_bottom_key = "visualization_5"
        widgets[viz_bottom_key] = apply_viz_style({
            "actions": [],
            "name": viz_bottom_key,
            "type": "visualization",
            "source": {"name": visualizations[4]},
            "parameters": {
                "legendPosition": "Right",
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                "widgetStyle": {},
            },
        })
        layout_widgets.append({
            "name": viz_bottom_key,
            "column": 2,
            "row": small_viz_row + small_viz_height + 1,
            "colspan": 68,
            "rowspan": 53,
        })
    
    return widgets, layout_widgets


def build_performance_overview_pattern(
    column_count: int,
    primary_metric: str,
    secondary_metrics: List[str],
    visualizations: List[str],
    filters: List[Any],  # List[FilterDef] - avoiding circular import
    pages: List[Any],  # List[PageDef] - avoiding circular import
    sdm_name: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Build performance overview pattern: large metric left, smaller metrics right, time navigation.
    
    Layout per page:
    - Row 0-4: Title and time period filters
    - Row 5-9: Time period navigation buttons (Week/Month/Day)
    - Row 10-28: Large metric on left (24 cols), smaller metrics on right (21 cols each)
    - Row 29+: Visualizations in containers with section headers
    
    Args:
        column_count: Total columns (typically 72)
        primary_metric: Primary metric API name (large, left side)
        secondary_metrics: List of secondary metric API names (smaller, right side)
        visualizations: List of visualization API names
        filters: List of filter definitions
        pages: List of page definitions (typically time periods)
        sdm_name: SDM API name for filters
        
    Returns:
        (widgets_dict, pages_list_with_layout_widgets)
    """
    widgets: Dict[str, Any] = {}
    all_pages: List[Dict[str, Any]] = []
    
    # Build time period navigation buttons
    nav_button_keys: List[str] = []
    for pi, pg in enumerate(pages):
        bkey = f"button_{pi + 1}"
        nav_button_keys.append(bkey)
        widgets[bkey] = apply_button_style({
            "actions": [{
                "actionType": "navigate",
                "eventType": "click",
                "parameters": {
                    "destination": {"target": pg.name, "type": "page"},
                },
            }],
            "name": bkey,
            "type": "button",
            "parameters": {
                "text": pg.label,
                "alignmentX": "center",
                "alignmentY": "center",
                "fontSize": 16,
                "widgetStyle": {},
            },
        }, is_active=(pi == 0))
    
    # Build filters
    # Deduplicate filters to prevent using the same field twice
    filters = deduplicate_filter_defs(filters)
    filter_keys: List[str] = []
    for i, fd in enumerate(filters):
        fkey = f"list_{i + 3}"  # Match template naming
        filter_keys.append(fkey)
        widgets[fkey] = apply_filter_style({
            "actions": [],
            "name": fkey,
            "type": "filter",
            "label": fd.label or fd.field_name,
            "source": {"name": sdm_name},
            "parameters": {
                "filterOption": {
                    "dataType": fd.data_type,
                    "fieldName": fd.field_name,
                    "objectName": fd.object_name,
                    "selectionType": fd.selection_type,
                },
                "isLabelHidden": False,
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                "viewType": "list",
                "widgetStyle": {},
            },
        })
    
    # Build pages
    for pi, pg in enumerate(pages):
        page_widgets: List[Dict[str, Any]] = []
        row = 0
        
        # Title
        title_key = f"text_1_{pi + 1}"
        widgets[title_key] = apply_text_header_style({
            "actions": [],
            "name": title_key,
            "type": "text",
            "parameters": {
                "content": [
                    {"attributes": {"color": "#042339", "size": "42px"}, "insert": "Dashboard Name"},
                    {"attributes": {"align": "left"}, "insert": "\n"},
                ],
                "widgetStyle": {"backgroundColor": "#f3f3f3", "borderColor": "#f3f3f3", "borderEdges": ["all"]},
            },
        })
        page_widgets.append({
            "name": title_key,
            "column": 1,
            "row": row,
            "colspan": 25,
            "rowspan": 5,
        })
        
        # Filters
        if filter_keys:
            for i, fk in enumerate(filter_keys):
                page_widgets.append({
                    "name": fk,
                    "column": 33 + i * 12,
                    "row": row,
                    "colspan": 12,
                    "rowspan": 4,
                })
        row += 5
        
        # Time period navigation buttons
        if len(pages) > 1:
            btn_col = 57
            btn_width = 4
            for i, bk in enumerate(nav_button_keys):
                page_widgets.append({
                    "name": bk,
                    "column": btn_col + i * 4,
                    "row": row,
                    "colspan": btn_width,
                    "rowspan": 2,
                })
            row += 2
        
        # Container for metrics section
        container_key = f"container_1_{pi + 1}"
        widgets[container_key] = apply_container_style({
            "actions": [],
            "name": container_key,
            "type": "container",
            "parameters": {"widgetStyle": {"borderRadius": 16}},
        })
        page_widgets.append({
            "name": container_key,
            "column": 1,
            "row": row,
            "colspan": 70,
            "rowspan": 47,
        })
        
        # Section header
        section_key = f"text_3_{pi + 1}"
        widgets[section_key] = apply_text_header_style({
            "actions": [],
            "name": section_key,
            "type": "text",
            "parameters": {
                "content": [
                    {"attributes": {"color": "#03234d", "size": "20px"}, "insert": "Section Header"},
                    {"attributes": {"align": "left"}, "insert": "\n"},
                ],
                "widgetStyle": {},
            },
        })
        page_widgets.append({
            "name": section_key,
            "column": 2,
            "row": row + 1,
            "colspan": 15,
            "rowspan": 2,
        })
        
        # Primary metric (large, left)
        metric_row = row + 3
        primary_key = f"metric_1_{pi + 1}"
        widgets[primary_key] = apply_metric_style({
            "actions": [],
            "name": primary_key,
            "type": "metric",
            "source": {"name": primary_metric},
            "parameters": {
                "metricOption": {
                    "sdmApiName": sdm_name,
                    "layout": {
                        "componentVisibility": {
                            "details": True,
                            "title": True,
                            "value": True,
                            "comparison": True,
                            "chart": True,
                            "insights": False,
                        }
                    }
                },
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                "widgetStyle": {},
            },
        })
        page_widgets.append({
            "name": primary_key,
            "column": 2,
            "row": metric_row,
            "colspan": 24,
            "rowspan": 19,
        })
        
        # Secondary metrics (smaller, right)
        for i, metric_name in enumerate(secondary_metrics[:4]):  # Max 4 secondary metrics
            mkey = f"metric_{i + 2}_{pi + 1}"
            widgets[mkey] = apply_metric_style({
                "actions": [],
                "name": mkey,
                "type": "metric",
                "source": {"name": metric_name},
                "parameters": {
                    "metricOption": {
                        "sdmApiName": sdm_name,
                        "layout": {
                            "componentVisibility": {
                                "details": True,
                                "title": True,
                                "value": True,
                                "comparison": True,
                                "chart": False,
                                "insights": False,
                            }
                        }
                    },
                    "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                    "widgetStyle": {},
                },
            })
            # Arrange in 2x2 grid on right
            col_offset = 27 if i < 2 else 49
            row_offset = 0 if i % 2 == 0 else 10
            page_widgets.append({
                "name": mkey,
                "column": col_offset,
                "row": metric_row + row_offset,
                "colspan": 21,
                "rowspan": 9,
            })
        
        # Visualizations in containers
        viz_start_row = metric_row + 22
        if visualizations:
            # First visualization (larger)
            viz1_key = f"visualization_1_{pi + 1}"
            widgets[viz1_key] = apply_viz_style({
                "actions": [],
                "name": viz1_key,
                "type": "visualization",
                "source": {"name": visualizations[0] if visualizations else ""},
                "parameters": {
                    "legendPosition": "Bottom",
                    "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                    "widgetStyle": {},
                },
            })
            page_widgets.append({
                "name": viz1_key,
                "column": 2,
                "row": viz_start_row,
                "colspan": 24,
                "rowspan": 20,
            })
            
            # Second visualization (right side)
            if len(visualizations) > 1:
                viz2_key = f"visualization_4_{pi + 1}"
                widgets[viz2_key] = apply_viz_style({
                    "actions": [],
                    "name": viz2_key,
                    "type": "visualization",
                    "source": {"name": visualizations[1]},
                    "parameters": {
                        "legendPosition": "Bottom",
                        "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                        "widgetStyle": {},
                    },
                })
                page_widgets.append({
                    "name": viz2_key,
                    "column": 27,
                    "row": viz_start_row,
                    "colspan": 43,
                    "rowspan": 20,
                })
        
        # Bottom section container
        bottom_row = viz_start_row + 22
        container2_key = f"container_2_{pi + 1}"
        widgets[container2_key] = apply_container_style({
            "actions": [],
            "name": container2_key,
            "type": "container",
            "parameters": {"widgetStyle": {"borderRadius": 16}},
        })
        page_widgets.append({
            "name": container2_key,
            "column": 1,
            "row": bottom_row,
            "colspan": 70,
            "rowspan": 29,
        })
        
        # Section header for bottom
        section2_key = f"text_5_{pi + 1}"
        widgets[section2_key] = apply_text_header_style({
            "actions": [],
            "name": section2_key,
            "type": "text",
            "parameters": {
                "content": [
                    {"attributes": {"color": "#03234d", "size": "20px"}, "insert": "Section Header"},
                    {"attributes": {"align": "left"}, "insert": "\n"},
                ],
                "widgetStyle": {},
            },
        })
        page_widgets.append({
            "name": section2_key,
            "column": 2,
            "row": bottom_row + 1,
            "colspan": 15,
            "rowspan": 2,
        })
        
        # Large visualization at bottom
        if len(visualizations) > 2:
            viz3_key = f"visualization_3_{pi + 1}"
            widgets[viz3_key] = apply_viz_style({
                "actions": [],
                "name": viz3_key,
                "type": "visualization",
                "source": {"name": visualizations[2]},
                "parameters": {
                    "legendPosition": "Right",
                    "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                    "widgetStyle": {},
                },
            })
            page_widgets.append({
                "name": viz3_key,
                "column": 2,
                "row": bottom_row + 4,
                "colspan": 68,
                "rowspan": 24,
            })
        
        all_pages.append({
            "name": pg.name,
            "label": pg.label,
            "widgets": page_widgets,
        })
    
    return widgets, all_pages


# ---------------------------------------------------------------------------
# Pattern Validation
# ---------------------------------------------------------------------------

def validate_pattern_output(
    widgets: Dict[str, Any],
    pages: List[Dict[str, Any]],
    column_count: int = 72
) -> Tuple[bool, List[str]]:
    """Validate pattern output structure.
    
    Checks:
    - Widget source references use only 'name' (not 'id', 'label', 'type')
    - Layout grid constraints (column + colspan ≤ column_count)
    - Required widget structure
    - Widget names match layout references
    
    Args:
        widgets: Widget definitions dict
        pages: List of page definitions with widgets
        column_count: Total columns in grid
        
    Returns:
        (is_valid: bool, list_of_errors: List[str])
    """
    errors = []
    
    # Collect all widget names from layout
    layout_widget_names = set()
    for page in pages:
        for widget_layout in page.get("widgets", []):
            widget_name = widget_layout.get("name")
            if widget_name:
                layout_widget_names.add(widget_name)
    
    # Validate widgets
    for widget_key, widget in widgets.items():
        if not isinstance(widget, dict):
            errors.append(f"Widget '{widget_key}' is not a dict")
            continue
        
        # Check widget has 'name' field matching key
        widget_name = widget.get("name")
        if widget_name != widget_key:
            errors.append(f"Widget '{widget_key}': name field '{widget_name}' doesn't match key")
        
        # Check widget source structure
        if "source" in widget:
            source = widget["source"]
            if not isinstance(source, dict):
                errors.append(f"Widget '{widget_key}': source is not a dict")
            else:
                # Source should only have "name", not "id", "label", "type"
                invalid_keys = ["id", "label", "type"]
                for key in invalid_keys:
                    if key in source:
                        errors.append(
                            f"Widget '{widget_key}': source contains invalid key '{key}' "
                            f"(should only have 'name' field)"
                        )
                
                # Source must have "name"
                if "name" not in source:
                    errors.append(f"Widget '{widget_key}': source missing required 'name' field")
        
        # Check widget type is valid
        widget_type = widget.get("type")
        valid_types = ["visualization", "metric", "filter", "text", "button", "container"]
        if widget_type and widget_type not in valid_types:
            errors.append(f"Widget '{widget_key}': invalid type '{widget_type}' (valid: {', '.join(valid_types)})")
    
    # Validate layout grid constraints
    for page_idx, page in enumerate(pages):
        widgets_list = page.get("widgets", [])
        for widget_layout in widgets_list:
            widget_name = widget_layout.get("name")
            col = widget_layout.get("column", 0)
            colspan = widget_layout.get("colspan", 0)
            row = widget_layout.get("row", 0)
            rowspan = widget_layout.get("rowspan", 0)
            
            # Check widget is referenced in widgets dict
            if widget_name and widget_name not in widgets:
                errors.append(
                    f"Page {page_idx}: Widget '{widget_name}' referenced in layout but not in widgets dict"
                )
            
            # Check grid bounds
            if col < 0:
                errors.append(f"Page {page_idx}: Widget '{widget_name}' has negative column ({col})")
            if colspan < 1:
                errors.append(f"Page {page_idx}: Widget '{widget_name}' has invalid colspan ({colspan})")
            if col + colspan > column_count:
                errors.append(
                    f"Page {page_idx}: Widget '{widget_name}' exceeds grid bounds "
                    f"(column {col} + colspan {colspan} > {column_count})"
                )
            if row < 0:
                errors.append(f"Page {page_idx}: Widget '{widget_name}' has negative row ({row})")
            if rowspan < 1:
                errors.append(f"Page {page_idx}: Widget '{widget_name}' has invalid rowspan ({rowspan})")
    
    # Check all widgets in layout are defined
    for widget_name in layout_widget_names:
        if widget_name not in widgets:
            errors.append(f"Widget '{widget_name}' referenced in layout but not defined in widgets dict")
    
    return len(errors) == 0, errors
