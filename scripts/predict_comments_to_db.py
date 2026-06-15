"""Predict unlabeled database comments and optionally persist the outcomes."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_classifier import load_comment_classifier
from nlp_pipeline.comment_database import (
    apply_comment_predictions,
    iter_unclassified_comment_batches,
    predict_comment_batch,
)


def main() -> None:
    _load_env_file(ROOT / "src" / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default="data/processed/comment_nlp/comment_classifier.joblib",
    )
    parser.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "6767")))
    parser.add_argument("--user", default=os.environ.get("MYSQL_USER", "dsait4055dbuser"))
    parser.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD", ""))
    parser.add_argument("--database", default=os.environ.get("MYSQL_DB", "dsait4055db"))
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Optional path to write per-comment predictions for inspection.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist predictions. Without this flag the command is a dry run.",
    )
    args = parser.parse_args()

    model = load_comment_classifier(args.model)
    connection = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )

    processed = 0
    predicted_positive = 0
    updated = 0
    probability_sum = 0.0
    collected_predictions: list[dict[str, object]] = []
    try:
        for rows in iter_unclassified_comment_batches(
            connection,
            batch_size=args.batch_size,
            limit=args.limit,
        ):
            predictions = predict_comment_batch(
                model=model,
                rows=rows,
                threshold=args.threshold,
            )
            processed += len(predictions)
            predicted_positive += sum(row["prediction"] for row in predictions)
            probability_sum += sum(
                row["positive_probability"] for row in predictions
            )
            if args.output_csv:
                collected_predictions.extend(predictions)
            if args.apply:
                updated += apply_comment_predictions(connection, predictions)
    finally:
        connection.close()

    if args.output_csv:
        _write_predictions_csv(args.output_csv, collected_predictions)

    summary = {
        "mode": "apply" if args.apply else "dry_run",
        "processed": processed,
        "predicted_positive": predicted_positive,
        "predicted_negative": processed - predicted_positive,
        "mean_positive_probability": (
            probability_sum / processed if processed else None
        ),
        "updated_rows": updated,
        "threshold": args.threshold,
        "output_csv": args.output_csv,
    }
    print(json.dumps(summary, indent=2))


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _write_predictions_csv(path: str | Path, predictions: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(predictions)


if __name__ == "__main__":
    main()
