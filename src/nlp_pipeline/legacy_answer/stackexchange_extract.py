"""Streaming helpers for extracting a small Stack Exchange subset."""

from __future__ import annotations

import csv
import html
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def _clear_element(element: ET.Element) -> None:
    element.clear()


def _iter_rows(
    xml_path: str | Path,
    max_rows: int | None = None,
    start_row: int = 0,
):
    """Yield XML row attribute dictionaries from a Stack Exchange dump file."""
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


def extract_debug_subset(
    posts_xml_path: str | Path,
    votes_xml_path: str | Path,
    output_dir: str | Path,
    target_questions: int = 1000,
    post_row_limit: int | None = 500000,
    vote_row_limit: int | None = 500000,
    sampling_strategy: str = "repeated_acceptance",
    post_row_offset: int = 0,
    vote_row_offset: int = 0,
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

    question_summary, answer_to_question = _scan_post_summaries(
        posts_xml_path, post_row_limit, post_row_offset
    )
    question_ids = _select_question_ids(
        votes_xml_path=votes_xml_path,
        vote_row_limit=vote_row_limit,
        vote_row_offset=vote_row_offset,
        question_summary=question_summary,
        answer_to_question=answer_to_question,
        target_questions=target_questions,
        sampling_strategy=sampling_strategy,
    )

    question_rows = _load_question_rows(
        posts_xml_path=posts_xml_path,
        post_row_limit=post_row_limit,
        post_row_offset=post_row_offset,
        question_ids=question_ids,
    )

    answer_rows: list[dict[str, str]] = []
    answer_ids_in_subset: set[str] = set()

    for row in _iter_rows(
        posts_xml_path, max_rows=post_row_limit, start_row=post_row_offset
    ):
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
    for row in _iter_rows(
        votes_xml_path, max_rows=vote_row_limit, start_row=vote_row_offset
    ):
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
        "sampling_strategy": sampling_strategy,
        "post_row_limit": post_row_limit or 0,
        "vote_row_limit": vote_row_limit or 0,
        "post_row_offset": post_row_offset,
        "vote_row_offset": vote_row_offset,
    }


def _scan_post_summaries(
    posts_xml_path: str | Path,
    post_row_limit: int | None,
    post_row_offset: int,
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    question_summary: dict[str, dict[str, str]] = {}
    answer_to_question: dict[str, str] = {}

    for row in _iter_rows(
        posts_xml_path, max_rows=post_row_limit, start_row=post_row_offset
    ):
        post_type_id = row.get("PostTypeId")
        post_id = row.get("Id")
        if not post_id:
            continue

        if post_type_id == "1" and row.get("AcceptedAnswerId"):
            question_summary[post_id] = {
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
            continue

        if post_type_id == "2":
            parent_id = row.get("ParentId")
            if parent_id:
                answer_to_question[post_id] = parent_id

    return question_summary, answer_to_question


def _select_question_ids(
    votes_xml_path: str | Path,
    vote_row_limit: int | None,
    vote_row_offset: int,
    question_summary: dict[str, dict[str, str]],
    answer_to_question: dict[str, str],
    target_questions: int,
    sampling_strategy: str,
) -> set[str]:
    acceptance_by_question: dict[str, list[dict[str, str]]] = defaultdict(list)
    distinct_answers_by_question: dict[str, set[str]] = defaultdict(set)

    for row in _iter_rows(
        votes_xml_path, max_rows=vote_row_limit, start_row=vote_row_offset
    ):
        if row.get("VoteTypeId") != "1":
            continue
        answer_id = row.get("PostId")
        question_id = answer_to_question.get(answer_id or "")
        if not question_id or question_id not in question_summary:
            continue
        acceptance_by_question[question_id].append(
            {
                "answer_id": answer_id or "",
                "accepted_at": row.get("CreationDate", ""),
            }
        )
        distinct_answers_by_question[question_id].add(answer_id or "")

    repeated_questions = [
        question_id
        for question_id, answers in distinct_answers_by_question.items()
        if len(answers) >= 2
    ]
    repeated_questions.sort(
        key=lambda question_id: (
            -len(distinct_answers_by_question[question_id]),
            -len(acceptance_by_question[question_id]),
            question_id,
        )
    )

    if sampling_strategy == "repeated_acceptance":
        selected = repeated_questions[:target_questions]
        if len(selected) < target_questions:
            fallback = [
                question_id
                for question_id in question_summary
                if question_id not in set(selected) and question_id in acceptance_by_question
            ]
            selected.extend(fallback[: target_questions - len(selected)])
        return set(selected)

    accepted_questions = [
        question_id for question_id in question_summary if question_id in acceptance_by_question
    ]
    return set(accepted_questions[:target_questions])


def _load_question_rows(
    posts_xml_path: str | Path,
    post_row_limit: int | None,
    post_row_offset: int,
    question_ids: set[str],
) -> list[dict[str, str]]:
    question_rows: list[dict[str, str]] = []
    for row in _iter_rows(
        posts_xml_path, max_rows=post_row_limit, start_row=post_row_offset
    ):
        if row.get("PostTypeId") != "1":
            continue
        post_id = row.get("Id")
        if post_id not in question_ids:
            continue
        question_rows.append(
            {
                "question_id": post_id or "",
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
    return question_rows


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
