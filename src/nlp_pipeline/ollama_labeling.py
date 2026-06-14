"""Local Ollama-based labeling helpers for answer outdatedness."""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path


SYSTEM_PROMPT = """You label Stack Exchange answers for likely outdatedness or supersession.
Return only valid JSON with keys:
- "label": 1 if the answer is likely outdated, superseded, obsolete, or no longer the best answer; otherwise 0
- "confidence": a float between 0 and 1
- "reason": a short snake_case reason
- "explanation": one short sentence
Rules:
- Older non-accepted answers that recommend legacy or obsolete approaches should usually be labeled 1.
- Current accepted answers should usually be labeled 0 unless the text itself clearly says it is outdated.
- Do not return markdown fences or any extra text.
- Return one compact JSON object only."""


_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def label_answers_with_ollama(
    input_csv_path: str | Path,
    output_csv_path: str | Path,
    model: str,
    limit: int | None = None,
    only_unaccepted: bool = True,
    ollama_executable: str | None = None,
    verbose: bool = False,
    ollama_host: str = "http://127.0.0.1:11434",
) -> dict[str, int | str]:
    """
    Label answers with a local Ollama model.

    Expected input columns:
    - question_title
    - question_body
    - answer_body
    - answer_id
    - question_id
    - is_accepted_snapshot (optional)
    """
    rows = _read_csv(input_csv_path)
    selected_rows = []
    for row in rows:
        if only_unaccepted and row.get("is_accepted_snapshot") == "1":
            continue
        selected_rows.append(row)
        if limit is not None and len(selected_rows) >= limit:
            break

    output_rows: list[dict[str, str]] = []
    output_path = Path(output_csv_path)
    executable = resolve_ollama_executable(ollama_executable) if ollama_executable else None
    total = len(selected_rows)
    if verbose:
        if executable:
            print(f"Using Ollama executable: {executable}")
        print(f"Using Ollama host: {ollama_host}")
        print(f"Selected rows for labeling: {total}")

    for index, row in enumerate(selected_rows, start=1):
        if verbose:
            print(
                f"[{index}/{total}] Labeling answer_id={row.get('answer_id', '')} "
                f"question_id={row.get('question_id', '')}"
            )
        prompt = build_label_prompt(row)
        try:
            response = run_ollama_json(
                model=model,
                prompt=prompt,
                ollama_executable=executable,
                ollama_host=ollama_host,
            )
        except Exception as exc:
            if verbose:
                print(f"[{index}/{total}] -> parse_error={type(exc).__name__}: {exc}")
            fallback_prompt = build_fallback_prompt(row)
            response = run_ollama_json(
                model=model,
                prompt=fallback_prompt,
                ollama_executable=executable,
                ollama_host=ollama_host,
            )

        output_rows.append(_build_output_row(row, response))
        _write_csv(
            output_path,
            output_rows,
            [
                "question_id",
                "answer_id",
                "is_accepted_snapshot",
                "heuristic_label",
                "ollama_label",
                "ollama_confidence",
                "ollama_reason",
                "ollama_explanation",
                "question_title",
                "answer_body",
            ],
        )
        if verbose:
            print(
                f"[{index}/{total}] -> label={response.get('label', '')} "
                f"confidence={response.get('confidence', '')} "
                f"reason={response.get('reason', '')}"
            )

    return {
        "output_csv": str(output_path),
        "labeled_rows": len(output_rows),
    }


def build_label_prompt(row: dict[str, str]) -> str:
    """Build the annotation prompt for a single answer."""
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Question title:\n{row.get('question_title', '').strip()}\n\n"
        f"Question body:\n{row.get('question_body', '').strip()}\n\n"
        f"Answer body:\n{row.get('answer_body', '').strip()}\n\n"
        f"Current accepted snapshot flag: {row.get('is_accepted_snapshot', '')}\n"
    )


def build_fallback_prompt(row: dict[str, str]) -> str:
    """Build a shorter fallback prompt if the richer one fails to parse cleanly."""
    return (
        "Return only JSON with keys label, confidence, reason, explanation. "
        "Label 1 for likely outdated or superseded, otherwise 0.\n\n"
        f"Question title: {row.get('question_title', '').strip()}\n"
        f"Answer body: {row.get('answer_body', '').strip()[:1200]}\n"
        f"Accepted flag: {row.get('is_accepted_snapshot', '')}\n"
    )


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


def _extract_json_object(text: str) -> str:
    text = _strip_terminal_noise(text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Ollama response did not contain JSON: {text[:200]}")
    return text[start : end + 1]


def _sanitize_json_text(text: str) -> str:
    """Remove raw control characters that sometimes appear in model output."""
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


def _build_output_row(row: dict[str, str], response: dict[str, object]) -> dict[str, str]:
    return {
        "question_id": row.get("question_id", ""),
        "answer_id": row.get("answer_id", ""),
        "is_accepted_snapshot": row.get("is_accepted_snapshot", ""),
        "heuristic_label": row.get("weak_label", ""),
        "ollama_label": str(response.get("label", "")),
        "ollama_confidence": str(response.get("confidence", "")),
        "ollama_reason": str(response.get("reason", "")),
        "ollama_explanation": str(response.get("explanation", "")),
        "question_title": row.get("question_title", ""),
        "answer_body": row.get("answer_body", ""),
    }


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


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(
    path: str | Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
