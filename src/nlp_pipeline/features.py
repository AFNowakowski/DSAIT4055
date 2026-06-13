"""Feature extraction for answer text."""

from __future__ import annotations

import re

import pandas as pd

from .preprocessing import normalize_text


_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_URL_RE = re.compile(r"https?://")
_CODE_FENCE_RE = re.compile(r"```|<code>|</code>")


def build_text_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create simple, interpretable answer-text features."""
    features = df.copy()
    normalized = features["answer_body"].fillna("").map(normalize_text)

    features["answer_char_count"] = normalized.str.len()
    features["answer_word_count"] = normalized.str.split().str.len()
    features["has_year"] = normalized.str.contains(_YEAR_RE, regex=True).astype(int)
    features["url_count"] = normalized.str.count(_URL_RE)
    features["code_marker_count"] = features["answer_body"].fillna("").str.count(
        _CODE_FENCE_RE
    )

    return features
