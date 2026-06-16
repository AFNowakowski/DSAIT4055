"""Synthetic demo data for the baseline detector."""

from __future__ import annotations

import pandas as pd


def make_demo_detector_dataset() -> pd.DataFrame:
    """Return a small labeled dataset for smoke-testing the detector."""
    rows = [
        {
            "answer_body": "Use Python 2.7 and this 2013 library version. The old API endpoint is enough.",
            "is_deprecated": 1,
        },
        {
            "answer_body": "This worked in 2012. Install package v1 and edit the XML config manually.",
            "is_deprecated": 1,
        },
        {
            "answer_body": "Deprecated solution for Android KitKat using an old support library.",
            "is_deprecated": 1,
        },
        {
            "answer_body": "For 2015 use this jQuery plugin and a legacy callback URL.",
            "is_deprecated": 1,
        },
        {
            "answer_body": "Old Java 8 workaround with a broken download link and manual patch step.",
            "is_deprecated": 1,
        },
        {
            "answer_body": "Legacy answer: rely on Python 2, outdated docs, and a discontinued package mirror.",
            "is_deprecated": 1,
        },
        {
            "answer_body": "Use the current Python 3.12 client, maintained docs, and the latest API method.",
            "is_deprecated": 0,
        },
        {
            "answer_body": "Modern answer with a stable REST endpoint, tested dependency versions, and updated steps.",
            "is_deprecated": 0,
        },
        {
            "answer_body": "Recommended approach: official package, current syntax, and actively maintained tooling.",
            "is_deprecated": 0,
        },
        {
            "answer_body": "Use the new SDK, current authentication flow, and recent documentation examples.",
            "is_deprecated": 0,
        },
        {
            "answer_body": "This answer uses the latest package manager command and current framework settings.",
            "is_deprecated": 0,
        },
        {
            "answer_body": "Up-to-date solution with the maintained library and a tested deployment command.",
            "is_deprecated": 0,
        },
    ]
    return pd.DataFrame(rows)
