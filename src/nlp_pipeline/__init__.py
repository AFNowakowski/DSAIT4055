"""Starter package for the NLP answer deprecation pipeline."""

from .ollama_labeling import label_answers_with_ollama

try:
    from .cross_validation import evaluate_with_cross_validation
    from .detector import AnswerDeprecationDetector
    from .error_analysis import collect_cross_validation_errors
    from .evaluation import train_test_baseline_detector
    from .merge_labels import merge_training_labels
except ModuleNotFoundError:  # pragma: no cover - optional dependency during scaffold stage
    evaluate_with_cross_validation = None
    AnswerDeprecationDetector = None
    collect_cross_validation_errors = None
    train_test_baseline_detector = None
    merge_training_labels = None

try:
    from .survival import build_survival_table, estimate_half_life
except ModuleNotFoundError:  # pragma: no cover - optional dependency during scaffold stage
    build_survival_table = None
    estimate_half_life = None

__all__ = [
    "AnswerDeprecationDetector",
    "evaluate_with_cross_validation",
    "collect_cross_validation_errors",
    "train_test_baseline_detector",
    "merge_training_labels",
    "label_answers_with_ollama",
    "build_survival_table",
    "estimate_half_life",
]
