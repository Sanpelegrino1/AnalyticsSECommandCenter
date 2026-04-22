from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    TableName, escape_name, HyperException
)

def run_eval_10():
    path_to_database = Path("sales_verification.hyper")

    # Assuming 'Sales' in 'Extract'
    sales_table = TableName("Extract", "Sales")

    try:
        # Start the HyperProcess
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            # 1. Open the existing file read-only using CreateMode.NONE
            # This is standard for post-ingestion validation or QA processes.
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.NONE
            ) as connection:
                # 2. Use 'execute_scalar_query' for a single result count
                # Perform a SQL check for any null values in the target column.
                # Wrap the column name 'OrderID' in escape_name to handle it correctly.
                null_count = connection.execute_scalar_query(
                    query=f"SELECT COUNT(*) FROM {sales_table} "
                    f"WHERE {escape_name('OrderID')} IS NULL"
                )

                # 3. Validate results and report results
                if null_count > 0:
                    print(f"FAILED QA Check: Found {null_count} NULL values in the OrderID column!")
                else:
                    print(f"PASSED QA Check: No NULL values detected in any OrderID records.")

                # Return boolean for pipeline usage
                return null_count == 0

    except HyperException as ex:
        print(f"An error occurred during verification: {ex}")
        raise

if __name__ == "__main__":
    run_eval_10()
