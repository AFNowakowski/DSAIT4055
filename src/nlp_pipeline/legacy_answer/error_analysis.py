"""Error-analysis helpers for the baseline detector."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .detector import AnswerDeprecationDetector


def collect_cross_validation_errors(
    dataset: pd.DataFrame,
    label_column: str = "final_label",
    num_folds: int = 5,
) -> dict[str, Any]:
    """
    Collect false positives and false negatives across cross-validation folds.

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

    max_folds = min(len(positive), len(negative), num_folds)
    if max_folds < 2:
        raise ValueError("Not enough labeled examples for at least 2 folds.")

    positive_folds = _split_into_folds(positive, max_folds)
    negative_folds = _split_into_folds(negative, max_folds)

    false_positives: list[dict[str, Any]] = []
    false_negatives: list[dict[str, Any]] = []

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

        detector = AnswerDeprecationDetector()
        detector.fit(train_df[["answer_body"]].copy(), train_df[label_column].copy())

        predictions = detector.predict(test_df[["answer_body"]].copy())
        probabilities = detector.predict_proba(test_df[["answer_body"]].copy())

        for row, prediction, probability in zip(
            test_df.to_dict(orient="records"),
            predictions,
            probabilities,
        ):
            actual = int(row[label_column])
            predicted = int(prediction)
            positive_score = float(probability[1])

            error_row = {
                "fold": fold_index + 1,
                "question_id": row.get("question_id", ""),
                "answer_id": row.get("answer_id", ""),
                "actual_label": actual,
                "predicted_label": predicted,
                "predicted_positive_score": round(positive_score, 4),
                "weak_label": row.get("weak_label", ""),
                "ollama_label": row.get("ollama_label", ""),
                "ollama_reason": row.get("ollama_reason", ""),
                "question_title": row.get("question_title", ""),
                "answer_body": row.get("answer_body", ""),
            }

            if actual == 0 and predicted == 1:
                false_positives.append(error_row)
            elif actual == 1 and predicted == 0:
                false_negatives.append(error_row)

    return {
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def _split_into_folds(df: pd.DataFrame, num_folds: int) -> list[pd.DataFrame]:
    folds: list[list[dict[str, Any]]] = [[] for _ in range(num_folds)]
    records = df.to_dict(orient="records")
    for index, record in enumerate(records):
        folds[index % num_folds].append(record)
    return [pd.DataFrame(fold) for fold in folds]
