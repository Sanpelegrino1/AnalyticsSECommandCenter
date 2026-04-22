# Tableau Next Record Access Shares Skill

A production-ready [Agent Skill](https://agentskills.io) that lets you share Tableau Next workspaces, dashboards, and visualizations via the Record Access Shares REST API.

Use this skill when the agent needs to grant access, make assets public, share with ALL_USERS, list who has access, or automate sharing in Tableau Next.

---

## Install

### Prerequisites

- [Cursor](https://cursor.sh) or [Claude Code](https://claude.ai/code) with Agent mode
- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) for authentication
- Authenticated Salesforce org with Tableau Next access

### One-Command Install

**macOS/Linux:**
```bash
git clone https://git.soma.salesforce.com/alaviron/tableau-skills.git
cd tableau-skills/skills/tableau-next-record-access-shares
./install.sh                    # Cursor (default)
./install.sh --target claude     # Claude Code
./install.sh --target all        # All platforms
./install.sh --force             # Overwrite without prompting
```

**Windows (PowerShell):**
```powershell
git clone https://git.soma.salesforce.com/alaviron/tableau-skills.git
cd tableau-skills\skills\tableau-next-record-access-shares
.\install.ps1                    # Cursor (default)
.\install.ps1 -Target claude     # Claude Code
.\install.ps1 -Target all        # All platforms
.\install.ps1 -Force              # Overwrite without prompting
```

Restart your agent after installation.

### Platform Paths

| Platform | macOS/Linux | Windows |
|----------|-------------|---------|
| Cursor | `~/.cursor/skills/tableau-next-record-access-shares/` | `%USERPROFILE%\.cursor\skills\tableau-next-record-access-shares\` |
| Claude Code | `~/.claude/skills/tableau-next-record-access-shares/` | `%USERPROFILE%\.claude\skills\tableau-next-record-access-shares\` |

### Manual Install

**Cursor:**
```bash
mkdir -p ~/.cursor/skills/tableau-next-record-access-shares
cp -r . ~/.cursor/skills/tableau-next-record-access-shares/
```

**Claude Code:**
```bash
mkdir -p ~/.claude/skills/tableau-next-record-access-shares
cp -r . ~/.claude/skills/tableau-next-record-access-shares/
```

---

## Quick Start

### 1. Authenticate

```bash
sf org login web --alias myorg
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

### 2. Get Workspace ID

```bash
curl "${SF_INSTANCE}/services/data/v64.0/tableau/workspaces?limit=50" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

Use the `id` from the response as `recordId`.

### 3. Share with Everyone (Viewer)

```bash
curl -X POST "${SF_INSTANCE}/services/data/v64.0/tableau/records/{recordId}/shares" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "accessRequestItems": [{
      "accessType": "Viewer",
      "applicationDomain": "Tableau",
      "setupObjectType": "AnalyticsWorkspace",
      "userOrGroupId": "ALL_USERS"
    }]
  }'
```

### 4. Share with Specific User (Editor)

Replace `005Ho00000LqtX0IAJ` with the user ID:

```json
{
  "accessRequestItems": [{
    "accessType": "Editor",
    "applicationDomain": "Tableau",
    "setupObjectType": "AnalyticsWorkspace",
    "userOrGroupId": "005Ho00000LqtX0IAJ"
  }]
}
```

---

## API Endpoints Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/tableau/records/{recordId}/shares` | List shares |
| POST | `/tableau/records/{recordId}/shares` | Create shares |
| PATCH | `/tableau/records/{recordId}/shares` | Update shares |
| DELETE | `/tableau/records/{recordId}/shares/{userOrGroupId}` | Remove one user's access |
| DELETE | `/tableau/records/{recordId}/shares` | Remove all shares |

**Enums:** `accessType`: Editor, Owner, Viewer | `setupObjectType`: AnalyticsWorkspace, AnalyticsDashboard, AnalyticsVisualization | `applicationDomain`: Tableau

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| 401 Unauthorized | Token expired — run `sf org display --target-org $SF_ORG --json` to refresh |
| 404 Not Found | Invalid `recordId` or `userOrGroupId` — verify IDs with GET /tableau/workspaces |
| `failedRecordShares` in response | Check `errorCode`, `errorMessage` per item; retry or fix invalid user IDs |
| Partial success | Some shares succeed, others fail — inspect `failedRecordShares` for details |

---

## Reference

For full type definitions, request/response schemas, and enum details, see [references/api-reference.md](references/api-reference.md).

---

## Maintainer

Antoine Laviron — [alaviron@salesforce.com](mailto:alaviron@salesforce.com)
