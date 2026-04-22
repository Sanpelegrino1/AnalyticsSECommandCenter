import pandas as pd
from pathlib import Path
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    NOT_NULLABLE, SqlType, TableDefinition,
    Inserter, TableName, escape_name, HyperException
)

def run_eval_03():
    path_to_database = Path("geodata.hyper")

    # Sample pandas DataFrame with geospatial coordinates
    df = pd.DataFrame({
        "City": ["Seattle", "Munich", "Tokyo"],
        "Longitude": [-122.338083, 11.584329, 139.650311],
        "Latitude": [47.647528, 48.139257, 35.6762]
    })

    # Prepare data for insertion: Convert coordinates into WKT point format
    # Tableau expects lowercase (point(lon lat))
    df["WKT"] = df.apply(lambda row: f"point({row.Longitude} {row.Latitude})", axis=1)

    # Define the target table schema with a 'geography' type column
    geo_table = TableDefinition(
        table_name=TableName("Extract", "Extract"),
        columns=[
            TableDefinition.Column("City", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("Location", SqlType.geography(), NOT_NULLABLE),
        ]
    )

    # Define the layout of our input data (pandas columns we will feed into Inserter)
    inserter_definition = [
        TableDefinition.Column("City", SqlType.text(), NOT_NULLABLE),
        TableDefinition.Column("WKT_input", SqlType.text(), NOT_NULLABLE),
    ]

    # Map the input columns to the target table columns
    # 'City' is passed through directly.
    # 'WKT_input' is CAST to GEOGRAPHY format for the 'Location' column.
    column_mappings = [
        "City",
        Inserter.ColumnMapping(
            "Location",
            f"CAST({escape_name('WKT_input')} AS GEOGRAPHY)"
        )
    ]

    try:
        with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
            with Connection(
                endpoint=hyper.endpoint,
                database=path_to_database,
                create_mode=CreateMode.CREATE_AND_REPLACE
            ) as connection:
                # Create the schema and table
                connection.catalog.create_schema(schema=geo_table.table_name.schema_name)
                connection.catalog.create_table(table_definition=geo_table)

                # Use the Inserter with the defined column mapping and input data definition
                with Inserter(connection, geo_table, column_mappings,
                              inserter_definition=inserter_definition) as inserter:
                    # Provide City and the WKT string for each row
                    inserter.add_rows(df[["City", "WKT"]].values.tolist())
                    inserter.execute()

                print(f"Successfully loaded {len(df)} geospatial rows into {path_to_database}")

    except HyperException as ex:
        print(f"An error occurred: {ex}")
        raise

if __name__ == "__main__":
    run_eval_03()
