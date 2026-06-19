"""Fill hl_IndicatedDeprecation in Comments.sql using heuristic candidate rules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_nlp import (
    classify_comment_candidate,
    iter_sql_statements,
    parse_comment_insert,
)


INSERT_SQL_PREFIX = (
    "INSERT INTO dsait4055db.Comments "
    "(Id, PostId, Score, Text, CreationDate, UserDisplayName, UserId, "
    "hl_IndicatedDeprecation) VALUES "
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-sql", default="Comments.sql")
    parser.add_argument(
        "--output-sql",
        default="data/processed/comment_nlp/Comments_heuristic_labeled.sql",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Also overwrite rows where hl_IndicatedDeprecation is already set.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_sql)
    output_path = Path(args.output_sql)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    predicted_positive = 0
    preserved_existing = 0

    with input_path.open("r", encoding="utf-8", errors="replace") as src, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        for statement in iter_sql_statements(src):
            row = parse_comment_insert(statement)
            if row is None:
                dst.write(statement.rstrip())
                dst.write(";\n")
                continue

            if row["source_label"] and not args.overwrite_existing:
                dst.write(statement.rstrip())
                dst.write(";\n")
                preserved_existing += 1
                continue

            category, _reason = classify_comment_candidate(row["text"])
            prediction = 1 if category == "temporal_candidate" else 0
            predicted_positive += prediction
            processed += 1

            dst.write(_build_insert_statement(row, prediction))
            dst.write("\n")

    summary = {
        "input_sql": str(input_path),
        "output_sql": str(output_path),
        "processed_rows": processed,
        "predicted_positive": predicted_positive,
        "predicted_negative": processed - predicted_positive,
        "preserved_existing": preserved_existing,
        "positive_rule": "candidate_category == temporal_candidate",
    }
    print(json.dumps(summary, indent=2))


def _build_insert_statement(row: dict[str, str], prediction: int) -> str:
    values = [
        _sql_literal(row.get("comment_id", ""), numeric=True),
        _sql_literal(row.get("post_id", ""), numeric=True),
        _sql_literal(row.get("score", ""), numeric=True),
        _sql_literal(row.get("text", "")),
        _sql_literal(row.get("creation_date", "")),
        _sql_literal(row.get("user_display_name", "")),
        _sql_literal(row.get("user_id", ""), numeric=True),
        str(prediction),
    ]
    return INSERT_SQL_PREFIX + "(" + ", ".join(values) + ");"


def _sql_literal(value: str, numeric: bool = False) -> str:
    if value == "":
        return "null"
    if numeric:
        return value
    escaped = (
        value.replace("\\", "\\\\")
        .replace("\0", "\\0")
        .replace("\b", "\\b")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\x1a", "\\Z")
        .replace("'", "\\'")
        .replace('"', '\\"')
    )
    return f"'{escaped}'"


if __name__ == "__main__":
    main()
