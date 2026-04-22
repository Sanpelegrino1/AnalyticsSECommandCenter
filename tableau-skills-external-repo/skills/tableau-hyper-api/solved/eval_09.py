from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    TableName, escape_name, escape_string_literal, HyperException
)

def run_eval_09():
    jan_path = Path("January.hyper")
    feb_path = Path("February.hyper")

    # Assuming both tables are named 'Sales' in the 'Extract' schema
    sales_table = TableName("Extract", "Sales")

    try:
        # Start the HyperProcess
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            # 1. Open 'January' for modification using CreateMode.NONE
            # This will be our target database for the merge.
            with Connection(
                endpoint=hyper.endpoint,
                database=jan_path,
                create_mode=CreateMode.NONE
            ) as connection:
                # 2. Use 'ATTACH DATABASE' to link 'February' into the current session.
                # Use a database alias like 'feb_db' to reference it in queries.
                connection.execute_command(
                    command=f"ATTACH DATABASE {escape_string_literal(str(feb_path))} AS {escape_name('feb_db')}"
                )

                # 3. Perform a high-speed server-side merge using 'INSERT INTO ... SELECT'
                # This moves data directly between files without loading it into Python objects.
                # Refer to the table in the attached database as 'feb_db'.'Extract'.'Sales'
                count = connection.execute_command(
                    command=f"INSERT INTO {sales_table} "
                    f"SELECT * FROM {escape_name('feb_db')}.{sales_table}"
                )

                # 4. Detach when finished (optional, as connection close cleans up)
                connection.execute_command(command=f"DETACH DATABASE {escape_name('feb_db')}")

                print(f"Successfully merged {count} rows from {feb_path} into {jan_path}")

    except HyperException as ex:
        print(f"An error occurred during merge: {ex}")
        raise

if __name__ == "__main__":
    run_eval_09()
