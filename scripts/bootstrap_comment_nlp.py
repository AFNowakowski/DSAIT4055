"""Train and run a provisional comment ranker without human labels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_bootstrap import (
    bootstrap_comment_model,
    score_comments_with_bootstrap,
)
from nlp_pipeline.comment_nlp import iter_sql_statements, parse_comment_insert


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-sql", default="Comments.sql")
    parser.add_argument("--output-dir", default="data/processed/comment_nlp")
    parser.add_argument("--random-background-size", type=int, default=5000)
    parser.add_argument("--random-background-weight", type=float, default=0.2)
    parser.add_argument("--review-per-group", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=4055)
    args = parser.parse_args()

    training = bootstrap_comment_model(
        rows=_iter_sql_rows(Path(args.input_sql)),
        output_dir=args.output_dir,
        random_negative_size=args.random_background_size,
        random_negative_weight=args.random_background_weight,
        random_seed=args.seed,
    )
    scoring = score_comments_with_bootstrap(
        rows=_iter_sql_rows(Path(args.input_sql)),
        model_path=training["model_path"],
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        review_per_group=args.review_per_group,
    )
    print("Bootstrap comment NLP complete")
    print(json.dumps({"training": training, "scoring": scoring}, indent=2))


def _iter_sql_rows(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for statement in iter_sql_statements(handle):
            row = parse_comment_insert(statement)
            if row is not None:
                yield row


if __name__ == "__main__":
    main()
