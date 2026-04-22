# Prompt Template: Evaluate `Tableau-Next-Claude-Skills` for Selective Adoption

Use this prompt when you want a coding agent to assess the upstream `Tableau-Next-Claude-Skills` repository as a fact-finding and planning exercise only.

"Evaluate the repository `https://github.com/arapaport-tableau/Tableau-Next-Claude-Skills` as an upstream skill bank for this workspace. Do not copy files into this repo, do not implement workflows here, and do not build or run the upstream automation unless inspection requires it. This is a fact-finding and planning mission only.

Inspect the repository piece by piece and create a full catalog of every meaningful asset. For each asset, capture:
- path
- type (`skill`, `prompt`, `script`, `workflow`, `config`, `doc`, `template`, `other`)
- purpose
- execution model
- required tools and runtime assumptions
- auth and secret handling assumptions
- whether it is Claude-specific, Python-specific, Mac-specific, Tableau Next-specific, or Data Cloud-specific
- whether this repo already has an equivalent or partial equivalent
- whether it should be recreated here, adapted here, referenced only, or ignored
- the rationale for that recommendation

Also produce these sections:
1. Repository overview and intended audience.
2. Inventory by folder and capability area.
3. Comparison against this repo's existing `skills/`, `playbooks/`, `prompts/`, `scripts/`, and `README.md` workflow model.
4. Assets that are strong candidates for selective adoption.
5. Assets that should not be adopted because they conflict with this repo's architecture, auth strategy, or platform assumptions.
6. Missing capabilities in this repo that the upstream repo highlights.
7. A recommended phased adoption plan that names exactly what should be recreated locally and where it should live.
8. Documentation updates this repo would eventually need if adoption happens.

Do not make changes. Do not create skills, prompts, or scripts in this repo as part of this run. End with a decision-oriented planning report that helps a future agent selectively absorb the right parts and leave the rest alone." 