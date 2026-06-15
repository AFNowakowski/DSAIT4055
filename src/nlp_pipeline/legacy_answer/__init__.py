"""Legacy answer-level NLP workflow modules."""

from .cross_validation import evaluate_with_cross_validation
from .detector import AnswerDeprecationDetector
from .error_analysis import collect_cross_validation_errors
from .evaluation import train_test_baseline_detector
from .merge_labels import merge_training_labels
from .ollama_labeling import label_answers_with_ollama
from .survival import build_survival_table, estimate_half_life

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
