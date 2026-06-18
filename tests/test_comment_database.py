"""Tests for database prediction helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_database import predict_comment_batch


class FakeModel:
    def predict_proba(self, texts: list[str]) -> list[list[float]]:
        return [
            [0.2, 0.8] if "deprecated" in text else [0.9, 0.1]
            for text in texts
        ]


class CommentDatabasePredictionTests(unittest.TestCase):
    def test_threshold_creates_binary_database_values(self) -> None:
        rows = [
            {"comment_id": 1, "post_id": 10, "text": "This is deprecated."},
            {"comment_id": 2, "post_id": 10, "text": "Thanks, this works."},
        ]

        predictions = predict_comment_batch(FakeModel(), rows, threshold=0.7)

        self.assertEqual([row["prediction"] for row in predictions], [1, 0])
        self.assertEqual(predictions[0]["positive_probability"], 0.8)

    def test_rejects_invalid_threshold(self) -> None:
        with self.assertRaises(ValueError):
            predict_comment_batch(FakeModel(), [], threshold=1.1)


if __name__ == "__main__":
    unittest.main()
