from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    TableName, escape_name, HyperException
)

def run_eval_08():
    path_to_database = Path("sales_extract.hyper")

    # Target table name for modernization
    table_name = TableName("Extract", "Sales")

    try:
        # Start the HyperProcess
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            # 1. Open the existing file for schema changes using CreateMode.NONE
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.NONE
            ) as connection:
                # 2. Use 'ALTER TABLE ... ADD COLUMN' SQL statement via execute_command
                # We'll add the new column 'DiscountCode' as a nullable text field.
                # All existing rows will have null for this new column initially.
                connection.execute_command(
                    command=f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {escape_name('DiscountCode')} TEXT NULL"
                )
                print(f"Successfully added column 'DiscountCode' to {path_to_database} using ALTER TABLE.")

    except HyperException as ex:
        print(f"An error occurred: {ex}")
        raise

if __name__ == "__main__":
    run_eval_08()
