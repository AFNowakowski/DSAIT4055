"""Evaluate merged training labels with cross-validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.cross_validation import evaluate_with_cross_validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-csv",
        default="data/subsets/weak_label_subset/training_labels.csv",
    )
    parser.add_argument("--label-column", default="final_label")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    dataset = pd.read_csv(args.input_csv)
    results = evaluate_with_cross_validation(
        dataset=dataset,
        label_column=args.label_column,
        num_folds=args.folds,
    )

    print("Cross-validation complete")
    print(f"Folds: {results['num_folds']}")
    print(f"Mean accuracy: {results['mean_accuracy']:.3f}")
    print(f"Mean precision: {results['mean_precision']:.3f}")
    print(f"Mean recall: {results['mean_recall']:.3f}")
    print(f"Mean F1: {results['mean_f1']:.3f}")
    print()

    for row in results["fold_results"]:
        print(
            f"Fold {row['fold']}: "
            f"train={row['train_rows']} "
            f"test={row['test_rows']} "
            f"accuracy={row['accuracy']:.3f} "
            f"precision={row['precision']:.3f} "
            f"recall={row['recall']:.3f} "
            f"f1={row['f1']:.3f} "
            f"tp={row['tp']} tn={row['tn']} fp={row['fp']} fn={row['fn']}"
        )


if __name__ == "__main__":
    main()
