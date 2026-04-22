---
name: writing-hyper-api-code
description: >
  Generates correct Python code for Tableau Hyper API (.hyper extract files).
  Covers creating, reading, updating, and deleting data in Hyper files, loading
  from CSV/Parquet/pandas, querying external data, spatial data, expressions in
  inserts, and publishing to Tableau Server/Cloud. Use when the user mentions
  Hyper files, Tableau extracts, .hyper, tableauhyperapi, HyperProcess, or
  building ETL pipelines for Tableau. Do NOT use for general SQL tasks on other
  databases (Postgres, Snowflake) or for pure data analysis without Hyper files.
---

# Writing Hyper API Code

Generate correct Python code for Tableau's Hyper API (`tableauhyperapi` package).

## Setup

```bash
pip install tableauhyperapi
# Optional, for specific recipes:
pip install pandas        # DataFrame ↔ Hyper conversion
pip install pantab         # Quick Hyper ↔ pandas bridging
pip install tableauserverclient  # Publishing to Tableau Server/Cloud
```

## Workflows

Follow these sequential steps for common tasks to ensure reliability and performance.

### Workflow: Creating a New Extract
1. **Define Schema**: Create a `TableDefinition` with appropriate `SqlTypes`.
2. **Start Process**: Wrap logic in a `HyperProcess` context manager.
3. **Connect**: Use a `Connection` with `CreateMode.CREATE_AND_REPLACE`.
4. **Create Table**: Use `connection.catalog.create_table`.
5. **Load Data**: Use `Inserter` for small batches or `COPY` for large CSV/Parquet files.
6. **Flush**: Call `inserter.execute()` before the `with Inserter` block exits.

### Workflow: Reading or Inspecting an Extract
1. **Open Connection**: Use `CreateMode.NONE` to avoid accidental file creation/overwriting.
2. **Execute Query**: Use `execute_list_query` for rows or `execute_scalar_query` for single values.
3. **Inspect Catalog**: If schema is unknown, use `connection.catalog.get_table_names()`.

### Workflow: Modifying an Existing Extract
1. **Open Connection**: Use `CreateMode.NONE`.
2. **Run DML**: Use `execute_command` for `UPDATE` or `DELETE`.
3. **Use Escaping**: Always wrap identifiers in `escape_name()` and literals in `escape_string_literal()`.

## Evaluation
This skill includes a comprehensive evaluation suite in `evals/evals.json` covering 11 critical patterns (joins, incremental updates, ETL, etc.).

### Running Evaluations
1.  **Select a Case**: Use `evals/evals.json` to pick a test scenario.
2.  **Generate Code**: Ask the assistant to generate code for that scenario.
3.  **Grade Output**: Use the `scripts/run_evals.py` script to generate a grading prompt. Follow the "Strengths & Weaknesses" logic documented in `evals/GRADING_STRATEGY.md`.

## Core Pattern

Every Hyper API program follows a nested context-manager pattern. Start a `HyperProcess`, then open a `Connection` to a `.hyper` file within it:

```python
from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    NOT_NULLABLE, NULLABLE, SqlType, TableDefinition,
    Inserter, escape_name, escape_string_literal,
    TableName, HyperException
)

with HyperProcess(telemetry=Telemetry.SEND_USAGE_DATA_TO_TABLEAU) as hyper:
    with Connection(
        endpoint=hyper.endpoint,
        database=Path("my_file.hyper"),
        create_mode=CreateMode.CREATE_AND_REPLACE
    ) as connection:
        # All operations go here
        pass
```

Set `telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU` to opt out.

## Defining Tables

Use `TableDefinition` with `SqlType` for column types. Tables default to the `"public"` schema unless a `TableName` specifies otherwise:

```python
# Public schema (default)
customer_table = TableDefinition(
    table_name="Customer",
    columns=[
        TableDefinition.Column("Customer ID", SqlType.text(), NOT_NULLABLE),
        TableDefinition.Column("Customer Name", SqlType.text(), NOT_NULLABLE),
        TableDefinition.Column("Loyalty Points", SqlType.big_int(), NOT_NULLABLE),
        TableDefinition.Column("Segment", SqlType.text(), NULLABLE),
    ]
)

# Named schema — Tableau's historical default for extracts
extract_table = TableDefinition(
    table_name=TableName("Extract", "Extract"),
    columns=[
        TableDefinition.Column("Order ID", SqlType.int(), NOT_NULLABLE),
        TableDefinition.Column("Ship Date", SqlType.date(), NULLABLE),
        TableDefinition.Column("Amount", SqlType.double(), NOT_NULLABLE),
    ]
)
```

When using a non-default schema, create it before the table:

```python
connection.catalog.create_schema(schema=extract_table.table_name.schema_name)
connection.catalog.create_table(table_definition=extract_table)
```

