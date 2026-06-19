"""Minimal helpers for calling a local Ollama HTTP endpoint."""

from __future__ import annotations

import json
import urllib.request


def run_ollama_json(
    model: str,
    prompt: str,
    ollama_host: str,
) -> dict[str, object]:
    """Call the local Ollama HTTP API and parse the JSON response."""
    url = ollama_host.rstrip("/") + "/api/generate"
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": 0.0,
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if "response" not in payload:
        raise ValueError(f"Unexpected Ollama HTTP payload: {payload!r}")
    return _normalize_response(payload)


def _normalize_response(payload: object) -> dict[str, object]:
    """Normalize the Ollama HTTP payload into the expected label schema."""
    if isinstance(payload, dict):
        if "label" in payload:
            return payload
        if "response" in payload:
            inner = payload["response"]
            if isinstance(inner, str):
                if not inner.strip():
                    raise ValueError(f"Empty Ollama response field: {payload!r}")
                return _normalize_response(json.loads(inner))
            if isinstance(inner, dict):
                return _normalize_response(inner)
    raise ValueError(f"Unexpected Ollama payload shape: {payload!r}")
