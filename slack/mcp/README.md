# Slack MCP Setup

This workspace uses `.vscode/mcp.json` as the shared Slack MCP entry point for VS Code.

## Purpose

- Make the shared Slack MCP server discoverable from this repo.
- Keep the connection workflow consistent across the team.
- Avoid committing the real server URL or any secrets into the repo.

## Current workspace configuration

The repo includes a workspace MCP server named `slackShared` in `.vscode/mcp.json`.

It is configured as an HTTP MCP server and prompts each user for the shared server URL through VS Code's MCP input storage the first time the server starts.

Important distinction:

- Do not paste the Heroku helper page URL into `.vscode/mcp.json`.
- Do not paste a Slack OAuth callback URL with `?code=...` into `.vscode/mcp.json`.
- Those URLs are part of a one-time auth helper flow and are not the stable MCP server URL.

The public Slack MCP transport endpoint is `https://mcp.slack.com/mcp`, but Slack requires MCP clients to be backed by a registered Slack app with a fixed app ID. The generic VS Code workspace `mcp.json` format exposes the server URL and optional headers, but not the Slack client identity setup shown by Slack's helper page for supported clients such as Cursor and Claude Code.

That means this workspace should normally point at one of these:

- A colleague-managed shared MCP bridge or proxy that already handles the Slack app identity and OAuth flow for your team.
- A future repo-local wrapper that your team controls and documents here.

It should not assume that pasting the Slack demo helper URL alone is enough for raw VS Code MCP.

## Operator steps

1. Open this repo in VS Code.
2. Run `MCP: Open Workspace Folder MCP Configuration` if you want to inspect the shared config.
3. Run `MCP: List Servers`.
4. Select `slackShared`.
5. Start the server.
6. Enter the colleague-managed shared Slack MCP bridge URL when prompted.
7. Review the trust prompt before allowing the server to start.
8. Confirm the server exposes the expected Slack tools, prompts, or resources in chat.

## Validation

- `slackShared` appears in `MCP: List Servers`.
- The server starts without configuration errors.
- Slack tools or prompts become available in chat.
- The configured URL is a stable MCP server endpoint, not an OAuth callback.

## Failure modes

- Wrong server URL: stop the server, correct the stored input, and restart it.
- Heroku helper or callback URL used by mistake: replace it with the real shared MCP bridge URL.
- Server trust denied: reset trust with `MCP: Reset Trust` and review the configuration again.
- Shared server unavailable: confirm the colleague-managed server is running and reachable from your network.
- Auth requirements change: update `.vscode/mcp.json` to use MCP input variables for the required headers rather than committing secrets.

## What the Heroku page is for

The page at `slack-mcp-app-demo-46d57964318d.herokuapp.com` is a Slack MCP demo installer and OAuth helper. It currently points supported clients to the real Slack MCP endpoint `https://mcp.slack.com/mcp` and shows client-specific setup for tools like Cursor and Claude Code.

If you revisit a callback URL from that page later, Slack returns `invalid_code` because OAuth authorization codes are short-lived and single-use.

## Practical linkage path for this repo

1. Ask your colleague for the stable shared Slack MCP bridge URL, not the helper page link.
2. Confirm whether that shared service is a proxy or gateway that already handles Slack app identity and OAuth.
3. Put that stable bridge URL into the `slackShared` prompt when VS Code starts the server.
4. If your colleague does not have a bridge and only has the Slack helper page, use a supported client like Cursor or Claude Code for direct Slack MCP first, or build a small team-owned wrapper before trying to use plain VS Code workspace MCP for Slack.

## Next extensions

- Add Slack deployment scripts under `scripts/` if this repo starts publishing repeatable content to Slack.
- Add a playbook or skill once the Slack deployment workflow has been proven enough times to extract.