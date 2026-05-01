#!/usr/bin/env python3

import argparse
import csv
import json
from collections import deque
from pathlib import Path


def load_manifest(manifest_path: Path) -> dict:
    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_fact_table(manifest: dict) -> str:
    for table in manifest.get("tables", []):
        if table.get("tableRole") == "fact":
            return table["tableName"]
    raise ValueError("Manifest does not define a fact table.")


def build_table_map(manifest: dict) -> dict[str, dict]:
    return {table["tableName"]: table for table in manifest.get("tables", [])}


def build_join_graph(manifest: dict) -> dict[str, list[dict]]:
    graph: dict[str, list[dict]] = {}
    for join_path in manifest.get("joinPaths", []):
        graph.setdefault(join_path["fromTable"], []).append(join_path)
    return graph


def discover_table_order(fact_table: str, join_graph: dict[str, list[dict]]) -> list[str]:
    order: list[str] = []
    queue = deque([fact_table])
    seen = {fact_table}

    while queue:
        current = queue.popleft()
        order.append(current)
        for join_path in join_graph.get(current, []):
            child = join_path["toTable"]
            if child not in seen:
                seen.add(child)
                queue.append(child)

    return order


def read_csv_headers(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader)


def load_lookup_table(csv_path: Path, key_field: str) -> dict[str, dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        lookup: dict[str, dict[str, str]] = {}
        for row in reader:
            lookup[row[key_field]] = row
    return lookup


def join_dimension_rows(
    current_table: str,
    current_row: dict[str, str],
    join_graph: dict[str, list[dict]],
    lookups: dict[str, dict[str, dict[str, str]]],
    joined_rows: dict[str, dict[str, str]],
    missing_counts: dict[str, int],
) -> None:
    for join_path in join_graph.get(current_table, []):
        from_field = join_path["fromField"]
        to_table = join_path["toTable"]
        to_field = join_path["toField"]

        join_value = current_row.get(from_field, "")
        matched_row = lookups.get(to_table, {}).get(join_value)
        if matched_row is None:
            missing_counts[to_table] = missing_counts.get(to_table, 0) + 1
            joined_rows[to_table] = {}
            continue

        joined_rows[to_table] = matched_row
        join_dimension_rows(to_table, matched_row, join_graph, lookups, joined_rows, missing_counts)


def build_output_headers(table_order: list[str], headers_by_table: dict[str, list[str]]) -> list[str]:
    output_headers: list[str] = []
    for table_name in table_order:
        for column_name in headers_by_table[table_name]:
            output_headers.append(f"{table_name}__{column_name}")
    return output_headers


def flatten_manifest_csv(manifest_path: Path, output_path: Path, limit: int | None = None) -> dict:
    manifest = load_manifest(manifest_path)
    dataset_dir = manifest_path.parent
    table_map = build_table_map(manifest)
    fact_table = resolve_fact_table(manifest)
    join_graph = build_join_graph(manifest)
    table_order = discover_table_order(fact_table, join_graph)

    headers_by_table: dict[str, list[str]] = {}
    for table_name in table_order:
        csv_path = dataset_dir / f"{table_name}.csv"
        headers_by_table[table_name] = read_csv_headers(csv_path)

    lookups: dict[str, dict[str, dict[str, str]]] = {}
    for table_name in table_order:
        if table_name == fact_table:
            continue
        primary_keys = table_map[table_name].get("primaryKey") or []
        if len(primary_keys) != 1:
            raise ValueError(f"Table {table_name} must have exactly one primary key field for flattening.")
        csv_path = dataset_dir / f"{table_name}.csv"
        lookups[table_name] = load_lookup_table(csv_path, primary_keys[0])

    output_headers = build_output_headers(table_order, headers_by_table)
    missing_counts: dict[str, int] = {}
    row_count = 0

    fact_csv_path = dataset_dir / f"{fact_table}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with fact_csv_path.open("r", encoding="utf-8-sig", newline="") as fact_handle, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as output_handle:
        reader = csv.DictReader(fact_handle)
        writer = csv.DictWriter(output_handle, fieldnames=output_headers)
        writer.writeheader()

        for fact_row in reader:
            joined_rows: dict[str, dict[str, str]] = {fact_table: fact_row}
            join_dimension_rows(fact_table, fact_row, join_graph, lookups, joined_rows, missing_counts)

            output_row: dict[str, str] = {}
            for table_name in table_order:
                source_row = joined_rows.get(table_name, {})
                for column_name in headers_by_table[table_name]:
                    output_row[f"{table_name}__{column_name}"] = source_row.get(column_name, "")

            writer.writerow(output_row)
            row_count += 1
            if limit is not None and row_count >= limit:
                break

    return {
        "datasetName": manifest.get("datasetName", ""),
        "manifestPath": str(manifest_path),
        "outputPath": str(output_path),
        "factTable": fact_table,
        "tableOrder": table_order,
        "rowCount": row_count,
        "missingJoinCounts": missing_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Flatten a manifest-defined relational CSV dataset into one wide CSV.")
    parser.add_argument("--manifest", required=True, help="Path to the manifest JSON file.")
    parser.add_argument("--output", help="Output CSV path. Defaults to <dataset folder>/<manifest stem>.flattened.csv")
    parser.add_argument("--limit", type=int, help="Optional row limit for quick validation runs.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    output_path = Path(args.output).resolve() if args.output else manifest_path.with_name(f"{manifest_path.stem}.flattened.csv")

    summary = flatten_manifest_csv(manifest_path, output_path, args.limit)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())