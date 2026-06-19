"""Update Comments.hl_IndicatedDeprecation directly from Ollama-labeled CSV rows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_db import (
    apply_ollama_labels_to_db,
    connect_comment_db,
    load_env_file,
)


def main() -> None:
    load_env_file(ROOT / "src" / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--labels-csv", required=True)
    parser.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "6767")))
    parser.add_argument("--user", default=os.environ.get("MYSQL_USER", "dsait4055dbuser"))
    parser.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD", ""))
    parser.add_argument("--database", default=os.environ.get("MYSQL_DB", "dsait4055db"))
    parser.add_argument("--positive-label", default="temporal_obsolescence")
    parser.add_argument(
        "--include-question-comments",
        action="store_true",
        help="Do not restrict updates to comments on answers only.",
    )
    parser.add_argument(
        "--only-fill-null",
        action="store_true",
        help="Leave existing hl_IndicatedDeprecation values untouched.",
    )
    parser.add_argument(
        "--do-not-zero-unmatched",
        action="store_true",
        help="Update only comment_ids present in the labels CSV.",
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
        summary = apply_ollama_labels_to_db(
            connection=connection,
            labels_csv_path=args.labels_csv,
            positive_label=args.positive_label,
            answer_comments_only=not args.include_question_comments,
            set_unmatched_zero=not args.do_not_zero_unmatched,
            overwrite_existing=not args.only_fill_null,
        )
    finally:
        connection.close()

    print("Database comment label update complete")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
