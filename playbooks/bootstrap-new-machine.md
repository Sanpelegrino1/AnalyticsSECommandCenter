# Bootstrap a New Machine

Use this playbook when the repo has been cloned onto a new Windows machine and you want the workspace ready without manual rediscovery.

## Inputs

- A Windows machine with `winget` available.
- Local permission to install developer tools.
- The repo checked out locally.

## Steps

1. Open `AnalyticsSECommandCenter.code-workspace` in VS Code.
2. Run `Bootstrap: Audit workspace machine`.
3. If any required item is missing, run `Bootstrap: Install missing prerequisites`.
4. Confirm `.env.local` exists.
5. Add Tableau PAT values only if Tableau automation is needed on this machine.
6. Run `Salesforce: List orgs` to verify the CLI can see your local auth state.
7. Run `Salesforce: Login web and register alias` if you need a new org alias on this machine.

## Validation

- `scripts/bootstrap/setup-workspace.ps1` reports required tools and extensions as present.
- VS Code shows the recommended extensions installed.
- `sf --version` works in the integrated terminal.
- `scripts/tableau/auth-status.ps1` succeeds after local Tableau config is supplied.

## Failure modes

- `winget` blocked by policy: install required tools manually, then rerun the audit.
- `code` command missing: enable the VS Code shell command path or reinstall VS Code.
- Java too old: install a supported JDK and rerun the audit.
