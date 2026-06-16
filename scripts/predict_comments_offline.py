"""Run the trained comment classifier without requiring MySQL ingress."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_classifier import load_comment_classifier
from nlp_pipeline.comment_database import predict_comment_batch
from nlp_pipeline.comment_nlp import iter_sql_statements, parse_comment_insert


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default="data/processed/comment_nlp/comment_classifier.joblib",
    )
    parser.add_argument("--text", default=None, help="Classify a single comment string.")
    parser.add_argument("--input-csv", default=None, help="CSV with at least a text column.")
    parser.add_argument("--input-sql", default=None, help="Comments.sql-style input file.")
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output-csv", default=None)
    args = parser.parse_args()

    provided_inputs = sum(
        value is not None for value in (args.text, args.input_csv, args.input_sql)
    )
    if provided_inputs != 1:
        parser.error("Provide exactly one of --text, --input-csv, or --input-sql.")

    model = load_comment_classifier(args.model)

    if args.text is not None:
        rows = [
            {
                "comment_id": "",
                "post_id": "",
                "score": "",
                "text": args.text,
                "creation_date": "",
                "source_label": "",
            }
        ]
        prediction = predict_comment_batch(model, rows, threshold=args.threshold)[0]
        print(json.dumps(prediction, indent=2))
        return

    if args.input_csv is not None:
        rows = _read_csv_rows(
            path=Path(args.input_csv),
            text_column=args.text_column,
            limit=args.limit,
        )
    else:
        rows = _read_sql_rows(Path(args.input_sql), limit=args.limit)

    predictions = predict_comment_batch(model, rows, threshold=args.threshold)

    if args.output_csv:
        _write_predictions_csv(Path(args.output_csv), predictions)

    summary = {
        "processed": len(predictions),
        "predicted_positive": sum(int(row["prediction"]) for row in predictions),
        "predicted_negative": sum(1 - int(row["prediction"]) for row in predictions),
        "threshold": args.threshold,
        "output_csv": args.output_csv,
    }
    print(json.dumps(summary, indent=2))


def _read_csv_rows(
    path: Path,
    text_column: str,
    limit: int | None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            rows.append(
                {
                    "comment_id": row.get("comment_id", str(index)),
                    "post_id": row.get("post_id", ""),
                    "score": row.get("score", ""),
                    "text": row.get(text_column, ""),
                    "creation_date": row.get("creation_date", ""),
                    "source_label": row.get("source_label", ""),
                }
            )
            if limit is not None and len(rows) >= limit:
                break
    return rows


def _read_sql_rows(path: Path, limit: int | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for statement in iter_sql_statements(handle):
            row = parse_comment_insert(statement)
            if row is None:
                continue
            rows.append(row)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def _write_predictions_csv(path: Path, predictions: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "comment_id",
        "post_id",
        "score",
        "creation_date",
        "text",
        "source_label",
        "prediction",
        "positive_probability",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(predictions)


if __name__ == "__main__":
    main()
