"""Weak-supervision bootstrap for comment-obsolescence ranking."""

from __future__ import annotations

import csv
import heapq
import json
import random
import re
from pathlib import Path
from typing import Iterator

import joblib
import pandas as pd

from .comment_classifier import build_comment_classifier


_STRONG_TEMPORAL_PATTERNS = [
    (
        "temporal_state_change",
        re.compile(
            r"\b(?:this|that|the|your)?\s*"
            r"(?:answer|method|function|api|approach|solution|code|syntax|option|"
            r"property|module|library|package|command|feature|class)\s+"
            r"(?:is|was|has been|became)\s+(?:now\s+)?"
            r"(?:deprecated|outdated|obsolete)\b",
            re.I,
        ),
    ),
    (
        "temporal_version_marker",
        re.compile(
            r"\b(?:deprecated|outdated|obsolete|removed)\b.{0,60}"
            r"\b(?:in|since|from|as of|after)\s+"
            r"(?:version\s+|v\.?\s*)?\d+(?:\.\d+){0,2}\b",
            re.I,
        ),
    ),
    (
        "no_longer_supported",
        re.compile(
            r"\bno longer\s+(?:works?|supported|available|valid|recommended|"
            r"exists?|used|needed)\b",
            re.I,
        ),
    ),
    (
        "removed_since_version",
        re.compile(
            r"\b(?:was|were|has been|is|are)?\s*removed\s+"
            r"(?:"
            r"(?:in|since|as of)\s+(?:version\s+|v\.?\s*)?\d+"
            r"|from\s+(?:the\s+)?(?:api|language|library|package|framework|"
            r"current\s+(?:version|release|branch)|latest\s+(?:version|release)|"
            r"master\s+branch)"
            r")\b",
            re.I,
        ),
    ),
    (
        "version_replacement",
        re.compile(
            r"\b(?:since|as of|starting (?:with|from)|in)\s+"
            r"(?:version|v\.?)?\s*\d+(?:\.\d+){0,2}.+"
            r"\b(?:use|replace|renamed|removed|deprecated)\b",
            re.I,
        ),
    ),
]

_STRONG_NEGATIVE_PATTERNS = [
    (
        "external_resource_unavailable",
        re.compile(
            r"\b(?:link|page|video|website|site|url|fiddle|codepen)\b.{0,40}"
            r"\b(?:no longer\s+(?:works?|available|exists?|active|valid)|"
            r"is\s+(?:dead|broken)|returns?\s+404)\b",
            re.I,
        ),
    ),
    (
        "explicit_freshness",
        re.compile(
            r"\b(?:is|are|was|were|it'?s)\s+not\s+deprecated\b|"
            r"\bstill\s+(?:works?|supported|valid|available)\b|"
            r"\bworks?\s+(?:fine\s+)?in\s+20\d{2}\b",
            re.I,
        ),
    ),
    (
        "original_incorrectness",
        re.compile(
            r"\b(?:this|that|the answer|your answer|it)\s+"
            r"(?:is|was)\s+(?:simply\s+)?(?:incorrect|wrong)\b",
            re.I,
        ),
    ),
]


def weak_supervision_label(text: str) -> tuple[int | None, str, float]:
    """Return a provisional label, reason, and training weight."""
    for reason, pattern in _STRONG_NEGATIVE_PATTERNS:
        if pattern.search(text):
            return 0, reason, 1.0
    for reason, pattern in _STRONG_TEMPORAL_PATTERNS:
        if pattern.search(text):
            return 1, reason, 1.0
    return None, "abstain", 0.0


