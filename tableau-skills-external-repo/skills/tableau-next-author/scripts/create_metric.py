#!/usr/bin/env python3
"""Create semantic metrics on semantic models.

Metrics reference calculated fields or table fields via measurementReference, require a
time dimension, and can carry native metric filters.

Usage:
        # Step 1: Create calculated field first when you need reusable semantic logic
    python scripts/create_calc_field.py \\
      --sdm Sales_Cloud12_backward \\
      --type measurement \\
      --name Total_Revenue_clc \\
      --label "Total Revenue" \\
      --expression "SUM([Amount])" \\
      --aggregation Sum

    # Step 2: Create metric referencing the calculated field
    python scripts/create_metric.py \\
      --sdm Sales_Cloud12_backward \\
      --name Total_Revenue_mtc \\
      --label "Total Revenue" \\
      --calculated-field Total_Revenue_clc \\
      --time-field Close_Date \\
      --time-table Opportunity_TAB_Sales_Cloud

        # Or create a direct filtered metric variant by copying an existing metric's
        # filters array into a JSON file and passing it through unchanged.
        python scripts/create_metric.py \\
            --sdm Sales_Cloud12_backward \\
            --name Total_Revenue_Last_60_Days_mtc \\
            --label "Total Revenue Last 60 Days" \\
            --calculated-field Total_Revenue_clc \\
            --time-field Close_Date \\
            --time-table Opportunity_TAB_Sales_Cloud \\
            --filters-file metric-filters.json

        # Dry-run (show payload without POSTing)
    python scripts/create_metric.py \\
      --sdm Sales_Cloud12_backward \\
      --name Account_Count_mtc \\
      --label "Account Count" \\
      --calculated-field Account_Count_clc \\
      --time-field Close_Date \\
      --time-table Opportunity_TAB_Sales_Cloud \\
      --dry-run
"""

import argparse
import json
import sys
from typing import Any, Dict, Optional

from lib.metric_templates import (
    METRIC_TEMPLATE_REGISTRY,
    build_semantic_metric,
    validate_metric,
)
from lib.sf_api import calculated_field_endpoint, get_credentials, sf_post


