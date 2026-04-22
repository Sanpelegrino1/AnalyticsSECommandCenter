# Tableau Next Authoring Skill

A production-ready [Agent Skill](https://agentskills.io) that lets you create Tableau Next visualizations and dashboards via the Salesforce REST API, just by describing what you want in plain language.

> **API Version:** `v66.0` with `minorVersion=12`
> **Specification:** Compliant with [Agent Skills specification](https://agentskills.io/specification) for cross-platform portability

---

## What This Does

Once installed, you can ask Cursor:

> "Create a donut chart showing open pipeline by region using the Sales Intelligence SDM"

The AI agent will:
1. Discover available Semantic Data Models (SDMs) via the API
2. Identify the right fields (dimensions, measures, calculated fields)
3. Generate the correct v66.x JSON payload
4. POST it to Salesforce to create the visualization
5. Return the live URL

---

## Install

### Prerequisites

- [Cursor](https://cursor.sh) with Agent mode enabled
- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli)
  - macOS/Linux: `brew install sf`
  - Windows: Download from [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli)
- [jq](https://stedolan.github.io/jq/) (optional, for JSON parsing)
  - macOS/Linux: `brew install jq`
  - Windows: Download from [jq releases](https://github.com/jqlang/jq/releases) or use PowerShell's `ConvertFrom-Json`
- An authenticated Salesforce org with Tableau Next access

### One-Command Install

**macOS/Linux:**
```bash
git clone https://git.soma.salesforce.com/alaviron/tableau-skills.git
cd tableau-skills/skills/tableau-next-author
./install.sh                           # Cursor (default)
./install.sh --target claude           # Claude Code
./install.sh --target all              # All platforms
./install.sh --force                   # Overwrite without prompting
```

**Windows (PowerShell):**
```powershell
git clone https://git.soma.salesforce.com/alaviron/tableau-skills.git
cd tableau-skills/skills/tableau-next-author
.\install.ps1                          # Cursor (default)
.\install.ps1 -Target claude            # Claude Code
.\install.ps1 -Target all -Force        # All platforms, overwrite
```

Restart your agent after installation.

### Platform Paths

| Platform | macOS/Linux | Windows |
|----------|-------------|---------|
| Cursor | `~/.cursor/skills/` | `%USERPROFILE%\.cursor\skills\` |
| Claude Code | `~/.claude/skills/` | `%USERPROFILE%\.claude\skills\` |

### Manual Install

**Cursor:**
```bash
mkdir -p ~/.cursor/skills/tableau-next-author
cp -r . ~/.cursor/skills/tableau-next-author/
```

**Claude Code:**
```bash
mkdir -p ~/.claude/skills/tableau-next-author
cp -r . ~/.claude/skills/tableau-next-author/
```

---

## Quick Start

### 1. Authenticate

```bash
# Log in to your Salesforce org
sf org login web --alias myorg

# Export credentials for curl commands
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

See [references/authentication.md](references/authentication.md) for complete setup including OAuth flows and helper scripts.

### 2. Discover Your Data

```bash
# List all available Semantic Models
curl -X GET "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models" \
  -H "Authorization: Bearer ${SF_TOKEN}"

# Get fields for a specific SDM
curl -X GET "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/{SDM_API_NAME}" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

### 3. Ask Cursor to Build It

With the skill installed, open a Cursor chat and describe what you want:

```
Create a horizontal bar chart of Closed Won revenue by Region using my 
Sales_Intelligence_Model SDM. Sort descending. Use currency format.
```

The agent reads [SKILL.md](SKILL.md) as its instruction set and handles the rest.

---

## What's Included

### Core Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Main agent instruction file (agents read this automatically) |
| `README.md` | User-facing documentation (this file) |
| `install.sh` / `install.ps1` | Cross-platform installation scripts |

### Reference Documentation (`references/`)

All detailed documentation follows the [Agent Skills specification](https://agentskills.io/specification) and is organized in the `references/` directory:

| File | Purpose |
|------|---------|
| `workflow.md` | Step-by-step dashboard creation process (discovery → dashboard) |
| `templates-guide.md` | Template catalog, chart type decision matrix, and dashboard patterns |
| `scripts-guide.md` | Script usage, location, and automation guidance |
| `troubleshooting.md` | Common API errors and solutions catalog |
| `advanced-features.md` | Calculated fields and formula syntax reference |
| `chart-catalog.md` | Copy-paste chart templates (Vizql, Map, Flow) |
| `examples.md` | 3 complete industry examples (Sales, Marketing, HR) |
| `api-reference.md` | Full REST API endpoint reference |
| `authentication.md` | Auth setup guide + helper scripts |

### Automation Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `discover_sdm.py` | SDM field discovery (lists dimensions, measures, aggregation types) |
| `generate_viz.py` | Template-based viz JSON generator with style overrides |
| `generate_dashboard.py` | Dashboard JSON generator with filters, metrics, multi-page support |
| `create_dashboard.py` | Generic dashboard creation workflow (accepts viz specs, auto-generates vizzes, POSTs to API) |
| `generate_dashboard_pattern.py` | Dashboard pattern generator (f_layout, z_layout, etc.) |
| `apply_viz_template.py` | Create visualizations from templates with auto-select |
| `create_calc_field.py` | Create calculated measurements and dimensions on semantic models |
| `validate_viz.py` | Pre-POST validation (catches 16 common API errors) |
| `verify_dashboard.py` | Dashboard structure verification (validates references, visualizations, metrics) |
| `test_harness.py` | Integration test harness (verifies all chart types work) |

---

## Supported Chart Types

| Chart | `marks.panes.type` | `layout` | Use Case |
|-------|-------------------|----------|---------|
| Horizontal/Vertical Bar | `"Bar"` | `"Vizql"` | Compare categories |
| Donut | `"Donut"` | `"Vizql"` | Part-to-whole |
| Line | `"Line"` | `"Vizql"` | Trends over time |
| Table | `"Circle"` | `"Table"` | Detailed row data |
| Scatter | `"Circle"` | `"Vizql"` | Correlations |
| Text | `"Text"` | `"Vizql"` | Annotations |

---

## Testing

The project includes a comprehensive pytest-based test suite covering unit tests for library modules and integration tests for main scripts.

### Running Tests

```bash
# Run all tests
pytest tests/

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage report
pytest --cov=scripts/lib --cov-report=html

# Run specific test file
pytest tests/unit/test_validators.py
```

### Test Structure

```
tests/
├── unit/                    # Unit tests for library modules
│   ├── test_validators.py   # 17 validation rules
│   ├── test_templates.py    # Chart builders, inference functions
│   ├── test_dashboard_patterns.py  # Pattern builders, deduplication
│   ├── test_viz_templates.py # Field matching, chart recommendations
│   └── test_calc_field_templates.py  # Calculated field builders
├── integration/             # Integration tests for main scripts
│   └── test_generate_viz.py # JSON generation workflows
├── fixtures/                # Test data fixtures
│   ├── sample_viz_payloads.json
│   └── sample_sdm_responses.json
└── conftest.py              # Shared pytest fixtures
```

---

## v66.8 Key Changes from v65.11

If you used the v65.11 skill before, the main breaking changes in v66.8 are:

- **`marks.ALL` is gone** — replaced by `marks.panes` + `marks.headers`
- **Style structure changed**: `style.axis.fields.{key}`, `style.encodings.fields.{key}`, `style.headers` (was `allHeaders`)
- **Encoding field styles required**: any measure in `marks.panes.encodings` needs `style.encodings.fields.{key}: {"defaults": {"format": {}}}`
- **Palette validation**: sequential and diverging palettes have different allowed step properties

**Note:** This skill uses API v66.0 with `minorVersion=12`. If you're migrating from v65.11, see the troubleshooting guide for common breaking changes.

---

## API Endpoints (v66.0)

```
Discovery:
GET  /services/data/v66.0/ssot/semantic/models
GET  /services/data/v66.0/ssot/semantic/models/{apiName}

Creation:
POST /services/data/v66.0/tableau/visualizations?minorVersion=12
POST /services/data/v66.0/tableau/dashboards?minorVersion=12
POST /services/data/v66.0/tableau/workspaces
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-measurements
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-dimensions

Read/Update:
GET   /services/data/v66.0/tableau/visualizations/{id}?minorVersion=12
PATCH /services/data/v66.0/tableau/visualizations/{id}?minorVersion=12
GET   /services/data/v66.0/tableau/dashboards/{id}?minorVersion=12
PATCH /services/data/v66.0/tableau/dashboards/{id}?minorVersion=12
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `"encodings style is required for the F2 field"` | Add `"F2": {"defaults": {"format": {}}}` to `style.encodings.fields` |
| `"startToMiddleSteps isn't available with sequential palettes"` | Remove diverging step props from 2-color palettes |
| `"Value required for [fonts]"` | Include all 7 font definitions in `style.fonts` |
| `401 Unauthorized` | Token expired — re-run `sf org display` to refresh |
| Field not found | Check `apiName` vs `fieldName` in SDM response; use `apiName` |

---

## Contributing

1. Fork this repo
2. Make changes to the skill files
3. Test by asking Cursor to create a visualization
4. Submit a PR

The skill improves as you add examples — if you build a great visualization, add it to [references/examples.md](references/examples.md).

---

## Maintainer

Antoine Laviron — [alaviron@salesforce.com](mailto:alaviron@salesforce.com)

