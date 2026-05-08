from __future__ import annotations

import re
import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class Classification:
    severity: str
    summary: str
    deadline: str | None = None
    source: str = "heuristic"


CRITICAL = {
    "third party",
    "third-party",
    "sell",
    "share",
    "penalty",
    "fine",
    "arbitration",
    "ownership",
    "license",
    "ai training",
    "biometric",
    "surveillance",
    "deadline",
}

MODERATE = {
    "renew",
    "price",
    "fee",
    "terminate",
    "suspend",
    "modify",
    "retention",
    "delete",
    "consent",
}


def _deadline(text: str) -> str | None:
    match = re.search(
        r"\b(?:by|before|until|effective)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        text,
        flags=re.I,
    )
    return match.group(1) if match else None


def _classify_with_ollama(diff_text: str) -> Classification | None:
    prompt = f"""
You are Silent Witness, a legal policy-change classifier.
Classify this unified diff as CRITICAL, MODERATE, LOW, or NO_CHANGE.
Return strict JSON only with keys severity, summary, deadline.

Rubric:
CRITICAL: new third-party data sharing, fees/penalties, IP ownership/license changes,
arbitration, opt-out deadline, surveillance expansion.
MODERATE: auto-renewal, price changes, termination rights, retention, consent wording.
LOW: typos, formatting, minor clarifications.

Diff:
{diff_text[:6000]}
"""
    payload = json.dumps(
        {
            "model": "llama3.2:1b",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    try:
        request = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=18) as response:
            raw = json.loads(response.read().decode("utf-8"))
        parsed = json.loads(raw.get("response", "{}"))
        severity = str(parsed.get("severity", "LOW")).upper()
        if severity not in {"CRITICAL", "MODERATE", "LOW", "NO_CHANGE"}:
            return None
        return Classification(
            severity=severity,
            summary=str(parsed.get("summary") or "Policy wording changed."),
            deadline=parsed.get("deadline") or _deadline(diff_text),
            source="ollama",
        )
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None


def classify(diff_text: str, use_ollama: bool = True) -> Classification:
    if use_ollama:
        ollama_result = _classify_with_ollama(diff_text)
        if ollama_result:
            return ollama_result

    lowered = diff_text.lower()
    severity = "LOW"
    if any(term in lowered for term in CRITICAL):
        severity = "CRITICAL"
    elif any(term in lowered for term in MODERATE):
        severity = "MODERATE"
    elif not diff_text.strip():
        severity = "NO_CHANGE"

    added = [line[1:].strip() for line in diff_text.splitlines() if line.startswith("+")]
    removed = [line[1:].strip() for line in diff_text.splitlines() if line.startswith("-")]
    if added:
        summary = f"Policy wording added or changed around: {added[0][:180]}"
    elif removed:
        summary = f"Policy wording was removed around: {removed[0][:180]}"
    else:
        summary = "No meaningful policy wording changed."

    return Classification(severity=severity, summary=summary, deadline=_deadline(diff_text))
