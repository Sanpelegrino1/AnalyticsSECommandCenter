from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    NOT_NULLABLE, SqlType, TableDefinition,
    escape_string_literal, HyperException
)

def run_eval_01():
    path_to_database = Path("sales_data.hyper")
    path_to_csv = Path("sales_data.csv")

    # Define the table schema
    sales_table = TableDefinition(
        table_name="Sales",
        columns=[
            TableDefinition.Column("Date", SqlType.date(), NOT_NULLABLE),
            TableDefinition.Column("Product", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("Quantity", SqlType.int(), NOT_NULLABLE),
            TableDefinition.Column("Revenue", SqlType.double(), NOT_NULLABLE),
        ]
    )

    try:
        # Start the HyperProcess
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            # Create a new .hyper file (overwriting if it exists)
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.CREATE_AND_REPLACE
            ) as connection:
                # Create the table
                connection.catalog.create_table(table_definition=sales_table)

                # Load data from CSV using the COPY command (high performance)
                # FORMAT csv, HEADER option, and proper escaping for the file path
                count = connection.execute_command(
                    command=f"COPY {sales_table.table_name} "
                    f"FROM {escape_string_literal(str(path_to_csv))} "
                    f"WITH (FORMAT csv, HEADER)"
                )
                print(f"Successfully loaded {count} rows from {path_to_csv} into {path_to_database}")

    except HyperException as ex:
        print(f"An error occurred: {ex}")
        raise

if __name__ == "__main__":
    run_eval_01()
