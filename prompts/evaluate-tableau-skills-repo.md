# Prompt Template: Evaluate `alaviron/tableau-skills` for Selective Adoption

Use this prompt when you want a coding agent to assess the upstream `tableau-skills` repository as a fact-finding and planning exercise only.

"Evaluate the repository `https://git.soma.salesforce.com/alaviron/tableau-skills` as an upstream skill bank for this workspace. Do not clone, import, build, modify, or adopt anything yet. This is a fact-finding and planning mission only.

Work asset by asset through the repository and produce a complete catalog of what exists. For each asset, record:
- path
- type (`skill`, `prompt`, `script`, `playbook`, `config`, `doc`, `template`, `other`)
- stated purpose
- required runtime or toolchain
- auth model and secret handling assumptions
- dependencies on Claude, Python, Salesforce CLI, Tableau APIs, or Data Cloud APIs
- whether it overlaps with an existing asset in this repo
- whether it should be adopted here, adapted here, referenced only, or left alone
- why

Also produce these sections:
1. Repository overview and operating model.
2. Inventory by folder and asset type.
3. Mapping to this repo's current structure under `skills/`, `playbooks/`, `prompts/`, `scripts/`, and `notes/registries/`.
4. Gaps this upstream repo would fill for this workspace.
5. Conflicts or mismatches in auth model, platform assumptions, toolchain, naming, and workflow design.
6. A recommended adoption plan ordered by priority, but without making any changes.
7. A reject/defer list with reasons.
8. Risks of wholesale import or submodule use.

Be explicit when access is blocked or partial. If the repo cannot be fully inspected from the current session, document exactly what was inaccessible, what evidence was still gathered, and what follow-up access would be required. Optimize for a durable evaluation document that a future agent can use to decide what to selectively recreate in this repo.

You are working alongside another agent evaluating a different upstream repository. Keep your output normalized enough that the two evaluation reports can be compared side by side, but do not depend on the other agent's results to complete this assessment."