"""Fill hl_IndicatedDeprecation in Comments SQL from comment-level Ollama labels."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_nlp import iter_sql_statements, parse_comment_insert


INSERT_SQL_PREFIX = (
    "INSERT INTO dsait4055db.Comments "
    "(Id, PostId, Score, Text, CreationDate, UserDisplayName, UserId, "
    "hl_IndicatedDeprecation) VALUES "
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-sql", default="Comments.sql")
    parser.add_argument("--labels-csv", required=True)
    parser.add_argument(
        "--output-sql",
        default="data/processed/comment_nlp/Comments_ollama_labeled.sql",
    )
    parser.add_argument(
        "--positive-label",
        default="temporal_obsolescence",
        help="Ollama label value that should map to 1.",
    )
    args = parser.parse_args()

    label_map = _read_label_map(Path(args.labels_csv), args.positive_label)
    input_path = Path(args.input_sql)
    output_path = Path(args.output_sql)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    predicted_positive = 0
    matched_label_rows = 0

    with input_path.open("r", encoding="utf-8", errors="replace") as src, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        for statement in iter_sql_statements(src):
            row = parse_comment_insert(statement)
            if row is None:
                dst.write(statement.rstrip())
                dst.write(";\n")
                continue

            comment_id = row.get("comment_id", "")
            prediction = label_map.get(comment_id, 0)
            if comment_id in label_map:
                matched_label_rows += 1
            predicted_positive += prediction
            processed += 1

            dst.write(_build_insert_statement(row, prediction))
            dst.write("\n")

    summary = {
        "input_sql": str(input_path),
        "labels_csv": str(args.labels_csv),
        "output_sql": str(output_path),
        "processed_rows": processed,
        "matched_label_rows": matched_label_rows,
        "predicted_positive": predicted_positive,
        "predicted_negative": processed - predicted_positive,
        "default_for_unmatched_rows": 0,
        "positive_label": args.positive_label,
    }
    print(json.dumps(summary, indent=2))


def _read_label_map(path: Path, positive_label: str) -> dict[str, int]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    label_map: dict[str, int] = {}
    for row in rows:
        comment_id = row.get("comment_id", "")
        if not comment_id:
            continue
        label_map[comment_id] = 1 if row.get("ollama_label", "").strip() == positive_label else 0
    return label_map


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
