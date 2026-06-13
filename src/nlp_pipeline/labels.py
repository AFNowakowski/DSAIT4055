"""Event-label construction for answer deprecation."""

from __future__ import annotations

import pandas as pd


def label_deprecation_by_acceptance_switch(
    accepted_history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Mark an accepted answer as deprecated if another answer later becomes accepted
    for the same question.

    Expected input columns:
    - question_id
    - answer_id
    - accepted_at
    """
    history = accepted_history.copy()
    history["accepted_at"] = pd.to_datetime(history["accepted_at"], utc=True)
    history = history.sort_values(["question_id", "accepted_at"])

    history["next_answer_id"] = history.groupby("question_id")["answer_id"].shift(-1)
    history["event_at"] = history.groupby("question_id")["accepted_at"].shift(-1)
    history["event_observed"] = history["next_answer_id"].notna().astype(int)

    return history
