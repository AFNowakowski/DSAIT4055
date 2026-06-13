"""Simple baseline detector scaffold."""

from __future__ import annotations

import math
from collections import Counter

import pandas as pd

from .preprocessing import normalize_text


class AnswerDeprecationDetector:
    """A lightweight baseline classifier for likely answer deprecation."""

    def __init__(self) -> None:
        self.vocabulary_: dict[str, float] = {}
        self.bias_: float = 0.0
        self.fitted_: bool = False

    def _tokenize(self, text: str) -> list[str]:
        return normalize_text(text).split()

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "AnswerDeprecationDetector":
        positive_counts: Counter[str] = Counter()
        negative_counts: Counter[str] = Counter()

        for answer_body, label in zip(X["answer_body"].fillna(""), y):
            tokens = self._tokenize(answer_body)
            if int(label) == 1:
                positive_counts.update(tokens)
            else:
                negative_counts.update(tokens)

        vocabulary = set(positive_counts) | set(negative_counts)
        total_positive = sum(positive_counts.values())
        total_negative = sum(negative_counts.values())
        vocab_size = max(len(vocabulary), 1)

        self.vocabulary_ = {}
        for token in vocabulary:
            pos = positive_counts[token] + 1
            neg = negative_counts[token] + 1
            pos_prob = pos / (total_positive + vocab_size)
            neg_prob = neg / (total_negative + vocab_size)
            self.vocabulary_[token] = math.log(pos_prob / neg_prob)

        positive_docs = int((y == 1).sum())
        negative_docs = int((y == 0).sum())
        self.bias_ = math.log((positive_docs + 1) / (negative_docs + 1))
        self.fitted_ = True
        return self

    def _raw_score(self, text: str) -> float:
        score = self.bias_
        for token in self._tokenize(text):
            score += self.vocabulary_.get(token, 0.0)
        return score

    def predict_proba(self, X: pd.DataFrame) -> list[list[float]]:
        if not self.fitted_:
            raise ValueError("Detector must be fitted before prediction.")

        probabilities: list[list[float]] = []
        for text in X["answer_body"].fillna(""):
            raw = self._raw_score(text)
            positive = 1.0 / (1.0 + math.exp(-raw))
            probabilities.append([1.0 - positive, positive])
        return probabilities

    def predict(self, X: pd.DataFrame) -> list[int]:
        return [1 if row[1] >= 0.5 else 0 for row in self.predict_proba(X)]

    def score(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Return the mean accuracy on the given evaluation set."""
        predictions = self.predict(X)
        correct = sum(int(pred == actual) for pred, actual in zip(predictions, y))
        return correct / max(len(predictions), 1)
