# Authentication Guide for Tableau Next API

Easy authentication using Salesforce CLI - no manual token copy/paste needed!

## Quick Start (Recommended)

### Prerequisites

- Salesforce CLI installed (`sf` command)
- Authenticated org with alias (e.g., `sf org login web --alias myorg`)
- `jq` installed for JSON parsing (`brew install jq` on Mac)

### One-Time Setup

Set environment variables for your org:

```bash
export SF_ORG=myorg  # Your SF CLI org alias

# Get credentials automatically
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

Now use in all API calls:

```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v65.0/ssot/semantic/models" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

---

## Helper Script (Copy & Use)

Create `tableau-api.sh` for easy API calls:

```bash
#!/bin/bash
# tableau-api.sh - Easy Tableau Next API calls using SF CLI
#
# Usage:
#   ./tableau-api.sh myorg GET /ssot/semantic/models
#   ./tableau-api.sh myorg POST /tableau/visualizations viz.json

set -e

ORG_ALIAS=${1}
METHOD=${2}
ENDPOINT=${3}
DATA_FILE=${4}

if [ -z "$ORG_ALIAS" ] || [ -z "$METHOD" ] || [ -z "$ENDPOINT" ]; then
    echo "Usage: $0 <org-alias> <GET|POST|PATCH|DELETE> <endpoint> [data-file]"
    echo ""
    echo "Examples:"
    echo "  $0 myorg GET /ssot/semantic/models"
    echo "  $0 myorg POST /tableau/visualizations viz.json"
    exit 1
fi

# Get credentials from SF CLI
echo "🔐 Getting credentials for org: $ORG_ALIAS..." >&2
ORG_INFO=$(sf org display --target-org $ORG_ALIAS --json 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "❌ Error: Org '$ORG_ALIAS' not found. Run: sf org list" >&2
    exit 1
fi

TOKEN=$(echo $ORG_INFO | jq -r '.result.accessToken')
INSTANCE=$(echo $ORG_INFO | jq -r '.result.instanceUrl')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "❌ Error: Could not get access token. Try: sf org login web --alias $ORG_ALIAS" >&2
    exit 1
fi

# Build full URL
FULL_URL="${INSTANCE}/services/data/v65.0${ENDPOINT}"

# Add minorVersion for Tableau endpoints
if [[ "$ENDPOINT" == *"/tableau/"* ]]; then
    if [[ "$ENDPOINT" != *"?"* ]]; then
        FULL_URL="${FULL_URL}?minorVersion=11"
    else
        FULL_URL="${FULL_URL}&minorVersion=11"
    fi
fi

echo "🚀 Calling: $METHOD $FULL_URL" >&2
echo "" >&2

# Make API call
if [ -z "$DATA_FILE" ]; then
    # GET/DELETE without body
    curl -s -X $METHOD \
        "$FULL_URL" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" | jq '.'
else
    # POST/PATCH with body
    if [ ! -f "$DATA_FILE" ]; then
        echo "❌ Error: File not found: $DATA_FILE" >&2
        exit 1
    fi
    
    curl -s -X $METHOD \
        "$FULL_URL" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d @"$DATA_FILE" | jq '.'
fi
```

**Make it executable:**
```bash
chmod +x tableau-api.sh
```

**Usage Examples:**

```bash
# List semantic models
./tableau-api.sh myorg GET /ssot/semantic/models

# Get specific SDM
./tableau-api.sh myorg GET /ssot/semantic/models/Sales_Analytics_Model

# Create visualization
./tableau-api.sh myorg POST /tableau/visualizations revenue_by_region.json

# List dashboards
./tableau-api.sh myorg GET /tableau/dashboards
```

---

## Python Helper Class

For Python users, save as `tableau_api.py`:

