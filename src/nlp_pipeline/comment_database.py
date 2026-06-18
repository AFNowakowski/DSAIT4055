"""Database integration for comment-obsolescence predictions."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


SELECT_UNCLASSIFIED_SQL = """
SELECT Id, PostId, Score, Text, CreationDate
FROM Comments
WHERE hl_IndicatedDeprecation IS NULL
  AND Id > %s
ORDER BY Id
LIMIT %s
"""

UPDATE_PREDICTION_SQL = """
UPDATE Comments
SET hl_IndicatedDeprecation = %s
WHERE Id = %s
  AND hl_IndicatedDeprecation IS NULL
"""


def iter_unclassified_comment_batches(
    connection: Any,
    batch_size: int = 5000,
    limit: int | None = None,
) -> Iterator[list[dict[str, Any]]]:
    """Yield unclassified comments with keyset pagination."""
    last_id = 0
    emitted = 0

    while limit is None or emitted < limit:
        current_batch_size = batch_size
        if limit is not None:
            current_batch_size = min(batch_size, limit - emitted)
        if current_batch_size <= 0:
            break

        with connection.cursor() as cursor:
            cursor.execute(SELECT_UNCLASSIFIED_SQL, (last_id, current_batch_size))
            rows = cursor.fetchall()
        if not rows:
            break

        normalized_rows = [
            {
                "comment_id": int(row["Id"]),
                "post_id": int(row["PostId"]),
                "score": int(row["Score"]),
                "text": row["Text"] or "",
                "creation_date": str(row["CreationDate"]),
                "source_label": "",
            }
            for row in rows
        ]
        yield normalized_rows

        emitted += len(normalized_rows)
        last_id = normalized_rows[-1]["comment_id"]


def predict_comment_batch(
    model: Any,
    rows: list[dict[str, Any]],
    threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Return binary predictions and positive-class probabilities."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1.")

    texts = [row["text"] for row in rows]
    probabilities = model.predict_proba(texts)
    predictions: list[dict[str, Any]] = []
    for row, probability_pair in zip(rows, probabilities):
        positive_probability = float(probability_pair[1])
        predictions.append(
            {
                **row,
                "prediction": int(positive_probability >= threshold),
                "positive_probability": positive_probability,
            }
        )
    return predictions


def apply_comment_predictions(
    connection: Any,
    predictions: list[dict[str, Any]],
) -> int:
    """Write predictions while preserving rows classified by another process."""
    parameters = [
        (row["prediction"], row["comment_id"])
        for row in predictions
    ]
    with connection.cursor() as cursor:
        cursor.executemany(UPDATE_PREDICTION_SQL, parameters)
        updated_rows = cursor.rowcount
    connection.commit()
    return int(updated_rows)
