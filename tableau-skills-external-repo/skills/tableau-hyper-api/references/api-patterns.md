# API Patterns Reference

Detailed reference for Hyper API types, options, and utilities.

## Table of Contents
- [SqlType Mapping](#sqltype-mapping)
- [CreateMode Options](#createmode-options)
- [Escape Functions](#escape-functions)
- [Query Execution Methods](#query-execution-methods)
- [Catalog API](#catalog-api)
- [Process and Connection Parameters](#process-and-connection-parameters)

## SqlType Mapping

| Python / Data Type | SqlType Constructor | Notes |
|---|---|---|
| String | `SqlType.text()` | Variable-length text |
| Integer (16-bit) | `SqlType.small_int()` | -32,768 to 32,767 |
| Integer (32-bit) | `SqlType.int()` | Standard integer |
| Integer (64-bit) | `SqlType.big_int()` | Large integers |
| Float | `SqlType.double()` | 64-bit floating point |
| Decimal | `SqlType.numeric(precision, scale)` | e.g. `SqlType.numeric(8, 2)` |
| Boolean | `SqlType.bool()` | True/False |
| Date | `SqlType.date()` | Use `datetime.date` |
| Timestamp | `SqlType.timestamp()` | Use `datetime.datetime` |
| Timestamp w/ TZ | `SqlType.timestamp_tz()` | Timezone-aware |
| Time | `SqlType.time()` | Time of day |
| Geography | `SqlType.geography()` | Spatial data (WKT) |
| Binary | `SqlType.bytes()` | Raw bytes |
| Interval | `SqlType.interval()` | Time intervals |
| JSON | `SqlType.json()` | JSON data |
| OID | `SqlType.oid()` | Object identifiers |

Column nullability uses `NOT_NULLABLE` or `NULLABLE` constants from `tableauhyperapi`.

## CreateMode Options

| Mode | Behavior |
|---|---|
| `CreateMode.CREATE_AND_REPLACE` | Create new file, replace if exists. Use for fresh extracts. |
| `CreateMode.CREATE` | Create new file, error if exists. Use when duplicates are unexpected. |
| `CreateMode.CREATE_IF_NOT_EXISTS` | Create only if file doesn't exist. Use for idempotent scripts. |
| `CreateMode.NONE` | Open existing file only, error if missing. Use for read/update operations. |

## Escape Functions

Use these to prevent SQL injection and handle special characters:

```python
from tableauhyperapi import escape_name, escape_string_literal

# Identifiers (table names, column names with spaces/special chars)
escape_name("Customer ID")       # → "Customer ID" (quoted identifier)
escape_name("Orders")            # → "Orders"

# String values in SQL expressions
escape_string_literal("O'Brien")  # → 'O''Brien' (escaped single quote)
escape_string_literal("/path/to/file.csv")
```

**Rule of thumb:** `escape_name` for column/table names, `escape_string_literal` for values. Omitting these causes breakage on names with spaces, quotes, or reserved words.

## Query Execution Methods

| Method | Returns | Use When |
|---|---|---|
| `execute_list_query(query)` | `list[list]` — rows as lists of values | Reading multiple rows |
| `execute_scalar_query(query)` | Single value | `SELECT COUNT(*)`, single-cell results |
| `execute_command(command)` | `int` — affected row count | INSERT/UPDATE/DELETE/COPY statements |

## Catalog API

The `connection.catalog` object provides schema/table metadata:

```python
catalog = connection.catalog

# Schema operations
catalog.create_schema(schema="Extract")
catalog.has_schema(schema="Extract")           # → bool
schemas = catalog.get_schema_names()            # → list of SchemaName

# Table operations
catalog.create_table(table_definition=my_table)
catalog.has_table(name=TableName("Extract", "Extract"))  # → bool
tables = catalog.get_table_names(schema="public")        # → list of TableName
table_def = catalog.get_table_definition(name=my_table)  # → TableDefinition

# Inspect columns from a TableDefinition
for col in table_def.columns:
    print(col.name, col.type, col.nullability, col.collation)
```

## Process and Connection Parameters

### HyperProcess Parameters

```python
process_parameters = {
    "log_file_max_count": "2",          # Limit log files
    "log_file_size_limit": "100M",      # Limit log file size
}

with HyperProcess(
    telemetry=Telemetry.SEND_USAGE_DATA_TO_TABLEAU,
    parameters=process_parameters
) as hyper:
    ...
```

### Connection Parameters

```python
connection_parameters = {
    "lc_time": "en_US",  # Locale for time formatting
}

with Connection(
    endpoint=hyper.endpoint,
    database=path_to_database,
    create_mode=CreateMode.CREATE_AND_REPLACE,
    parameters=connection_parameters
) as connection:
    ...
```

Full parameter documentation: [Process Settings](https://tableau.github.io/hyper-db/docs/hyper-api/hyper_process#process-settings), [Connection Settings](https://tableau.github.io/hyper-db/docs/hyper-api/connection#connection-settings).
