# Author Tableau Next Dashboards

## Purpose

Build Tableau Next visualizations and dashboards from an existing semantic model using the external Tableau authoring toolkit that is now cloned into this workspace.

## When to use it

Use this when the user wants to create Tableau Next visualizations or dashboards, choose chart types, build a dashboard narrative, or apply a prepared visualization spec to a workspace.

## Inputs

- Salesforce org alias.
- Workspace name or workspace id.
- Semantic model API name.
- Dashboard API name and label.
- Either a plain-language dashboard brief or a prepared visualization spec JSON file.

## Prerequisites

- Salesforce CLI auth for the target org works.
- The semantic model already exists and is readable in Tableau Next.
- The external toolkit exists at `tableau-skills-external-repo/skills/tableau-next-author`.
- Python dependencies from `tableau-skills-external-repo/skills/tableau-next-author/scripts/requirements.txt` are installed if you will run the scripts.

## Exact steps

1. Discover the semantic model fields with `tableau-skills-external-repo/skills/tableau-next-author/scripts/discover_sdm.py`.
2. Design the dashboard narrative before picking charts: KPIs first, then trends, then dimensional breakdowns, then correlations.
3. Write or refine a visualization spec JSON in `tmp/`.
4. Run `tableau-skills-external-repo/skills/tableau-next-author/scripts/create_dashboard.py` with the target org, workspace, semantic model, dashboard name, and spec file.
5. If needed, use the helper generators in the same folder such as `generate_viz.py`, `generate_dashboard.py`, or `apply_viz_template.py` before the final create step.

## Validation

- The create script returns created visualization and dashboard ids or URLs.
- The resulting dashboard resolves in the target workspace.
- The visualization spec uses business-friendly labels, not only technical field names.

## Failure modes

- The semantic model name is wrong or unreadable in the target org.
- The workspace does not exist or the user lacks author access.
- The spec references fields that do not exist on the semantic model.
- The generated payload passes local checks but the Tableau Next API rejects it for an unsupported chart or formatting combination.

## Cleanup or rollback

- Remove temporary spec files from `tmp/` if they are no longer needed.
- If a bad dashboard was created, delete or replace it through the target org's Tableau Next UI or the matching authoring workflow.

## Commands and links

- `tableau-skills-external-repo/skills/tableau-next-author/SKILL.md`
- `tableau-skills-external-repo/skills/tableau-next-author/README.md`
- `tableau-skills-external-repo/skills/tableau-next-author/scripts/discover_sdm.py`
- `tableau-skills-external-repo/skills/tableau-next-author/scripts/create_dashboard.py`
- `tableau-skills-external-repo/skills/tableau-next-author/scripts/apply_viz_template.py`