```python
#!/usr/bin/env python3
"""Tableau Next API helper using Salesforce CLI credentials."""

import subprocess
import json
import requests
from typing import Optional, Dict, Any


class TableauNextAPI:
    """Easy Tableau Next API calls using SF CLI org aliases."""
    
    def __init__(self, org_alias: str = 'default'):
        """Initialize with SF CLI org alias."""
        self.org_alias = org_alias
        self._load_credentials()
    
    def _load_credentials(self):
        """Get credentials from SF CLI."""
        try:
            result = subprocess.run(
                ['sf', 'org', 'display', '--target-org', self.org_alias, '--json'],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            self.token = data['result']['accessToken']
            self.instance = data['result']['instanceUrl']
            self.base_url = f"{self.instance}/services/data/v65.0"
        except subprocess.CalledProcessError:
            raise ValueError(f"Org '{self.org_alias}' not found. Run: sf org list")
        except (KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Could not parse SF CLI output: {e}")
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        add_minor_version: bool = False
    ) -> Dict[str, Any]:
        """Make authenticated API request."""
        url = f"{self.base_url}{endpoint}"
        
        # Add minorVersion for Tableau endpoints
        if '/tableau/' in endpoint and add_minor_version:
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}minorVersion=11"
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json() if response.text else {}
    
    # Discovery methods
    
    def list_semantic_models(self) -> Dict[str, Any]:
        """List all semantic models."""
        return self._request('GET', '/ssot/semantic/models')
    
    def get_semantic_model(self, sdm_name: str) -> Dict[str, Any]:
        """Get semantic model definition."""
        return self._request('GET', f'/ssot/semantic/models/{sdm_name}')
    
    def list_dashboards(self) -> Dict[str, Any]:
        """List all dashboards."""
        return self._request('GET', '/tableau/dashboards')
    
    def list_visualizations(self) -> Dict[str, Any]:
        """List all visualizations."""
        return self._request('GET', '/tableau/visualizations')
    
    # Creation methods
    
    def create_visualization(self, viz_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new visualization."""
        return self._request(
            'POST',
            '/tableau/visualizations',
            data=viz_data,
            add_minor_version=True
        )
    
    def create_dashboard(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dashboard."""
        return self._request(
            'POST',
            '/tableau/dashboards',
            data=dashboard_data,
            add_minor_version=True
        )
    
    def create_workspace(self, workspace_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workspace."""
        return self._request('POST', '/tableau/workspaces', data=workspace_data)


# Example usage
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python tableau_api.py <org-alias>")
        sys.exit(1)
    
    org = sys.argv[1]
    api = TableauNextAPI(org)
    
    print(f"✓ Connected to: {api.instance}")
    print(f"\n📊 Semantic Models:")
    
    models = api.list_semantic_models()
    for model in models.get('semanticModels', [])[:5]:
        print(f"  - {model.get('label')} ({model.get('apiName')})")
```

**Usage:**

```python
from tableau_api import TableauNextAPI

# Initialize with org alias
api = TableauNextAPI('myorg')

# List semantic models
models = api.list_semantic_models()

# Get specific SDM
sdm = api.get_semantic_model('Sales_Analytics_Model')

# Create visualization
viz_data = {...}  # Your visualization JSON
result = api.create_visualization(viz_data)
print(f"Created: {result['id']}")
```

---

## Environment Variables Pattern

For scripts and CI/CD, set once and reuse:

```bash
# .env file or in ~/.bashrc
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

Then in any script:

```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v65.0/ssot/semantic/models" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Refresh token** (tokens expire after 2 hours):

```bash
# Create refresh script: refresh-token.sh
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
echo "✓ Token refreshed for $SF_ORG"
```

---

## Manual Token (For CI/CD)

If you can't use SF CLI, get a token manually:

### Option 1: Connected App with JWT

```bash
# Use SF CLI to get token from JWT
sf org login jwt \
  --client-id YOUR_CONSUMER_KEY \
  --jwt-key-file server.key \
  --username user@example.com \
  --alias cicd-org

# Then use the helper scripts above
```

### Option 2: Manual OAuth Flow

1. Create Connected App in Salesforce Setup
2. Get authorization code via web flow
3. Exchange for access token
4. Use token in API calls

See: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_oauth_and_connected_apps.htm

---

## Troubleshooting

### "Org not found"

```bash
# List available orgs
sf org list

# Login to new org
sf org login web --alias myorg
```

### "Access token is null"

Your org session expired:

```bash
sf org login web --alias myorg
```

### "jq: command not found"

Install jq:

```bash
# Mac
brew install jq

# Linux
sudo apt-get install jq

# Windows (via Chocolatey)
choco install jq
```

### Token expired (after 2 hours)

Tokens auto-refresh with SF CLI:

```bash
# Just re-export
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
```

---

## Quick Reference

| Task | Command |
|------|---------|
| List orgs | `sf org list` |
| Login | `sf org login web --alias myorg` |
| Get token | `sf org display --target-org myorg --json \| jq -r '.result.accessToken'` |
| List SDMs | `./tableau-api.sh myorg GET /ssot/semantic/models` |
| Create viz | `./tableau-api.sh myorg POST /tableau/visualizations viz.json` |
| Python | `api = TableauNextAPI('myorg')` |

---

## Next Steps

With authentication set up, proceed to:
1. [SKILL.md](SKILL.md) - Main authoring workflow
2. [chart-catalog.md](chart-catalog.md) - Chart templates
3. [examples.md](examples.md) - Complete workflows

**All examples in this skill now assume you have SF CLI credentials available!**
