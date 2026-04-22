"""Salesforce org authentication and credential management.

Provides functions for authenticating to Salesforce orgs and managing
credentials via environment variables.
"""

import json
import os
import shutil
import subprocess
import sys
from typing import Tuple


def _resolve_sf_command() -> str | None:
    """Resolve the Salesforce CLI executable across platforms."""
    for candidate in ("sf", "sf.cmd", "sf.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _run_sf_org_display(org_alias: str) -> subprocess.CompletedProcess[str]:
    """Run `sf org display` with a Windows-safe executable resolution."""
    sf_command = _resolve_sf_command()
    if not sf_command:
        raise FileNotFoundError("Salesforce CLI executable not found in PATH")

    return subprocess.run(
        [sf_command, "org", "display", "--target-org", org_alias, "--json"],
        capture_output=True,
        text=True,
    )


def authenticate_to_org(org_alias: str) -> bool:
    """Authenticate to Salesforce org and set environment variables.
    
    Uses Salesforce CLI to authenticate and sets SF_TOKEN and SF_INSTANCE
    environment variables for use by other modules.
    
    Args:
        org_alias: Salesforce org alias (e.g., "GDO_TEST_001")
        
    Returns:
        True if authentication successful, False otherwise
        
    Raises:
        No exceptions raised - errors are printed to stderr and False is returned
    """
    os.environ["SF_ORG"] = org_alias

    # Allow callers to inject credentials explicitly, which is useful when the
    # CLI is not directly invokable from the Python process on Windows.
    if os.environ.get("SF_TOKEN") and os.environ.get("SF_INSTANCE"):
        print(f"✓ Using existing SF_TOKEN/SF_INSTANCE for org '{org_alias}'")
        return True

    try:
        result = _run_sf_org_display(org_alias)
    except FileNotFoundError as exc:
        print(f"✗ Error authenticating to org '{org_alias}': {exc}", file=sys.stderr)
        return False
    
    if result.returncode != 0:
        print(f"✗ Error authenticating to org '{org_alias}': {result.stderr}", file=sys.stderr)
        return False
    
    try:
        org_data = json.loads(result.stdout)
        os.environ["SF_TOKEN"] = org_data["result"]["accessToken"]
        os.environ["SF_INSTANCE"] = org_data["result"]["instanceUrl"]
        print(f"✓ Authenticated to org '{org_alias}'")
        return True
    except (json.JSONDecodeError, KeyError) as e:
        print(f"✗ Error parsing org data: {e}", file=sys.stderr)
        return False


def get_org_info(org_alias: str) -> Tuple[str, str]:
    """Get org access token and instance URL without setting environment variables.
    
    Args:
        org_alias: Salesforce org alias
        
    Returns:
        Tuple of (access_token, instance_url)
        
    Raises:
        ValueError: If authentication fails or org data cannot be parsed
    """
    if os.environ.get("SF_TOKEN") and os.environ.get("SF_INSTANCE"):
        return os.environ["SF_TOKEN"], os.environ["SF_INSTANCE"]

    try:
        result = _run_sf_org_display(org_alias)
    except FileNotFoundError as exc:
        raise ValueError(f"Failed to authenticate to org '{org_alias}': {exc}") from exc
    
    if result.returncode != 0:
        raise ValueError(f"Failed to authenticate to org '{org_alias}': {result.stderr}")
    
    try:
        org_data = json.loads(result.stdout)
        token = org_data["result"]["accessToken"]
        instance = org_data["result"]["instanceUrl"]
        return token, instance
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse org data: {e}")
