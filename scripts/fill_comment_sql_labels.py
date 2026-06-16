"""Fill hl_IndicatedDeprecation in Comments.sql using the trained classifier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_classifier import load_comment_classifier
from nlp_pipeline.comment_database import predict_comment_batch
from nlp_pipeline.comment_nlp import iter_sql_statements, parse_comment_insert


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
        default="data/processed/comment_nlp/Comments_labeled.sql",
    )
    parser.add_argument(
        "--model",
        default="data/processed/comment_nlp/comment_classifier.joblib",
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Also overwrite rows where hl_IndicatedDeprecation is already set.",
    )
    args = parser.parse_args()

    model = load_comment_classifier(args.model)
    input_path = Path(args.input_sql)
    output_path = Path(args.output_sql)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    predicted_positive = 0
    preserved_existing = 0
    batched_rows: list[dict[str, str]] = []
    output_rows: list[dict[str, object]] = []

    with input_path.open("r", encoding="utf-8", errors="replace") as src, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        for statement in iter_sql_statements(src):
            row = parse_comment_insert(statement)
            if row is None:
                _flush_batch(
                    dst=dst,
                    model=model,
                    rows=batched_rows,
                    output_rows=output_rows,
                    threshold=args.threshold,
                )
                processed += len(output_rows)
                predicted_positive += sum(int(r["prediction"]) for r in output_rows)
                output_rows.clear()
                dst.write(statement.rstrip())
                dst.write(";\n")
                continue

            if row["source_label"] and not args.overwrite_existing:
                _flush_batch(
                    dst=dst,
                    model=model,
                    rows=batched_rows,
                    output_rows=output_rows,
                    threshold=args.threshold,
                )
                processed += len(output_rows)
                predicted_positive += sum(int(r["prediction"]) for r in output_rows)
                output_rows.clear()
                dst.write(statement.rstrip())
                dst.write(";\n")
                preserved_existing += 1
                continue

            batched_rows.append(row)
            if len(batched_rows) >= args.batch_size:
                _flush_batch(
                    dst=dst,
                    model=model,
                    rows=batched_rows,
                    output_rows=output_rows,
                    threshold=args.threshold,
                )
                processed += len(output_rows)
                predicted_positive += sum(int(r["prediction"]) for r in output_rows)
                output_rows.clear()

        _flush_batch(
            dst=dst,
            model=model,
            rows=batched_rows,
            output_rows=output_rows,
            threshold=args.threshold,
        )
        processed += len(output_rows)
        predicted_positive += sum(int(r["prediction"]) for r in output_rows)

    summary = {
        "input_sql": str(input_path),
        "output_sql": str(output_path),
        "processed_rows": processed,
        "predicted_positive": predicted_positive,
        "predicted_negative": processed - predicted_positive,
        "preserved_existing": preserved_existing,
        "threshold": args.threshold,
    }
    print(json.dumps(summary, indent=2))


def _flush_batch(
    dst,
    model,
    rows: list[dict[str, str]],
    output_rows: list[dict[str, object]],
    threshold: float,
) -> None:
    if not rows:
        return
    predictions = predict_comment_batch(model, rows, threshold=threshold)
    for prediction in predictions:
        dst.write(_build_insert_statement(prediction))
        dst.write("\n")
        output_rows.append(prediction)
    rows.clear()


def _build_insert_statement(row: dict[str, object]) -> str:
    values = [
        _sql_literal(str(row.get("comment_id", "")), numeric=True),
        _sql_literal(str(row.get("post_id", "")), numeric=True),
        _sql_literal(str(row.get("score", "")), numeric=True),
        _sql_literal(str(row.get("text", ""))),
        _sql_literal(str(row.get("creation_date", ""))),
        _sql_literal(str(row.get("user_display_name", ""))),
        _sql_literal(str(row.get("user_id", "")), numeric=True),
        str(int(row.get("prediction", 0))),
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
