# Author Tableau Next Semantic Layer

## Purpose

Enrich an existing Tableau Next semantic model with calculated fields and semantic metrics using the external semantic-authoring toolkit in this workspace.

## When to use it

Use this when the user wants to add a calculated field, create a semantic metric, create a filtered metric variant, validate a Tableau expression, or inspect the available fields on a live semantic model before dashboard authoring.

## Inputs

- Salesforce org alias.
- Semantic model API name.
- Calculated field or metric API name and label.
- Tableau expression.
- Aggregation type for measurements when needed.

## Prerequisites

- Salesforce CLI auth for the target org works.
- The semantic model already exists and is readable.
- The external toolkit exists at `tableau-skills-external-repo/skills/tableau-semantic-authoring`.
- Python dependencies for the shared scripts are installed.

## Exact steps

1. Inspect the live model with `tableau-skills-external-repo/skills/tableau-semantic-authoring/scripts/discover_sdm.py`.
2. Confirm the exact field API names before writing any expression.
3. Create calculated fields with `create_calc_field.py`.
4. If the request is a scoped variant of an existing metric, inspect the live metric and create the new metric with native metric filters instead of introducing a new calculated field.
5. Create semantic metrics with `create_metric.py` after choosing the right path:
	- reusable logic: create or reuse the calculated field first
	- scoped variant: reuse the existing metric logic and pass native filters directly
6. Re-run discovery to confirm the new `_clc` or `_mtc` definitions are present.

## Validation

- Discovery output shows the new calculated field or metric.
- Expressions use qualified table fields and unqualified calculated-field references correctly.
- No unsupported double-underscore names or invalid aggregation types are introduced.

## Failure modes

- The expression references fields that do not exist on the model.
- A scoped metric variant is implemented as a new calculated field when only metric filters were needed.
- A metric is created before its referenced calculated field exists when a reusable calculated field really was required.
- The API name violates Salesforce naming rules.
- The operator uses the wrong aggregation type for a ratio or already-aggregated expression.

## Cleanup or rollback

- Remove or replace incorrect semantic fields through the same semantic-authoring workflow if they were created with the wrong definition.
- Delete temporary expression drafts from `tmp/` if used.

## Commands and links

- `tableau-skills-external-repo/skills/tableau-semantic-authoring/SKILL.md`
- `tableau-skills-external-repo/skills/tableau-semantic-authoring/scripts/discover_sdm.py`
- `tableau-skills-external-repo/skills/tableau-semantic-authoring/scripts/create_calc_field.py`
- `tableau-skills-external-repo/skills/tableau-semantic-authoring/scripts/create_metric.py`
