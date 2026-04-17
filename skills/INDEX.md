# Skill Index

Use this file as the first stop before running repeated operational work.

| Skill | When to use it | Required inputs | Validation |
| --- | --- | --- | --- |
| `salesforce-org-login-and-alias-registration.md` | New org login or alias refresh | Alias, login URL, purpose, notes | Alias appears in `sf org list` and registry is updated |
| `switch-active-salesforce-org-context.md` | Change active Salesforce org | Alias | `sf config get target-org` or org open uses the expected alias |
| `run-soql-and-export-results.md` | Query org data for inspection or export | Alias, SOQL query, output path | Export file exists and record count looks correct |
| `retrieve-or-deploy-metadata.md` | Bring down or push Salesforce metadata | Alias, manifest path or metadata name | CLI command completes successfully |
| `upload-csv-to-data-cloud.md` | Bulk-upload CSV data into a configured Data Cloud ingestion target | Target key, CSV path, local auth secrets | Job reaches `JobComplete` or returns a diagnosable failure |
| `create-lightning-app.md` | Build a Lightning app through a repeatable admin flow | Org alias, app name, visibility choices | App appears in Setup and App Launcher |
| `create-and-assign-permission-set.md` | Create access scaffolding for demo users | Org alias, permission set name, assignee | Permission set exists and user assignment succeeds |
| `open-key-salesforce-setup-surfaces.md` | Jump to common Setup pages quickly | Org alias, target surface | Browser opens the right Setup page |
| `tableau-cloud-auth-bootstrap.md` | Register or validate Tableau target auth | Target key, server URL, site content URL, PAT in local env | Auth status script succeeds |
| `list-tableau-cloud-projects-and-content.md` | Inspect Tableau project structure and content inventory | Target key | Project or content list returns without auth errors |
| `publish-or-inspect-tableau-content.md` | Publish workbook or datasource, or inspect content details | Target key, file path or content type and id | Publish returns success or inspect returns expected object |
