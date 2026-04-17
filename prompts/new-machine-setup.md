# Prompt Template: Set Up This Workspace on a New Machine

Use this prompt with a coding agent after cloning the repo:

"Audit this repository as an operations workspace. Run `scripts/bootstrap/setup-workspace.ps1` first. Install only missing required prerequisites, keep secrets out of tracked files, create `.env.local` from `.env.example` if needed, verify VS Code recommendations and tasks, and summarize any manual auth steps still required for Salesforce and Tableau Cloud."
