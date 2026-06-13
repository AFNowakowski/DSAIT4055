"""Run a synthetic baseline NLP demo."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.demo_data import make_demo_detector_dataset
from nlp_pipeline.evaluation import train_test_baseline_detector


def main() -> None:
    dataset = make_demo_detector_dataset()
    results = train_test_baseline_detector(dataset)

    print("Baseline NLP demo")
    print(f"Train rows: {results['train_rows']}")
    print(f"Test rows: {results['test_rows']}")
    print(f"Accuracy: {results['accuracy']:.3f}")
    print(f"F1 score: {results['f1']:.3f}")
    print()
    print(results["report"])


if __name__ == "__main__":
    main()