See [api-patterns.md](references/api-patterns.md) for the full `SqlType` reference and `CreateMode` options.

## CRUD Operations

### Insert — Use the `Inserter`

```python
data = [
    ["DK-13375", "Dennis Kane", 518, "Consumer"],
    ["EB-13705", "Ed Braxton", 815, "Corporate"],
]

with Inserter(connection, customer_table) as inserter:
    inserter.add_rows(rows=data)      # Batch insert (preferred)
    # inserter.add_row(row=single_row)  # Single row alternative
    inserter.execute()                  # Flush to disk
```

For computed columns during insert, use `Inserter.ColumnMapping` with SQL expressions — see the [Expressions example](#expressions-during-insert) below.

### Read — SQL Queries

```python
# Multiple rows → list of lists
rows = connection.execute_list_query(
    query=f"SELECT * FROM {customer_table.table_name}"
)

# Single scalar value
count = connection.execute_scalar_query(
    query=f"SELECT COUNT(*) FROM {customer_table.table_name}"
)
```

### Update and Delete — `execute_command`

`execute_command` runs DML statements and returns the affected row count:

```python
# Update
updated = connection.execute_command(
    command=f"UPDATE {escape_name('Customer')} "
    f"SET {escape_name('Loyalty Points')} = {escape_name('Loyalty Points')} + 50 "
    f"WHERE {escape_name('Segment')} = {escape_string_literal('Corporate')}"
)

# Delete
deleted = connection.execute_command(
    command=f"DELETE FROM {escape_name('Orders')} "
    f"WHERE {escape_name('Customer ID')} = {escape_string_literal('DK-13375')}"
)
```

Use `escape_name()` for identifiers (table/column names) and `escape_string_literal()` for string values — this prevents SQL injection and handles special characters.

## Loading Data

### From CSV — COPY command (fastest)

```python
path_to_csv = str(Path("data/customers.csv"))
count = connection.execute_command(
    command=f"COPY {customer_table.table_name} FROM {escape_string_literal(path_to_csv)} "
    f"WITH (FORMAT csv, NULL 'NULL', DELIMITER ',', HEADER)"
)
```

### From Parquet

```python
count = connection.execute_command(
    command=f"COPY {table.table_name} FROM {escape_string_literal('orders.parquet')} "
    f"WITH (FORMAT PARQUET)"
)
```

### From pandas DataFrame

```python
import pandas as pd

df = pd.DataFrame({"Name": ["Alice", "Bob"], "Score": [95, 87]})

with Inserter(connection, my_table) as inserter:
    for row in df.itertuples(index=False, name=None):
        inserter.add_row(row)
    inserter.execute()
```

See [community-recipes.md](references/community-recipes.md) for more data source recipes (S3, external queries, pantab).

## Expressions During Insert

Transform data on-the-fly during insertion using `Inserter.ColumnMapping`. Define an `inserter_definition` describing the *input* columns, and `column_mappings` describing how they map to the *target* table:

```python
# Target table has: Order ID (int), Ship Timestamp (timestamp), Ship Priority (int)
# Input data has:   Order ID (int), Ship Timestamp Text (text), Ship Priority Text (text)

inserter_definition = [
    TableDefinition.Column("Order ID", SqlType.int(), NOT_NULLABLE),
    TableDefinition.Column("Ship Timestamp Text", SqlType.text(), NOT_NULLABLE),
    TableDefinition.Column("Ship Priority Text", SqlType.text(), NOT_NULLABLE),
]

column_mappings = [
    "Order ID",  # Pass through as-is
    Inserter.ColumnMapping(
        "Ship Timestamp",
        f'to_timestamp({escape_name("Ship Timestamp Text")}, '
        f'{escape_string_literal("YYYY-MM-DD HH24:MI:SS")})'
    ),
    Inserter.ColumnMapping(
        "Ship Priority",
        f'CASE {escape_name("Ship Priority Text")} '
        f'WHEN {escape_string_literal("Urgent")} THEN 1 '
        f'WHEN {escape_string_literal("Medium")} THEN 2 '
        f'WHEN {escape_string_literal("Low")} THEN 3 END'
    ),
]

with Inserter(connection, target_table, column_mappings,
              inserter_definition=inserter_definition) as inserter:
    inserter.add_rows(data)
    inserter.execute()
```

## Spatial Data

Insert WKT geometry as `SqlType.geography()` using a CAST expression:

```python
extract_table = TableDefinition(
    table_name=TableName("Extract", "Extract"),
    columns=[
        TableDefinition.Column("Name", SqlType.text(), NOT_NULLABLE),
        TableDefinition.Column("Location", SqlType.geography(), NOT_NULLABLE),
    ]
)

inserter_definition = [
    TableDefinition.Column("Name", SqlType.text(), NOT_NULLABLE),
    TableDefinition.Column("Location_as_text", SqlType.text(), NOT_NULLABLE),
]

column_mappings = [
    "Name",
    Inserter.ColumnMapping("Location", f'CAST({escape_name("Location_as_text")} AS GEOGRAPHY)'),
]

data = [["Seattle", "point(-122.338083 47.647528)"], ["Munich", "point(11.584329 48.139257)"]]

with Inserter(connection, extract_table, column_mappings,
              inserter_definition=inserter_definition) as inserter:
    inserter.add_rows(data)
    inserter.execute()
```

## Querying External Data

Query CSV and Parquet files directly without importing them, using `external()`:

```python
# Query a Parquet file directly
rows = connection.execute_list_query(
    "SELECT order_key, price FROM external('orders.parquet') WHERE priority = 'LOW'"
)

# CSV requires a DESCRIPTOR for the schema
rows = connection.execute_list_query("""
    SELECT * FROM external('customers.csv',
        COLUMNS => DESCRIPTOR(id int, country text, name text),
        DELIMITER => ',', FORMAT => 'csv', HEADER => true)
""")
```

## Inspecting Hyper Files

List schemas, tables, and columns using the catalog API:

```python
with Connection(endpoint=hyper.endpoint, database=path, create_mode=CreateMode.NONE) as conn:
    for schema_name in conn.catalog.get_schema_names():
        for table in conn.catalog.get_table_names(schema=schema_name):
            table_def = conn.catalog.get_table_definition(name=table)
            for col in table_def.columns:
                print(f"{col.name}: {col.type}, nullable={col.nullability}")
```

Use `CreateMode.NONE` when opening an existing file read-only — it raises an error if the file doesn't exist, which is the safest default for introspection.

## Publishing to Tableau Server/Cloud

Use `tableauserverclient` (TSC) alongside the Hyper API:

```python
import tableauserverclient as TSC

tableau_auth = TSC.PersonalAccessTokenAuth(
    token_name="my_token", personal_access_token="secret", site_id="my_site"
)
server = TSC.Server("https://my-server.online.tableau.com", use_server_version=True)

with server.auth.sign_in(tableau_auth):
    project_id = None
    for project in TSC.Pager(server.projects):
        if project.name == "my_project":
            project_id = project.id
            break

    datasource = TSC.DatasourceItem(project_id)
    server.datasources.publish(datasource, "my_file.hyper", TSC.Server.PublishMode.Overwrite)
```

Publish modes: `Overwrite`, `Append`, `CreateNew`. Store tokens in environment variables, not in code.

## Troubleshooting

Common issues and how to fix them:

- **"File already exists" error** → Use `CreateMode.CREATE_AND_REPLACE` or `CreateMode.CREATE_IF_NOT_EXISTS` instead of `CreateMode.CREATE`
- **"File does not exist" error** → Use `CreateMode.CREATE` or `CREATE_AND_REPLACE` for new files; `CreateMode.NONE` requires the file to already exist
- **Data not appearing after insert** → Ensure `inserter.execute()` is called before the `with Inserter` block exits. Without it, data is not flushed
- **Column name errors in SQL** → Wrap column/table names containing spaces or reserved words with `escape_name()`
- **Wrong row count after COPY** → Check CSV delimiter, NULL encoding, and HEADER option match your file format
- **Spatial data fails** → Ensure WKT strings use lowercase function names like `point(lon lat)` not `POINT(lon lat)`, and use the CAST expression via `Inserter.ColumnMapping`

### Common Pitfalls & Edge Cases

- **File Locking**: Only one `HyperProcess` can access a `.hyper` file at a time for writing. If you get a "database is already in use" error, ensure no other scripts or Tableau Desktop are holding the file open.
- **Detailed Exceptions**: When catching `HyperException`, check `ex.main_message` and `ex.hint` for specific SQL guidance.
- **Empty CSV Headers**: If a CSV has a header but `COPY` fails, verify the `HEADER` option is present and the delimiter is correct.

After writing Hyper API code, verify it by confirming:
1. The `HyperProcess` and `Connection` are both used as context managers (`with` blocks)
2. The correct `CreateMode` is used (especially `NONE` for existing files vs `CREATE_AND_REPLACE` for new files)
3. All identifiers use `escape_name()` and string values use `escape_string_literal()`
4. `inserter.execute()` is called after adding rows

## Error Handling

Wrap the main logic in a `HyperException` handler:

```python
if __name__ == "__main__":
    try:
        run_my_hyper_task()
    except HyperException as ex:
        print(ex)
        exit(1)
```

## Reference Files

- [api-patterns.md](references/api-patterns.md) — SqlType mappings, CreateMode options, escape functions, catalog API, process/connection parameters
- [community-recipes.md](references/community-recipes.md) — Cookbook recipes for pandas, Parquet, S3, CSV export, external queries, publishing workflows
