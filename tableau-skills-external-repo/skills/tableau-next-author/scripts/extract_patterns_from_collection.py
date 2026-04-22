#!/usr/bin/env python3
"""Extract learning patterns from real dashboard collection.

Analyzes 26+ dashboard packages to extract:
- Chart type usage patterns
- Field combinations
- Dashboard layout patterns
- Filter selections
- Naming patterns
- Field usage frequency
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Collection directory
COLLECTION_DIR = Path.home() / ".cursor" / "skills" / "tableau-next-author" / ".cursor" / "tabnext-tools-main" / "collection"
OUTPUT_DIR = COLLECTION_DIR / "training_data"
OUTPUT_FILE = OUTPUT_DIR / "patterns.json"


def infer_chart_type(viz_json: Dict[str, Any]) -> str:
    """Infer template name from visualization structure.
    
    Args:
        viz_json: Visualization JSON dict
        
    Returns:
        Template name (e.g., "revenue_by_category", "trend_over_time")
    """
    vspec = viz_json.get("visualSpecification", {})
    marks = vspec.get("marks", {})
    panes = marks.get("panes", {})
    
    if not panes:
        return "unknown"
    
    # Panes can be dict or list - handle both
    if isinstance(panes, dict):
        pane_type = panes.get("type", "")
        encodings = panes.get("encodings", [])
    elif isinstance(panes, list) and panes:
        pane_type = panes[0].get("type", "")
        encodings = panes[0].get("encodings", [])
    else:
        return "unknown"
    
    # Check layout type (for tables)
    layout = vspec.get("layout", {})
    if isinstance(layout, dict) and layout.get("type") == "Table":
        return "top_n_leaderboard"
    
    # Map pane types to templates
    if pane_type == "Donut":
        return "market_share_donut"
    elif pane_type == "Bar":
        # Check for stacked bar (Color encoding)
        has_color = any(e.get("type") == "Color" for e in encodings)
        if has_color:
            return "stacked_bar_by_dimension"
        else:
            return "revenue_by_category"
    elif pane_type == "Line":
        # Check for multi-series (Color encoding)
        has_color = any(e.get("type") == "Color" for e in encodings)
        if has_color:
            return "multi_series_line"
        else:
            return "trend_over_time"
    elif pane_type == "Circle":
        # Could be scatter plot or table
        if isinstance(layout, dict) and layout.get("type") == "Table":
            return "top_n_leaderboard"
        else:
            return "scatter_correlation"
    elif pane_type == "Funnel":
        return "conversion_funnel"
    else:
        return "unknown"


def extract_fields_from_viz(viz_json: Dict[str, Any]) -> Dict[str, str]:
    """Extract field mappings from visualization.
    
    Args:
        viz_json: Visualization JSON dict
        
    Returns:
        Dict mapping field roles to field names (e.g., {"category": "Region", "amount": "Amount_USD"})
    """
    fields = {}
    
    vspec = viz_json.get("visualSpecification", {})
    marks = vspec.get("marks", {})
    panes = marks.get("panes", {})
    
    if not panes:
        return fields
    
    # Get encodings
    if isinstance(panes, dict):
        encodings = panes.get("encodings", [])
    elif isinstance(panes, list) and panes:
        encodings = panes[0].get("encodings", [])
    else:
        return fields
    
    # Extract fields from encodings
    for encoding in encodings:
        encoding_type = encoding.get("type", "")
        field_obj = encoding.get("field", {})
        field_name = field_obj.get("name", "")
        
        if not field_name:
            continue
        
        # Map encoding types to field roles
        if encoding_type == "Label":
            fields["measure"] = field_name
        elif encoding_type == "Color":
            fields["color_dim"] = field_name
        elif encoding_type == "Detail":
            fields["category"] = field_name
        elif encoding_type == "Angle":
            if "measure" not in fields:
                fields["measure"] = field_name
        elif encoding_type == "Size":
            if "measure" not in fields:
                fields["measure"] = field_name
    
    # Also check columns/rows for dimensions
    columns = vspec.get("columns", [])
    rows = vspec.get("rows", [])
    
    for col in columns:
        if isinstance(col, dict):
            field_obj = col.get("field", {})
            if isinstance(field_obj, dict):
                field_name = field_obj.get("name", "")
                if field_name and "category" not in fields:
                    fields["category"] = field_name
    
    for row in rows:
        if isinstance(row, dict):
            field_obj = row.get("field", {})
            if isinstance(field_obj, dict):
                field_name = field_obj.get("name", "")
                if field_name and "measure" not in fields:
                    fields["measure"] = field_name
    
    return fields


def infer_dashboard_pattern(dashboard_json: Dict[str, Any]) -> str:
    """Infer dashboard pattern from widget structure.
    
    Args:
        dashboard_json: Dashboard JSON dict
        
    Returns:
        Pattern name (e.g., "f_layout", "z_layout")
    """
    widgets = dashboard_json.get("widgets", {})
    
    # Count widget types
    metric_count = sum(1 for w in widgets.values() if w.get("type") == "metric")
    viz_count = sum(1 for w in widgets.values() if w.get("type") == "visualization")
    filter_count = sum(1 for w in widgets.values() if w.get("type") == "filter")
    
    # Infer pattern based on counts
    if metric_count >= 3 and viz_count >= 5:
        return "f_layout"
    elif metric_count >= 6 and viz_count >= 5:
        return "z_layout"
    elif metric_count >= 4 and viz_count == 0:
        return "unknown"
    elif metric_count >= 3 and viz_count >= 2:
        return "unknown"
    elif metric_count == 5 and viz_count == 5:
        return "performance_overview"
    else:
        return "unknown"


def analyze_naming_pattern(name: str, label: Optional[str] = None) -> str:
    """Analyze naming pattern (business-friendly vs technical).
    
    Args:
        name: Visualization API name
        label: Visualization display label (optional)
        
    Returns:
        Pattern classification: "business_friendly", "technical", or "generic"
    """
    if not name:
        return "generic"
    
    # Check for technical suffixes
    if any(suffix in name for suffix in ["_Clc", "_mtc", "_MTC", "_CLC", "_clc"]):
        return "technical"
    
    # Check for generic names
    if name.startswith("Viz_") or name.startswith("Trend_") or name.startswith("Chart_") or name.startswith("Whitespace"):
        return "generic"
    
    # Check if name is descriptive (has multiple words separated by underscores)
    parts = name.split("_")
    if len(parts) >= 2:
        return "business_friendly"
    
    return "generic"


def extract_industry_from_filename(filename: str) -> str:
    """Extract industry/domain from filename.
    
    Args:
        filename: Package filename
        
    Returns:
        Industry name (e.g., "Sales", "Marketing", "HR")
    """
    filename_lower = filename.lower()
    
    if "sales" in filename_lower:
        return "Sales"
    elif "marketing" in filename_lower:
        return "Marketing"
    elif "service" in filename_lower:
        return "Service"
    elif "hr" in filename_lower or "workforce" in filename_lower:
        return "HR"
    elif "clinical" in filename_lower or "provider" in filename_lower:
        return "Healthcare"
    elif "manufacturing" in filename_lower or "mfg" in filename_lower or "production" in filename_lower:
        return "Manufacturing"
    elif "hotel" in filename_lower:
        return "Hospitality"
    elif "kam" in filename_lower:
        return "Key Account Management"
    else:
        return "Other"


def extract_patterns_from_package(package_file: Path) -> Dict[str, Any]:
    """Extract patterns from a single package file.
    
    Args:
        package_file: Path to package JSON file
        
    Returns:
        Dict with extracted patterns
    """
    patterns = {
        "package_name": package_file.stem,
        "industry": extract_industry_from_filename(package_file.name),
        "visualizations": [],
        "dashboard_pattern": None,
        "filters": [],
        "fields_used": set(),
    }
    
    try:
        with open(package_file, 'r') as f:
            package = json.load(f)
    except Exception as e:
        print(f"Error reading {package_file.name}: {e}")
        return patterns
    
    components = package.get("components", {})
    
    # Extract visualization patterns
    viz_dict = components.get("visualizations", {})
    for viz_name, viz_json in viz_dict.items():
        chart_type = infer_chart_type(viz_json)
        fields = extract_fields_from_viz(viz_json)
        label = viz_json.get("label", "")
        naming_pattern = analyze_naming_pattern(viz_name, label)
        
        patterns["visualizations"].append({
            "name": viz_name,
            "label": label,
            "template": chart_type,
            "fields": fields,
            "naming_pattern": naming_pattern,
        })
        
        # Track fields used
        for field_name in fields.values():
            if field_name:
                patterns["fields_used"].add(field_name)
    
    # Extract dashboard pattern
    dashboard = components.get("dashboard", {})
    if dashboard:
        patterns["dashboard_pattern"] = infer_dashboard_pattern(dashboard)
        
        # Extract filters
        widgets = dashboard.get("widgets", {})
        for widget_id, widget in widgets.items():
            if widget.get("type") == "filter":
                filter_params = widget.get("parameters", {}).get("filterOption", {})
                patterns["filters"].append({
                    "fieldName": filter_params.get("fieldName"),
                    "objectName": filter_params.get("objectName"),
                    "dataType": filter_params.get("dataType"),
                })
    
    # Convert set to list for JSON serialization
    patterns["fields_used"] = list(patterns["fields_used"])
    
    return patterns


def aggregate_statistics(all_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate statistics from all extracted patterns.
    
    Args:
        all_patterns: List of pattern dicts from all packages
        
    Returns:
        Aggregated statistics dict
    """
    stats = {
        "chart_type_usage": defaultdict(int),
        "field_combinations": defaultdict(int),
        "dashboard_patterns": defaultdict(int),
        "common_dimensions": defaultdict(int),
        "common_measures": defaultdict(int),
        "filter_selections": defaultdict(int),
        "naming_patterns": defaultdict(int),
        "industry_distributions": defaultdict(lambda: {
            "chart_types": defaultdict(int),
            "common_fields": defaultdict(int),
        }),
        "total_packages": len(all_patterns),
        "total_visualizations": 0,
        "total_dashboards": 0,
    }
    
    for pkg_patterns in all_patterns:
        industry = pkg_patterns["industry"]
        
        # Count visualizations
        stats["total_visualizations"] += len(pkg_patterns["visualizations"])
        
        # Count dashboards
        if pkg_patterns["dashboard_pattern"]:
            stats["total_dashboards"] += 1
            stats["dashboard_patterns"][pkg_patterns["dashboard_pattern"]] += 1
        
        # Process visualizations
        for viz in pkg_patterns["visualizations"]:
            template = viz["template"]
            stats["chart_type_usage"][template] += 1
            stats["industry_distributions"][industry]["chart_types"][template] += 1
            
            # Track naming patterns
            stats["naming_patterns"][viz["naming_pattern"]] += 1
            
            # Track field combinations
            fields = viz["fields"]
            if fields:
                # Create a canonical representation of field combination
                field_combo_key = f"{template}:{json.dumps(fields, sort_keys=True)}"
                stats["field_combinations"][field_combo_key] += 1
                
                # Track individual fields
                for role, field_name in fields.items():
                    if role in ["category", "color_dim", "stack_dim"]:
                        stats["common_dimensions"][field_name] += 1
                        stats["industry_distributions"][industry]["common_fields"][field_name] += 1
                    elif role in ["measure", "amount"]:
                        stats["common_measures"][field_name] += 1
        
        # Process filters
        for filter_def in pkg_patterns["filters"]:
            field_name = filter_def.get("fieldName")
            if field_name:
                stats["filter_selections"][field_name] += 1
    
    # Convert to percentages and sort
    result = {
        "chart_type_usage": dict(sorted(stats["chart_type_usage"].items(), key=lambda x: x[1], reverse=True)),
        "dashboard_patterns": dict(sorted(stats["dashboard_patterns"].items(), key=lambda x: x[1], reverse=True)),
        "common_dimensions": {},
        "common_measures": {},
        "filter_selections": {},
        "naming_patterns": {},
        "industry_distributions": {},
        "total_packages": stats["total_packages"],
        "total_visualizations": stats["total_visualizations"],
        "total_dashboards": stats["total_dashboards"],
    }
    
    # Calculate frequencies for dimensions
    total_viz = stats["total_visualizations"]
    if total_viz > 0:
        for field_name, count in sorted(stats["common_dimensions"].items(), key=lambda x: x[1], reverse=True):
            result["common_dimensions"][field_name] = round(count / total_viz, 3)
        
        for field_name, count in sorted(stats["common_measures"].items(), key=lambda x: x[1], reverse=True):
            result["common_measures"][field_name] = round(count / total_viz, 3)
    
    # Calculate frequencies for filters
    total_dashboards = stats["total_dashboards"]
    if total_dashboards > 0:
        for field_name, count in sorted(stats["filter_selections"].items(), key=lambda x: x[1], reverse=True):
            result["filter_selections"][field_name] = round(count / total_dashboards, 3)
    
    # Calculate naming pattern frequencies
    total_naming = sum(stats["naming_patterns"].values())
    if total_naming > 0:
        for pattern, count in sorted(stats["naming_patterns"].items(), key=lambda x: x[1], reverse=True):
            result["naming_patterns"][pattern] = round(count / total_naming, 3)
    
    # Process industry distributions
    for industry, dist in stats["industry_distributions"].items():
        if dist["chart_types"]:
            total_charts = sum(dist["chart_types"].values())
            result["industry_distributions"][industry] = {
                "chart_types": {
                    k: round(v / total_charts, 3) 
                    for k, v in sorted(dist["chart_types"].items(), key=lambda x: x[1], reverse=True)
                },
                "common_fields": dict(sorted(dist["common_fields"].items(), key=lambda x: x[1], reverse=True)[:10]),
            }
    
    return result


def main():
    """Main extraction function."""
    print(f"Extracting patterns from collection: {COLLECTION_DIR}")
    
    # Find all package JSON files
    package_files = list(COLLECTION_DIR.glob("*_package*.json"))
    print(f"Found {len(package_files)} package files")
    
    if not package_files:
        print("No package files found!")
        return
    
    # Extract patterns from each package
    all_patterns = []
    for package_file in package_files:
        print(f"Processing {package_file.name}...")
        patterns = extract_patterns_from_package(package_file)
        all_patterns.append(patterns)
    
    # Aggregate statistics
    print("\nAggregating statistics...")
    stats = aggregate_statistics(all_patterns)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\nExtraction complete!")
    print(f"Processed {stats['total_packages']} packages")
    print(f"Found {stats['total_visualizations']} visualizations")
    print(f"Found {stats['total_dashboards']} dashboards")
    print(f"\nTop chart types:")
    for chart_type, count in list(stats["chart_type_usage"].items())[:5]:
        print(f"  {chart_type}: {count}")
    print(f"\nTop dimensions:")
    for dim, freq in list(stats["common_dimensions"].items())[:5]:
        print(f"  {dim}: {freq:.1%}")
    print(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
