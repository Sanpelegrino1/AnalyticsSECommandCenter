#!/usr/bin/env python3
"""Generate a complete Tableau Next visualization JSON payload (Vizql-oriented).

Usage:
    python scripts/generate_viz.py \\
      --chart-type bar \\
      --name "Revenue_by_Region" \\
      --label "Revenue by Region" \\
      --sdm-name Sales_Intelligence_Model \\
      --sdm-label "Sales Intelligence" \\
      --workspace-name My_Workspace \\
      --workspace-label "My Workspace" \\
      --columns F1 \\
      --rows F2 \\
      --field F1 role=Dimension fieldName=Region objectName=Opportunity \\
      --field F2 role=Measure fieldName=Amount objectName=Opportunity function=Sum \\
      --encoding F2 type=Label \\
      --style backgroundColor=#1A1A1A \\
      --style fontColor=#FFFFFF \\
      -o revenue_by_region.json
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

from lib.style_defaults import parse_style_args
from lib.templates import (
    build_bar,
    build_donut,
    build_dot_matrix,
    build_funnel,
    build_heatmap,
    build_line,
    build_root_envelope,
    build_scatter,
    build_table,
    validate_full_visualization,
)

CHART_TYPES = ["bar", "line", "donut", "scatter", "table", "funnel", "heatmap", "dot_matrix"]


def parse_field_arg(tokens: List[str]) -> Tuple[str, dict]:
    """Parse ``--field F1 role=Dimension fieldName=Region ...`` into (key, definition)."""
    if len(tokens) < 2:
        print(f"Error: --field needs at least a key and one property: {tokens}", file=sys.stderr)
        sys.exit(1)

    field_key = tokens[0]
    props: Dict[str, Any] = {"type": "Field"}

    for tok in tokens[1:]:
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        if v == "null" or v == "None":
            v = None
        props[k] = v

    role = props.get("role", "Dimension")
    if role == "Measure":
        props.setdefault("displayCategory", "Continuous")
    else:
        props.setdefault("displayCategory", "Discrete")

    # Ensure function is None for dimensions
    if role == "Dimension" and "function" not in props:
        props["function"] = None

    return field_key, props


def parse_encoding_arg(tokens: List[str]) -> dict:
    """Parse ``--encoding F2 type=Label`` into an encoding dict."""
    if len(tokens) < 2:
        print(f"Error: --encoding needs at least a fieldKey and type=...: {tokens}", file=sys.stderr)
        sys.exit(1)

    enc: Dict[str, str] = {"fieldKey": tokens[0]}
    for tok in tokens[1:]:
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        enc[k] = v
    return enc


def parse_legend_arg(tokens: List[str]) -> Tuple[str, dict]:
    """Parse ``--legend F2 position=Right`` into (fieldKey, config)."""
    if not tokens:
        return "", {}
    field_key = tokens[0]
    cfg: Dict[str, Any] = {"isVisible": True, "position": "Right", "title": {"isVisible": True}}
    for tok in tokens[1:]:
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        if k == "position":
            cfg["position"] = v
    return field_key, cfg


def parse_sort_arg(tokens: List[str]) -> Tuple[str, dict]:
    """Parse ``--sort F1 byField=F2 order=Descending type=Nested``."""
    if not tokens:
        return "", {}
    field_key = tokens[0]
    cfg: Dict[str, str] = {}
    for tok in tokens[1:]:
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        cfg[k] = v
    return field_key, cfg


def build_viz(args: argparse.Namespace) -> Dict[str, Any]:
    """Assemble the complete visualization payload from parsed CLI args.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Complete visualization JSON payload dict
    """
    # Parse fields
    fields: Dict[str, Dict[str, Any]] = {}
    if args.field:
        for f_tokens in args.field:
            fk, fdef = parse_field_arg(f_tokens)
            fields[fk] = fdef

    # Parse encodings
    encodings: List[Dict[str, str]] = []
    if args.encoding:
        for e_tokens in args.encoding:
            encodings.append(parse_encoding_arg(e_tokens))

    # Parse legends
    legends: Dict[str, Dict[str, Any]] = {}
    if args.legend:
        for l_tokens in args.legend:
            lk, lcfg = parse_legend_arg(l_tokens)
            if lk:
                legends[lk] = lcfg

    # Parse sort orders
    sort_fields: Dict[str, Dict[str, str]] = {}
    if args.sort:
        for s_tokens in args.sort:
            sk, scfg = parse_sort_arg(s_tokens)
            if sk:
                sort_fields[sk] = scfg

    sort_orders = None
    if sort_fields:
        sort_orders = {"columns": [], "fields": sort_fields, "rows": []}

    columns = args.columns or []
    rows = args.rows or []
    overrides = parse_style_args(args.style)
    chart = args.chart_type

    # Build the visualSpecification based on chart type
    if chart == "bar":
        vis_spec = build_bar(fields, columns, rows, encodings, legends, overrides,
                             measure_values=args.measure_values, sort_orders=sort_orders)
    elif chart == "line":
        vis_spec = build_line(fields, columns, rows, encodings, legends, overrides)
    elif chart == "donut":
        vis_spec = build_donut(fields, columns, rows, encodings, legends, overrides,
                               sort_orders=sort_orders)
    elif chart == "scatter":
        vis_spec = build_scatter(fields, columns, rows, encodings, legends, overrides)
    elif chart == "table":
        vis_spec = build_table(fields, rows, overrides, columns=columns)
    elif chart == "funnel":
        vis_spec = build_funnel(fields, columns, rows, encodings, legends, overrides)
    elif chart == "heatmap":
        color_fk = None
        for e in encodings:
            if e.get("type") == "Color":
                color_fk = e.get("fieldKey")
                break
        vis_spec = build_heatmap(fields, columns, rows, encodings, legends, overrides,
                                 color_field_key=color_fk)
    elif chart == "dot_matrix":
        size_fk = None
        for e in encodings:
            if e.get("type") == "Size":
                size_fk = e.get("fieldKey")
                break
        vis_spec = build_dot_matrix(fields, columns, rows, encodings, legends, overrides,
                                    size_field_key=size_fk)
    else:
        print(f"Error: Unknown chart type '{chart}'. Valid: {', '.join(CHART_TYPES)}", file=sys.stderr)
        sys.exit(1)

    return build_root_envelope(
        name=args.name,
        label=args.label,
        sdm_name=args.sdm_name,
        sdm_label=args.sdm_label,
        workspace_name=args.workspace_name,
        workspace_label=args.workspace_label,
        fields=fields,
        visual_spec=vis_spec,
        sort_orders=sort_orders,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Tableau Next visualization JSON payload",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required metadata
    parser.add_argument("--chart-type", required=True, choices=CHART_TYPES, help="Chart type")
    parser.add_argument("--name", required=True, help="Visualization API name")
    parser.add_argument("--label", required=True, help="Visualization display label")
    parser.add_argument("--sdm-name", required=True, help="Semantic Data Model API name")
    parser.add_argument("--sdm-label", required=True, help="SDM display label")
    parser.add_argument("--workspace-name", required=True, help="Workspace API name")
    parser.add_argument("--workspace-label", required=True, help="Workspace display label")

    # Shelf placement
    parser.add_argument("--columns", nargs="*", default=[], help="Field keys for columns (X axis)")
    parser.add_argument("--rows", nargs="*", default=[], help="Field keys for rows (Y axis)")
    parser.add_argument("--measure-values", nargs="*", default=None,
                        help="Field keys for measureValues (multi-measure bar charts)")

    # Field definitions (repeatable)
    parser.add_argument("--field", action="append", nargs="+", metavar="KEY_PROP",
                        help="Define a field: --field F1 role=Dimension fieldName=Region objectName=Opp")

    # Encodings (repeatable)
    parser.add_argument("--encoding", action="append", nargs="+", metavar="KEY_PROP",
                        help="Add encoding: --encoding F2 type=Label")

    # Legends (repeatable)
    parser.add_argument("--legend", action="append", nargs="+", metavar="KEY_PROP",
                        help="Add legend: --legend F3 position=Right")

    # Sort orders (repeatable)
    parser.add_argument("--sort", action="append", nargs="+", metavar="KEY_PROP",
                        help="Add sort: --sort F1 byField=F2 order=Descending type=Nested")

    # Style overrides (repeatable)
    parser.add_argument("--style", action="append", metavar="KEY=VALUE",
                        help="Style override: --style backgroundColor=#1A1A1A")

    # Output
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output file (default: stdout)")
    parser.add_argument("--validate", action="store_true",
                        help="Validate payload before outputting (catches common API errors)")

    args = parser.parse_args()

    payload = build_viz(args)
    
    # Validate if requested
    if args.validate:
        is_valid, errors = validate_full_visualization(payload)
        if not is_valid:
            print("Validation errors:", file=sys.stderr)
            for err in errors:
                print(f"  ❌ {err}", file=sys.stderr)
            sys.exit(1)
        print("✓ Validation passed", file=sys.stderr)
    
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