def bootstrap_comment_model(
    rows: Iterator[dict[str, str]],
    output_dir: str | Path,
    random_negative_size: int = 5000,
    random_negative_weight: float = 0.2,
    random_seed: int = 4055,
) -> dict[str, object]:
    """Train a provisional ranker from rules and low-weight unlabeled examples."""
    if not 0.0 < random_negative_weight <= 1.0:
        raise ValueError("random_negative_weight must be between 0 and 1.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    seed_path = output_path / "bootstrap_training_seeds.csv"
    model_path = output_path / "bootstrap_comment_classifier.joblib"
    metadata_path = output_path / "bootstrap_metadata.json"

    rng = random.Random(random_seed)
    strong_rows: list[dict[str, object]] = []
    random_rows: list[dict[str, object]] = []
    abstained_seen = 0
    total_rows = 0

    for row in rows:
        total_rows += 1
        label, reason, weight = weak_supervision_label(row["text"])
        training_row = {
            "comment_id": row["comment_id"],
            "post_id": row["post_id"],
            "text": row["text"],
            "weak_label": label,
            "weak_reason": reason,
            "sample_weight": weight,
        }
        if label is not None:
            strong_rows.append(training_row)
            continue

        abstained_seen += 1
        training_row["weak_label"] = 0
        training_row["weak_reason"] = "unlabeled_as_background"
        training_row["sample_weight"] = random_negative_weight
        _reservoir_add(
            random_rows,
            training_row,
            random_negative_size,
            abstained_seen,
            rng,
        )

    training_rows = strong_rows + random_rows
    positive_count = sum(row["weak_label"] == 1 for row in training_rows)
    negative_count = sum(row["weak_label"] == 0 for row in training_rows)
    if positive_count == 0 or negative_count == 0:
        raise ValueError("Bootstrap training requires provisional examples of both classes.")

    training_df = pd.DataFrame(training_rows)
    model = build_comment_classifier()
    model.fit(
        training_df["text"],
        training_df["weak_label"].astype(int),
        classifier__sample_weight=training_df["sample_weight"].astype(float),
    )
    joblib.dump(model, model_path)
    _write_csv(seed_path, training_rows)

    metadata: dict[str, object] = {
        "model_type": "weak_supervision_bootstrap_ranker",
        "validated": False,
        "intended_use": "ranking comments for later human review",
        "must_not_update_final_database_label": True,
        "source_rows": total_rows,
        "strong_positive_seeds": positive_count,
        "negative_seeds": negative_count,
        "random_background_seeds": len(random_rows),
        "random_background_weight": random_negative_weight,
        "model_path": str(model_path),
        "training_seeds_csv": str(seed_path),
        "random_seed": random_seed,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def score_comments_with_bootstrap(
    rows: Iterator[dict[str, str]],
    model_path: str | Path,
    output_dir: str | Path,
    batch_size: int = 5000,
    review_per_group: int = 200,
) -> dict[str, object]:
    """Score comments and create positive, uncertain, and expansion review queues."""
    model = joblib.load(model_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    scores_path = output_path / "bootstrap_scores.csv"
    review_path = output_path / "bootstrap_review_queue.csv"

    top_positive: list[tuple[float, int, dict[str, object]]] = []
    top_uncertain: list[tuple[float, int, dict[str, object]]] = []
    top_expansion: list[tuple[float, int, dict[str, object]]] = []
    processed = 0
    predicted_positive = 0
    batch: list[dict[str, str]] = []

    with scores_path.open("w", encoding="utf-8", newline="") as score_handle:
        fieldnames = [
            "comment_id",
            "post_id",
            "bootstrap_score",
            "weak_seed_label",
            "weak_seed_reason",
        ]
        writer = csv.DictWriter(score_handle, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                batch_stats = _score_batch(
                    model,
                    batch,
                    writer,
                    top_positive,
                    top_uncertain,
                    top_expansion,
                    review_per_group,
                )
                processed += batch_stats["processed"]
                predicted_positive += batch_stats["predicted_positive"]
                batch.clear()

        if batch:
            batch_stats = _score_batch(
                model,
                batch,
                writer,
                top_positive,
                top_uncertain,
                top_expansion,
                review_per_group,
            )
            processed += batch_stats["processed"]
            predicted_positive += batch_stats["predicted_positive"]

    review_rows = _select_unique_review_rows(
        [
            ("high_score_rule_abstained", top_expansion),
            ("most_uncertain", top_uncertain),
            ("highest_score", top_positive),
        ],
        review_per_group,
    )
    review_rows.sort(key=lambda row: (row["review_group"], -row["bootstrap_score"]))
    _write_csv(review_path, review_rows)

    return {
        "processed_rows": processed,
        "score_above_0_5": predicted_positive,
        "scores_csv": str(scores_path),
        "review_queue_csv": str(review_path),
        "review_rows": len(review_rows),
    }


def _score_batch(
    model: object,
    rows: list[dict[str, str]],
    writer: csv.DictWriter,
    top_positive: list[tuple[float, int, dict[str, object]]],
    top_uncertain: list[tuple[float, int, dict[str, object]]],
    top_expansion: list[tuple[float, int, dict[str, object]]],
    capacity: int,
) -> dict[str, int]:
    probabilities = model.predict_proba([row["text"] for row in rows])
    predicted_positive = 0

    for row, probability_pair in zip(rows, probabilities):
        score = float(probability_pair[1])
        label, reason, _ = weak_supervision_label(row["text"])
        predicted_positive += int(score >= 0.5)
        writer.writerow(
            {
                "comment_id": row["comment_id"],
                "post_id": row["post_id"],
                "bootstrap_score": round(score, 8),
                "weak_seed_label": "" if label is None else label,
                "weak_seed_reason": reason,
            }
        )
        review_row: dict[str, object] = {
            "comment_id": row["comment_id"],
            "post_id": row["post_id"],
            "score": row.get("score", ""),
            "creation_date": row.get("creation_date", ""),
            "text": row["text"],
            "bootstrap_score": score,
            "weak_seed_label": "" if label is None else label,
            "weak_seed_reason": reason,
            "human_label": "",
            "review_notes": "",
        }
        comment_id = int(row["comment_id"])
        heap_capacity = capacity * 3
        _bounded_heap_add(top_positive, score, comment_id, review_row, heap_capacity)
        _bounded_heap_add(
            top_uncertain,
            -abs(score - 0.5),
            comment_id,
            review_row,
            heap_capacity,
        )
        if label is None:
            _bounded_heap_add(
                top_expansion,
                score,
                comment_id,
                review_row,
                heap_capacity,
            )

    return {"processed": len(rows), "predicted_positive": predicted_positive}


def _bounded_heap_add(
    heap: list[tuple[float, int, dict[str, object]]],
    priority: float,
    comment_id: int,
    row: dict[str, object],
    capacity: int,
) -> None:
    item = (priority, comment_id, row)
    if len(heap) < capacity:
        heapq.heappush(heap, item)
    elif item[:2] > heap[0][:2]:
        heapq.heapreplace(heap, item)


def _heap_rows(
    heap: list[tuple[float, int, dict[str, object]]],
    review_group: str,
) -> list[dict[str, object]]:
    rows = []
    for _, _, row in sorted(heap, reverse=True):
        rows.append({"review_group": review_group, **row})
    return rows


def _select_unique_review_rows(
    groups: list[tuple[str, list[tuple[float, int, dict[str, object]]]]],
    per_group: int,
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    selected_ids: set[str] = set()
    for review_group, heap in groups:
        group_count = 0
        for row in _heap_rows(heap, review_group):
            comment_id = str(row["comment_id"])
            if comment_id in selected_ids:
                continue
            selected.append(row)
            selected_ids.add(comment_id)
            group_count += 1
            if group_count >= per_group:
                break
    return selected


def _reservoir_add(
    reservoir: list[dict[str, object]],
    row: dict[str, object],
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


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
