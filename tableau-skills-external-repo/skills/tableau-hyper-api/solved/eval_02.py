from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    escape_name, escape_string_literal, HyperException
)

def run_eval_02():
    path_to_database = Path("existing_customers.hyper")

    try:
        # Start the HyperProcess
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            # Open the existing file for modification using CreateMode.NONE
            # This is safer than CREATE_AND_REPLACE which would overwrite the file.
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.NONE
            ) as connection:
                # Update records using SQL and proper escaping
                # 'Customer' is table name, 'Segment' and 'Loyalty Points' are columns
                updated_count = connection.execute_command(
                    command=f"UPDATE {escape_name('Customers')} "
                    f"SET {escape_name('Loyalty Points')} = 1000 "
                    f"WHERE {escape_name('Segment')} = {escape_string_literal('Consumer')}"
                )
                print(f"Successfully updated {updated_count} rows in {path_to_database}")

    except HyperException as ex:
        print(f"An error occurred: {ex}")
        raise

if __name__ == "__main__":
    run_eval_02()
