from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    NOT_NULLABLE, SqlType, TableDefinition,
    Inserter, TableName, HyperException
)

def run_eval_07():
    path_to_database = Path("daily_sales.hyper")

    # The existing table definition
    sales_table = TableDefinition(
        table_name=TableName("Extract", "Sales"),
        columns=[
            TableDefinition.Column("Date", SqlType.date(), NOT_NULLABLE),
            TableDefinition.Column("Amount", SqlType.double(), NOT_NULLABLE),
        ]
    )

    # Today's new daily records
    new_data = [
        ["2024-03-19", 1250.50],
        ["2024-03-19", 980.00],
    ]

    try:
        # Start the HyperProcess
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            # 1. Open the existing file using CreateMode.NONE 
            # This is critical as CREATE_AND_REPLACE would wipe existing history.
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.NONE
            ) as connection:
                # 2. Append new records using the Inserter
                # The Inserter will append these rows to the end of the existing table.
                with Inserter(connection, sales_table) as inserter:
                    inserter.add_rows(new_data)
                    inserter.execute()

                print(f"Successfully appended {len(new_data)} daily records to {path_to_database}")

    except HyperException as ex:
        print(f"An error occurred: {ex}")
        raise

if __name__ == "__main__":
    run_eval_07()
