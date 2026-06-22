"""Comment-based obsolescence labels and ephemeral-vs-stable survival comparison.

Onset of obsolescence for an accepted answer is defined as the earliest comment
on that answer (matched by Comments.PostId) with hl_IndicatedDeprecation = 1.
Answers with no such comment are right-censored. This is the only event
definition in scope; the legacy overtaking-based labels in
nlp_pipeline.legacy_answer are not used here.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test

from .legacy_answer.survival import build_survival_table

EPHEMERAL_TAGS = {"angular", "react-native", "angularjs", "webpack", "npm"}
STABLE_TAGS = {"c", "algorithm", "math", "regex", "dynamic-programming"}

# accepted_at = earliest VoteTypeId=1 (acceptance) vote per answer.
# event_at = earliest comment on that answer flagged as indicating obsolescence.
ACCEPTED_ANSWERS_SQL = """
SELECT
    a.Id AS answer_id,
    a.ParentId AS question_id,
    acc.accepted_at,
    ev.event_at,
    q.Tags AS question_tags
FROM Posts a
JOIN (
    SELECT PostId, MIN(CreationDate) AS accepted_at
    FROM Votes
    WHERE VoteTypeId = 1
    GROUP BY PostId
) acc ON acc.PostId = a.Id
JOIN Posts q ON q.Id = a.ParentId
LEFT JOIN (
    SELECT PostId, MIN(CreationDate) AS event_at
    FROM Comments
    WHERE hl_IndicatedDeprecation = 1
    GROUP BY PostId
) ev ON ev.PostId = a.Id
WHERE a.PostTypeId = 2
"""

_TAG_RE = re.compile(r"<([^>]+)>")


def _primary_tag(tags_field: str | None) -> str | None:
    """Return the first tag in a raw '<tag1><tag2>' Posts.Tags string."""
    if not tags_field:
        return None
    match = _TAG_RE.search(tags_field)
    return match.group(1) if match else None


def fetch_comment_obsolescence_labels(connection: Any) -> pd.DataFrame:
    """Build one row per accepted answer with its acceptance time, first flagged-comment
    onset (if any), and the parent question's primary tag."""
    with connection.cursor() as cursor:
        cursor.execute(ACCEPTED_ANSWERS_SQL)
        rows = cursor.fetchall()

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["primary_tag"] = df["question_tags"].apply(_primary_tag)
    df["event_observed"] = df["event_at"].notna().astype(int)
    return df.drop(columns=["question_tags"])


def assign_tech_bucket(labeled_answers: pd.DataFrame) -> pd.DataFrame:
    """Label each answer 'ephemeral' or 'stable' from its question's primary tag.
    Answers whose primary tag is in neither list get None and are excluded later."""

    def _bucket(tag: str | None) -> str | None:
        if tag in EPHEMERAL_TAGS:
            return "ephemeral"
        if tag in STABLE_TAGS:
            return "stable"
        return None

    df = labeled_answers.copy()
    df["tech_bucket"] = df["primary_tag"].apply(_bucket)
    return df


def summarize_event_rate(labeled_answers: pd.DataFrame) -> dict[str, Any]:
    """Report what fraction of accepted answers ever got a flagged comment, overall
    and per tech bucket if available. Run this before trusting the survival curves:
    if the event rate is very low, most of the curve is censoring, not signal."""
    total = len(labeled_answers)
    observed = int(labeled_answers["event_observed"].sum())
    summary: dict[str, Any] = {
        "total_accepted_answers": total,
        "event_observed": observed,
        "censored": total - observed,
        "event_rate": observed / total if total else None,
    }

    if "tech_bucket" in labeled_answers.columns:
        per_bucket: dict[str, Any] = {}
        bucketed = labeled_answers.dropna(subset=["tech_bucket"])
        for bucket, group in bucketed.groupby("tech_bucket"):
            bucket_total = len(group)
            bucket_observed = int(group["event_observed"].sum())
            per_bucket[bucket] = {
                "total_accepted_answers": bucket_total,
                "event_observed": bucket_observed,
                "censored": bucket_total - bucket_observed,
                "event_rate": bucket_observed / bucket_total if bucket_total else None,
            }
        summary["per_bucket"] = per_bucket

    return summary


def build_comment_survival_table(
    labeled_answers_with_bucket: pd.DataFrame,
    observation_end: str | pd.Timestamp,
) -> pd.DataFrame:
    """Add duration_days via the generic survival.build_survival_table, then
    reattach tech_bucket (which that generic function does not carry through)."""
    survival_df = build_survival_table(labeled_answers_with_bucket, observation_end)
    return survival_df.merge(
        labeled_answers_with_bucket[["answer_id", "tech_bucket"]],
        on="answer_id",
        how="left",
    )


def _half_life(kmf: KaplanMeierFitter) -> float | None:
    curve = kmf.survival_function_.reset_index()
    time_col, survival_col = curve.columns[0], curve.columns[1]
    below_half = curve[curve[survival_col] <= 0.5]
    return None if below_half.empty else float(below_half.iloc[0][time_col])


def compare_bucket_survival(survival_df: pd.DataFrame) -> dict[str, Any]:
    """Fit Kaplan-Meier curves for the ephemeral and stable buckets and run a
    log-rank test for whether the two half-lives actually differ."""
    ephemeral = survival_df[survival_df["tech_bucket"] == "ephemeral"]
    stable = survival_df[survival_df["tech_bucket"] == "stable"]

    if ephemeral.empty or stable.empty:
        raise ValueError("Both buckets need at least one accepted answer to compare.")

    kmf_ephemeral = KaplanMeierFitter(label="ephemeral").fit(
        ephemeral["duration_days"], ephemeral["event_observed"]
    )
    kmf_stable = KaplanMeierFitter(label="stable").fit(
        stable["duration_days"], stable["event_observed"]
    )

    result = logrank_test(
        ephemeral["duration_days"],
        stable["duration_days"],
        event_observed_A=ephemeral["event_observed"],
        event_observed_B=stable["event_observed"],
    )

    return {
        "ephemeral_n": int(len(ephemeral)),
        "stable_n": int(len(stable)),
        "ephemeral_half_life_days": _half_life(kmf_ephemeral),
        "stable_half_life_days": _half_life(kmf_stable),
        "logrank_p_value": float(result.p_value),
        "ephemeral_kmf": kmf_ephemeral,
        "stable_kmf": kmf_stable,
    }
