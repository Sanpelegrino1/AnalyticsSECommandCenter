#!/usr/bin/env python3
"""Generate a complete Tableau Next dashboard JSON payload.

This script generates dashboard JSON payloads for Tableau Next dashboards.
It supports multiple visualizations, filters, metrics, pages, and containers.

Usage:
    python scripts/generate_dashboard.py \\
      --name "Sales_Dashboard" --label "Sales Dashboard" \\
      --workspace-name My_WS \\
      --sdm-name Sales_Model \\
      --title "Sales Performance" \\
      --viz Revenue_by_Region --viz Pipeline_Donut \\
      --filter fieldName=Account_Industry objectName=Opportunity dataType=Text \\
      --metric Total_Revenue_mtc \\
      --style backgroundColor=#1A1A1A \\
      --page "Overview" --page "Details" \\
      -o dashboard.json

Key Functions:
    - parse_container_arg: Parse container definition arguments
    - main: Main CLI entry point
"""

import argparse
import json
import sys
from typing import Any, Dict, List

from lib.filter_utils import parse_filter_arg
from lib.style_defaults import parse_style_args
from lib.templates import (
    ContainerDef,
    FilterDef,
    MetricDef,
    PageDef,
    VizDef,
    build_dashboard,
)


def parse_container_arg(tokens: List[str]) -> ContainerDef:
    """Parse container argument tokens into a ContainerDef.
    
    Parses CLI-style container arguments like:
    ``col=0 row=20 colspan=48 rowspan=2 navigateTo=Page2``
    
    Args:
        tokens: List of key=value tokens
        
    Returns:
        ContainerDef dataclass instance with parsed values
    """
    props: Dict[str, str] = {}
    for tok in tokens:
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        props[k] = v

    return ContainerDef(
        column=int(props.get("col", "0")),
        row=int(props.get("row", "0")),
        colspan=int(props.get("colspan", "48")),
        rowspan=int(props.get("rowspan", "10")),
        navigate_to_page=props.get("navigateTo"),
        border_color=props.get("borderColor", "#cccccc"),
        page_index=int(props.get("pageIndex", "0")),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Tableau Next dashboard JSON payload",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--name", required=True, help="Dashboard API name")
    parser.add_argument("--label", required=True, help="Dashboard display label")
    parser.add_argument("--workspace-name", required=True, help="Workspace API name")
    parser.add_argument("--sdm-name", default=None, help="SDM API name (for filter source)")
    parser.add_argument("--title", required=True, help="Title text displayed on dashboard")

    parser.add_argument("--viz", action="append", dest="vizzes", metavar="API_NAME",
                        help="Visualization API name (repeatable)")
    parser.add_argument("--filter", action="append", nargs="+", dest="filters", metavar="KEY=VAL",
                        help="Filter def: --filter fieldName=X objectName=Y dataType=Text")
    parser.add_argument("--metric", action="append", nargs="+", dest="metrics", metavar="METRIC",
                        help="Metric: --metric metricName sdmName=SDM_Name")
    parser.add_argument("--page", action="append", dest="pages", metavar="LABEL",
                        help="Page label (repeatable, enables multi-page layout)")
    parser.add_argument("--container", action="append", nargs="+", dest="containers", metavar="KEY=VAL",
                        help="Container: --container col=0 row=20 colspan=48 rowspan=2")
    parser.add_argument("--style", action="append", metavar="KEY=VALUE",
                        help="Style override: --style backgroundColor=#1A1A1A")

    parser.add_argument("--column-count", type=int, default=48, help="Grid columns (default 48)")
    parser.add_argument("--row-height", type=int, default=20, help="Row height px (default 20)")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output file (default: stdout)")

    args = parser.parse_args()

    viz_defs = [VizDef(viz_api_name=v) for v in (args.vizzes or [])]
    filter_defs = [parse_filter_arg(ft) for ft in (args.filters or [])]

    metric_defs = []
    for mt in (args.metrics or []):
        props: Dict[str, str] = {}
        metric_name = mt[0]
        for tok in mt[1:]:
            if "=" in tok:
                k, v = tok.split("=", 1)
                props[k] = v
        sdm = props.get("sdmName", args.sdm_name or "")
        metric_defs.append(MetricDef(metric_api_name=metric_name, sdm_api_name=sdm))

    page_defs = [PageDef(label=p) for p in args.pages] if args.pages else None
    container_defs = [parse_container_arg(ct) for ct in (args.containers or [])] or None
    overrides = parse_style_args(args.style)

    payload = build_dashboard(
        name=args.name,
        label=args.label,
        workspace_name=args.workspace_name,
        title_text=args.title,
        viz_defs=viz_defs,
        filter_defs=filter_defs if filter_defs else None,
        metric_defs=metric_defs if metric_defs else None,
        sdm_name=args.sdm_name,
        column_count=args.column_count,
        row_height=args.row_height,
        overrides=overrides if overrides else None,
        page_defs=page_defs,
        container_defs=container_defs,
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