def parse_metric_filters(filter_json_args: Optional[list[str]], filters_file: Optional[str]) -> Optional[list[dict[str, Any]]]:
    """Parse metric filters from repeated JSON args and/or a JSON file.

    The filter schema is API-defined and can vary by use case. Callers should inspect an
    existing live metric first, then pass the copied filter objects through unchanged.
    """
    parsed_filters: list[dict[str, Any]] = []

    if filters_file:
        try:
            with open(filters_file, "r", encoding="utf-8") as handle:
                file_value = json.load(handle)
        except OSError as exc:
            print(f"Error: Unable to read filters file '{filters_file}': {exc}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as exc:
            print(f"Error: Invalid JSON in filters file '{filters_file}': {exc}", file=sys.stderr)
            sys.exit(1)

        if not isinstance(file_value, list) or any(not isinstance(item, dict) for item in file_value):
            print("Error: --filters-file must contain a JSON array of filter objects", file=sys.stderr)
            sys.exit(1)
        parsed_filters.extend(file_value)

    for raw_filter in filter_json_args or []:
        try:
            filter_value = json.loads(raw_filter)
        except json.JSONDecodeError as exc:
            print(f"Error: Invalid JSON in --filter-json: {exc}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(filter_value, dict):
            print("Error: Each --filter-json value must be a single JSON object", file=sys.stderr)
            sys.exit(1)
        parsed_filters.append(filter_value)

    return parsed_filters or None


def resolve_expression(
    template: Optional[str],
    template_args: Optional[str],
    expression: Optional[str]
) -> str:
    """Resolve expression from template or use provided expression.

    Args:
        template: Template name (sum, avg, win_rate, etc.)
        template_args: JSON string with template arguments
        expression: Direct expression string

    Returns:
        Resolved expression string
    """
    if template:
        if template not in METRIC_TEMPLATE_REGISTRY:
            print(
                f"Error: Unknown template '{template}'. Valid: {', '.join(METRIC_TEMPLATE_REGISTRY.keys())}",
                file=sys.stderr
            )
            sys.exit(1)

        if not template_args:
            print(f"Error: --template-args required when using --template", file=sys.stderr)
            sys.exit(1)

        try:
            args = json.loads(template_args)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --template-args: {e}", file=sys.stderr)
            sys.exit(1)

        template_func = METRIC_TEMPLATE_REGISTRY[template]
        try:
            return template_func(**args)
        except TypeError as e:
            print(f"Error: Template '{template}' arguments mismatch: {e}", file=sys.stderr)
            print(
                f"Expected arguments: {template_func.__code__.co_varnames[:template_func.__code__.co_argcount]}",
                file=sys.stderr
            )
            sys.exit(1)

    if expression:
        return expression

    print("Error: Either --template or --expression must be provided", file=sys.stderr)
    sys.exit(1)


def normalize_api_name(name: str) -> str:
    """Ensure API name ends with _mtc and doesn't have double underscores.
    
    Salesforce API names cannot contain double underscores (__).

    Args:
        name: API name

    Returns:
        Normalized API name (no double underscores, ends with _mtc)
    """
    name = name.strip()
    # Replace double underscores with single underscore
    while "__" in name:
        name = name.replace("__", "_")
    if not name.endswith("_mtc"):
        return f"{name}_mtc"
    return name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create semantic metrics on semantic models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--sdm", required=True, help="Semantic model API name")
    parser.add_argument("--name", required=True, help="API name (auto-appends _mtc if missing)")
    parser.add_argument("--label", required=True, help="Display label")

    # Calculated field reference (preferred method)
    parser.add_argument("--calculated-field", required=True, help="API name of calculated field to reference")
    
    # Time dimension (required for metrics)
    parser.add_argument("--time-field", required=True, help="Time dimension field API name (e.g., Close_Date)")
    parser.add_argument("--time-table", required=True, help="Time dimension table API name (e.g., Opportunity_TAB_Sales_Cloud)")

    # Legacy expression support (deprecated - metrics should reference calculated fields)
    expr_group = parser.add_mutually_exclusive_group(required=False)
    expr_group.add_argument("--expression", help="[DEPRECATED] Tableau formula expression - use --calculated-field instead")
    expr_group.add_argument("--template", choices=list(METRIC_TEMPLATE_REGISTRY.keys()), help="[DEPRECATED] Template name - use --calculated-field instead")

    parser.add_argument("--template-args", help="JSON dict of template arguments (required with --template)")
    parser.add_argument("--description", default="", help="Field description")
    parser.add_argument(
        "--filter-json",
        action="append",
        help="Metric filter as a JSON object. Repeat to add multiple filters.",
    )
    parser.add_argument(
        "--filters-file",
        help="Path to a JSON file containing an array of metric filter objects.",
    )

    # Additional dimensions for breakdown analysis
    parser.add_argument(
        "--additional-dimension",
        action="append",
        help="Additional dimension for breakdown analysis (format: fieldApiName:tableApiName). Can be repeated multiple times."
    )

    parser.add_argument("--dry-run", action="store_true", help="Show payload without POSTing")
    parser.add_argument("-o", "--output", help="Write JSON to file (default: stdout)")

    args = parser.parse_args()

    # Use calculated field reference (required)
    calculated_field_api_name = args.calculated_field
    
    # Warn if legacy expression/template args are provided
    if args.expression or args.template:
        print("Warning: --expression and --template are deprecated. Using --calculated-field instead.", file=sys.stderr)

    # Parse additional dimensions
    additional_dims = []
    if args.additional_dimension:
        for dim_spec in args.additional_dimension:
            if ":" not in dim_spec:
                print(
                    f"Error: Invalid format for --additional-dimension: {dim_spec}. Expected format: fieldApiName:tableApiName",
                    file=sys.stderr
                )
                sys.exit(1)
            field_name, table_name = dim_spec.split(":", 1)
            additional_dims.append({
                "tableFieldReference": {
                    "fieldApiName": field_name.strip(),
                    "tableApiName": table_name.strip()
                }
            })

    metric_filters = parse_metric_filters(args.filter_json, args.filters_file)

    # Normalize API name
    api_name = normalize_api_name(args.name)

    # Validate
    is_valid, errors = validate_metric(
        api_name=api_name,
        expression=None  # No expression validation needed for calculated field reference
    )
    if not is_valid:
        print("Validation errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    # Build payload
    payload = build_semantic_metric(
        api_name=api_name,
        label=args.label,
        calculated_field_api_name=calculated_field_api_name,
        time_dimension_field_name=args.time_field,
        time_dimension_table_name=args.time_table,
        description=args.description,
        filters=metric_filters,
        additional_dimensions=additional_dims if additional_dims else None,
    )

    # Output payload
    output_json = json.dumps(payload, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
            f.write("\n")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(output_json)

    # Dry-run mode - exit before POST
    if args.dry_run:
        print("\n[Dry-run mode - payload shown above, not POSTed]", file=sys.stderr)
        return

    # POST to API
    token, instance = get_credentials()
    endpoint = calculated_field_endpoint(args.sdm, "metrics")

    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    if resp:
        actual_name = resp.get('apiName', api_name)
        print(f"\n✓ Created semantic metric: {api_name}", file=sys.stderr)
        if actual_name != api_name:
            print(f"  → Actual API name: {actual_name}", file=sys.stderr)
        if "label" in resp:
            print(f"  Label: {resp['label']}", file=sys.stderr)
    else:
        print(f"\n✓ Semantic metric created successfully", file=sys.stderr)


if __name__ == "__main__":
    main()
