# Slack Integration

This directory is the repo-native landing zone for Slack work that belongs with this workspace.

Use it for:

- Shared Slack MCP setup used from VS Code chat.
- Repo-local notes and helpers for deploying or publishing into Slack when that work belongs with the Salesforce, Data Cloud, Tableau, or demo-prep workflows in this repo.
- Future script-backed Slack delivery steps that should live beside the rest of the operational tooling.

Do not use it for:

- Slack workspace administration.
- Slack app provisioning or org-level security policy changes.
- Secrets, tokens, or shared server credentials in tracked files.

Those admin concerns stay in the separate Slack admin repo.

## Directory layout

- `mcp/` contains the shared Slack MCP setup notes for this workspace.

## Quick start

1. Get the shared Slack MCP server URL from the colleague who owns or operates that server.
2. Open `.vscode/mcp.json` in this repo.
3. Start the `slackShared` MCP server from VS Code, or run `MCP: List Servers` and start it there.
4. When VS Code prompts for `slack-mcp-server-url`, enter the shared server URL.
5. Trust the server only after reviewing the configuration.
6. Use the Slack MCP tools, prompts, or resources from chat as needed for deployment or publishing work.

## Notes

- The workspace MCP config is intentionally scoped to shared connectivity only.
- If the shared server later requires authentication headers, extend `.vscode/mcp.json` with VS Code input variables instead of hardcoding secrets.
- If Slack deployment work becomes repeatable, add script-backed helpers under `scripts/` and document them here.