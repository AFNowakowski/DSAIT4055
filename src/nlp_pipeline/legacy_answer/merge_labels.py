"""Merge heuristic and Ollama labels into one training dataset."""

from __future__ import annotations

import csv
from pathlib import Path


def merge_training_labels(
    weak_labels_csv_path: str | Path,
    ollama_labels_csv_path: str | Path,
    output_csv_path: str | Path,
) -> dict[str, int | str]:
    """
    Merge weak labels and Ollama labels into a single training dataset.

    Rule:
    - use `ollama_label` when present
    - otherwise fall back to `weak_label`
    """
    weak_rows = _read_csv(weak_labels_csv_path)
    ollama_rows = _read_csv(ollama_labels_csv_path)

    ollama_by_answer_id = {
        row["answer_id"]: row
        for row in ollama_rows
        if row.get("answer_id")
    }

    merged_rows: list[dict[str, str]] = []
    ollama_override_count = 0
    heuristic_fallback_count = 0

    for row in weak_rows:
        answer_id = row.get("answer_id", "")
        ollama_row = ollama_by_answer_id.get(answer_id)

        weak_label = row.get("weak_label", "")
        ollama_label = ""
        final_label = weak_label
        label_source = "weak_label"

        if ollama_row and ollama_row.get("ollama_label", "") != "":
            ollama_label = ollama_row.get("ollama_label", "")
            final_label = ollama_label
            label_source = "ollama_label"
            ollama_override_count += 1
        else:
            heuristic_fallback_count += 1

        merged_rows.append(
            {
                "question_id": row.get("question_id", ""),
                "answer_id": answer_id,
                "question_title": row.get("question_title", ""),
                "question_body": row.get("question_body", ""),
                "accepted_answer_id_snapshot": row.get("accepted_answer_id_snapshot", ""),
                "is_accepted_snapshot": row.get("is_accepted_snapshot", ""),
                "answer_creation_date": row.get("answer_creation_date", ""),
                "answer_score": row.get("answer_score", ""),
                "comment_count": row.get("comment_count", ""),
                "comment_text": row.get("comment_text", ""),
                "answer_body": row.get("answer_body", ""),
                "weak_label": weak_label,
                "weak_label_reason": row.get("weak_label_reason", ""),
                "weak_label_confidence": row.get("weak_label_confidence", ""),
                "ollama_label": ollama_label,
                "ollama_confidence": ollama_row.get("ollama_confidence", "") if ollama_row else "",
                "ollama_reason": ollama_row.get("ollama_reason", "") if ollama_row else "",
                "ollama_explanation": ollama_row.get("ollama_explanation", "") if ollama_row else "",
                "final_label": final_label,
                "label_source": label_source,
            }
        )

    _write_csv(
        output_csv_path,
        merged_rows,
        [
            "question_id",
            "answer_id",
            "question_title",
            "question_body",
            "accepted_answer_id_snapshot",
            "is_accepted_snapshot",
            "answer_creation_date",
            "answer_score",
            "comment_count",
            "comment_text",
            "answer_body",
            "weak_label",
            "weak_label_reason",
            "weak_label_confidence",
            "ollama_label",
            "ollama_confidence",
            "ollama_reason",
            "ollama_explanation",
            "final_label",
            "label_source",
        ],
    )

    return {
        "output_csv": str(output_csv_path),
        "merged_rows": len(merged_rows),
        "ollama_override_count": ollama_override_count,
        "heuristic_fallback_count": heuristic_fallback_count,
    }


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(
    path: str | Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
