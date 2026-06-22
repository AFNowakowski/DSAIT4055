"""Annotate comment review rows with a local Ollama model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_ollama_labeling import label_comment_annotations_with_ollama


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-csv",
        default="data/processed/comment_nlp/annotation_sample.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="data/processed/comment_nlp/annotation_sample_ollama.csv",
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--include-human-labeled",
        action="store_true",
        help="Also send rows that already have a human_label.",
    )
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    results = label_comment_annotations_with_ollama(
        input_csv_path=args.input_csv,
        output_csv_path=args.output_csv,
        model=args.model,
        limit=args.limit if args.limit > 0 else None,
        only_unlabeled=not args.include_human_labeled,
        ollama_host=args.ollama_host,
        verbose=args.verbose,
    )

    print("Comment Ollama labeling complete")
    print(f"Output CSV: {results['output_csv']}")
    print(f"Labeled rows: {results['labeled_rows']}")
    print(f"Existing rows reused: {results['existing_rows']}")
    print(f"New rows labeled: {results['new_rows_labeled']}")


if __name__ == "__main__":
    main()
