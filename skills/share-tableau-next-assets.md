# Share Tableau Next Assets

## Purpose

Grant, inspect, update, or remove Tableau Next access for workspaces, dashboards, and visualizations through the Record Access Shares REST API.

## When to use it

Use this when the user wants to share Tableau Next content with a user, make a workspace broadly visible, inspect who already has access, or automate access changes for workspaces, dashboards, or visualizations.

## Inputs

- Salesforce org alias.
- Asset record id.
- Setup object type: `AnalyticsWorkspace`, `AnalyticsDashboard`, or `AnalyticsVisualization`.
- User or group id, or `ALL_USERS`.
- Desired access level: `Viewer`, `Editor`, or `Owner`.

## Prerequisites

- Salesforce CLI auth for the target org works.
- The target asset id was discovered live, not guessed.
- The external reference exists at `tableau-skills-external-repo/skills/tableau-next-record-access-shares/SKILL.md`.

## Exact steps

1. Export the org access token and instance URL from Salesforce CLI.
2. Discover the target asset id from the Tableau Next list endpoints if it is not already known.
3. Inspect current shares with `GET /services/data/v64.0/tableau/records/{recordId}/shares`.
4. Create or update shares with the documented POST or PATCH payload shape.
5. Re-read the share list and confirm the target principal and access level.

## Validation

- The API returns the target principal in `successfulRecordShares` or the share list.
- Any `failedRecordShares` entries are empty or explicitly understood.
- The shared user can access the intended Tableau Next asset.

## Failure modes

- The record id points to the wrong asset or wrong object type.
- The org token is expired or does not have the required permissions.
- The share request partially succeeds and must be checked item by item.

## Cleanup or rollback

- Remove one share with the documented DELETE endpoint for a principal.
- Remove all shares from the record only when that is explicitly intended.

## Commands and links

- `tableau-skills-external-repo/skills/tableau-next-record-access-shares/SKILL.md`
- `tableau-skills-external-repo/skills/tableau-next-record-access-shares/README.md`
- `scripts/tableau/list-next-workspaces.ps1`
- `scripts/tableau/list-next-semantic-models.ps1`
