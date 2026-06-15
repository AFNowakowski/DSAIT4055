"""Prepare comment-level data for temporal-obsolescence classification."""

from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, TextIO


COMMENT_FIELDS = [
    "comment_id",
    "post_id",
    "score",
    "text",
    "creation_date",
    "user_display_name",
    "user_id",
    "source_label",
]

ANNOTATION_FIELDS = [
    "comment_id",
    "post_id",
    "score",
    "creation_date",
    "text",
    "candidate_category",
    "candidate_reason",
    "human_label",
    "review_notes",
]

_INSERT_PREFIX = "INSERT INTO dsait4055db.Comments"

_FRESHNESS_RULES = [
    ("not_deprecated", re.compile(r"\b(?:is|are|was|were|it'?s)\s+not\s+deprecated\b", re.I)),
    ("still_supported", re.compile(r"\bstill\s+(?:works?|supported|valid|available)\b", re.I)),
    ("works_in_year", re.compile(r"\bworks?\s+(?:fine\s+)?in\s+20\d{2}\b", re.I)),
]

_TEMPORAL_RULES = [
    ("explicit_deprecated", re.compile(r"\bdeprecat(?:e|ed|es|ing|ion)\b", re.I)),
    ("explicit_outdated", re.compile(r"\boutdated\b", re.I)),
    ("explicit_obsolete", re.compile(r"\bobsolete\b", re.I)),
    ("no_longer", re.compile(
        r"\bno longer\s+(?:works?|supported|available|valid|recommended|exists?|used|needed)\b",
        re.I,
    )),
    ("removed_api", re.compile(
        r"\b(?:was|were|has been|is|are)?\s*removed\s+(?:in|from|since|as of)\b",
        re.I,
    )),
    ("version_replacement", re.compile(
        r"\b(?:since|as of|starting (?:with|from)|in)\s+"
        r"(?:version|v\.?)?\s*\d+(?:\.\d+){0,2}.+"
        r"\b(?:use|replace|renamed|removed|deprecated)\b",
        re.I,
    )),
    ("newer_version", re.compile(
        r"\b(?:newer|latest|recent|current)\s+versions?\b.{0,80}"
        r"\b(?:use|require|removed|deprecated|changed|renamed)\b",
        re.I,
    )),
]

_INCORRECT_RULES = [
    ("explicit_incorrect", re.compile(
        r"\b(?:this|that|the answer|your answer|it)\s+(?:is|was)\s+(?:simply\s+)?incorrect\b",
        re.I,
    )),
    ("explicit_wrong", re.compile(
        r"\b(?:this|that|the answer|your answer|it)\s+(?:is|was)\s+(?:simply\s+)?wrong\b",
        re.I,
    )),
    ("never_worked", re.compile(r"\b(?:can|could|does|did|will|would)\s+never\s+work\b", re.I)),
]

_FAILURE_RULES = [
    ("does_not_work", re.compile(
        r"\b(?:does(?:n['’]t|\s+not)|did(?:n['’]t|\s+not)|won['’]t|will\s+not)\s+work\b",
        re.I,
    )),
    ("not_working", re.compile(r"\b(?:is|are|was|were|it['’]s)\s+not\s+working\b", re.I)),
    ("fails_with", re.compile(r"\bfails?\s+(?:for|on|under|with|when)\b", re.I)),
]


def iter_sql_statements(handle: TextIO, chunk_size: int = 1024 * 1024) -> Iterator[str]:
    """Yield SQL statements, respecting quoted strings and backslash escapes."""
    buffer: list[str] = []
    in_quote = False
    escaped = False

    while True:
        chunk = handle.read(chunk_size)
        if not chunk:
            break

        for char in chunk:
            buffer.append(char)
            if escaped:
                escaped = False
                continue
            if char == "\\" and in_quote:
                escaped = True
                continue
            if char == "'":
                in_quote = not in_quote
                continue
            if char == ";" and not in_quote:
                statement = "".join(buffer).strip()
                buffer.clear()
                if statement:
                    yield statement

    remainder = "".join(buffer).strip()
    if remainder:
        yield remainder


