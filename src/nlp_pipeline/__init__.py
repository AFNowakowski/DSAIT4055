"""Starter package for the NLP answer deprecation pipeline."""

from .detector import AnswerDeprecationDetector
from .evaluation import train_test_baseline_detector
from .ollama_labeling import label_answers_with_ollama

try:
    from .survival import build_survival_table, estimate_half_life
except ModuleNotFoundError:  # pragma: no cover - optional dependency during scaffold stage
    build_survival_table = None
    estimate_half_life = None

__all__ = [
    "AnswerDeprecationDetector",
    "train_test_baseline_detector",
    "label_answers_with_ollama",
    "build_survival_table",
    "estimate_half_life",
]
