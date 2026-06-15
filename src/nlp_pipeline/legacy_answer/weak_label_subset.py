"""Build weakly supervised outdated/superseded labels from Stack Exchange data."""

from __future__ import annotations

import csv
import html
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path


OUTDATED_PATTERNS = [
    "deprecated",
    "outdated",
    "obsolete",
    "no longer works",
    "doesn't work anymore",
    "does not work anymore",
    "old answer",
    "legacy",
]


def _clear_element(element: ET.Element) -> None:
    element.clear()


def _iter_rows(
    xml_path: str | Path,
    max_rows: int | None = None,
    start_row: int = 0,
):
    seen = 0
    context = ET.iterparse(xml_path, events=("end",))
    for _, elem in context:
        if elem.tag == "row":
            seen += 1
            if seen <= start_row:
                _clear_element(elem)
                continue
            yield elem.attrib
            _clear_element(elem)
            if max_rows is not None and (seen - start_row) >= max_rows:
                break


def _clean_html_text(text: str) -> str:
    if not text:
        return ""
    return html.unescape(text)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def extract_weak_label_subset(
    posts_xml_path: str | Path,
    comments_xml_path: str | Path,
    output_dir: str | Path,
    target_questions: int = 500,
    post_row_limit: int | None = 2_000_000,
    comment_row_limit: int | None = 2_000_000,
    post_row_offset: int = 0,
    comment_row_offset: int = 0,
    min_answer_count: int = 2,
) -> dict[str, int | str]:
    """Extract a bounded subset for weakly supervised answer labeling."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    question_rows: list[dict[str, str]] = []
    question_ids: set[str] = set()
    accepted_answer_ids: set[str] = set()

    for row in _iter_rows(posts_xml_path, max_rows=post_row_limit, start_row=post_row_offset):
        if row.get("PostTypeId") != "1":
            continue
        accepted_answer_id = row.get("AcceptedAnswerId")
        if not accepted_answer_id:
            continue

        answer_count_raw = row.get("AnswerCount", "0")
        try:
            answer_count = int(answer_count_raw)
        except ValueError:
            answer_count = 0
        if answer_count < min_answer_count:
            continue

        question_id = row.get("Id")
        if not question_id:
            continue

        question_ids.add(question_id)
        accepted_answer_ids.add(accepted_answer_id)
        question_rows.append(
            {
                "question_id": question_id,
                "accepted_answer_id_snapshot": accepted_answer_id,
                "question_creation_date": row.get("CreationDate", ""),
                "question_score": row.get("Score", ""),
                "answer_count": answer_count_raw,
                "title": _clean_html_text(row.get("Title", "")),
                "body": _clean_html_text(row.get("Body", "")),
                "tags": _clean_html_text(row.get("Tags", "")),
            }
        )
        if len(question_rows) >= target_questions:
            break

    answer_rows: list[dict[str, str]] = []
    answer_ids: set[str] = set()
    for row in _iter_rows(posts_xml_path, max_rows=post_row_limit, start_row=post_row_offset):
        if row.get("PostTypeId") != "2":
            continue
        parent_id = row.get("ParentId")
        if parent_id not in question_ids:
            continue
        answer_id = row.get("Id", "")
        answer_ids.add(answer_id)
        answer_rows.append(
            {
                "answer_id": answer_id,
                "question_id": parent_id or "",
                "is_accepted_snapshot": "1" if answer_id in accepted_answer_ids else "0",
                "answer_creation_date": row.get("CreationDate", ""),
                "answer_score": row.get("Score", ""),
                "answer_body": _clean_html_text(row.get("Body", "")),
                "owner_user_id": row.get("OwnerUserId", ""),
            }
        )

    comment_rows: list[dict[str, str]] = []
    for row in _iter_rows(
        comments_xml_path,
        max_rows=comment_row_limit,
        start_row=comment_row_offset,
    ):
        post_id = row.get("PostId")
        if post_id not in answer_ids:
            continue
        comment_rows.append(
            {
                "comment_id": row.get("Id", ""),
                "post_id": post_id or "",
                "comment_score": row.get("Score", ""),
                "comment_creation_date": row.get("CreationDate", ""),
                "comment_text": _clean_html_text(row.get("Text", "")),
            }
        )

    _write_csv(
        output_path / "questions.csv",
        question_rows,
        [
            "question_id",
            "accepted_answer_id_snapshot",
            "question_creation_date",
            "question_score",
            "answer_count",
            "title",
            "body",
            "tags",
        ],
    )
    _write_csv(
        output_path / "answers.csv",
        answer_rows,
        [
            "answer_id",
            "question_id",
            "is_accepted_snapshot",
            "answer_creation_date",
            "answer_score",
            "answer_body",
            "owner_user_id",
        ],
    )
    _write_csv(
        output_path / "comments.csv",
        comment_rows,
        [
            "comment_id",
            "post_id",
            "comment_score",
            "comment_creation_date",
            "comment_text",
        ],
    )

    return {
        "output_dir": str(output_path),
        "sampled_questions": len(question_rows),
        "sampled_answers": len(answer_rows),
        "sampled_comments": len(comment_rows),
    }


def build_weak_labels(
    questions_csv_path: str | Path,
    answers_csv_path: str | Path,
    comments_csv_path: str | Path,
    output_csv_path: str | Path,
    min_gap_days: float = 0.0,
) -> dict[str, int | str]:
    """Create weak labels for outdated or superseded answers."""
    questions = _read_csv(questions_csv_path)
    answers = _read_csv(answers_csv_path)
    comments = _read_csv(comments_csv_path)

    question_to_accepted = {
        row["question_id"]: row["accepted_answer_id_snapshot"]
        for row in questions
        if row.get("question_id") and row.get("accepted_answer_id_snapshot")
    }
    question_lookup = {row["question_id"]: row for row in questions if row.get("question_id")}
    answers_by_question: dict[str, list[dict[str, str]]] = defaultdict(list)
    answer_lookup = {row["answer_id"]: row for row in answers if row.get("answer_id")}

    for answer in answers:
        question_id = answer.get("question_id", "")
        if question_id:
            answers_by_question[question_id].append(answer)

    comments_by_post: dict[str, list[str]] = defaultdict(list)
    for comment in comments:
        post_id = comment.get("post_id", "")
        text = comment.get("comment_text", "")
        if post_id and text:
            comments_by_post[post_id].append(text)

    label_rows: list[dict[str, str | int | float]] = []
    skipped_rows = 0

    for question_id, sibling_answers in answers_by_question.items():
        accepted_answer_id = question_to_accepted.get(question_id)
        accepted_answer = answer_lookup.get(accepted_answer_id or "")
        question = question_lookup.get(question_id)
        if not accepted_answer or not question:
            continue

        accepted_created = _parse_dt(accepted_answer["answer_creation_date"])
        accepted_score = _safe_int(accepted_answer.get("answer_score", "0"))

        for answer in sibling_answers:
            answer_id = answer["answer_id"]
            answer_created = _parse_dt(answer["answer_creation_date"])
            answer_score = _safe_int(answer.get("answer_score", "0"))
            all_comments = " ".join(comments_by_post.get(answer_id, []))
            all_comments_lower = all_comments.lower()

            label = ""
            reason = ""
            confidence = ""
            gap_days = round((accepted_created - answer_created).total_seconds() / 86400, 3)

            if answer_id == accepted_answer_id:
                label = "0"
                reason = "current_accepted_answer"
                confidence = "1.0"
            else:
                has_outdated_comment = any(
                    pattern in all_comments_lower for pattern in OUTDATED_PATTERNS
                )
                is_older_than_accepted = gap_days >= min_gap_days
                not_better_than_accepted = answer_score <= accepted_score

                if has_outdated_comment:
                    label = "1"
                    reason = "outdated_comment_cue"
                    confidence = "0.95"
                elif is_older_than_accepted and not_better_than_accepted:
                    label = "1"
                    reason = "older_than_current_accepted_answer"
                    confidence = "0.70"
                else:
                    skipped_rows += 1
                    continue

            label_rows.append(
                {
                    "question_id": question_id,
                    "question_title": question.get("title", ""),
                    "question_body": question.get("body", ""),
                    "accepted_answer_id_snapshot": accepted_answer_id or "",
                    "answer_id": answer_id,
                    "is_accepted_snapshot": answer.get("is_accepted_snapshot", ""),
                    "answer_creation_date": answer.get("answer_creation_date", ""),
                    "answer_score": answer.get("answer_score", ""),
                    "comment_count": len(comments_by_post.get(answer_id, [])),
                    "comment_text": all_comments,
                    "weak_label": label,
                    "weak_label_reason": reason,
                    "weak_label_confidence": confidence,
                    "days_before_current_accepted": gap_days,
                    "answer_body": answer.get("answer_body", ""),
                }
            )

    _write_csv(
        Path(output_csv_path),
        label_rows,
        [
            "question_id",
            "question_title",
            "question_body",
            "accepted_answer_id_snapshot",
            "answer_id",
            "is_accepted_snapshot",
            "answer_creation_date",
            "answer_score",
            "comment_count",
            "comment_text",
            "weak_label",
            "weak_label_reason",
            "weak_label_confidence",
            "days_before_current_accepted",
            "answer_body",
        ],
    )

    return {
        "output_csv": str(output_csv_path),
        "labeled_rows": len(label_rows),
        "skipped_rows": skipped_rows,
        "positive_labels": sum(1 for row in label_rows if row["weak_label"] == "1"),
        "negative_labels": sum(1 for row in label_rows if row["weak_label"] == "0"),
    }


def _safe_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def _write_csv(path: Path, rows: list[dict[str, str | int | float]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def contains_outdated_language(text: str) -> bool:
    """Return whether a comment body contains a simple outdatedness cue."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return any(pattern in normalized for pattern in OUTDATED_PATTERNS)
