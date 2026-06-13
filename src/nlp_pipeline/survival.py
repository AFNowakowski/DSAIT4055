"""Survival-analysis helpers."""

from __future__ import annotations

import pandas as pd
from lifelines import KaplanMeierFitter


def build_survival_table(
    labeled_answers: pd.DataFrame,
    observation_end: str | pd.Timestamp,
) -> pd.DataFrame:
    """Build a survival-analysis table from labeled accepted-answer history."""
    df = labeled_answers.copy()
    df["accepted_at"] = pd.to_datetime(df["accepted_at"], utc=True)
    df["event_at"] = pd.to_datetime(df["event_at"], utc=True)
    observation_end = pd.to_datetime(observation_end, utc=True)

    censor_time = df["event_at"].fillna(observation_end)
    df["duration_days"] = (censor_time - df["accepted_at"]).dt.total_seconds() / 86400

    return df[
        [
            "question_id",
            "answer_id",
            "accepted_at",
            "event_at",
            "duration_days",
            "event_observed",
        ]
    ].copy()


def estimate_half_life(survival_df: pd.DataFrame) -> tuple[KaplanMeierFitter, float | None]:
    """Fit a Kaplan-Meier estimator and return the estimated half-life in days."""
    kmf = KaplanMeierFitter()
    kmf.fit(
        durations=survival_df["duration_days"],
        event_observed=survival_df["event_observed"],
    )

    curve = kmf.survival_function_.reset_index()
    time_col = curve.columns[0]
    survival_col = curve.columns[1]
    below_half = curve[curve[survival_col] <= 0.5]
    half_life = None if below_half.empty else float(below_half.iloc[0][time_col])

    return kmf, half_life
