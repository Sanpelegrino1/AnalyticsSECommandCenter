# Write Tableau Hyper API Python

## Purpose

Generate correct Python code for Tableau Hyper API workflows, including creating, reading, loading, and modifying `.hyper` extract files.

## When to use it

Use this when the user asks for Tableau Hyper API code, `.hyper` extract generation, Hyper ETL patterns, CSV or pandas loads into Hyper, or Python publishing flows that depend on Hyper files.

## Inputs

- The target Hyper workflow: create, inspect, update, delete, or load.
- Expected table schema.
- Source data format such as CSV, Parquet, pandas, or SQL query output.
- Optional Tableau Server or Cloud publishing requirement.

## Prerequisites

- Python is available.
- The external reference exists at `tableau-skills-external-repo/skills/tableau-hyper-api/SKILL.md`.
- Required packages such as `tableauhyperapi`, and optionally `pandas`, `pantab`, or `tableauserverclient`, are installed when the chosen recipe needs them.

## Exact steps

1. Choose the narrow Hyper workflow first: create, inspect, modify, or load.
2. Define the schema explicitly with Hyper API types.
3. Build the Python code around the standard `HyperProcess` and `Connection` context-manager pattern.
4. Use `Inserter` or `COPY` based on data size and source format.
5. If publishing is required, add the publish step only after the extract is created successfully.

## Validation

- The code uses the standard Hyper API process and connection lifecycle.
- Identifiers and string literals are escaped correctly when SQL is constructed.
- The chosen load pattern matches the data source and scale.

## Failure modes

- The code opens an extract with the wrong `CreateMode` and overwrites data unexpectedly.
- The table schema does not match the inserted data types.
- Large CSV or Parquet loads use row-by-row insertion when `COPY` is the better path.

## Cleanup or rollback

- Remove temporary `.hyper` files when they are only intermediate artifacts.
- Recreate the extract from source data if schema or load logic was incorrect.

## Commands and links

- `tableau-skills-external-repo/skills/tableau-hyper-api/SKILL.md`
- `tableau-skills-external-repo/skills/tableau-hyper-api/references/api-patterns.md`
- `tableau-skills-external-repo/skills/tableau-hyper-api/references/community-recipes.md`
