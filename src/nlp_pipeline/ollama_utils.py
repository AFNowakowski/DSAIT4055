"""Shared helpers for calling a local Ollama model and parsing JSON output."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path


_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def run_ollama_json(
    model: str,
    prompt: str,
    ollama_executable: str | None,
    ollama_host: str,
) -> dict[str, object]:
    """Run a local Ollama model and parse a JSON-only response."""
    try:
        return run_ollama_via_http(
            model=model,
            prompt=prompt,
            ollama_host=ollama_host,
        )
    except Exception:
        if not ollama_executable:
            raise
        return run_ollama_via_cli(
            model=model,
            prompt=prompt,
            ollama_executable=ollama_executable,
        )


def run_ollama_via_http(
    model: str,
    prompt: str,
    ollama_host: str,
) -> dict[str, object]:
    """Call the local Ollama HTTP API for cleaner structured output."""
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


def run_ollama_via_cli(
    model: str,
    prompt: str,
    ollama_executable: str,
) -> dict[str, object]:
    """Fallback CLI execution path if the HTTP API is unavailable."""
    command = [
        ollama_executable,
        "run",
        model,
        "--format",
        "json",
        "--hidethinking",
        "--nowordwrap",
        prompt,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    content = completed.stdout.strip() or completed.stderr.strip()
    payload = _extract_json_object(content)
    return _normalize_response(json.loads(_sanitize_json_text(payload)))


def resolve_ollama_executable(explicit_path: str | None = None) -> str:
    """Resolve the local Ollama executable path on Windows-friendly defaults."""
    candidates = []
    if explicit_path:
        candidates.append(explicit_path)

    which_result = shutil.which("ollama")
    if which_result:
        candidates.append(which_result)

    candidates.append(r"C:\Users\anton\AppData\Local\Programs\Ollama\ollama.exe")

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    raise FileNotFoundError(
        "Could not find ollama executable. Pass --ollama-exe with the full path."
    )


def _extract_json_object(text: str) -> str:
    text = _strip_terminal_noise(text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Ollama response did not contain JSON: {text[:200]}")
    return text[start : end + 1]


def _sanitize_json_text(text: str) -> str:
    sanitized = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return sanitized


def _strip_terminal_noise(text: str) -> str:
    cleaned = _ANSI_ESCAPE_RE.sub("", text)
    cleaned = cleaned.replace("```json", "").replace("```", "")
    return cleaned.strip()


def _normalize_response(payload: object) -> dict[str, object]:
    """Normalize Ollama JSON output into the expected label schema."""
    if isinstance(payload, dict):
        if "label" in payload:
            return payload
        if "thinking" in payload and isinstance(payload["thinking"], str):
            inner = payload["thinking"]
            if inner.strip():
                extracted = _extract_json_object(inner)
                return _normalize_response(json.loads(_sanitize_json_text(extracted)))
        if "response" in payload:
            inner = payload["response"]
            if isinstance(inner, str):
                if not inner.strip():
                    raise ValueError(f"Empty Ollama response field: {payload!r}")
                extracted = _extract_json_object(inner)
                return _normalize_response(json.loads(_sanitize_json_text(extracted)))
            if isinstance(inner, dict):
                return _normalize_response(inner)
    raise ValueError(f"Unexpected Ollama payload shape: {payload!r}")