def parse_comment_insert(statement: str) -> dict[str, str] | None:
    """Parse one INSERT statement from Comments.sql."""
    if not statement.startswith(_INSERT_PREFIX):
        return None

    values_marker = " VALUES "
    marker_index = statement.find(values_marker)
    if marker_index == -1:
        raise ValueError("Comment INSERT does not contain a VALUES clause.")

    values_text = statement[marker_index + len(values_marker) :].strip()
    if values_text.endswith(";"):
        values_text = values_text[:-1].rstrip()
    if not values_text.startswith("(") or not values_text.endswith(")"):
        raise ValueError("Comment INSERT has an invalid values tuple.")

    values = _split_sql_values(values_text[1:-1])
    if len(values) != 8:
        raise ValueError(f"Expected 8 comment values, found {len(values)}.")

    parsed = [_decode_sql_value(value) for value in values]
    return dict(zip(COMMENT_FIELDS, parsed))


def classify_comment_candidate(text: str) -> tuple[str, str]:
    """Assign a review stratum; this is not a ground-truth label."""
    for reason, pattern in _FRESHNESS_RULES:
        if pattern.search(text):
            return "freshness_confirmation", reason
    for reason, pattern in _TEMPORAL_RULES:
        if pattern.search(text):
            return "temporal_candidate", reason
    for reason, pattern in _INCORRECT_RULES:
        if pattern.search(text):
            return "incorrectness_candidate", reason
    for reason, pattern in _FAILURE_RULES:
        if pattern.search(text):
            return "failure_candidate", reason
    return "random_negative", "no_rule_match"


