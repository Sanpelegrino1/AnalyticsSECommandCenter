# Community Recipes

Cookbook-style recipes for common Hyper API tasks, based on the community-supported samples.

## Table of Contents
- [pandas DataFrame → Hyper](#pandas-dataframe--hyper)
- [Hyper → CSV via pantab](#hyper--csv-via-pantab)
- [Parquet → Hyper](#parquet--hyper)
- [Query External Data](#query-external-data)
- [S3 and Cloud Sources](#s3-and-cloud-sources)
- [Publish to Tableau Server/Cloud](#publish-to-tableau-servercloud)
- [List Hyper File Contents](#list-hyper-file-contents)
- [Defragment a Hyper File](#defragment-a-hyper-file)
- [Convert Hyper File Format](#convert-hyper-file-format)

## pandas DataFrame → Hyper

```python
import pandas as pd
from tableauhyperapi import (HyperProcess, Telemetry, Connection, CreateMode,
                              NOT_NULLABLE, SqlType, TableDefinition, Inserter)

df = pd.DataFrame({"Name": ["Alice", "Bob"], "Score": [95, 87]})

table = TableDefinition(table_name="Scores", columns=[
    TableDefinition.Column("Name", SqlType.text(), NOT_NULLABLE),
    TableDefinition.Column("Score", SqlType.big_int(), NOT_NULLABLE),
])

with HyperProcess(telemetry=Telemetry.SEND_USAGE_DATA_TO_TABLEAU) as hyper:
    with Connection(endpoint=hyper.endpoint, database="scores.hyper",
                    create_mode=CreateMode.CREATE_AND_REPLACE) as conn:
        conn.catalog.create_table(table_definition=table)
        with Inserter(conn, table) as inserter:
            for row in df.itertuples(index=False, name=None):
                inserter.add_row(row)
            inserter.execute()
```

Map pandas dtypes to SqlType: `object` → `text()`, `int64` → `big_int()`, `float64` → `double()`, `datetime64` → `timestamp()`, `bool` → `bool()`.

## Hyper → CSV via pantab

```python
import pantab

# Read a single table into a DataFrame
df = pantab.frame_from_hyper("my_file.hyper", table=("Extract", "Extract"))
df.to_csv("output.csv", index=False)

# Read all tables at once
all_tables = pantab.frames_from_hyper("my_file.hyper")
for table_name, df in all_tables.items():
    df.to_csv(f"{table_name.name}.csv", index=False)
```

Install: `pip install pantab`. Note pantab dtype mappings may need adjustment — see [pantab caveats](https://pantab.readthedocs.io/en/latest/caveats.html).

## Parquet → Hyper

Use the `COPY` command with `FORMAT PARQUET`. The table definition must match the Parquet schema:

```python
from tableauhyperapi import (HyperProcess, Telemetry, Connection, CreateMode,
                              NOT_NULLABLE, SqlType, TableDefinition, escape_string_literal)

table = TableDefinition(table_name="orders", columns=[
    TableDefinition.Column("order_key", SqlType.int(), NOT_NULLABLE),
    TableDefinition.Column("customer_key", SqlType.int(), NOT_NULLABLE),
    TableDefinition.Column("total_price", SqlType.numeric(8, 2), NOT_NULLABLE),
])

with HyperProcess(telemetry=Telemetry.SEND_USAGE_DATA_TO_TABLEAU) as hyper:
    with Connection(endpoint=hyper.endpoint, database="orders.hyper",
                    create_mode=CreateMode.CREATE_AND_REPLACE) as conn:
        conn.catalog.create_table(table_definition=table)
        count = conn.execute_command(
            f"COPY {table.table_name} FROM {escape_string_literal('orders.parquet')} "
            f"WITH (FORMAT PARQUET)"
        )
        print(f"Inserted {count} rows")
```

## Query External Data

Query CSV and Parquet files without importing them into a Hyper file:

```python
# Parquet — schema is inferred
rows = connection.execute_list_query(
    "SELECT order_key, price FROM external('orders.parquet') WHERE priority = 'LOW'"
)

# CSV — schema must be specified via DESCRIPTOR
rows = connection.execute_list_query("""
    SELECT * FROM external('customers.csv',
        COLUMNS => DESCRIPTOR(id int, country text, name text),
        DELIMITER => ',', FORMAT => 'csv', HEADER => true)
""")

# Join across file formats
rows = connection.execute_list_query("""
    SELECT c.country, SUM(o.quantity * o.price) as revenue
    FROM external('orders.parquet') o
    JOIN external('customers.csv',
        COLUMNS => DESCRIPTOR(customer_key int, country text, name text),
        DELIMITER => ',', FORMAT => 'csv', HEADER => false) c
    ON o.customer_key = c.customer_key
    GROUP BY c.country
""")

# CREATE TABLE from external query
connection.execute_command("""
    CREATE TABLE filtered_orders AS
    SELECT order_key, price FROM external('orders.parquet')
    WHERE priority = 'LOW'
""")
```

## S3 and Cloud Sources

Hyper can natively read from S3 and S3-compatible services (e.g., Google Cloud Storage):

```python
# Read Parquet from S3
connection.execute_command("""
    CREATE TEMP EXTERNAL TABLE orders
    FOR 's3://my-bucket/orders/*.parquet'
    WITH ( FORMAT => 'parquet' )
""")
rows = connection.execute_list_query("SELECT * FROM orders")

# S3-compatible (e.g., Google Cloud Storage)
connection.execute_command(f"""
    SET 's3_endpoint' = 'storage.googleapis.com';
    CREATE TEMP EXTERNAL TABLE data
    FOR 's3://my-gcs-bucket/data.parquet'
    WITH ( FORMAT => 'parquet' )
""")
```

S3 credentials are configured via standard AWS environment variables or process parameters.

## Publish to Tableau Server/Cloud

After creating a `.hyper` file, publish it using `tableauserverclient`:

```python
import tableauserverclient as TSC

# Use Personal Access Tokens (store in env vars, never hardcode)
auth = TSC.PersonalAccessTokenAuth(
    token_name=os.environ["TABLEAU_TOKEN_NAME"],
    personal_access_token=os.environ["TABLEAU_TOKEN_VALUE"],
    site_id="my_site"
)
server = TSC.Server("https://my-server.online.tableau.com", use_server_version=True)

with server.auth.sign_in(auth):
    # Find project
    project_id = None
    for project in TSC.Pager(server.projects):
        if project.name == "target_project":
            project_id = project.id
            break

    datasource = TSC.DatasourceItem(project_id)
    server.datasources.publish(
        datasource, "my_extract.hyper", TSC.Server.PublishMode.Overwrite
    )
```

Publish modes: `Overwrite` (replace existing), `Append` (add rows), `CreateNew` (fail if exists).

## List Hyper File Contents

Inspect schemas, tables, and columns inside a `.hyper` file:

```python
from tableauhyperapi import HyperProcess, Telemetry, Connection, CreateMode, Nullability

with HyperProcess(telemetry=Telemetry.SEND_USAGE_DATA_TO_TABLEAU) as hyper:
    with Connection(hyper.endpoint, "my_file.hyper", CreateMode.NONE) as conn:
        for schema in conn.catalog.get_schema_names():
            for table in conn.catalog.get_table_names(schema=schema):
                table_def = conn.catalog.get_table_definition(name=table)
                print(f"Table {table.name} ({len(table_def.columns)} columns):")
                for col in table_def.columns:
                    nullable = "" if col.nullability == Nullability.NOT_NULLABLE else " NULLABLE"
                    print(f"  {col.name}: {col.type}{nullable}")
```

## Defragment a Hyper File

Copy all tables from an existing file into a fresh one to reduce file fragmentation:

```python
with HyperProcess(telemetry=Telemetry.SEND_USAGE_DATA_TO_TABLEAU) as hyper:
    with Connection(hyper.endpoint, "original.hyper", CreateMode.NONE) as source:
        with Connection(hyper.endpoint, "defragmented.hyper",
                        CreateMode.CREATE_AND_REPLACE) as target:
            for schema in source.catalog.get_schema_names():
                target.catalog.create_schema_if_not_exists(schema)
                for table in source.catalog.get_table_names(schema=schema):
                    table_def = source.catalog.get_table_definition(name=table)
                    target.catalog.create_table(table_definition=table_def)
                    target.execute_command(
                        f"INSERT INTO {table} SELECT * FROM {table} IN "
                        f"DATABASE {escape_string_literal('original.hyper')}"
                    )
```

## Convert Hyper File Format

Same approach as defragment — copy tables between files. Hyper automatically uses the current file format version for the new file.
