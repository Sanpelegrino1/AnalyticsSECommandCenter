#!/usr/bin/env python3
"""
Package a Tableau Next dashboard from a Salesforce org using the Package & Deploy API.

Fetches credentials via Salesforce CLI (sf).

Usage:
    python package_dashboard.py --org myorg --dashboard Sales_Dashboard [--output tableauNext/Sales_package.json]
    python package_dashboard.py --org myorg --list  # List available dashboards
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

# HTTP timeout: packaging typically completes within 2 minutes for complex dashboards
API_TIMEOUT = 120

DEFAULT_API_BASE = "https://next-package-deploy.demo.tableau.com/api"
DEFAULT_CLIENT_ID = "tableau-package-deploy"
ENV_API_BASE = "TABNEXT_API_BASE"


def get_sf_credentials(org_alias: str) -> Tuple[str, str]:
    """Get access token and instance URL from Salesforce CLI."""
    try:
        result = subprocess.run(
            ["sf", "org", "display", "--target-org", org_alias, "--json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        data = json.loads(result.stdout)
        token = data.get("result", {}).get("accessToken")
        instance = data.get("result", {}).get("instanceUrl")
        if not token or not instance:
            print(f"Error: Could not get credentials for org '{org_alias}'", file=sys.stderr)
            sys.exit(1)
        return token, instance
    except subprocess.CalledProcessError:
        print(f"Error: Org '{org_alias}' not found. Run: sf org list", file=sys.stderr)
        sys.exit(1)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error: Could not parse SF CLI output: {e}", file=sys.stderr)
        sys.exit(1)


def list_dashboards(api_base: str, headers: dict) -> list:
    """List available dashboards from the org."""
    url = f"{api_base.rstrip('/')}/v1/dashboards/list"
    try:
        import requests
    except ImportError:
        print("Error: pip install requests", file=sys.stderr)
        sys.exit(1)

    resp = requests.get(url, headers=headers, timeout=API_TIMEOUT)
    resp.raise_for_status()
    result = resp.json()
    return result.get("dashboards", [])


def package_dashboard(api_base: str, headers: dict, dashboard_api_name: str) -> dict:
    """Package a dashboard and return the API response."""
    url = f"{api_base.rstrip('/')}/v1/dashboards/package"
    try:
        import requests
    except ImportError:
        print("Error: pip install requests", file=sys.stderr)
        sys.exit(1)

    payload = {"dashboard_api_name": dashboard_api_name}
    resp = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)

    if resp.status_code == 404:
        print(f"Error: Dashboard '{dashboard_api_name}' not found. Use --list to see available dashboards.", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 401:
        print("Error: Authentication failed. Try: sf org login web --alias <org>", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Package a Tableau Next dashboard")
    parser.add_argument("--org", required=True, help="Salesforce org alias")
    parser.add_argument("--dashboard", help="Dashboard API name (e.g. Sales_Dashboard)")
    parser.add_argument("--list", action="store_true", help="List available dashboards")
    parser.add_argument("--output", help="Output JSON path (default: tableauNext/{name}_package.json)")
    parser.add_argument("--api-base", default=os.getenv(ENV_API_BASE, DEFAULT_API_BASE), help="API base URL")
    parser.add_argument("--client-id", default=DEFAULT_CLIENT_ID, help="Client ID for requests")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    if not api_base.endswith("/api"):
        api_base = f"{api_base}/api"

    token, instance = get_sf_credentials(args.org)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Instance-Url": instance,
        "X-Client-Id": args.client_id,
        "Content-Type": "application/json",
    }

    if args.list:
        dashboards = list_dashboards(api_base, headers)
        if not dashboards:
            print("No dashboards found.")
        else:
            print(f"Found {len(dashboards)} dashboard(s):")
            for d in dashboards:
                print(f"  - {d.get('apiName', '?')}: {d.get('label', 'No label')}")
        return

    if not args.dashboard:
        print("Error: --dashboard required (or use --list)", file=sys.stderr)
        sys.exit(1)

    result = package_dashboard(api_base, headers, args.dashboard)
    package_data = result.get("package_data")
    if not package_data:
        print("Error: API did not return package_data", file=sys.stderr)
        sys.exit(1)

    out_path = args.output or f"tableauNext/{args.dashboard}_package.json"
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(package_data, f, indent=2, ensure_ascii=False)

    print(f"Package saved to: {path}")
    print(f"Size: {len(json.dumps(package_data)):,} bytes")


if __name__ == "__main__":
    main()
