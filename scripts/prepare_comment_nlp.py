"""Prepare Comments.sql for local NLP and manual annotation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_nlp import prepare_comment_nlp_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-sql", default="Comments.sql")
    parser.add_argument("--output-dir", default="data/processed/comment_nlp")
    parser.add_argument("--sample-size", type=int, default=800)
    parser.add_argument("--seed", type=int, default=4055)
    parser.add_argument(
        "--skip-all-comments",
        action="store_true",
        help="Do not write the large comments.csv file.",
    )
    args = parser.parse_args()

    summary = prepare_comment_nlp_dataset(
        sql_path=args.input_sql,
        output_dir=args.output_dir,
        annotation_sample_size=args.sample_size,
        random_seed=args.seed,
        write_all_comments=not args.skip_all_comments,
    )

    print("Comment NLP preparation complete")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
