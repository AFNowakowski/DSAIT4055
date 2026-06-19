"""Local Ollama-based labeling helpers for comment review suggestions."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .ollama_utils import resolve_ollama_executable, run_ollama_json


SYSTEM_PROMPT = """You label Stack Overflow comments for answer-obsolescence review.
Return only valid JSON with keys:
- "label": one of "temporal_obsolescence", "freshness_confirmation", "incorrectness", "situational_failure", "neutral"
- "confidence": a float between 0 and 1
- "reason": a short snake_case reason
- "explanation": one short sentence
Label definitions:
- temporal_obsolescence: the comment says the answer became outdated because a version, API, platform, syntax, or recommended practice changed over time
- freshness_confirmation: the comment says the answer still works or is still supported
- incorrectness: the answer was wrong independently of technological change
- situational_failure: the answer failed in one environment or for one user without enough evidence of temporal change
- neutral: none of the above
Rules:
- Do not infer obsolescence from negativity alone.
- Prefer situational_failure over temporal_obsolescence when the comment only says something does not work.
- Prefer incorrectness when the comment says the answer is simply wrong.
- Return one compact JSON object only with no markdown fences or extra text."""


LABEL_SYNONYMS = {
    "1": "temporal_obsolescence",
    "0": "neutral",
    "temporal": "temporal_obsolescence",
    "obsolete": "temporal_obsolescence",
    "outdated": "temporal_obsolescence",
    "deprecated": "temporal_obsolescence",
    "fresh": "freshness_confirmation",
    "freshness": "freshness_confirmation",
    "still_supported": "freshness_confirmation",
    "incorrect": "incorrectness",
    "wrong": "incorrectness",
    "failure": "situational_failure",
    "does_not_work": "situational_failure",
    "not_working": "situational_failure",
    "other": "neutral",
}

OUTPUT_FIELDS = [
    "comment_id",
    "post_id",
    "score",
    "creation_date",
    "text",
    "candidate_category",
    "candidate_reason",
    "human_label",
    "review_notes",
    "ollama_label",
    "ollama_confidence",
    "ollama_reason",
    "ollama_explanation",
]


def label_comment_annotations_with_ollama(
    input_csv_path: str | Path,
    output_csv_path: str | Path,
    model: str,
    limit: int | None = None,
    only_unlabeled: bool = True,
    ollama_executable: str | None = None,
    verbose: bool = False,
    ollama_host: str = "http://127.0.0.1:11434",
    resume: bool = True,
) -> dict[str, int | str]:
    """Label comment review rows with a local Ollama model."""
    rows = _read_csv(input_csv_path)
    output_path = Path(output_csv_path)
    existing_rows = _read_csv(output_path) if resume and output_path.exists() else []
    existing_comment_ids = {
        row["comment_id"]
        for row in existing_rows
        if row.get("comment_id")
    }

    selected_rows = []
    skipped_existing = 0
    skipped_human_labeled = 0
    for row in rows:
        if only_unlabeled and row.get("human_label", "").strip():
            skipped_human_labeled += 1
            continue
        if row.get("comment_id") in existing_comment_ids:
            skipped_existing += 1
            continue
        selected_rows.append(row)
        if limit is not None and len(selected_rows) >= limit:
            break

    output_rows: list[dict[str, str]] = list(existing_rows)
    executable = resolve_ollama_executable(ollama_executable) if ollama_executable else None
    total = len(selected_rows)

    if verbose:
        if executable:
            print(f"Using Ollama executable: {executable}")
        print(f"Using Ollama host: {ollama_host}")
        print(f"Existing labeled rows: {len(existing_rows)}")
        print(f"Skipped already labeled rows: {skipped_existing}")
        print(f"Skipped human-labeled rows: {skipped_human_labeled}")
        print(f"Selected rows for labeling: {total}")

    for index, row in enumerate(selected_rows, start=1):
        if verbose:
            print(
                f"[{index}/{total}] Labeling comment_id={row.get('comment_id', '')} "
                f"post_id={row.get('post_id', '')}"
            )
        prompt = build_comment_label_prompt(row)
        try:
            response = run_ollama_json(
                model=model,
                prompt=prompt,
                ollama_executable=executable,
                ollama_host=ollama_host,
            )
        except Exception as exc:
            if verbose:
                print(f"[{index}/{total}] -> parse_error={type(exc).__name__}: {exc}")
            response = run_ollama_json(
                model=model,
                prompt=build_comment_fallback_prompt(row),
                ollama_executable=executable,
                ollama_host=ollama_host,
            )

        normalized = _normalize_comment_response(response)
        output_rows.append(_build_output_row(row, normalized))
        _write_csv(output_path, output_rows, OUTPUT_FIELDS)

        if verbose:
            print(
                f"[{index}/{total}] -> label={normalized.get('label', '')} "
                f"confidence={normalized.get('confidence', '')} "
                f"reason={normalized.get('reason', '')}"
            )

    return {
        "output_csv": str(output_path),
        "labeled_rows": len(output_rows),
        "new_rows_labeled": total,
        "existing_rows": len(existing_rows),
    }


def build_comment_label_prompt(row: dict[str, str]) -> str:
    """Build the annotation prompt for a single comment."""
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Comment text:\n{row.get('text', '').strip()}\n\n"
        f"Candidate category from rule-based sampler: {row.get('candidate_category', '').strip()}\n"
        f"Candidate reason from rule-based sampler: {row.get('candidate_reason', '').strip()}\n"
        f"Comment score: {row.get('score', '').strip()}\n"
        f"Creation date: {row.get('creation_date', '').strip()}\n"
    )


def build_comment_fallback_prompt(row: dict[str, str]) -> str:
    """Build a shorter fallback prompt if the richer one fails to parse cleanly."""
    return (
        "Return only JSON with keys label, confidence, reason, explanation. "
        "Allowed labels are temporal_obsolescence, freshness_confirmation, "
        "incorrectness, situational_failure, neutral.\n\n"
        f"Comment: {row.get('text', '').strip()[:1500]}\n"
        f"Rule hint: {row.get('candidate_category', '').strip()}\n"
    )


def _normalize_comment_response(payload: dict[str, object]) -> dict[str, object]:
    raw_label = str(payload.get("label", "")).strip().lower()
    label = LABEL_SYNONYMS.get(raw_label, raw_label)
    if label not in {
        "temporal_obsolescence",
        "freshness_confirmation",
        "incorrectness",
        "situational_failure",
        "neutral",
    }:
        raise ValueError(f"Unexpected Ollama comment label: {payload!r}")
    return {
        "label": label,
        "confidence": payload.get("confidence", ""),
        "reason": payload.get("reason", ""),
        "explanation": payload.get("explanation", ""),
    }


def _build_output_row(row: dict[str, str], response: dict[str, object]) -> dict[str, str]:
    return {
        "comment_id": row.get("comment_id", ""),
        "post_id": row.get("post_id", ""),
        "score": row.get("score", ""),
        "creation_date": row.get("creation_date", ""),
        "text": row.get("text", ""),
        "candidate_category": row.get("candidate_category", ""),
        "candidate_reason": row.get("candidate_reason", ""),
        "human_label": row.get("human_label", ""),
        "review_notes": row.get("review_notes", ""),
        "ollama_label": str(response.get("label", "")),
        "ollama_confidence": str(response.get("confidence", "")),
        "ollama_reason": str(response.get("reason", "")),
        "ollama_explanation": str(response.get("explanation", "")),
    }


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
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
