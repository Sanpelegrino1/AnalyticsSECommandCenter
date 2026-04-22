#!/usr/bin/env python3
"""Generic dashboard creation workflow.

Accepts visualization specifications from AI and creates a complete dashboard.

Usage:
    # With pre-generated specs file:
    python scripts/create_dashboard.py \
      --org GDO_TEST_001 \
      --sdm Sales_Cloud12_backward \
      --workspace TEST_SKILL \
      --name Sales_Dashboard \
      --viz-specs viz_specs.json

    # Optional JSON keys in viz_specs file:
    #   "pattern": "f_layout" | "z_layout" | "performance_overview"
    #       (omit to auto-select; CLI --pattern overrides this)
    #   "pattern_args": { ... }  # e.g. primary_metric, secondary_metrics, pages, title_text
    
    # With auto-generated visualizations:
    python scripts/create_dashboard.py \
      --org GDO_TEST_001 \
      --sdm Sales_Cloud12_backward \
      --workspace TEST_SKILL \
      --name Sales_Dashboard \
      --auto-generate-viz \
      --num-viz 5
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from lib.auth import authenticate_to_org
from lib.dashboard_patterns import PATTERN_REQUIREMENTS, auto_select_pattern
from lib.dashboard_workflow import (
    create_dashboard_from_pattern,
    create_visualization_from_spec,
    discover_metrics,
    discover_sdm_fields,
    ensure_workspace,
)
from lib.filter_utils import enrich_filters, generate_filters_from_fields, validate_filters
from lib.name_utils import (
    clean_field_name_for_display,
    generate_business_friendly_name,
    validate_business_friendly_name,
)
from lib.validators import get_pattern_filter_requirements, validate_viz_specs
from lib.viz_templates import recommend_diverse_chart_types


def auto_generate_viz_specs(
    sdm_name: str,
    num_viz: int = 5
) -> List[Dict[str, Any]]:
    """Auto-generate visualization specs using recommend_diverse_chart_types.
    
    WARNING: Auto-generate bypasses narrative design workflow. Consider using
    --viz-specs with manually designed visualizations for better results.
    
    Args:
        sdm_name: SDM API name
        num_viz: Number of visualizations to generate
        
    Returns:
        List of visualization specification dicts
    """
    print("\n⚠ Warning: Auto-generate bypasses narrative design workflow.")
    print("  Consider using --viz-specs with manually designed visualizations for better results.")
    
    print(f"\nDiscovering fields from SDM '{sdm_name}'...")
    sdm_fields = discover_sdm_fields(sdm_name)
    if not sdm_fields:
        print("✗ Error: Could not discover SDM fields", file=sys.stderr)
        sys.exit(1)
    
    print(f"  Found {len(sdm_fields)} fields")
    
    # Get diverse chart recommendations
    print(f"\nRecommending {num_viz} diverse visualizations...")
    recommendations = recommend_diverse_chart_types(
        sdm_fields=sdm_fields,
        num_charts=num_viz,
    )
    
    if not recommendations:
        print("✗ Error: Could not generate visualization recommendations", file=sys.stderr)
        sys.exit(1)
    
    print(f"  Recommended {len(recommendations)} visualizations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"    {i}. {rec['template']}: {rec.get('reasoning', 'N/A')}")
    
    # Build visualization specs
    visualizations = []
    for i, rec in enumerate(recommendations, 1):
        template = rec["template"]
        fields = rec["fields"].copy()
        
        # Generate business-friendly name and label (passing sdm_fields)
        viz_name, viz_label = generate_business_friendly_name(template, fields, sdm_fields)
        
        # Ensure uniqueness by appending number if needed (but prefer descriptive names)
        # Only append number if we detect a duplicate pattern
        if i > 1:
            # Check if name is too generic (like "Trend" or "Analysis")
            if len(viz_name.split("_")) <= 2 and not any(char.isdigit() for char in viz_name):
                # Make it more specific by including template context
                if "category" in fields:
                    category_name = fields["category"]
                    category = clean_field_name_for_display(category_name, sdm_fields)
                    viz_label = f"{category} {viz_label}"
                    viz_name = viz_label.replace(" ", "_")
        
        # Validate name before adding to list
        is_valid, error_msg = validate_business_friendly_name(viz_name, viz_label)
        if not is_valid:
            print(f"⚠ Warning: {error_msg}", file=sys.stderr)
            print(f"  Visualization '{viz_name}' may need manual review.", file=sys.stderr)
        
        viz_spec = {
            "template": template,
            "name": viz_name,
            "label": viz_label,
            "fields": fields,
        }
        
        # Add color_dim if present in fields (extract to top level)
        if "color_dim" in fields:
            viz_spec["color_dim"] = fields.pop("color_dim")
        
        visualizations.append(viz_spec)
    
    return visualizations


def main():
    parser = argparse.ArgumentParser(
        description="Create a dashboard from AI-provided visualization specifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument("--org", required=True, help="Salesforce org alias")
    parser.add_argument("--sdm", required=True, dest="sdm_name", help="SDM API name")
    parser.add_argument("--workspace", required=True, dest="workspace_name", help="Workspace API name")
    parser.add_argument("--name", required=True, help="Dashboard API name")
    parser.add_argument("--label", help="Dashboard display label (defaults to name)")
    parser.add_argument("--viz-specs", help="JSON file with visualization specifications (required if --auto-generate-viz not used)")
    parser.add_argument("--pattern", help="Dashboard pattern (auto-selected if not provided)")
    parser.add_argument("--auto-generate-viz", action="store_true", help="Auto-generate visualization specs using recommend_diverse_chart_types")
    parser.add_argument("--num-viz", type=int, default=5, help="Number of visualizations to auto-generate (default: 5, only used with --auto-generate-viz)")

    args = parser.parse_args()
    
    # Validate arguments
    if not args.auto_generate_viz and not args.viz_specs:
        print("✗ Error: Either --viz-specs or --auto-generate-viz must be provided", file=sys.stderr)
        sys.exit(1)
    
    # Authenticate
    if not authenticate_to_org(args.org):
        sys.exit(1)

    # Load or generate visualization specs
    spec_metrics: Optional[List[str]] = None
    spec_pattern: Optional[str] = None
    spec_pattern_args: Dict[str, Any] = {}
    if args.auto_generate_viz:
        viz_specs = auto_generate_viz_specs(args.sdm_name, args.num_viz)
        filters = []
        workspace_label = args.workspace_name.replace("_", " ").title()
    else:
        # Load visualization specs from file
        try:
            with open(args.viz_specs) as f:
                spec_data = json.load(f)
        except FileNotFoundError:
            print(f"✗ Error: Visualization specs file not found: {args.viz_specs}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"✗ Error: Invalid JSON in specs file: {e}", file=sys.stderr)
            sys.exit(1)
        
        viz_specs = spec_data.get("visualizations", [])
        filters = spec_data.get("filters", [])
        workspace_label = spec_data.get("workspace_label")
        spec_metrics = spec_data.get("metrics")
        spec_pattern = spec_data.get("pattern")
        spec_pattern_args = spec_data.get("pattern_args") or {}
    
    if spec_pattern in ("vertical_metrics", "horizontal_metrics"):
        print(
            "✗ Error: Dashboard patterns 'vertical_metrics' and 'horizontal_metrics' were removed. "
            "Use 'f_layout', 'z_layout', or 'performance_overview' (see templates-guide.md).",
            file=sys.stderr,
        )
        sys.exit(1)
    
    if not viz_specs:
        print("✗ Error: No visualizations specified (at least one is required).", file=sys.stderr)
        sys.exit(1)
    
    # Step 1: Ensure workspace exists
    success, actual_workspace_name = ensure_workspace(args.workspace_name, workspace_label)
    if not success:
        sys.exit(1)
    
    # Step 2: Discover SDM fields for validation
    print(f"\nDiscovering fields from SDM '{args.sdm_name}'...")
    sdm_fields = discover_sdm_fields(args.sdm_name)
    if not sdm_fields:
        sys.exit(1)
    
    # Step 2b: Enrich filters with objectName, dataType, and label from SDM
    if filters:
        print(f"\nEnriching filters from SDM...")
        enrich_filters(filters, sdm_fields)

        # Validate filters have required fields
        is_valid, error_msg = validate_filters(filters, sdm_fields, sdm_name=args.sdm_name)
        if not is_valid:
            print(error_msg, file=sys.stderr)
            sys.exit(1)
        
        print(f"  Enriched {len(filters)} filter(s) with objectName, dataType, and label")
    
    # Step 3: Validate visualization specs
    if viz_specs and not validate_viz_specs(viz_specs, sdm_fields):
        sys.exit(1)
    
    # Step 3b: Validate business-friendly names
    if viz_specs:
        print("\nValidating visualization names...")
        validation_errors = []
        for viz_spec in viz_specs:
            viz_name = viz_spec.get("name", "")
            viz_label = viz_spec.get("label", "")
            is_valid, error_msg = validate_business_friendly_name(viz_name, viz_label)
            if not is_valid:
                validation_errors.append(f"  - {viz_name}: {error_msg}")
        
        if validation_errors:
            print("✗ Error: Validation failed for visualization names:", file=sys.stderr)
            for error in validation_errors:
                print(error, file=sys.stderr)
            print("\nPlease update visualization specs to use business-friendly names without technical suffixes.", file=sys.stderr)
            sys.exit(1)
        
        print("✓ All visualization names validated")
    
    # Step 4: Create visualizations
    print(f"\nCreating {len(viz_specs)} visualizations...")
    viz_names = []
    failed_count = 0
    for viz_spec in viz_specs:
        actual_viz_name = create_visualization_from_spec(
            viz_spec=viz_spec,
            sdm_name=args.sdm_name,
            workspace_name=args.workspace_name,
        )
        if actual_viz_name:
            viz_names.append(actual_viz_name)
        else:
            failed_count += 1
            print(f"✗ Error: Failed to create visualization '{viz_spec.get('name', 'unknown')}'", file=sys.stderr)
    
    # Fail if too many visualizations failed (>50%)
    if viz_specs and failed_count > len(viz_specs) * 0.5:
        print(f"\n✗ Error: Too many visualizations failed ({failed_count}/{len(viz_specs)})", file=sys.stderr)
        print("  Dashboard creation aborted. Please fix visualization specs and try again.", file=sys.stderr)
        sys.exit(1)
    
    if not viz_names:
        print("✗ No visualizations created. Cannot create dashboard.", file=sys.stderr)
        sys.exit(1)
    
    if failed_count > 0:
        print(f"⚠ Warning: {failed_count} visualization(s) failed, but proceeding with {len(viz_names)} successful visualization(s)")
    
    print(f"\n✓ Created {len(viz_names)} visualizations")
    
    # Step 5: Discover metrics
    print(f"\nDiscovering metrics from SDM '{args.sdm_name}'...")
    all_metrics = discover_metrics(args.sdm_name)
    
    if spec_metrics:
        available = set(all_metrics)
        missing = [m for m in spec_metrics if m not in available]
        if missing:
            print(
                f"✗ Error: viz-specs 'metrics' entries not found on SDM: {', '.join(missing)}",
                file=sys.stderr,
            )
            sys.exit(1)
        metric_names = list(spec_metrics)
        print(f"  Using {len(metric_names)} metric(s) from viz-specs: {', '.join(metric_names)}")
    elif all_metrics:
        print(f"  Found {len(all_metrics)} metrics: {', '.join(all_metrics[:5])}{'...' if len(all_metrics) > 5 else ''}")
        # Use metrics for dashboard (will be trimmed by pattern requirements)
        metric_names = all_metrics
    else:
        print("  No metrics found in SDM")
        metric_names = []
    
    # Step 6: Select dashboard pattern (CLI --pattern overrides spec "pattern")
    if args.pattern:
        pattern = args.pattern
        pattern_args = dict(spec_pattern_args)
        print(f"\nUsing specified pattern: {pattern}")
    elif spec_pattern:
        pattern = spec_pattern
        pattern_args = dict(spec_pattern_args)
        print(f"\nUsing pattern from viz-specs file: {pattern}")
        if pattern_args:
            print(f"  Pattern args: {pattern_args}")
    else:
        print("\nAuto-selecting dashboard pattern...")
        pattern, pattern_args = auto_select_pattern(
            metrics=metric_names,
            visualizations=viz_names,
            filters=filters,
        )
        print(f"  Selected pattern: {pattern}")
        if pattern_args:
            print(f"  Pattern args: {pattern_args}")

    dashboard_label = args.label or args.name.replace("_", " ").title()
    if pattern in ("f_layout", "z_layout"):
        pattern_args.setdefault("title_text", dashboard_label)

    if pattern == "performance_overview" and metric_names:
        pattern_args.setdefault("primary_metric", metric_names[0])
        if not pattern_args.get("secondary_metrics") and len(metric_names) > 1:
            pattern_args["secondary_metrics"] = metric_names[1:5]
        pattern_args.setdefault("pages", ["Week", "Month", "Day"])
    
    # Step 6b: Validate filter count matches pattern requirements
    pattern_req = get_pattern_filter_requirements(pattern)
    if pattern_req and len(filters) != pattern_req:
        print(f"\n⚠ Warning: Pattern '{pattern}' requires {pattern_req} filters, but {len(filters)} provided", file=sys.stderr)
        print("  Dashboard may not render correctly. Please update filters to match pattern requirements.", file=sys.stderr)
    
    # Step 7: Create dashboard
    print(f"\nCreating dashboard '{args.name}' using pattern '{pattern}'...")

    success, dashboard_id, actual_dashboard_name = create_dashboard_from_pattern(
        pattern=pattern,
        name=args.name,
        label=dashboard_label,
        workspace_name=args.workspace_name,
        sdm_name=args.sdm_name,
        viz_names=viz_names,
        metric_names=metric_names,
        filters=filters if filters else None,
        pattern_args=pattern_args if pattern_args else None,
    )
    
    if success:
        print("\n✓ Dashboard creation complete!")
        print(f"  Dashboard ID: {dashboard_id}")
        if actual_dashboard_name and actual_dashboard_name != args.name:
            print(f"  Actual API name: {actual_dashboard_name}")
        sys.exit(0)
    else:
        print(f"\n✗ Dashboard creation failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
