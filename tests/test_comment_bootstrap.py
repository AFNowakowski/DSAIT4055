"""Tests for weak-supervision bootstrap labels."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_bootstrap import weak_supervision_label


class WeakSupervisionTests(unittest.TestCase):
    def test_versioned_deprecation_is_positive(self) -> None:
        label, reason, weight = weak_supervision_label(
            "This API is deprecated in version 4. Use the new endpoint."
        )

        self.assertEqual(label, 1)
        self.assertNotEqual(reason, "abstain")
        self.assertEqual(weight, 1.0)

    def test_freshness_negation_is_negative(self) -> None:
        label, reason, _ = weak_supervision_label(
            "This function is not deprecated and is still supported."
        )

        self.assertEqual(label, 0)
        self.assertEqual(reason, "explicit_freshness")

    def test_generic_failure_abstains(self) -> None:
        label, reason, weight = weak_supervision_label(
            "This does not work on my server."
        )

        self.assertIsNone(label)
        self.assertEqual(reason, "abstain")
        self.assertEqual(weight, 0.0)

    def test_dead_link_is_not_answer_obsolescence(self) -> None:
        label, reason, _ = weak_supervision_label(
            "The link no longer works and returns 404."
        )

        self.assertEqual(label, 0)
        self.assertEqual(reason, "external_resource_unavailable")


if __name__ == "__main__":
    unittest.main()
