#!/usr/bin/env python3
"""Apply a visualization template to create a Tableau Next visualization.

Usage:
    python scripts/apply_viz_template.py \\
      --template revenue_by_category \\
      --sdm Sales_Model \\
      --category Region \\
      --amount Total_Amount \\
      --name Revenue_by_Region \\
      --label "Revenue by Region" \\
      --workspace My_Workspace \\
      --post

    python scripts/apply_viz_template.py --list-templates
    python scripts/apply_viz_template.py --preview revenue_by_category
"""

import argparse
import json
import sys
from typing import Any, Dict, Optional

from lib.sf_api import get_credentials, sf_get, sf_post, sdm_detail_endpoint, visualization_endpoint
from lib.sdm_discovery import discover_sdm_fields
from lib.templates import build_viz_from_template_def
from lib.validators import validate
from lib.viz_templates import (
    analyze_fields_for_chart_selection,
    find_matching_fields,
    get_template,
    get_template_info,
    list_templates,
)


def apply_template(
    template_name: str,
    sdm_name: str,
    sdm_label: Optional[str],
    workspace_name: str,
    workspace_label: Optional[str],
    name: str,
    label: str,
    field_overrides: Optional[Dict[str, str]] = None,
    auto_match: bool = False,
    overrides: Optional[Dict[str, Any]] = None,
) -> dict:
    """Apply a template to create a visualization.
    
    Args:
        template_name: Template name
        sdm_name: SDM API name
        sdm_label: SDM display label (defaults to sdm_name)
        workspace_name: Workspace API name
        workspace_label: Workspace display label (defaults to workspace_name)
        name: Visualization API name
        label: Visualization display label
        field_overrides: Optional dict mapping template field names to SDM field names
        auto_match: If True, auto-match fields using keyword scoring
        overrides: Optional style overrides
        
    Returns:
        Visualization JSON payload
    """
    # Load template
    template = get_template(template_name)
    if not template:
        print(f"Error: Template '{template_name}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Discover SDM fields
    print(f"Discovering fields from SDM '{sdm_name}'...", file=sys.stderr)
    sdm_fields = discover_sdm_fields(sdm_name)
    if sdm_fields is None:
        print(f"Error: Could not discover SDM '{sdm_name}'", file=sys.stderr)
        sys.exit(1)
    
    # Get SDM label if not provided
    if not sdm_label:
        token, instance = get_credentials()
        sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
        sdm_label = sdm_data.get("label", sdm_name) if sdm_data else sdm_name
    
    # Match fields
    if auto_match:
        print("Auto-matching fields...", file=sys.stderr)
        # Include optional_fields in matching
        all_template_fields = {**template["required_fields"], **template.get("optional_fields", {})}
        field_mappings = find_matching_fields(
            sdm_fields,
            all_template_fields,
            user_overrides=field_overrides
        )
        
        # Print matches
        for template_field, sdm_field in field_mappings.items():
            print(f"  ✓ Matched {template_field}: {sdm_field['fieldName']} ({sdm_field.get('role', 'Unknown')})", file=sys.stderr)
    else:
        # Use explicit field overrides
        field_mappings = {}
        for template_field_name, sdm_field_name in (field_overrides or {}).items():
            if sdm_field_name in sdm_fields:
                field_mappings[template_field_name] = sdm_fields[sdm_field_name]
            else:
                print(f"Error: Field '{sdm_field_name}' not found in SDM", file=sys.stderr)
                sys.exit(1)
    
    # Check all required fields are matched (optional_fields are optional)
    required_fields = template["required_fields"]
    missing_fields = set(required_fields.keys()) - set(field_mappings.keys())
    if missing_fields:
        print(f"Error: Missing required fields: {', '.join(missing_fields)}", file=sys.stderr)
        sys.exit(1)
    
    # Build visualization
    viz_json = build_viz_from_template_def(
        template_def=template,
        sdm_name=sdm_name,
        sdm_label=sdm_label or sdm_name,
        workspace_name=workspace_name,
        workspace_label=workspace_label or workspace_name,
        field_mappings=field_mappings,
        name=name,
        label=label,
        overrides=overrides,
    )
    
    return viz_json


def post_visualization(viz_json: dict) -> tuple[Optional[str], Optional[str]]:
    """POST visualization to Salesforce API.
    
    Args:
        viz_json: Visualization JSON payload
        
    Returns:
        Tuple of (visualization_url, actual_api_name) if successful, (None, None) otherwise
    """
    token, instance = get_credentials()
    response, error = sf_post(token, instance, visualization_endpoint(), viz_json)
    
    if error:
        print(f"Error posting visualization: {error}", file=sys.stderr)
        return None, None
    
    viz_id = response.get("id", "")
    viz_url = response.get("url", "")
    actual_name = response.get("name", viz_json["name"])
    
    print(f"✓ Created visualization: {viz_json['name']} ({viz_id})", file=sys.stderr)
    if actual_name != viz_json["name"]:
        print(f"  → Actual API name: {actual_name}", file=sys.stderr)
    if viz_url:
        print(f"✓ URL: {viz_url}", file=sys.stderr)
    
    # Output actual name in parseable format for subprocess callers
    print(f"ACTUAL_NAME:{actual_name}", file=sys.stderr)
    
    return viz_url, actual_name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply visualization templates to create Tableau Next visualizations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    # List/preview commands
    parser.add_argument("--list-templates", action="store_true",
                        help="List all available templates")
    parser.add_argument("--preview", type=str, metavar="TEMPLATE",
                        help="Preview template requirements")
    
    # Template selection
    parser.add_argument("--template", type=str, metavar="NAME",
                        help="Template name to apply")
    
    # SDM and workspace
    parser.add_argument("--sdm", type=str, metavar="NAME", dest="sdm_name",
                        help="SDM API name")
    parser.add_argument("--sdm-label", type=str, metavar="LABEL",
                        help="SDM display label (defaults to SDM name)")
    parser.add_argument("--workspace", type=str, metavar="NAME", dest="workspace_name",
                        help="Workspace API name")
    parser.add_argument("--workspace-label", type=str, metavar="LABEL",
                        help="Workspace display label (defaults to workspace name)")
    
    # Visualization metadata
    parser.add_argument("--name", type=str, metavar="API_NAME",
                        help="Visualization API name")
    parser.add_argument("--label", type=str, metavar="LABEL",
                        help="Visualization display label")
    
    # Field overrides (dynamic based on template)
    parser.add_argument("--category", type=str, metavar="FIELD",
                        help="Category/dimension field name")
    parser.add_argument("--amount", type=str, metavar="FIELD",
                        help="Amount/measure field name")
    parser.add_argument("--date", type=str, metavar="FIELD",
                        help="Date field name")
    parser.add_argument("--measure", type=str, metavar="FIELD", nargs="+",
                        help="Measure field name(s) - can specify multiple for bar_multi_measure")
    parser.add_argument("--stage", type=str, metavar="FIELD",
                        help="Stage field name")
    parser.add_argument("--count", type=str, metavar="FIELD",
                        help="Count field name")
    parser.add_argument("--x-measure", type=str, metavar="FIELD", dest="x_measure",
                        help="X-axis measure field name")
    parser.add_argument("--y-measure", type=str, metavar="FIELD", dest="y_measure",
                        help="Y-axis measure field name")
    parser.add_argument("--size-measure", type=str, metavar="FIELD", dest="size_measure",
                        help="Size encoding measure field (scatter, heatmap)")
    parser.add_argument("--label-measure", type=str, metavar="FIELD", dest="label_measure",
                        help="Label encoding measure field (scatter)")
    parser.add_argument("--row-dim", type=str, metavar="FIELD", dest="row_dim",
                        help="Row dimension field name")
    parser.add_argument("--col-dim", type=str, metavar="FIELD", dest="col_dim",
                        help="Column dimension field name")
    parser.add_argument("--id-field", type=str, metavar="FIELD", dest="id_field",
                        help="ID field name")
    parser.add_argument("--label-field", type=str, metavar="FIELD", dest="label_field",
                        help="Label field name")
    parser.add_argument("--color-dim", type=str, metavar="FIELD", dest="color_dim",
                        help="Color dimension field name (for multi-series charts)")
    parser.add_argument("--stack-dim", type=str, metavar="FIELD", dest="stack_dim",
                        help="Stack dimension field name (for stacked bar charts)")
    parser.add_argument("--latitude", type=str, metavar="FIELD",
                        help="Latitude field (geomap_points template)")
    parser.add_argument("--longitude", type=str, metavar="FIELD",
                        help="Longitude field (geomap_points template)")
    parser.add_argument("--label-dim", type=str, metavar="FIELD", dest="label_dim",
                        help="Label dimension on map points (geomap_points)")
    parser.add_argument("--level1", type=str, metavar="FIELD",
                        help="First Flow / Sankey level dimension (flow_* templates)")
    parser.add_argument("--level2", type=str, metavar="FIELD",
                        help="Second Flow / Sankey level dimension (flow_* templates)")
    parser.add_argument("--link-measure", type=str, metavar="FIELD", dest="link_measure",
                        help="Measure for link width (flow_* templates)")
    parser.add_argument("--link-color-measure", type=str, metavar="FIELD", dest="link_color_measure",
                        help="Optional second measure for link Color (flow_sankey, flow_sankey_measure_on_marks; default: link measure)")
    parser.add_argument("--level2-color-dim", type=str, metavar="FIELD", dest="level2_color_dim",
                        help="Optional dimension for Color on second level bars (flow_sankey, flow_sankey_measure_on_marks; default: level2)")
    parser.add_argument("--level3", type=str, metavar="FIELD",
                        help="Third Flow level dimension (flow_package_three_level)")
    
    # Options
    parser.add_argument("--auto-match", action="store_true",
                        help="Auto-match fields using keyword scoring")
    parser.add_argument("--auto-select", action="store_true",
                        help="Auto-select chart type using decision matrix based on field types")
    parser.add_argument("--post", action="store_true",
                        help="POST visualization to Salesforce API")
    parser.add_argument("--validate", action="store_true",
                        help="Validate JSON before posting (future)")
    parser.add_argument("-o", "--output", type=str, metavar="FILE",
                        help="Output JSON to file (default: stdout)")
    parser.add_argument("--overrides", type=str, metavar="FILE",
                        help="JSON file with style/palette overrides")
    
    args = parser.parse_args()
    
    # Handle list/preview commands
    if args.list_templates:
        templates = list_templates()
        print("Available templates:")
        for tname in templates:
            info = get_template_info(tname)
            if info:
                print(f"  {tname:<30} - {info['description']}")
        return
    
    if args.preview:
        info = get_template_info(args.preview)
        if not info:
            print(f"Error: Template '{args.preview}' not found", file=sys.stderr)
            sys.exit(1)
        
        print(f"Template: {info['name']}")
        print(f"Description: {info['description']}")
        print(f"Chart Type: {info['chart_type']}")
        print("\nRequired Fields:")
        for field_name, requirements in info['required_fields'].items():
            role = requirements.get("role", "Unknown")
            data_types = requirements.get("dataType", [])
            optional = requirements.get("optional", False)
            opt_str = " (optional)" if optional else ""
            if data_types:
                print(f"  {field_name:<20} - {role} ({', '.join(data_types)}){opt_str}")
            else:
                print(f"  {field_name:<20} - {role}{opt_str}")
        if info.get("optional_fields"):
            print("\nOptional Fields:")
            for field_name, requirements in info["optional_fields"].items():
                role = requirements.get("role", "Unknown")
                data_types = requirements.get("dataType", [])
                if data_types:
                    print(f"  {field_name:<20} - {role} ({', '.join(data_types)})")
                else:
                    print(f"  {field_name:<20} - {role}")
        return
    
    # Validate required args for apply
    if not args.template and not args.auto_select:
        print("Error: --template is required (or use --auto-select)", file=sys.stderr)
        sys.exit(1)
    
    if not args.sdm_name:
        print("Error: --sdm is required", file=sys.stderr)
        sys.exit(1)
    
    if not args.workspace_name:
        print("Error: --workspace is required", file=sys.stderr)
        sys.exit(1)
    
    if not args.name:
        print("Error: --name is required", file=sys.stderr)
        sys.exit(1)
    
    if not args.label:
        args.label = args.name.replace("_", " ").title()
    
    # Build field overrides from CLI args
    field_overrides: Dict[str, str] = {}
    if args.category:
        field_overrides["category"] = args.category
    if args.amount:
        field_overrides["amount"] = args.amount
    if args.date:
        field_overrides["date"] = args.date
    if args.measure:
        # Handle multiple measures for bar_multi_measure template
        if len(args.measure) == 1:
            field_overrides["measure"] = args.measure[0]
        else:
            # Map to measure_1, measure_2, etc.
            for i, measure in enumerate(args.measure, 1):
                field_overrides[f"measure_{i}"] = measure
    if args.stage:
        field_overrides["stage"] = args.stage
    if args.count:
        field_overrides["count"] = args.count
    if args.x_measure:
        field_overrides["x_measure"] = args.x_measure
    if args.y_measure:
        field_overrides["y_measure"] = args.y_measure
    if args.size_measure:
        field_overrides["size_measure"] = args.size_measure
    if args.label_measure:
        field_overrides["label_measure"] = args.label_measure
    if args.row_dim:
        field_overrides["row_dim"] = args.row_dim
    if args.col_dim:
        field_overrides["col_dim"] = args.col_dim
    if args.id_field:
        field_overrides["id_field"] = args.id_field
    if args.label_field:
        field_overrides["label_field"] = args.label_field
    if args.color_dim:
        field_overrides["color_dim"] = args.color_dim
    if args.stack_dim:
        field_overrides["stack_dim"] = args.stack_dim
    if args.latitude:
        field_overrides["latitude"] = args.latitude
    if args.longitude:
        field_overrides["longitude"] = args.longitude
    if args.label_dim:
        field_overrides["label_dim"] = args.label_dim
    if args.level1:
        field_overrides["level1"] = args.level1
    if args.level2:
        field_overrides["level2"] = args.level2
    if args.link_measure:
        field_overrides["link_measure"] = args.link_measure
    if args.link_color_measure:
        field_overrides["link_color_measure"] = args.link_color_measure
    if args.level2_color_dim:
        field_overrides["level2_color_dim"] = args.level2_color_dim
    if args.level3:
        field_overrides["level3"] = args.level3
    
    # Auto-select chart type if requested
    if args.auto_select:
        # Discover SDM fields
        print(f"Discovering fields from SDM '{args.sdm_name}'...", file=sys.stderr)
        sdm_fields = discover_sdm_fields(args.sdm_name)
        
        # Build list of selected field names from CLI args
        selected_fields = list(field_overrides.values()) if field_overrides else None
        
        # Analyze and recommend
        analysis = analyze_fields_for_chart_selection(
            sdm_fields,
            selected_field_names=selected_fields
        )
        
        if not analysis["recommended_template"]:
            print(f"Error: Could not determine chart type. {analysis['reasoning']}", file=sys.stderr)
            sys.exit(1)
        
        print(f"Recommended chart type: {analysis['recommended_template']}", file=sys.stderr)
        print(f"Reasoning: {analysis['reasoning']}", file=sys.stderr)
        args.template = analysis["recommended_template"]
        
        # Update field overrides with recommended mappings if auto-match is also enabled
        if args.auto_match:
            for template_field, sdm_field in analysis["field_mappings"].items():
                if template_field not in field_overrides:
                    field_overrides[template_field] = sdm_field
    
    # Load overrides if provided
    overrides = None
    if args.overrides:
        with open(args.overrides) as f:
            overrides = json.load(f)

    # Apply template
    viz_json = apply_template(
        template_name=args.template,
        sdm_name=args.sdm_name,
        sdm_label=args.sdm_label,
        workspace_name=args.workspace_name,
        workspace_label=args.workspace_label,
        name=args.name,
        label=args.label,
        field_overrides=field_overrides if field_overrides else None,
        auto_match=args.auto_match,
        overrides=overrides,
    )
    
    # Validate before POST
    if args.post:
        validation_results = validate(viz_json)
        failures = [r for r in validation_results if not r.ok]
        if failures:
            print("Validation failed before POST:", file=sys.stderr)
            for r in failures:
                print(f"  [FAIL] {r.rule}: {r.message}", file=sys.stderr)
                if r.fix:
                    print(f"         Fix: {r.fix}", file=sys.stderr)
            print("\nVisualization JSON was not posted to API.", file=sys.stderr)
            sys.exit(1)
        
        viz_url, actual_name = post_visualization(viz_json)
        if not actual_name:
            sys.exit(1)
    
    # Output JSON
    output = json.dumps(viz_json, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
            f.write("\n")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
