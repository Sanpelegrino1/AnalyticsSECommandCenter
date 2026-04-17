# Add a New Demo Org

## Inputs

- Alias to use locally.
- Login or My Domain URL.
- Purpose and notes for the registry.

## Steps

1. Run `Salesforce: Login web and register alias`.
2. Confirm the login completes in the browser.
3. Run `Salesforce: List orgs` and confirm the alias appears.
4. Run `Salesforce: Set default org` if this should become the active context.
5. Add or review the non-secret metadata in `notes/registries/salesforce-orgs.json`.
6. Optionally run `Salesforce: Snapshot aliases` to capture the current alias state.

## Validation

- The alias is present in `sf org list`.
- `scripts/salesforce/open-org.ps1` opens the org without asking for new auth.
- `notes/registries/salesforce-orgs.json` contains the alias, login URL, purpose, and notes.

## Failure modes

- Browser login lands in the wrong org: fix the login URL and rerun.
- Alias already exists with stale metadata: rerun the login or update the registry entry.
