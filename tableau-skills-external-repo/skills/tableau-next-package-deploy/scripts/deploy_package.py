#!/usr/bin/env python3
"""
Deploy a Tableau Next dashboard package to a Salesforce org using the Package & Deploy API.

Fetches credentials via Salesforce CLI (sf). Polls deployment status until complete.

Usage:
    python deploy_package.py --org myorg --package tableauNext/Sales_package.json
    python deploy_package.py --org myorg --package package.json --workspace-label "Sales" --sdm-api-name Sales_SDM
    python deploy_package.py --org myorg --package package.json --dry-run  # Validate only
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

# Deployment can take several minutes; poll every 10 seconds
DEPLOY_TIMEOUT = 600
POLL_INTERVAL = 10
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


def build_deploy_payload(args: argparse.Namespace, package_data: dict) -> dict:
    """Build the deployment request payload."""
    payload = {
        "package_data": package_data,
        "workspace_choice": args.workspace_choice,
        "sdm_choice": args.sdm_choice,
        "sdm_api_name": args.sdm_api_name,
        "dry_run": args.dry_run,
        "skip_validation": args.skip_validation,
    }
    if args.workspace_choice == "create":
        payload["workspace_label"] = args.workspace_label
    else:
        payload["workspace_api_name"] = args.workspace_api_name
    if args.dependency_map:
        payload["dependency_map"] = args.dependency_map
    return payload


def main():
    parser = argparse.ArgumentParser(description="Deploy a Tableau Next dashboard package")
    parser.add_argument("--org", required=True, help="Salesforce org alias")
    parser.add_argument("--package", required=True, help="Path to package JSON file")
    parser.add_argument("--workspace-choice", choices=["create", "existing"], default="create")
    parser.add_argument("--workspace-api-name", help="Required if workspace-choice is existing")
    parser.add_argument("--workspace-label", help="Label for new workspace (default from package filename)")
    parser.add_argument("--sdm-choice", choices=["create", "existing"], default="create")
    parser.add_argument("--sdm-api-name", help="SDM API name (default from package filename)")
    parser.add_argument("--dependency-map", help="JSON string: field mapping for existing SDM")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not deploy")
    parser.add_argument("--skip-validation", action="store_true", help="Skip pre-deployment validation")
    parser.add_argument("--timeout", type=int, default=DEPLOY_TIMEOUT, help="Max seconds to wait")
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

    if args.dependency_map:
        try:
            args.dependency_map = json.loads(args.dependency_map)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid dependency-map JSON: {e}", file=sys.stderr)
            sys.exit(1)

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

    try:
        import requests
    except ImportError:
        print("Error: pip install requests", file=sys.stderr)
        sys.exit(1)

    payload = build_deploy_payload(args, package_data)
    deploy_url = f"{api_base}/v1/deployment/deploy"

    resp = requests.post(deploy_url, json=payload, headers=headers, timeout=API_TIMEOUT)
    if resp.status_code == 401:
        print("Error: Authentication failed. Try: sf org login web --alias <org>", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    result = resp.json()

    job_id = result.get("job_id")
    if not job_id:
        if result.get("status") == "dry_run_complete":
            valid = result.get("valid", False)
            print("Validation complete.")
            print(f"  Valid: {valid}")
            if result.get("errors"):
                print("  Errors:", result["errors"])
            if result.get("warnings"):
                print("  Warnings:", result["warnings"])
            sys.exit(0 if valid else 1)
        print("Error: API did not return job_id", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("Dry-run validation submitted; async validation not polled.")
        return

    print(f"Deployment started: {job_id}")
    status_url = f"{api_base}/v1/deployment/deploy/status/{job_id}"
    start = time.time()
    while time.time() - start < args.timeout:
        st_resp = requests.get(status_url, headers=headers, timeout=30)
        st_resp.raise_for_status()
        status = st_resp.json()
        s = status.get("status", "")
        if "steps" in status:
            for step in status["steps"]:
                print(f"  {step}")
        if s == "completed":
            print("Deployment completed.")
            if status.get("workspace_api_name"):
                print(f"  Workspace: {status['workspace_api_name']}")
            sys.exit(0)
        if s == "failed":
            print(f"Deployment failed: {status.get('error', 'Unknown')}", file=sys.stderr)
            sys.exit(1)
        time.sleep(POLL_INTERVAL)

    print("Error: Deployment timeout", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
