import psycopg2
from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    NOT_NULLABLE, SqlType, TableDefinition,
    Inserter, TableName, HyperException
)

def run_eval_04():
    path_to_database = Path("denormalized_sales.hyper")

    # Define the output schema for the denormalized table
    denormalized_table = TableDefinition(
        table_name=TableName("Extract", "Extract"),
        columns=[
            TableDefinition.Column("Order ID", SqlType.int(), NOT_NULLABLE),
            TableDefinition.Column("Customer Name", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("Product Name", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("Quantity", SqlType.int(), NOT_NULLABLE),
            TableDefinition.Column("Revenue", SqlType.double(), NOT_NULLABLE),
        ]
    )

    # SQL query to join the 4 tables in PostgreSQL
    # Using psycopg2 to fetch results and Hyper Inserter to load them
    query = """
    SELECT
        o.id AS "Order ID",
        c.name AS "Customer Name",
        p.name AS "Product Name",
        od.quantity AS "Quantity",
        od.quantity * od.unit_price AS "Revenue"
    FROM
        "Orders" o
        JOIN "Customers" c ON o.customer_id = c.id
        JOIN "Order_Details" od ON o.id = od.order_id
        JOIN "Products" p ON od.product_id = p.id
    """

    try:
        # 1. Connect to PostgreSQL and fetch joined data
        # Note: Using placeholder values for connection parameters
        with psycopg2.connect(
            dbname="postgres", user="user", password="password", host="localhost"
        ) as pg_conn:
            with pg_conn.cursor() as cursor:
                cursor.execute(query)

                # 2. Start HyperProcess and Connection to create the .hyper file
                with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
                    with Connection(
                        endpoint=hyper.endpoint,
                        database=path_to_database,
                        create_mode=CreateMode.CREATE_AND_REPLACE
                    ) as connection:
                        # Create schema and table
                        connection.catalog.create_schema(schema=denormalized_table.table_name.schema_name)
                        connection.catalog.create_table(table_definition=denormalized_table)

                        # 3. Use Inserter to load the joined PostgreSQL results into Hyper
                        # Inserter allows us to stream results row-by-row into the .hyper file
                        with Inserter(connection, denormalized_table) as inserter:
                            # Batch results for better performance
                            while True:
                                rows = cursor.fetchmany(1000)
                                if not rows:
                                    break
                                inserter.add_rows(rows)

                            inserter.execute()
                        print(f"Successfully created denormalized Hyper file: {path_to_database}")

    except (psycopg2.Error, HyperException) as ex:
        print(f"An error occurred: {ex}")
        raise

if __name__ == "__main__":
    run_eval_04()
