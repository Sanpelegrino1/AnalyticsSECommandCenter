#!/usr/bin/env python3
"""Verify a Tableau Next dashboard's structure and references.

Usage:
    python scripts/verify_dashboard.py --dashboard-name Sales_Dashboard
    python scripts/verify_dashboard.py --dashboard-name Sales_Dashboard --org-alias myorg
"""

import argparse
import json
import subprocess
import sys
from typing import List, Optional, Tuple

from lib.sf_api import get_credentials, sf_get, dashboard_endpoint, visualization_endpoint


def get_env_vars_from_org(org_alias: str) -> dict:
    """Get SF_TOKEN and SF_INSTANCE from org display."""
    result = subprocess.run(
        ["sf", "org", "display", "--target-org", org_alias, "--json"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error getting org info: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    
    org_data = json.loads(result.stdout)
    result_data = org_data.get("result", {})
    return {
        "SF_TOKEN": result_data.get("accessToken", ""),
        "SF_INSTANCE": result_data.get("instanceUrl", ""),
    }


def verify_visualization_exists(viz_name: str, token: str, instance: str) -> Tuple[bool, Optional[str]]:
    """Verify that a visualization exists by GETting it from the API."""
    response = sf_get(token, instance, visualization_endpoint(viz_name))
    
    if response is None:
        return False, "Visualization not found or API request failed"
    
    if isinstance(response, dict) and "errorCode" in response:
        return False, response.get("message", "Unknown error")
    
    if isinstance(response, list) and len(response) > 0:
        if "errorCode" in response[0]:
            return False, response[0].get("message", "Unknown error")
    
    return True, None


def verify_dashboard(dashboard_name: str, token: str, instance: str) -> Tuple[bool, List[str]]:
    """Verify dashboard structure and references.
    
    Returns:
        (is_valid: bool, list_of_errors: List[str])
    """
    errors = []
    
    # GET dashboard from API
    response = sf_get(token, instance, dashboard_endpoint(dashboard_name))
    
    if response is None:
        return False, [f"Dashboard '{dashboard_name}' not found or API request failed"]
    
    # Check for API errors
    if isinstance(response, dict) and "errorCode" in response:
        return False, [f"Dashboard '{dashboard_name}' not found: {response.get('message', 'Unknown error')}"]
    
    if isinstance(response, list) and len(response) > 0:
        if "errorCode" in response[0]:
            return False, [f"Dashboard '{dashboard_name}' not found: {response[0].get('message', 'Unknown error')}"]
    
    if not isinstance(response, dict):
        return False, [f"Unexpected response format: {response}"]
    
    print(f"✓ Found dashboard: {response.get('label', dashboard_name)} ({response.get('id', 'unknown')})")
    
    # Verify required fields
    required_fields = ["name", "label", "workspaceIdOrApiName", "style", "layouts", "widgets"]
    for field in required_fields:
        if field not in response:
            errors.append(f"Missing required field: '{field}'")
    
    # Verify style.widgetStyle exists
    if "style" in response:
        if "widgetStyle" not in response["style"]:
            errors.append("Missing 'style.widgetStyle' - required for dashboard rendering")
    else:
        errors.append("Missing 'style' field")
    
    # Verify layouts structure
    layouts = response.get("layouts", [])
    if not layouts:
        errors.append("Dashboard has no layouts")
    else:
        layout = layouts[0]
        if "style" not in layout:
            errors.append("Layout missing 'style' field - required for dashboard rendering")
        if "pages" not in layout:
            errors.append("Layout missing 'pages' field")
        
        # Check layout grid constraints
        if "columnCount" in layout:
            column_count = layout["columnCount"]
            pages = layout.get("pages", [])
            for page_idx, page in enumerate(pages):
                widgets = page.get("widgets", [])
                for widget in widgets:
                    col = widget.get("column", 0)
                    colspan = widget.get("colspan", 0)
                    if col + colspan > column_count:
                        errors.append(
                            f"Page {page_idx}: Widget '{widget.get('name', 'unknown')}' exceeds grid bounds "
                            f"(column {col} + colspan {colspan} > {column_count})"
                        )
    
    # Verify widgets reference existing visualizations
    widgets = response.get("widgets", {})
    referenced_viz_names = set()
    referenced_metrics = set()
    
    for widget_key, widget in widgets.items():
        if not isinstance(widget, dict):
            continue
        
        widget_type = widget.get("type")
        source = widget.get("source", {})
        
        # Check source structure (should only have "name")
        if "source" in widget:
            invalid_keys = ["id", "label", "type"]
            for key in invalid_keys:
                if key in source:
                    errors.append(f"Widget '{widget_key}': source contains invalid key '{key}' (should only have 'name')")
        
        if widget_type == "visualization":
            viz_name = source.get("name")
            if viz_name:
                referenced_viz_names.add(viz_name)
                # Verify visualization exists
                exists, verify_error = verify_visualization_exists(viz_name, token, instance)
                if not exists:
                    errors.append(f"Widget '{widget_key}' references non-existent visualization '{viz_name}': {verify_error}")
        
        elif widget_type == "metric":
            metric_name = source.get("name")
            if metric_name:
                referenced_metrics.add(metric_name)
                # Note: We can't easily verify metrics exist without SDM context, so we'll just note them
        
        elif widget_type == "filter":
            # Filters should reference SDM, not visualizations
            sdm_name = source.get("name")
            if not sdm_name:
                errors.append(f"Widget '{widget_key}': filter missing SDM reference in source.name")
    
    # Report summary
    print(f"\nDashboard Structure:")
    print(f"  - Widgets: {len(widgets)}")
    print(f"  - Visualizations referenced: {len(referenced_viz_names)}")
    if referenced_viz_names:
        print(f"    {', '.join(sorted(referenced_viz_names))}")
    print(f"  - Metrics referenced: {len(referenced_metrics)}")
    if referenced_metrics:
        print(f"    {', '.join(sorted(referenced_metrics))}")
    
    return len(errors) == 0, errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify a Tableau Next dashboard's structure and references",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--dashboard-name", "-n",
        required=True,
        help="Dashboard API name (e.g., Sales_Dashboard)"
    )
    parser.add_argument(
        "--org-alias", "-o",
        help="Salesforce org alias (if not set, uses SF_TOKEN/SF_INSTANCE env vars)"
    )
    
    args = parser.parse_args()
    
    # Get credentials
    if args.org_alias:
        env_vars = get_env_vars_from_org(args.org_alias)
        import os
        os.environ.update(env_vars)
    
    token, instance = get_credentials()
    
    # Verify dashboard
    print(f"Verifying dashboard: {args.dashboard_name}\n")
    is_valid, errors = verify_dashboard(args.dashboard_name, token, instance)
    
    if is_valid:
        print("\n✓ All checks passed - dashboard structure is valid")
        sys.exit(0)
    else:
        print(f"\n✗ Validation failed ({len(errors)} error(s)):")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
