#!/usr/bin/env python3
"""Generate a Tableau Next dashboard using predefined layout patterns.

This script generates dashboard JSON payloads using predefined layout patterns
that match production dashboard structures. Patterns enforce specific widget
counts and layouts for consistent dashboard design.

Available patterns:
  - f_layout: Metrics in left sidebar, visualizations in F-pattern
  - z_layout: Metrics in top row, visualizations in Z-pattern
  - performance_overview: Large metric left, smaller metrics right, time navigation

Usage:
    python scripts/generate_dashboard_pattern.py \\
      --pattern f_layout \\
      --name Sales_Dashboard \\
      --label "Sales Dashboard" \\
      --workspace-name My_WS \\
      --sdm-name Sales_Model \\
      --title-text "Sales Performance" \\
      --metrics Total_Revenue_mtc Win_Rate_mtc \\
      --viz Revenue_Bar Pipeline_Funnel \\
      --filter fieldName=Account_Industry objectName=Opportunity dataType=Text \\
      -o dashboard.json

Pattern-specific arguments:
  f_layout/z_layout:
    --title-text "Dashboard Title"

  performance_overview:
    --primary-metric Total_Revenue_mtc \\
    --secondary-metrics Win_Rate_mtc Pipeline_Count_mtc \\
    --pages "Week" "Month" "Day"

Key Functions:
    - main: Main CLI entry point with pattern validation
"""

import argparse
import json
import sys
from typing import Any, Dict, List

