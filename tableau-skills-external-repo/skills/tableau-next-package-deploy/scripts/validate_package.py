#!/usr/bin/env python3
"""
Validate a Tableau Next dashboard package against a target org before deployment.

Uses the validate-package endpoint. Does not deploy.

Usage:
    python validate_package.py --org myorg --package tableauNext/Sales_package.json
    python validate_package.py --org myorg --package package.json --sdm-api-name Sales_SDM
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

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


def main():
    parser = argparse.ArgumentParser(description="Validate a Tableau Next dashboard package")
    parser.add_argument("--org", required=True, help="Salesforce org alias")
    parser.add_argument("--package", required=True, help="Path to package JSON file")
    parser.add_argument("--workspace-choice", choices=["create", "existing"], default="create")
    parser.add_argument("--workspace-api-name", help="Required if workspace-choice is existing")
    parser.add_argument("--workspace-label", help="Label for new workspace")
    parser.add_argument("--sdm-choice", choices=["create", "existing"], default="create")
    parser.add_argument("--sdm-api-name", help="SDM API name (default from package filename)")
    parser.add_argument("--api-base", default=os.getenv(ENV_API_BASE, DEFAULT_API_BASE))
    parser.add_argument("--client-id", default=DEFAULT_CLIENT_ID)
    args = parser.parse_args()

    if args.workspace_choice == "existing" and not args.workspace_api_name:
        print("Error: --workspace-api-name required when workspace-choice is existing", file=sys.stderr)
        sys.exit(1)

    pkg_path = Path(args.package)
    if not pkg_path.exists():
        print(f"Error: Package file not found: {pkg_path}", file=sys.stderr)
        sys.exit(1)

    with open(pkg_path, "r", encoding="utf-8") as f:
        package_data = json.load(f)

    base_name = pkg_path.stem.replace("_package", "")
    args.workspace_label = args.workspace_label or f"{base_name.replace('_', ' ')} Workspace"
    args.sdm_api_name = args.sdm_api_name or f"{base_name}_SDM"

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

    payload = {
        "package_data": package_data,
        "workspace_choice": args.workspace_choice,
        "sdm_choice": args.sdm_choice,
        "sdm_api_name": args.sdm_api_name,
        "workspace_label": args.workspace_label if args.workspace_choice == "create" else None,
        "workspace_api_name": args.workspace_api_name if args.workspace_choice == "existing" else None,
    }

    try:
        import requests
    except ImportError:
        print("Error: pip install requests", file=sys.stderr)
        sys.exit(1)

    url = f"{api_base}/v1/deployment/validate-package"
    resp = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
    if resp.status_code == 401:
        print("Error: Authentication failed. Try: sf org login web --alias <org>", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    result = resp.json()

    valid = result.get("valid", False)
    print("Validation result:")
    print(f"  Valid: {valid}")
    if result.get("errors"):
        print("  Errors:")
        for e in result["errors"]:
            print(f"    - {e}")
    if result.get("warnings"):
        print("  Warnings:")
        for w in result["warnings"]:
            print(f"    - {w}")

    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
