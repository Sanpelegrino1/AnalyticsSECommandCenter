# AnalyticsSECommandCenter Agent Instructions

This repository is an operations workspace for Salesforce org setup, Salesforce Data Cloud ingestion work, Tableau Cloud interaction, and repeated demo-prep workflows.

Start here:

- Read `README.md` for the workspace entry points.
- Read `skills/INDEX.md` before inventing a new workflow.
- Use `scripts/bootstrap/setup-workspace.ps1` to audit or install missing machine prerequisites.

Operational rules:

- Keep secrets out of tracked files. Use Salesforce CLI's local auth store for Salesforce auth and `.env.local` or user environment variables for Data Cloud and Tableau secrets.
- Update `notes/registries/salesforce-orgs.json`, `notes/registries/data-cloud-targets.json`, and `notes/registries/tableau-targets.json` when you create or validate new non-secret targets.
- Prefer the scripts under `scripts/salesforce` and `scripts/tableau` over ad hoc one-off commands.

Skill extraction rules:

- If a workflow succeeds twice with substantially the same steps, extract it into a new or updated skill under `skills/`.
- If a workflow is completed a third time without meaningful variation, treat the skill as the default path.
- Every skill must capture purpose, inputs, prerequisites, exact steps, validation, failure modes, cleanup or rollback notes, and links or commands.
