"""Annotate weak-label subset rows with a local Ollama model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.legacy_answer.ollama_labeling import label_answers_with_ollama


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-csv",
        default="data/subsets/weak_label_subset/weak_labeled_answers.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="data/subsets/weak_label_subset/ollama_labels.csv",
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--include-accepted", action="store_true")
    parser.add_argument("--ollama-exe", default=None)
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    results = label_answers_with_ollama(
        input_csv_path=args.input_csv,
        output_csv_path=args.output_csv,
        model=args.model,
        limit=args.limit if args.limit > 0 else None,
        only_unaccepted=not args.include_accepted,
        ollama_executable=args.ollama_exe,
        ollama_host=args.ollama_host,
        verbose=args.verbose,
    )

    print("Ollama labeling complete")
    print(f"Output CSV: {results['output_csv']}")
    print(f"Labeled rows: {results['labeled_rows']}")
    print(f"Existing rows reused: {results['existing_rows']}")
    print(f"New rows labeled: {results['new_rows_labeled']}")


if __name__ == "__main__":
    main()
