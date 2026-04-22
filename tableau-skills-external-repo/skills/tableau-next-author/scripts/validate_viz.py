#!/usr/bin/env python3
"""Validate a Tableau Next visualization JSON before POSTing.

Usage:
    python scripts/validate_viz.py revenue_by_region.json
    python scripts/generate_viz.py ... | python scripts/validate_viz.py -
    python scripts/validate_viz.py --quiet revenue_by_region.json
"""

import argparse
import json
import sys

from lib.validators import validate, ValidationResult


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a Tableau Next visualization JSON payload",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="JSON file to validate, or '-' for stdin (default: stdin)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only print failures (exit code still reflects result)",
    )
    args = parser.parse_args()

    # Read input
    try:
        if args.input == "-":
            raw = sys.stdin.read()
        else:
            with open(args.input) as f:
                raw = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(2)
    except IOError as exc:
        print(f"Error reading input: {exc}", file=sys.stderr)
        sys.exit(2)

    # Parse JSON
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(payload, dict):
        print("Error: Top-level JSON value must be an object.", file=sys.stderr)
        sys.exit(2)

    # Validate
    results = validate(payload)
    failures = [r for r in results if not r.ok]
    passes = [r for r in results if r.ok]

    # Output
    if not args.quiet:
        for r in passes:
            print(f"  [PASS] {r.rule}: {r.message}")

    for r in failures:
        print(f"  [FAIL] {r.rule}: {r.message}")
        if r.fix:
            print(f"         Fix: {r.fix}")

    print()
    if failures:
        print(f"FAILED: {len(failures)} error(s), {len(passes)} passed.")
        sys.exit(1)
    else:
        print(f"ALL {len(passes)} checks passed — safe to POST.")
        sys.exit(0)


if __name__ == "__main__":
    main()
