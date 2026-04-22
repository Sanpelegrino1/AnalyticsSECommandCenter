# Tableau Next Package & Deploy Examples

Real-world workflows and CLI one-liners. Use when implementing migrations or automation.

## Table of Contents

- [Quick Package & Deploy](#quick-package--deploy)
- [Dev to QA to Prod Pipeline](#dev-to-qa-to-prod-pipeline)
- [Existing SDM Deployment](#existing-sdm-deployment)
- [Validation Before Deploy](#validation-before-deploy)
- [Bash One-Liners](#bash-one-liners)

---

## Quick Package & Deploy

**Scenario**: Package from dev org, deploy to QA.

```bash
# 1. Get API base
export API_BASE="${TABNEXT_API_BASE:-https://next-package-deploy.demo.tableau.com/api}"

# 2. Package from dev
python scripts/package_dashboard.py --org dev --dashboard Sales_Dashboard --output tableauNext/Sales_package.json

# 3. Validate against QA
python scripts/validate_package.py --org qa --package tableauNext/Sales_package.json

# 4. Deploy to QA
python scripts/deploy_package.py --org qa --package tableauNext/Sales_package.json
```

---

## Dev to QA to Prod Pipeline

**Scenario**: Migrate dashboard through environments.

```bash
# Package once from dev
python scripts/package_dashboard.py --org dev --dashboard Executive_Overview --output tableauNext/Executive_Overview_package.json

# Deploy to QA (creates new workspace + SDM each time)
python scripts/deploy_package.py --org qa --package tableauNext/Executive_Overview_package.json

# Deploy to prod with explicit names
python scripts/deploy_package.py --org prod --package tableauNext/Executive_Overview_package.json \
  --workspace-label "Executive Overview" --sdm-api-name Executive_Overview_SDM
```

---

## Existing SDM Deployment

**Scenario**: Deploy to an org that already has the semantic model. Map package fields to target SDM fields.

```bash
# 1. List existing SDMs
curl -s -X GET "$API_BASE/v1/deployment/semantic-models" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Instance-Url: $INSTANCE" \
  -H "Content-Type: application/json" | jq '.semantic_models'

# 2. Deploy with dependency map (field mapping)
python scripts/deploy_package.py --org target --package package.json \
  --sdm-choice existing --sdm-api-name Existing_Sales_SDM \
  --workspace-choice existing --workspace-api-name My_Workspace \
  --dependency-map '{"Package_Field_A": "Target_Field_X", "Package_Field_B": "Target_Field_Y"}'
```

---

## Validation Before Deploy

**Scenario**: Catch errors before deploying to production.

**Option A**: Use validate script
```bash
python scripts/validate_package.py --org prod --package tableauNext/Sales_package.json
```

**Option B**: Use dry-run in deploy
```bash
python scripts/deploy_package.py --org prod --package tableauNext/Sales_package.json --dry-run
```

**Option C**: Direct API call
```bash
# Build deploy_payload.json with package_data, workspace_choice, sdm_choice, sdm_api_name, etc.
# Add "dry_run": true
curl -s -X POST "$API_BASE/v1/deployment/deploy" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Instance-Url: $INSTANCE" \
  -H "Content-Type: application/json" \
  -d @deploy_payload.json
```

---

## Bash One-Liners

```bash
# List dashboards
TOKEN=$(sf org display --target-org myorg --json | jq -r '.result.accessToken')
INSTANCE=$(sf org display --target-org myorg --json | jq -r '.result.instanceUrl')
curl -s "$API_BASE/v1/dashboards/list" -H "Authorization: Bearer $TOKEN" -H "X-Instance-Url: $INSTANCE" | jq '.dashboards'

# Package (response has package_data - save manually or use script)
curl -s -X POST "$API_BASE/v1/dashboards/package" \
  -H "Authorization: Bearer $TOKEN" -H "X-Instance-Url: $INSTANCE" \
  -H "Content-Type: application/json" \
  -d '{"dashboard_api_name":"Sales_Dashboard"}' | jq '.package_data' > package.json
```
