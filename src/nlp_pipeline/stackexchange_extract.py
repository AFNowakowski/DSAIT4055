"""Streaming helpers for extracting a small Stack Exchange subset."""

from __future__ import annotations

import csv
import html
import xml.etree.ElementTree as ET
from pathlib import Path


def _clear_element(element: ET.Element) -> None:
    element.clear()


def _iter_rows(xml_path: str | Path, max_rows: int | None = None):
    """Yield XML row attribute dictionaries from a Stack Exchange dump file."""
    seen = 0
    context = ET.iterparse(xml_path, events=("end",))
    for _, elem in context:
        if elem.tag == "row":
            yield elem.attrib
            seen += 1
            _clear_element(elem)
            if max_rows is not None and seen >= max_rows:
                break


def _clean_html_text(text: str) -> str:
    if not text:
        return ""
    return html.unescape(text)


def extract_debug_subset(
    posts_xml_path: str | Path,
    votes_xml_path: str | Path,
    output_dir: str | Path,
    target_questions: int = 1000,
    post_row_limit: int | None = 500000,
    vote_row_limit: int | None = 500000,
) -> dict[str, int | str]:
    """
    Extract a small accepted-answer-focused subset from the Stack Exchange dump.

    Output files:
    - questions.csv
    - answers.csv
    - acceptance_votes.csv
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    question_ids: set[str] = set()
    question_rows: list[dict[str, str]] = []

    for row in _iter_rows(posts_xml_path, max_rows=post_row_limit):
        if row.get("PostTypeId") != "1":
            continue
        if not row.get("AcceptedAnswerId"):
            continue
        post_id = row.get("Id")
        if not post_id:
            continue
        question_ids.add(post_id)
        question_rows.append(
            {
                "question_id": post_id,
                "question_creation_date": row.get("CreationDate", ""),
                "question_score": row.get("Score", ""),
                "accepted_answer_id_snapshot": row.get("AcceptedAnswerId", ""),
                "answer_count": row.get("AnswerCount", ""),
                "title": _clean_html_text(row.get("Title", "")),
                "body": _clean_html_text(row.get("Body", "")),
                "tags": _clean_html_text(row.get("Tags", "")),
                "owner_user_id": row.get("OwnerUserId", ""),
            }
        )
        if len(question_ids) >= target_questions:
            break

    answer_rows: list[dict[str, str]] = []
    answer_ids_in_subset: set[str] = set()

    for row in _iter_rows(posts_xml_path, max_rows=post_row_limit):
        post_type_id = row.get("PostTypeId")
        post_id = row.get("Id")
        if post_type_id == "2" and row.get("ParentId") in question_ids:
            answer_id = post_id or ""
            answer_ids_in_subset.add(answer_id)
            answer_rows.append(
                {
                    "answer_id": answer_id,
                    "question_id": row.get("ParentId", ""),
                    "answer_creation_date": row.get("CreationDate", ""),
                    "answer_score": row.get("Score", ""),
                    "answer_body": _clean_html_text(row.get("Body", "")),
                    "owner_user_id": row.get("OwnerUserId", ""),
                }
            )

    acceptance_rows: list[dict[str, str]] = []
    for row in _iter_rows(votes_xml_path, max_rows=vote_row_limit):
        if row.get("VoteTypeId") != "1":
            continue
        answer_id = row.get("PostId")
        if answer_id not in answer_ids_in_subset:
            continue
        acceptance_rows.append(
            {
                "answer_id": answer_id or "",
                "acceptance_vote_id": row.get("Id", ""),
                "accepted_at": row.get("CreationDate", ""),
            }
        )

    _write_csv(
        output_path / "questions.csv",
        question_rows,
        [
            "question_id",
            "question_creation_date",
            "question_score",
            "accepted_answer_id_snapshot",
            "answer_count",
            "title",
            "body",
            "tags",
            "owner_user_id",
        ],
    )
    _write_csv(
        output_path / "answers.csv",
        answer_rows,
        [
            "answer_id",
            "question_id",
            "answer_creation_date",
            "answer_score",
            "answer_body",
            "owner_user_id",
        ],
    )
    _write_csv(
        output_path / "acceptance_votes.csv",
        acceptance_rows,
        ["answer_id", "acceptance_vote_id", "accepted_at"],
    )

    return {
        "output_dir": str(output_path),
        "sampled_questions": len(question_ids),
        "sampled_answers": len(answer_rows),
        "acceptance_votes": len(acceptance_rows),
        "post_row_limit": post_row_limit or 0,
        "vote_row_limit": vote_row_limit or 0,
    }


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
