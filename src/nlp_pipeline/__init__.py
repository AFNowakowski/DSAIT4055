"""NLP package with the active comment workflow and legacy answer workflow."""

from .comment_ollama_labeling import label_comment_annotations_with_ollama

try:
    from .legacy_answer import (
        AnswerDeprecationDetector,
        build_survival_table,
        collect_cross_validation_errors,
        estimate_half_life,
        evaluate_with_cross_validation,
        label_answers_with_ollama,
        merge_training_labels,
        train_test_baseline_detector,
    )
except ModuleNotFoundError:  # pragma: no cover - optional dependency during scaffold stage
    evaluate_with_cross_validation = None
    AnswerDeprecationDetector = None
    collect_cross_validation_errors = None
    train_test_baseline_detector = None
    merge_training_labels = None
    label_answers_with_ollama = None
    build_survival_table = None
    estimate_half_life = None

__all__ = [
    "AnswerDeprecationDetector",
    "evaluate_with_cross_validation",
    "collect_cross_validation_errors",
    "train_test_baseline_detector",
    "merge_training_labels",
    "label_answers_with_ollama",
    "label_comment_annotations_with_ollama",
    "build_survival_table",
    "estimate_half_life",
]
