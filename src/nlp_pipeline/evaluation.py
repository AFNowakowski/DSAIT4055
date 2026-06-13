"""Baseline training and evaluation helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .detector import AnswerDeprecationDetector


def _train_test_split(
    dataset: pd.DataFrame,
    test_size: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    positive = dataset[dataset["is_deprecated"] == 1]
    negative = dataset[dataset["is_deprecated"] == 0]

    positive_test = max(1, round(len(positive) * test_size))
    negative_test = max(1, round(len(negative) * test_size))

    test = pd.concat(
        [
            positive.iloc[:positive_test],
            negative.iloc[:negative_test],
        ],
        ignore_index=True,
    )
    train = pd.concat(
        [
            positive.iloc[positive_test:],
            negative.iloc[negative_test:],
        ],
        ignore_index=True,
    )

    if train.empty or test.empty:
        raise ValueError("Dataset split failed. Add more labeled examples.")

    return train, test


def _classification_report(y_true: list[int], y_pred: list[int]) -> tuple[float, str]:
    tp = sum(1 for actual, pred in zip(y_true, y_pred) if actual == 1 and pred == 1)
    tn = sum(1 for actual, pred in zip(y_true, y_pred) if actual == 0 and pred == 0)
    fp = sum(1 for actual, pred in zip(y_true, y_pred) if actual == 0 and pred == 1)
    fn = sum(1 for actual, pred in zip(y_true, y_pred) if actual == 1 and pred == 0)

    accuracy = (tp + tn) / max(len(y_true), 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)

    report = (
        f"accuracy: {accuracy:.3f}\n"
        f"precision: {precision:.3f}\n"
        f"recall: {recall:.3f}\n"
        f"f1: {f1:.3f}\n"
        f"tp={tp}, tn={tn}, fp={fp}, fn={fn}"
    )
    return f1, report


def train_test_baseline_detector(
    dataset: pd.DataFrame,
    label_column: str = "is_deprecated",
    test_size: float = 0.4,
    random_state: int = 42,
) -> dict[str, Any]:
    """
    Train and evaluate the baseline NLP detector on a labeled dataset.

    Expected columns:
    - `answer_body`
    - label column, default `is_deprecated`
    """
    required_columns = {"answer_body", label_column}
    missing = required_columns.difference(dataset.columns)
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"Dataset is missing required columns: {missing_str}")

    shuffled = dataset.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    train_df, test_df = _train_test_split(shuffled, test_size=test_size)

    X_train = train_df[["answer_body"]].copy()
    y_train = train_df[label_column].astype(int).copy()
    X_test = test_df[["answer_body"]].copy()
    y_test = test_df[label_column].astype(int).tolist()

    detector = AnswerDeprecationDetector()
    detector.fit(X_train, y_train)

    predictions = detector.predict(X_test)
    accuracy = detector.score(X_test, pd.Series(y_test))
    f1, report = _classification_report(y_test, predictions)

    return {
        "model": detector,
        "accuracy": accuracy,
        "f1": f1,
        "report": report,
        "test_rows": len(X_test),
        "train_rows": len(X_train),
    }
