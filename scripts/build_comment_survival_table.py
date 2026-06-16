"""Build the comment-obsolescence survival table and compare ephemeral vs. stable buckets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
import pymysql

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_survival import (
    assign_tech_bucket,
    build_comment_survival_table,
    compare_bucket_survival,
    fetch_comment_obsolescence_labels,
    summarize_event_rate,
)


def main() -> None:
    _load_env_file(ROOT / "src" / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "6767")))
    parser.add_argument("--user", default=os.environ.get("MYSQL_USER", "dsait4055dbuser"))
    parser.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD", ""))
    parser.add_argument("--database", default=os.environ.get("MYSQL_DB", "dsait4055db"))
    parser.add_argument(
        "--observation-end",
        default=None,
        help="ISO timestamp marking the end of the observation window. Defaults to now (UTC).",
    )
    parser.add_argument(
        "--output-csv",
        default="data/processed/comment_nlp/comment_survival_table.csv",
    )
    args = parser.parse_args()

    observation_end = (
        pd.Timestamp(args.observation_end, tz="UTC")
        if args.observation_end
        else pd.Timestamp.now(tz="UTC")
    )

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
        labeled = fetch_comment_obsolescence_labels(connection)
    finally:
        connection.close()

    if labeled.empty:
        print("No accepted answers found.")
        return

    labeled = assign_tech_bucket(labeled)

    event_summary = summarize_event_rate(labeled)
    print("Event rate sanity check (run this before trusting the comparison below):")
    print(json.dumps(event_summary, indent=2, default=str))

    bucketed = labeled.dropna(subset=["tech_bucket"])
    if bucketed.empty:
        print("No accepted answers fall into the ephemeral/stable tag buckets; skipping comparison.")
        return

    survival_df = build_comment_survival_table(bucketed, observation_end)

    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    survival_df.to_csv(output_path, index=False)
    print(f"Survival table written to {output_path}")

    comparison = compare_bucket_survival(survival_df)
    print("Bucket comparison:")
    print(
        json.dumps(
            {k: v for k, v in comparison.items() if not k.endswith("_kmf")},
            indent=2,
        )
    )


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
