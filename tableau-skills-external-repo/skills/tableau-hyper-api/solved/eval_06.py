import psycopg2
from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    NOT_NULLABLE, SqlType, TableDefinition,
    TableName, HyperException, escape_string_literal
)

def run_eval_06():
    path_to_database = Path("optimized_sales.hyper")
    path_to_temp_csv = Path("temp_sales_data.csv")

    # Define the table definition for our Hyper file
    sales_table = TableDefinition(
        table_name=TableName("Extract", "Sales"),
        columns=[
            TableDefinition.Column("Order ID", SqlType.int(), NOT_NULLABLE),
            TableDefinition.Column("Sales Amount", SqlType.double(), NOT_NULLABLE),
            TableDefinition.Column("Order Date", SqlType.date(), NOT_NULLABLE),
        ]
    )

    try:
        # 1. Connect to PostgreSQL and fetch large volumes of data efficiently
        # Using PostgreSQL's COPY TO command to write directly to a CSV file.
        # This is often faster than cursor-based paging for millions of rows.
        print("Extracting data from PostgreSQL...")
        with psycopg2.connect(
            dbname="postgres", user="user", host="localhost", password="password"
        ) as pg_conn:
            with pg_conn.cursor() as cursor:
                # Optimized extraction of millions of rows into a flat file format
                with open(path_to_temp_csv, "w") as f:
                    cursor.copy_expert(
                        f'COPY "Sales" TO STDOUT WITH (FORMAT CSV, HEADER)', 
                        f
                    )

        # 2. Start HyperProcess and Connection to create the .hyper file
        print("Loading data into Hyper using bulk load...")
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.CREATE_AND_REPLACE
            ) as connection:
                # Create schema and table
                connection.catalog.create_schema(schema=sales_table.table_name.schema_name)
                connection.catalog.create_table(table_definition=sales_table)

                # 3. Use Hyper's COPY FROM command for high-speed bulk loading
                # This is Hyper's fastest ingestion path for large volumes.
                count = connection.execute_command(
                    command=f"COPY {sales_table.table_name} "
                    f"FROM {escape_string_literal(str(path_to_temp_csv))} "
                    f"WITH (FORMAT CSV, HEADER)"
                )
                print(f"Successfully Bulk-Loaded {count} rows into {path_to_database}")

    except (psycopg2.Error, HyperException) as ex:
        print(f"An error occurred: {ex}")
        raise
    finally:
        # Cleanup temporary file
        if path_to_temp_csv.exists():
            path_to_temp_csv.unlink()

if __name__ == "__main__":
    run_eval_06()
