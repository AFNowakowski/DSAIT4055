"""Cross-validation helpers for the baseline detector."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .detector import AnswerDeprecationDetector


def evaluate_with_cross_validation(
    dataset: pd.DataFrame,
    label_column: str = "final_label",
    num_folds: int = 5,
) -> dict[str, Any]:
    """
    Evaluate the baseline detector with simple stratified cross-validation.

    Expected columns:
    - `answer_body`
    - label column, default `final_label`
    """
    required_columns = {"answer_body", label_column}
    missing = required_columns.difference(dataset.columns)
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"Dataset is missing required columns: {missing_str}")

    df = dataset.copy()
    df[label_column] = df[label_column].astype(int)

    positive = df[df[label_column] == 1].reset_index(drop=True)
    negative = df[df[label_column] == 0].reset_index(drop=True)

    if positive.empty or negative.empty:
        raise ValueError("Cross-validation requires both positive and negative labels.")

    max_folds = min(len(positive), len(negative), num_folds)
    if max_folds < 2:
        raise ValueError("Not enough labeled examples for at least 2 folds.")

    positive_folds = _split_into_folds(positive, max_folds)
    negative_folds = _split_into_folds(negative, max_folds)

    fold_results: list[dict[str, float | int]] = []
    for fold_index in range(max_folds):
        test_df = pd.concat(
            [positive_folds[fold_index], negative_folds[fold_index]],
            ignore_index=True,
        )
        train_df = pd.concat(
            [
                fold
                for index, fold in enumerate(positive_folds)
                if index != fold_index
            ]
            + [
                fold
                for index, fold in enumerate(negative_folds)
                if index != fold_index
            ],
            ignore_index=True,
        )

        X_train = train_df[["answer_body"]].copy()
        y_train = train_df[label_column].copy()
        X_test = test_df[["answer_body"]].copy()
        y_test = test_df[label_column].tolist()

        detector = AnswerDeprecationDetector()
        detector.fit(X_train, y_train)

        predictions = detector.predict(X_test)
        accuracy, precision, recall, f1, tp, tn, fp, fn = _metrics(y_test, predictions)
        fold_results.append(
            {
                "fold": fold_index + 1,
                "train_rows": len(train_df),
                "test_rows": len(test_df),
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": tp,
                "tn": tn,
                "fp": fp,
                "fn": fn,
            }
        )

    return {
        "num_folds": max_folds,
        "mean_accuracy": _mean([row["accuracy"] for row in fold_results]),
        "mean_precision": _mean([row["precision"] for row in fold_results]),
        "mean_recall": _mean([row["recall"] for row in fold_results]),
        "mean_f1": _mean([row["f1"] for row in fold_results]),
        "fold_results": fold_results,
    }


def _split_into_folds(df: pd.DataFrame, num_folds: int) -> list[pd.DataFrame]:
    folds: list[list[dict[str, Any]]] = [[] for _ in range(num_folds)]
    records = df.to_dict(orient="records")
    for index, record in enumerate(records):
        folds[index % num_folds].append(record)
    return [pd.DataFrame(fold) for fold in folds]


def _metrics(
    y_true: list[int],
    y_pred: list[int],
) -> tuple[float, float, float, float, int, int, int, int]:
    tp = sum(1 for actual, pred in zip(y_true, y_pred) if actual == 1 and pred == 1)
    tn = sum(1 for actual, pred in zip(y_true, y_pred) if actual == 0 and pred == 0)
    fp = sum(1 for actual, pred in zip(y_true, y_pred) if actual == 0 and pred == 1)
    fn = sum(1 for actual, pred in zip(y_true, y_pred) if actual == 1 and pred == 0)

    accuracy = (tp + tn) / max(len(y_true), 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)

    return accuracy, precision, recall, f1, tp, tn, fp, fn


def _mean(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)