def prepare_comment_nlp_dataset(
    sql_path: str | Path,
    output_dir: str | Path,
    annotation_sample_size: int = 800,
    random_seed: int = 4055,
    write_all_comments: bool = True,
) -> dict[str, object]:
    """Parse Comments.sql and prepare candidate and annotation CSV files."""
    input_path = Path(sql_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    comments_path = output_path / "comments.csv"
    candidates_path = output_path / "candidate_comments.csv"
    annotations_path = output_path / "annotation_sample.csv"
    summary_path = output_path / "summary.json"

    rng = random.Random(random_seed)
    category_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    candidate_rows: list[dict[str, str]] = []
    random_reservoir: list[dict[str, str]] = []
    random_seen = 0
    parsed_rows = 0
    malformed_rows = 0
    source_non_null_labels = 0

    comments_handle = None
    comments_writer = None
    if write_all_comments:
        comments_handle = comments_path.open("w", encoding="utf-8", newline="")
        comments_writer = csv.DictWriter(comments_handle, fieldnames=COMMENT_FIELDS)
        comments_writer.writeheader()

    try:
        with input_path.open("r", encoding="utf-8", errors="replace") as sql_handle:
            for statement in iter_sql_statements(sql_handle):
                try:
                    row = parse_comment_insert(statement)
                except ValueError:
                    malformed_rows += 1
                    continue
                if row is None:
                    continue

                parsed_rows += 1
                if row["source_label"]:
                    source_non_null_labels += 1
                if comments_writer is not None:
                    comments_writer.writerow(row)

                category, reason = classify_comment_candidate(row["text"])
                category_counts[category] += 1
                reason_counts[reason] += 1
                review_row = _to_review_row(row, category, reason)

                if category != "random_negative":
                    candidate_rows.append(review_row)
                else:
                    random_seen += 1
                    _reservoir_add(
                        random_reservoir,
                        review_row,
                        annotation_sample_size,
                        random_seen,
                        rng,
                    )
    finally:
        if comments_handle is not None:
            comments_handle.close()

    _write_csv(candidates_path, candidate_rows, ANNOTATION_FIELDS)
    annotation_rows = _build_annotation_sample(
        candidate_rows=candidate_rows,
        random_rows=random_reservoir,
        sample_size=annotation_sample_size,
        rng=rng,
    )
    _write_csv(annotations_path, annotation_rows, ANNOTATION_FIELDS)

    summary: dict[str, object] = {
        "input_sql": str(input_path),
        "parsed_rows": parsed_rows,
        "malformed_rows": malformed_rows,
        "source_non_null_labels": source_non_null_labels,
        "category_counts": dict(sorted(category_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "candidate_rows": len(candidate_rows),
        "annotation_rows": len(annotation_rows),
        "random_seed": random_seed,
        "comments_csv": str(comments_path) if write_all_comments else None,
        "candidates_csv": str(candidates_path),
        "annotations_csv": str(annotations_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def build_annotation_files_from_rows(
    rows: Iterator[dict[str, str]],
    output_dir: str | Path,
    annotation_sample_size: int = 800,
    random_seed: int = 4055,
) -> dict[str, object]:
    """Create candidate and annotation files from database-style comment rows."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    candidates_path = output_path / "candidate_comments.csv"
    annotations_path = output_path / "annotation_sample.csv"
    summary_path = output_path / "summary.json"

    rng = random.Random(random_seed)
    category_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    candidate_rows: list[dict[str, str]] = []
    random_reservoir: list[dict[str, str]] = []
    random_seen = 0
    parsed_rows = 0

    for row in rows:
        parsed_rows += 1
        category, reason = classify_comment_candidate(row["text"])
        category_counts[category] += 1
        reason_counts[reason] += 1
        review_row = _to_review_row(row, category, reason)
        if category != "random_negative":
            candidate_rows.append(review_row)
        else:
            random_seen += 1
            _reservoir_add(
                random_reservoir,
                review_row,
                annotation_sample_size,
                random_seen,
                rng,
            )

    _write_csv(candidates_path, candidate_rows, ANNOTATION_FIELDS)
    annotation_rows = _build_annotation_sample(
        candidate_rows=candidate_rows,
        random_rows=random_reservoir,
        sample_size=annotation_sample_size,
        rng=rng,
    )
    _write_csv(annotations_path, annotation_rows, ANNOTATION_FIELDS)

    summary: dict[str, object] = {
        "source": "database",
        "parsed_rows": parsed_rows,
        "category_counts": dict(sorted(category_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "candidate_rows": len(candidate_rows),
        "annotation_rows": len(annotation_rows),
        "random_seed": random_seed,
        "candidates_csv": str(candidates_path),
        "annotations_csv": str(annotations_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _split_sql_values(values_text: str) -> list[str]:
    values: list[str] = []
    current: list[str] = []
    in_quote = False
    escaped = False

    for char in values_text:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\" and in_quote:
            current.append(char)
            escaped = True
            continue
        if char == "'":
            current.append(char)
            in_quote = not in_quote
            continue
        if char == "," and not in_quote:
            values.append("".join(current).strip())
            current.clear()
            continue
        current.append(char)

    values.append("".join(current).strip())
    return values


def _decode_sql_value(value: str) -> str:
    if value.lower() == "null":
        return ""
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return _decode_mysql_string(value[1:-1])
    return value


def _decode_mysql_string(value: str) -> str:
    escapes = {
        "0": "\0",
        "b": "\b",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "Z": "\x1a",
        "\\": "\\",
        "'": "'",
        '"': '"',
    }
    decoded: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            index += 1
            decoded.append(escapes.get(value[index], value[index]))
        else:
            decoded.append(char)
        index += 1
    return "".join(decoded)


def _to_review_row(
    row: dict[str, str],
    category: str,
    reason: str,
) -> dict[str, str]:
    return {
        "comment_id": row["comment_id"],
        "post_id": row["post_id"],
        "score": row["score"],
        "creation_date": row["creation_date"],
        "text": row["text"],
        "candidate_category": category,
        "candidate_reason": reason,
        "human_label": "",
        "review_notes": "",
    }


def _reservoir_add(
    reservoir: list[dict[str, str]],
    row: dict[str, str],
    capacity: int,
    seen: int,
    rng: random.Random,
) -> None:
    if len(reservoir) < capacity:
        reservoir.append(row)
        return
    replacement_index = rng.randrange(seen)
    if replacement_index < capacity:
        reservoir[replacement_index] = row


def _build_annotation_sample(
    candidate_rows: list[dict[str, str]],
    random_rows: list[dict[str, str]],
    sample_size: int,
    rng: random.Random,
) -> list[dict[str, str]]:
    rows_by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        rows_by_category[row["candidate_category"]].append(row)
    rows_by_category["random_negative"].extend(random_rows)

    categories = [
        "temporal_candidate",
        "freshness_confirmation",
        "incorrectness_candidate",
        "failure_candidate",
        "random_negative",
    ]
    target_per_category = max(sample_size // len(categories), 1)
    selected: list[dict[str, str]] = []
    leftovers: list[dict[str, str]] = []

    for category in categories:
        category_rows = rows_by_category.get(category, [])
        rng.shuffle(category_rows)
        selected.extend(category_rows[:target_per_category])
        leftovers.extend(category_rows[target_per_category:])

    if len(selected) < sample_size:
        rng.shuffle(leftovers)
        selected.extend(leftovers[: sample_size - len(selected)])

    rng.shuffle(selected)
    return selected[:sample_size]


def _write_csv(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
