"""Build labels from an extracted Stack Exchange subset."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def build_subset_labels(
    answers_csv_path: str | Path,
    acceptance_votes_csv_path: str | Path,
    output_csv_path: str | Path,
) -> dict[str, int | str]:
    """
    Create answer-level labels from acceptance events.

    Label rule:
    - If a later accepted answer exists for the same question, current accepted answer
      is labeled deprecated.
    """
    answers = _read_csv(answers_csv_path)
    acceptance_votes = _read_csv(acceptance_votes_csv_path)

    answer_to_question = {
        row["answer_id"]: row["question_id"]
        for row in answers
        if row.get("answer_id") and row.get("question_id")
    }
    answer_lookup = {row["answer_id"]: row for row in answers if row.get("answer_id")}

    acceptance_by_question: dict[str, list[dict[str, str]]] = defaultdict(list)
    for vote in acceptance_votes:
        answer_id = vote.get("answer_id", "")
        question_id = answer_to_question.get(answer_id)
        if not question_id:
            continue
        acceptance_by_question[question_id].append(
            {
                "question_id": question_id,
                "answer_id": answer_id,
                "accepted_at": vote.get("accepted_at", ""),
            }
        )

    label_rows: list[dict[str, str | int | float]] = []
    for question_id, events in acceptance_by_question.items():
        ordered = _collapse_repeated_acceptances(events)
        for index, event in enumerate(ordered):
            answer = answer_lookup.get(event["answer_id"])
            if not answer:
                continue

            next_event = ordered[index + 1] if index + 1 < len(ordered) else None
            accepted_at = _parse_dt(event["accepted_at"])
            event_at = next_event["accepted_at"] if next_event else ""
            deprecated = 1 if next_event else 0

            duration_days = ""
            if next_event:
                delta = _parse_dt(next_event["accepted_at"]) - accepted_at
                duration_days = round(delta.total_seconds() / 86400, 3)

            label_rows.append(
                {
                    "question_id": question_id,
                    "answer_id": event["answer_id"],
                    "answer_creation_date": answer.get("answer_creation_date", ""),
                    "accepted_at": event["accepted_at"],
                    "event_at": event_at,
                    "is_deprecated": deprecated,
                    "duration_days": duration_days,
                    "answer_score": answer.get("answer_score", ""),
                    "answer_body": answer.get("answer_body", ""),
                }
            )

    with Path(output_csv_path).open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "question_id",
            "answer_id",
            "answer_creation_date",
            "accepted_at",
            "event_at",
            "is_deprecated",
            "duration_days",
            "answer_score",
            "answer_body",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(label_rows)

    return {
        "output_csv": str(output_csv_path),
        "labeled_rows": len(label_rows),
        "questions_with_acceptance_history": len(acceptance_by_question),
    }


def _collapse_repeated_acceptances(
    events: list[dict[str, str]],
) -> list[dict[str, str]]:
    ordered = sorted(events, key=lambda row: _parse_dt(row["accepted_at"]))
    collapsed: list[dict[str, str]] = []
    for event in ordered:
        if collapsed and collapsed[-1]["answer_id"] == event["answer_id"]:
            continue
        collapsed.append(event)
    return collapsed
