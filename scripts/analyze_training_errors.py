"""Analyze false positives and false negatives for the baseline detector."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.error_analysis import collect_cross_validation_errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-csv",
        default="data/subsets/weak_label_subset/training_labels.csv",
    )
    parser.add_argument("--label-column", default="final_label")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--show", type=int, default=5)
    args = parser.parse_args()

    dataset = pd.read_csv(args.input_csv)
    results = collect_cross_validation_errors(
        dataset=dataset,
        label_column=args.label_column,
        num_folds=args.folds,
    )

    false_positives = results["false_positives"]
    false_negatives = results["false_negatives"]

    print("Error analysis complete")
    print(f"False positives: {len(false_positives)}")
    print(f"False negatives: {len(false_negatives)}")
    print()

    print("Sample false positives")
    for row in false_positives[: args.show]:
        _print_error_row(row)

    print("Sample false negatives")
    for row in false_negatives[: args.show]:
        _print_error_row(row)


def _print_error_row(row: dict[str, object]) -> None:
    preview = str(row.get("answer_body", "")).replace("\n", " ").strip()
    preview = preview[:220]
    print(
        f"fold={row.get('fold')} "
        f"question_id={row.get('question_id')} "
        f"answer_id={row.get('answer_id')} "
        f"actual={row.get('actual_label')} "
        f"predicted={row.get('predicted_label')} "
        f"score={row.get('predicted_positive_score')} "
        f"weak={row.get('weak_label')} "
        f"ollama={row.get('ollama_label')} "
        f"reason={row.get('ollama_reason')}"
    )
    print(f"title={row.get('question_title', '')}")
    print(f"answer_preview={preview}")
    print()


if __name__ == "__main__":
    main()
