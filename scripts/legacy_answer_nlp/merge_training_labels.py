"""Merge heuristic and Ollama labels into one training dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.legacy_answer.merge_labels import merge_training_labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weak-labels",
        default="data/subsets/weak_label_subset/weak_labeled_answers.csv",
    )
    parser.add_argument(
        "--ollama-labels",
        default="data/subsets/weak_label_subset/ollama_labels.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="data/subsets/weak_label_subset/training_labels.csv",
    )
    args = parser.parse_args()

    results = merge_training_labels(
        weak_labels_csv_path=args.weak_labels,
        ollama_labels_csv_path=args.ollama_labels,
        output_csv_path=args.output_csv,
    )

    print("Training label merge complete")
    print(f"Output CSV: {results['output_csv']}")
    print(f"Merged rows: {results['merged_rows']}")
    print(f"Ollama overrides: {results['ollama_override_count']}")
    print(f"Heuristic fallbacks: {results['heuristic_fallback_count']}")


if __name__ == "__main__":
    main()
