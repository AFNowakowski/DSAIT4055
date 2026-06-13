"""Basic text preprocessing helpers."""

from __future__ import annotations

import re


_MULTISPACE_RE = re.compile(r"\s+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def normalize_text(text: str) -> str:
    """Return a lightly normalized text representation."""
    if not isinstance(text, str):
        return ""

    text = _HTML_TAG_RE.sub(" ", text)
    text = _MULTISPACE_RE.sub(" ", text)
    return text.strip().lower()
