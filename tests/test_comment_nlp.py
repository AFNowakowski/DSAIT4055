"""Tests for SQL comment parsing and review candidate selection."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.comment_nlp import (
    classify_comment_candidate,
    iter_sql_statements,
    parse_comment_insert,
)


class CommentSqlParsingTests(unittest.TestCase):
    def test_parses_multiline_and_escaped_comment_text(self) -> None:
        sql = (
            "INSERT INTO dsait4055db.Comments "
            "(Id, PostId, Score, Text, CreationDate, UserDisplayName, UserId, "
            "hl_IndicatedDeprecation) VALUES "
            "(1, 2, 3, 'It doesn\\'t work,\\nnow.', "
            "'2026-01-01 00:00:00', null, 4, null);"
        )

        statements = list(iter_sql_statements(io.StringIO(sql)))
        row = parse_comment_insert(statements[0])

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["comment_id"], "1")
        self.assertEqual(row["post_id"], "2")
        self.assertEqual(row["text"], "It doesn't work,\nnow.")
        self.assertEqual(row["source_label"], "")

    def test_statement_split_ignores_semicolon_inside_text(self) -> None:
        sql = (
            "INSERT INTO dsait4055db.Comments (x) VALUES "
            "(1, 2, 0, 'first; comment', '2026-01-01', null, null, null);"
            "INSERT INTO dsait4055db.Comments (x) VALUES "
            "(2, 3, 0, 'second', '2026-01-02', null, null, null);"
        )

        statements = list(iter_sql_statements(io.StringIO(sql)))

        self.assertEqual(len(statements), 2)


class CommentCandidateTests(unittest.TestCase):
    def test_temporal_change_is_selected(self) -> None:
        category, reason = classify_comment_candidate(
            "This API was removed in version 4; use the replacement."
        )

        self.assertEqual(category, "temporal_candidate")
        self.assertIn(reason, {"removed_api", "version_replacement"})

    def test_not_deprecated_takes_precedence(self) -> None:
        category, reason = classify_comment_candidate(
            "This function is not deprecated and is still supported."
        )

        self.assertEqual(category, "freshness_confirmation")
        self.assertEqual(reason, "not_deprecated")

    def test_deprecated_can_outrank_still_valid(self) -> None:
        category, reason = classify_comment_candidate(
            'This is an old and deprecated way to do a cross join. It is still valid syntax, but not best practice.'
        )

        self.assertEqual(category, "temporal_candidate")
        self.assertIn(reason, {"explicit_deprecated", "deprecated_in_favor_of", "old_way_or_syntax"})

    def test_deprecated_in_favor_of_is_temporal(self) -> None:
        category, reason = classify_comment_candidate(
            "parallelshell has been deprecated in favor of npm-run-all"
        )

        self.assertEqual(category, "temporal_candidate")
        self.assertIn(reason, {"explicit_deprecated", "deprecated_in_favor_of"})

    def test_version_cutoff_is_temporal(self) -> None:
        category, reason = classify_comment_candidate(
            "iif would never work in sql 2008, its sql 2012 and later"
        )

        self.assertEqual(category, "temporal_candidate")
        self.assertEqual(reason, "version_cutoff")

    def test_old_project_current_version_risk_is_temporal(self) -> None:
        category, reason = classify_comment_candidate(
            "Do note that this is a very old project by now, and the odds that it still works with your preferred version of Node are almost zero."
        )

        self.assertEqual(category, "temporal_candidate")
        self.assertEqual(reason, "old_project_current_version_risk")

    def test_version_mismatch_is_temporal(self) -> None:
        category, reason = classify_comment_candidate(
            "annotorious still works with AngularJs (v1.x) in their respective versions, but for Angular (v11) this library is not matching and a new one has to be created."
        )

        self.assertEqual(category, "temporal_candidate")
        self.assertEqual(reason, "version_mismatch")

    def test_generic_failure_is_not_temporal_ground_truth(self) -> None:
        category, reason = classify_comment_candidate(
            "This doesn't work on my server."
        )

        self.assertEqual(category, "failure_candidate")
        self.assertEqual(reason, "does_not_work")


if __name__ == "__main__":
    unittest.main()
