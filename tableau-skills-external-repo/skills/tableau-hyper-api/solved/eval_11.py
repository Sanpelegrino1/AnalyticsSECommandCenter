from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    NOT_NULLABLE, SqlType, TableDefinition,
    Inserter, TableName, HyperException
)

def run_eval_11():
    path_to_database = Path("deduplicated_sales.hyper")

    # Define the final target table schema in 'Extract'
    final_table = TableDefinition(
        table_name=TableName("Extract", "Sales"),
        columns=[
            TableDefinition.Column("Order ID", SqlType.int(), NOT_NULLABLE),
            TableDefinition.Column("Customer Name", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("Amount", SqlType.double(), NOT_NULLABLE),
        ]
    )

    # Input data with potential duplicate rows
    raw_data = [
        [101, "Alice", 50.0],
        [101, "Alice", 50.0], # Duplicate
        [102, "Bob", 75.0],
        [103, "Charlie", 90.0],
        [102, "Bob", 75.0],   # Duplicate
    ]

    try:
        # Start the HyperProcess
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            # 1. Open the file using CREATE_AND_REPLACE to start fresh
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.CREATE_AND_REPLACE
            ) as connection:
                # 2. Create the target schema and final table
                connection.catalog.create_schema(schema=final_table.table_name.schema_name)
                connection.catalog.create_table(table_definition=final_table)

                # 3. Use an internal temporary table for the raw, duplicate-prone load.
                # Use SQL 'CREATE TEMPORARY TABLE' and the final table definition as a template.
                # Temporary tables in Hyper exist only for the session and are faster for staging.
                temp_table_name = "raw_staging_table"
                connection.execute_command(
                    command=f"CREATE TEMPORARY TABLE {temp_table_name} "
                    f"AS SELECT * FROM {final_table.table_name} WITH NO DATA"
                )

                # 4. Load the raw, potentially messy data into the temporary staging table.
                # Note: Using execute_command to simulate loading from staging, or Inserter
                with Inserter(connection, TableName(None, temp_table_name)) as inserter:
                    inserter.add_rows(raw_data)
                    inserter.execute()

                # 5. Perform the high-performance de-duplication step in Hyper SQL.
                # Use 'INSERT INTO ... SELECT DISTINCT' to transfer only unique rows to the final table.
                # This leverages Hyper's optimized query engine for the heavy lifting.
                unique_rows = connection.execute_command(
                    command=f"INSERT INTO {final_table.table_name} "
                    f"SELECT DISTINCT * FROM {temp_table_name}"
                )

                print(f"Successfully loaded {unique_rows} unique records into {path_to_database} "
                      f"(out of {len(raw_data)} raw rows).")

    except HyperException as ex:
        print(f"An error occurred during de-duplication: {ex}")
        raise

if __name__ == "__main__":
    run_eval_11()
