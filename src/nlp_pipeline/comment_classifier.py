"""Local TF-IDF baseline for manually labeled obsolescence comments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline


POSITIVE_LABELS = {"1", "temporal_obsolescence", "obsolete", "outdated"}
NEGATIVE_LABELS = {
    "0",
    "fresh",
    "freshness_confirmation",
    "incorrect",
    "incorrectness",
    "situational_failure",
    "neutral",
    "other",
}


def build_comment_classifier() -> Pipeline:
    """Build an interpretable word and character TF-IDF classifier."""
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.98,
                    sublinear_tf=True,
                ),
            ),
            (
                "character",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=2,
                    sublinear_tf=True,
                ),
            ),
        ]
    )
    return Pipeline(
        [
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=4055,
                ),
            ),
        ]
    )


def evaluate_comment_annotations(
    annotations: pd.DataFrame,
    folds: int = 5,
) -> dict[str, Any]:
    """Evaluate annotations while keeping comments on one post in one fold."""
    required = {"text", "post_id", "human_label"}
    missing = required.difference(annotations.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    dataset = prepare_labeled_comments(annotations)
    dataset = dataset.dropna(subset=["post_id"]).copy()

    class_counts = dataset["binary_label"].value_counts()
    if len(class_counts) < 2:
        raise ValueError("Annotations need both temporal-obsolescence and negative labels.")

    usable_folds = min(folds, int(class_counts.min()))
    if usable_folds < 2:
        raise ValueError("At least two examples in each class are required.")

    splitter = StratifiedGroupKFold(
        n_splits=usable_folds,
        shuffle=True,
        random_state=4055,
    )
    model = build_comment_classifier()
    predictions = cross_val_predict(
        model,
        dataset["text"],
        dataset["binary_label"],
        groups=dataset["post_id"],
        cv=splitter,
        method="predict",
    )

    report = classification_report(
        dataset["binary_label"],
        predictions,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(dataset["binary_label"], predictions).tolist()
    return {
        "labeled_rows": len(dataset),
        "positive_rows": int((dataset["binary_label"] == 1).sum()),
        "negative_rows": int((dataset["binary_label"] == 0).sum()),
        "folds": usable_folds,
        "confusion_matrix": matrix,
        "classification_report": report,
    }


def prepare_labeled_comments(annotations: pd.DataFrame) -> pd.DataFrame:
    """Return reviewed comments with normalized binary labels."""
    required = {"text", "human_label"}
    missing = required.difference(annotations.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    dataset = annotations.copy()
    dataset["binary_label"] = dataset["human_label"].map(normalize_human_label)
    dataset = dataset.dropna(subset=["binary_label", "text"]).copy()
    dataset["binary_label"] = dataset["binary_label"].astype(int)

    class_counts = dataset["binary_label"].value_counts()
    if len(class_counts) < 2:
        raise ValueError("Training requires both positive and negative reviewed labels.")
    return dataset


def train_comment_classifier(
    annotations: pd.DataFrame,
    model_path: str | Path,
    metadata_path: str | Path | None = None,
) -> dict[str, Any]:
    """Fit the local classifier and persist it with basic training metadata."""
    dataset = prepare_labeled_comments(annotations)
    model = build_comment_classifier()
    model.fit(dataset["text"], dataset["binary_label"])

    output_path = Path(model_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)

    metadata = {
        "model_path": str(output_path),
        "labeled_rows": len(dataset),
        "positive_rows": int((dataset["binary_label"] == 1).sum()),
        "negative_rows": int((dataset["binary_label"] == 0).sum()),
        "positive_definition": "comment indicates temporal answer obsolescence",
        "negative_definition": "all other reviewed comment categories",
    }
    if metadata_path is not None:
        metadata_output_path = Path(metadata_path)
        metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_output_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )
    return metadata


def load_comment_classifier(model_path: str | Path) -> Pipeline:
    """Load a persisted comment classifier."""
    model = joblib.load(model_path)
    if not hasattr(model, "predict_proba"):
        raise ValueError("Saved object is not a probabilistic comment classifier.")
    return model


def normalize_human_label(value: object) -> float | None:
    normalized = str(value).strip().lower()
    if normalized in POSITIVE_LABELS:
        return 1.0
    if normalized in NEGATIVE_LABELS:
        return 0.0
    return None
