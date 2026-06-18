"""Prepare a manual annotation sample from unclassified database comments."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_database import iter_unclassified_comment_batches
from nlp_pipeline.comment_nlp import build_annotation_files_from_rows


def main() -> None:
    _load_env_file(ROOT / "src" / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "6767")))
    parser.add_argument("--user", default=os.environ.get("MYSQL_USER", "dsait4055dbuser"))
    parser.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD", ""))
    parser.add_argument("--database", default=os.environ.get("MYSQL_DB", "dsait4055db"))
    parser.add_argument("--output-dir", default="data/processed/comment_nlp")
    parser.add_argument("--sample-size", type=int, default=800)
    parser.add_argument("--seed", type=int, default=4055)
    parser.add_argument("--batch-size", type=int, default=5000)
    args = parser.parse_args()

    connection = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        rows = (
            row
            for batch in iter_unclassified_comment_batches(
                connection,
                batch_size=args.batch_size,
            )
            for row in batch
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


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


if __name__ == "__main__":
    main()
