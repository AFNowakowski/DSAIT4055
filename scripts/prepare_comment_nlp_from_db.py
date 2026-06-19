"""Prepare comment candidate files directly from the MySQL database."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_db import connect_comment_db, iter_comment_rows, load_env_file
from nlp_pipeline.comment_nlp import build_annotation_files_from_rows


def main() -> None:
    load_env_file(ROOT / "src" / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "6767")))
    parser.add_argument("--user", default=os.environ.get("MYSQL_USER", "dsait4055dbuser"))
    parser.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD", ""))
    parser.add_argument("--database", default=os.environ.get("MYSQL_DB", "dsait4055db"))
    parser.add_argument("--output-dir", default="data/processed/comment_nlp_db")
    parser.add_argument("--sample-size", type=int, default=800)
    parser.add_argument("--seed", type=int, default=4055)
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument(
        "--include-already-labeled",
        action="store_true",
        help="Also include rows where hl_IndicatedDeprecation is already set.",
    )
    parser.add_argument(
        "--include-question-comments",
        action="store_true",
        help="Do not restrict the export to comments on answers only.",
    )
    args = parser.parse_args()

    connection = connect_comment_db(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
    )
    try:
        rows = iter_comment_rows(
            connection=connection,
            batch_size=args.batch_size,
            only_unclassified=not args.include_already_labeled,
            answer_comments_only=not args.include_question_comments,
        )
        summary = build_annotation_files_from_rows(
            rows=rows,
            output_dir=args.output_dir,
            annotation_sample_size=args.sample_size,
            random_seed=args.seed,
        )
    finally:
        connection.close()

    print("Database comment NLP preparation complete")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
