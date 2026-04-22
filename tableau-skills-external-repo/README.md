# Tableau Skills for AI Agents

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Tableau-orange)
![Agent Skills](https://img.shields.io/badge/agent--skills-compliant-purple)

Production-ready agent skills for Tableau Next and Tableau Classic APIs.

> **Scope:** **Tableau Next** (Analytics on Salesforce Data 360) and **Tableau Classic** (including Tableau Cloud). NOT CRMA.

---

## Skills Catalog

| Skill | Description | Key Features | Installation |
|-------|-------------|--------------|--------------|
| [tableau-next-author](skills/tableau-next-author/) | Build Tableau Next dashboards with AI by describing what you want in plain language | Templates, SDM discovery, validation, automation scripts | [Install →](skills/tableau-next-author/README.md#install) |
| [tableau-next-package-deploy](skills/tableau-next-package-deploy/) | Package and deploy Tableau Next dashboards across orgs | Direct API integration, validation workflows, CI/CD support | [Install →](skills/tableau-next-package-deploy/) |
| [tableau-semantic-authoring](skills/tableau-semantic-authoring/) | Enrich Semantic Data Models with calculated fields and metrics | Business logic layer, Tableau expressions, semantic discovery | [Install →](skills/tableau-semantic-authoring/) |
| [tableau-next-record-access-shares](skills/tableau-next-record-access-shares/) | Share workspaces, dashboards, and visualizations via REST API | Record Access Shares API, ALL_USERS support | [Install →](skills/tableau-next-record-access-shares/README.md#install) |
| [tableau-hyper-api](skills/tableau-hyper-api/) | Generate correct Python code for Tableau Hyper API (.hyper extract files) | CRUD operations, CSV/Parquet/pandas loading, spatial data, publishing | [Install →](skills/tableau-hyper-api/SKILL.md) |

---

## Quick Start

### Install All Skills

```bash
git clone https://git.soma.salesforce.com/alaviron/tableau-skills.git
cd tableau-skills
./install.sh --target cursor

# Or with options:
./install.sh --target claude --force
./install.sh --skills tableau-next-author --target cursor
```

### Install Individual Skill

```bash
cd skills/tableau-next-author
./install.sh                    # Cursor (default)
./install.sh --target claude     # Claude Code
./install.sh --target all        # All platforms
```

### Authenticate

```bash
sf org login web --alias myorg
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

Restart your agent after installation.

---

## Platform Compatibility

| Platform | Path (macOS/Linux) |
|----------|--------------------|
| **Cursor** | `~/.cursor/skills/` |
| **Claude Code** | `~/.claude/skills/` |

All skills support Cursor and Claude Code.

---

## Prerequisites

- **Salesforce CLI** (`sf`) — for authentication
  - macOS/Linux: `brew install sf`
  - Windows: [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli)
- **Python 3.8+** — for automation scripts (tableau-next-author)
- **jq** — for JSON parsing (optional but recommended)
  - macOS/Linux: `brew install jq`
- **Authenticated Salesforce org** with Tableau Next access

---

## Resources

- [Agent Skills Specification](https://agentskills.io)
- [tableau-next-author documentation](skills/tableau-next-author/README.md)
- [tableau-next-package-deploy documentation](skills/tableau-next-package-deploy/SKILL.md)
- [tableau-semantic-authoring documentation](skills/tableau-semantic-authoring/SKILL.md)
- [tableau-next-record-access-shares documentation](skills/tableau-next-record-access-shares/README.md)
- [tableau-hyper-api documentation](skills/tableau-hyper-api/SKILL.md)

---

## License

MIT License — see [LICENSE](LICENSE).

## Maintainer

Antoine Laviron — [alaviron@salesforce.com](mailto:alaviron@salesforce.com)
