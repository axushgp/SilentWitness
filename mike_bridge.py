from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from utils import REPORTS_DIR, html_to_text


@dataclass
class MikeResult:
    clauses: list[dict[str, str]]
    report_path: str | None
    source: str
    error: str | None = None


def _changed_pairs(diff_text: str) -> tuple[str, str]:
    before = "\n".join(line[1:].strip() for line in diff_text.splitlines() if line.startswith("-"))
    after = "\n".join(line[1:].strip() for line in diff_text.splitlines() if line.startswith("+"))
    return before[:3000], after[:3000]


def fallback_clauses(diff_text: str) -> list[dict[str, str]]:
    before, after = _changed_pairs(diff_text)
    implication = "The changed wording may materially alter user rights, data use, or service obligations."
    lowered = diff_text.lower()
    if "third-party" in lowered or "third party" in lowered or "share" in lowered:
        implication = "Data sharing language expanded; review consent, processor, and fiduciary obligations."
    if "fee" in lowered or "penalty" in lowered or "charge" in lowered:
        implication = "Financial liability language changed; check notice, consent, and opt-out paths."
    if "ai training" in lowered or "license" in lowered or "content" in lowered:
        implication = "User content or IP rights may be affected by the revised clause."
    return [
        {
            "clause": "Detected policy change",
            "before": before or "No removed wording detected.",
            "after": after or "No added wording detected.",
            "legal_implication": implication,
            "page_citation": "Policy snapshot diff",
        }
    ]


def _docx_xml(title: str, clauses: list[dict[str, str]]) -> str:
    lines = [title, "", "Clause Review"]
    for index, clause in enumerate(clauses, start=1):
        lines.extend(
            [
                "",
                f"{index}. {clause.get('clause', 'Clause')}",
                f"Before: {clause.get('before', '')}",
                f"After: {clause.get('after', '')}",
                f"Legal implication: {clause.get('legal_implication', clause.get('implication', ''))}",
                f"Citation: {clause.get('page_citation', clause.get('citation', 'Policy snapshot'))}",
            ]
        )
    paragraphs = "".join(
        f"<w:p><w:r><w:t>{escape(line)}</w:t></w:r></w:p>" for line in lines
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{paragraphs}<w:sectPr/></w:body>
</w:document>"""


def write_docx(title: str, clauses: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", _docx_xml(title, clauses))


def _post_json(url: str, payload: dict, timeout: int = 18) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _normalise_clauses(raw: object) -> list[dict[str, str]]:
    if isinstance(raw, dict):
        raw = raw.get("clauses") or raw.get("table") or raw.get("results") or []
    if not isinstance(raw, list):
        return []
    clauses: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        clauses.append(
            {
                "clause": str(item.get("clause") or item.get("clause_name") or "Clause"),
                "before": str(item.get("before") or item.get("before_text") or ""),
                "after": str(item.get("after") or item.get("after_text") or ""),
                "legal_implication": str(item.get("legal_implication") or item.get("implication") or ""),
                "page_citation": str(item.get("page_citation") or item.get("citation") or "Policy snapshot"),
            }
        )
    return clauses


def analyze_policy(service: str, current_path: str | None, diff_text: str) -> MikeResult:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{service}_{date.today().isoformat()}.docx"
    document = ""
    if current_path and Path(current_path).exists():
        document = html_to_text(Path(current_path).read_text(encoding="utf-8", errors="replace"))

    try:
        response = _post_json(
            "http://localhost:3001/api/analyze",
            {"document": document, "mode": "tabular_review", "service": service, "diff": diff_text},
        )
        clauses = _normalise_clauses(response) or fallback_clauses(diff_text)
        try:
            export = _post_json(
                "http://localhost:3001/api/export/docx",
                {"service": service, "clauses": clauses},
            )
            maybe_path = export.get("path") or export.get("docx_path")
            if maybe_path:
                return MikeResult(clauses, str(maybe_path), "mike")
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        write_docx(f"Silent Witness Mike Review - {service}", clauses, report_path)
        return MikeResult(clauses, str(report_path), "mike")
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        clauses = fallback_clauses(diff_text)
        write_docx(f"Silent Witness Local Legal Review - {service}", clauses, report_path)
        return MikeResult(clauses, str(report_path), "local-fallback", str(exc))


def analyze_contract_text(filename: str, text: str) -> MikeResult:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(filename).stem).strip("-") or "contract"
    report_path = REPORTS_DIR / f"contract_{safe_name}_{date.today().isoformat()}.docx"
    diff_text = "\n".join(f"+{line}" for line in text.splitlines()[:80] if line.strip())
    try:
        response = _post_json(
            "http://localhost:3001/api/analyze",
            {"document": text[:12000], "mode": "contract_review", "service": filename},
        )
        clauses = _normalise_clauses(response) or fallback_clauses(diff_text)
        write_docx(f"Silent Witness Contract Review - {filename}", clauses, report_path)
        return MikeResult(clauses, str(report_path), "mike")
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        clauses = fallback_clauses(diff_text)
        write_docx(f"Silent Witness Local Contract Review - {filename}", clauses, report_path)
        return MikeResult(clauses, str(report_path), "local-fallback", str(exc))
