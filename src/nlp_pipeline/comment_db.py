"""Database helpers for the final comment-level obsolescence pipeline."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterator

import pymysql


def load_env_file(path: str | Path) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def connect_comment_db(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
):
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def iter_comment_rows(
    connection,
    batch_size: int = 5000,
    only_unclassified: bool = False,
    answer_comments_only: bool = True,
) -> Iterator[dict[str, str]]:
    """Yield database comments in batches, optionally limited to answers."""
    last_id = 0
    while True:
        rows = _fetch_comment_batch(
            connection=connection,
            last_id=last_id,
            batch_size=batch_size,
            only_unclassified=only_unclassified,
            answer_comments_only=answer_comments_only,
        )
        if not rows:
            break
        for row in rows:
            last_id = max(last_id, int(row["comment_id"]))
            yield row


def apply_ollama_labels_to_db(
    connection,
    labels_csv_path: str | Path,
    positive_label: str = "temporal_obsolescence",
    answer_comments_only: bool = True,
    set_unmatched_zero: bool = True,
    overwrite_existing: bool = True,
) -> dict[str, int | str | None]:
    """Update hl_IndicatedDeprecation from a labeled candidate CSV."""
    label_rows = _read_csv(labels_csv_path)
    label_map = {
        row["comment_id"]: 1 if row.get("ollama_label", "").strip() == positive_label else 0
        for row in label_rows
        if row.get("comment_id")
    }

    update_zero_count = 0
    if set_unmatched_zero:
        update_zero_count = _set_comments_to_zero(
            connection=connection,
            answer_comments_only=answer_comments_only,
            overwrite_existing=overwrite_existing,
        )

    matched_updates = 0
    matched_positive = 0
    with connection.cursor() as cursor:
        for comment_id, prediction in label_map.items():
            where_parts = ["Id = %s"]
            params: list[object] = [prediction, comment_id]
            if not overwrite_existing:
                where_parts.append("hl_IndicatedDeprecation IS NULL")
            sql = (
                "UPDATE Comments SET hl_IndicatedDeprecation = %s "
                f"WHERE {' AND '.join(where_parts)}"
            )
            matched_updates += cursor.execute(sql, params)
            matched_positive += prediction
    connection.commit()

    return {
        "labels_csv": str(labels_csv_path),
        "matched_label_rows": len(label_map),
        "matched_updates": matched_updates,
        "matched_positive": matched_positive,
        "matched_negative": len(label_map) - matched_positive,
        "set_unmatched_zero": set_unmatched_zero,
        "zero_update_rows": update_zero_count,
        "positive_label": positive_label,
    }


def _fetch_comment_batch(
    connection,
    last_id: int,
    batch_size: int,
    only_unclassified: bool,
    answer_comments_only: bool,
) -> list[dict[str, str]]:
    where_parts = ["c.Id > %s"]
    params: list[object] = [last_id]
    join_clause = ""

    if answer_comments_only:
        join_clause = "JOIN Posts p ON p.Id = c.PostId"
        where_parts.append("p.PostTypeId = 2")
    if only_unclassified:
        where_parts.append("c.hl_IndicatedDeprecation IS NULL")

    query = f"""
        SELECT
            c.Id AS comment_id,
            c.PostId AS post_id,
            c.Score AS score,
            c.Text AS text,
            DATE_FORMAT(c.CreationDate, '%%Y-%%m-%%d %%H:%%i:%%s') AS creation_date,
            COALESCE(c.UserDisplayName, '') AS user_display_name,
            COALESCE(CAST(c.UserId AS CHAR), '') AS user_id,
            COALESCE(CAST(c.hl_IndicatedDeprecation AS CHAR), '') AS source_label
        FROM Comments c
        {join_clause}
        WHERE {' AND '.join(where_parts)}
        ORDER BY c.Id
        LIMIT %s
    """
    params.append(batch_size)
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    return [{key: str(value) for key, value in row.items()} for row in rows]


def _set_comments_to_zero(
    connection,
    answer_comments_only: bool,
    overwrite_existing: bool,
) -> int:
    where_parts = []
    join_clause = ""
    if answer_comments_only:
        join_clause = "JOIN Posts p ON p.Id = c.PostId"
        where_parts.append("p.PostTypeId = 2")
    if not overwrite_existing:
        where_parts.append("c.hl_IndicatedDeprecation IS NULL")

    sql = "UPDATE Comments c "
    if join_clause:
        sql += join_clause + " "
    sql += "SET c.hl_IndicatedDeprecation = 0"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)

    with connection.cursor() as cursor:
        updated = cursor.execute(sql)
    connection.commit()
    return updated


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