from lib.filter_utils import parse_filter_arg
from lib.style_defaults import parse_style_args
from lib.templates import (
    FilterDef,
    MetricDef,
    PageDef,
    VizDef,
    build_dashboard_from_pattern,
)
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Tableau Next dashboard using predefined layout patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Required arguments (not required if --show-requirements)
    parser.add_argument("--pattern",
                        choices=["f_layout", "z_layout", "performance_overview"],
                        help="Layout pattern to use")
    parser.add_argument("--name", help="Dashboard API name")
    parser.add_argument("--label", help="Dashboard display label")
    parser.add_argument("--workspace-name", help="Workspace API name")
    parser.add_argument("--sdm-name", help="SDM API name (required for filters/metrics)")

    # Dashboard content
    parser.add_argument("--viz", action="append", dest="vizzes", metavar="API_NAME",
                        help="Visualization API name (repeatable)")
    parser.add_argument("--filter", action="append", nargs="+", dest="filters", metavar="KEY=VAL",
                        help="Filter def: --filter fieldName=X objectName=Y dataType=Text")
    parser.add_argument("--metrics", action="append", dest="metric_names", metavar="METRIC",
                        help="Metric API name (repeatable, e.g., Total_Revenue_mtc)")
    parser.add_argument("--page", action="append", dest="pages", metavar="LABEL",
                        help="Page label (repeatable, enables multi-page layout)")

    # Pattern-specific arguments
    parser.add_argument("--title-text", type=str, help="Title text (for f_layout/z_layout)")
    parser.add_argument("--primary-metric", type=str, help="Primary metric API name (for performance_overview)")
    parser.add_argument("--secondary-metrics", action="append", dest="secondary_metric_names", metavar="METRIC",
                        help="Secondary metric API name (repeatable, for performance_overview)")

    # Layout options
    parser.add_argument("--column-count", type=int, default=72, help="Grid columns (default 72)")
    parser.add_argument("--row-height", type=int, default=20, help="Row height px (default 20)")
    parser.add_argument("--style", action="append", metavar="KEY=VALUE",
                        help="Style override: --style backgroundColor=#1A1A1A")

    parser.add_argument("-o", "--output", type=str, default=None, help="Output file (default: stdout)")
    parser.add_argument("--validate-requirements", action="store_true",
                        help="Validate that widget counts match pattern requirements")
    parser.add_argument("--show-requirements", action="store_true",
                        help="Show pattern requirements and exit")

    args = parser.parse_args()

    # Handle --show-requirements flag
    if args.show_requirements:
        from lib.dashboard_patterns import PATTERN_REQUIREMENTS
        pattern = args.pattern or "f_layout"
        if pattern in PATTERN_REQUIREMENTS:
            req = PATTERN_REQUIREMENTS[pattern]
            print(f"\n{pattern.upper()} Requirements:")
            print(f"  Description: {req['description']}")
            print(f"  Filters: min={req['filters']['min']}, max={req['filters'].get('max', 'unlimited')}, recommended={req['filters']['recommended']}, slots={req['filters'].get('slots', 'flexible')}")
            print(f"  Metrics: min={req['metrics']['min']}, max={req['metrics'].get('max', 'unlimited')}, recommended={req['metrics']['recommended']}, slots={req['metrics'].get('slots', 'flexible')}")
            print(f"  Visualizations: min={req['visualizations']['min']}, max={req['visualizations'].get('max', 'unlimited')}, recommended={req['visualizations']['recommended']}, slots={req['visualizations'].get('slots', 'flexible')}")
            if "primary_metric" in req:
                print(f"  Primary Metric: required={req['primary_metric']['required']}")
        else:
            print(f"Error: Unknown pattern '{pattern}'", file=sys.stderr)
            if not args.pattern:
                print("Available patterns:", ", ".join(PATTERN_REQUIREMENTS.keys()), file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # Validate required arguments (unless --show-requirements)
    if not args.pattern:
        parser.error("--pattern is required (unless using --show-requirements)")
    if not args.name:
        parser.error("--name is required")
    if not args.label:
        parser.error("--label is required")
    if not args.workspace_name:
        parser.error("--workspace-name is required")
    if not args.sdm_name:
        parser.error("--sdm-name is required")

    # Validate pattern-specific requirements
    if args.pattern in ["f_layout", "z_layout"]:
        if not args.title_text:
            args.title_text = args.label  # Use label as fallback
    elif args.pattern == "performance_overview":
        if not args.primary_metric:
            print("Error: --primary-metric is required for performance_overview pattern", file=sys.stderr)
            sys.exit(1)
        if not args.secondary_metric_names:
            args.secondary_metric_names = []
        if not args.pages:
            args.pages = ["Week", "Month", "Day"]  # Default time periods

    # Build definitions
    viz_defs = [VizDef(viz_api_name=v) for v in (args.vizzes or [])]
    filter_defs = [parse_filter_arg(ft) for ft in (args.filters or [])] if args.filters else None

    metric_defs = []
    if args.metric_names:
        for metric_name in args.metric_names:
            metric_defs.append(MetricDef(metric_api_name=metric_name, sdm_api_name=args.sdm_name))

    page_defs = None
    if args.pages:
        page_defs = [PageDef(label=p) for p in args.pages]

    overrides = parse_style_args(args.style) if args.style else None

    # Build pattern-specific arguments
    pattern_args: Dict[str, Any] = {}
    if args.pattern in ["f_layout", "z_layout"]:
        pattern_args["title_text"] = args.title_text
    elif args.pattern == "performance_overview":
        pattern_args["primary_metric"] = args.primary_metric
        pattern_args["secondary_metrics"] = args.secondary_metric_names or []

    # For performance_overview, add primary metric to metric_defs if not already there
    if args.pattern == "performance_overview" and args.primary_metric:
        # Check if primary metric is already in metric_defs
        if not any(md.metric_api_name == args.primary_metric for md in metric_defs):
            metric_defs.insert(0, MetricDef(metric_api_name=args.primary_metric, sdm_api_name=args.sdm_name))
        # Add secondary metrics
        for sec_metric in (args.secondary_metric_names or []):
            if not any(md.metric_api_name == sec_metric for md in metric_defs):
                metric_defs.append(MetricDef(metric_api_name=sec_metric, sdm_api_name=args.sdm_name))

    # Validate requirements if requested
    if args.validate_requirements:
        from lib.dashboard_patterns import validate_pattern_requirements
        is_valid, warnings = validate_pattern_requirements(
            args.pattern,
            filter_defs or [],
            [md.metric_api_name for md in metric_defs] if metric_defs else [],
            [vd.viz_api_name for vd in viz_defs],
            **pattern_args
        )
        if warnings:
            print("Validation warnings:", file=sys.stderr)
            for warning in warnings:
                print(f"  ⚠ {warning}", file=sys.stderr)
            if not is_valid:
                print("Error: Pattern requirements not met. Use --show-requirements to see requirements.", file=sys.stderr)
                sys.exit(1)

    payload = build_dashboard_from_pattern(
        name=args.name,
        label=args.label,
        workspace_name=args.workspace_name,
        pattern=args.pattern,
        viz_defs=viz_defs,
        filter_defs=filter_defs,
        metric_defs=metric_defs if metric_defs else None,
        sdm_name=args.sdm_name,
        column_count=args.column_count,
        row_height=args.row_height,
        overrides=overrides,
        page_defs=page_defs,
        validate_requirements=args.validate_requirements,
        **pattern_args
    )

    output = json.dumps(payload, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
            f.write("\n")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
