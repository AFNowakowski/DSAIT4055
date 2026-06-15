"""Train and save the local comment-obsolescence classifier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_classifier import train_comment_classifier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--annotations",
        default="data/processed/comment_nlp/annotation_sample.csv",
    )
    parser.add_argument(
        "--model-output",
        default="data/processed/comment_nlp/comment_classifier.joblib",
    )
    parser.add_argument(
        "--metadata-output",
        default="data/processed/comment_nlp/comment_classifier_metadata.json",
    )
    args = parser.parse_args()

    annotations = pd.read_csv(args.annotations, keep_default_na=False)
    try:
        metadata = train_comment_classifier(
            annotations=annotations,
            model_path=args.model_output,
            metadata_path=args.metadata_output,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print("Comment classifier trained")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
