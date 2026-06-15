"""Evaluate manually labeled comments with a local TF-IDF baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_classifier import evaluate_comment_annotations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--annotations",
        default="data/processed/comment_nlp/annotation_sample.csv",
    )
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    annotations = pd.read_csv(args.annotations, keep_default_na=False)
    try:
        results = evaluate_comment_annotations(annotations, folds=args.folds)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
