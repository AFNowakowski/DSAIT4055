"""Filter prepared comment candidate CSV files by category and related fields."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--candidate-category", default=None)
    parser.add_argument("--candidate-reason", default=None)
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    filtered = []
    for row in rows:
        if args.candidate_category and row.get("candidate_category", "") != args.candidate_category:
            continue
        if args.candidate_reason and row.get("candidate_reason", "") != args.candidate_reason:
            continue
        filtered.append(row)

    fieldnames = list(rows[0].keys()) if rows else []
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(filtered)

    print(
        json.dumps(
            {
                "input_csv": str(input_path),
                "output_csv": str(output_path),
                "input_rows": len(rows),
                "filtered_rows": len(filtered),
                "candidate_category": args.candidate_category,
                "candidate_reason": args.candidate_reason,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
