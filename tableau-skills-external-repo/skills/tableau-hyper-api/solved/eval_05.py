import psycopg2
from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    NOT_NULLABLE, SqlType, TableDefinition,
    Inserter, TableName, HyperException
)

def run_eval_05():
    path_to_database = Path("multiple_tables.hyper")

    # Define the 4 table definitions for our Hyper file
    # Using TableName to specify the "Extract" schema (common in Tableau)
    tables = {
        "Orders": TableDefinition(
            table_name=TableName("Extract", "Orders"),
            columns=[
                TableDefinition.Column("id", SqlType.int(), NOT_NULLABLE),
                TableDefinition.Column("customer_id", SqlType.int(), NOT_NULLABLE),
                TableDefinition.Column("order_date", SqlType.date(), NOT_NULLABLE),
            ]
        ),
        "Customers": TableDefinition(
            table_name=TableName("Extract", "Customers"),
            columns=[
                TableDefinition.Column("id", SqlType.int(), NOT_NULLABLE),
                TableDefinition.Column("name", SqlType.text(), NOT_NULLABLE),
                TableDefinition.Column("email", SqlType.text(), NOT_NULLABLE),
            ]
        ),
        "Products": TableDefinition(
            table_name=TableName("Extract", "Products"),
            columns=[
                TableDefinition.Column("id", SqlType.int(), NOT_NULLABLE),
                TableDefinition.Column("name", SqlType.text(), NOT_NULLABLE),
                TableDefinition.Column("category", SqlType.text(), NOT_NULLABLE),
            ]
        ),
        "Order_Details": TableDefinition(
            table_name=TableName("Extract", "Order_Details"),
            columns=[
                TableDefinition.Column("order_id", SqlType.int(), NOT_NULLABLE),
                TableDefinition.Column("product_id", SqlType.int(), NOT_NULLABLE),
                TableDefinition.Column("quantity", SqlType.int(), NOT_NULLABLE),
                TableDefinition.Column("unit_price", SqlType.double(), NOT_NULLABLE),
            ]
        )
    }

    try:
        # 1. Connect to PostgreSQL
        with psycopg2.connect(
            dbname="postgres", user="user", host="localhost", password="password"
        ) as pg_conn:
            with pg_conn.cursor() as cursor:

                # 2. Start HyperProcess and Connection
                with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
                    with Connection(
                        endpoint=hyper.endpoint,
                        database=path_to_database,
                        create_mode=CreateMode.CREATE_AND_REPLACE
                    ) as connection:
                        
                        # Create the schema for all tables
                        connection.catalog.create_schema(schema="Extract")

                        # 3. Iterate through each table and perform independent load operations
                        for table_name, table_def in tables.items():
                            print(f"Loading table: {table_name}")
                            
                            # Create the table in Hyper
                            connection.catalog.create_table(table_definition=table_def)

                            # Fetch data from PostgreSQL for this table
                            cursor.execute(f'SELECT * FROM "{table_name}"')

                            # Use Inserter to load PostgreSQL data into this Hyper table
                            with Inserter(connection, table_def) as inserter:
                                while True:
                                    rows = cursor.fetchmany(1000)
                                    if not rows:
                                        break
                                    inserter.add_rows(rows)
                                inserter.execute()

                        print(f"Successfully loaded 4 tables into {path_to_database}")

    except (psycopg2.Error, HyperException) as ex:
        print(f"An error occurred: {ex}")
        raise

if __name__ == "__main__":
    run_eval_05()
