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
    
    # Enhanced analysis with more specific implications
    risk_score = 8  # default
    severity = "LOW"
    
    if any(term in lowered for term in ["third-party", "third party", "share", "transfer", "sell data"]):
        implication = "Data sharing language expanded; review consent, processor, and fiduciary obligations."
        risk_score = 16
        severity = "HIGH"
    elif any(term in lowered for term in ["fee", "penalty", "charge", "fine", "cost"]):
        implication = "Financial liability language changed; check notice, consent, and opt-out paths."
        risk_score = 15
        severity = "HIGH"
    elif any(term in lowered for term in ["ai training", "license", "content", "ip", "intellectual property"]):
        implication = "User content or IP rights may be affected by the revised clause."
        risk_score = 14
        severity = "MEDIUM"
    elif any(term in lowered for term in ["privacy", "gdpr", "data protection", "consent"]):
        implication = "Privacy or data protection terms modified; verify compliance with regulations."
        risk_score = 13
        severity = "MEDIUM"
    elif any(term in lowered for term in ["terminate", "termination", "cancel", "delete account"]):
        implication = "Account termination or service access terms changed."
        risk_score = 12
        severity = "MEDIUM"
    elif any(term in lowered for term in ["liability", "responsibility", "disclaimer"]):
        implication = "Liability or responsibility terms modified."
        risk_score = 10
        severity = "MEDIUM"
    
    return [
        {
            "clause": "Policy change detected",
            "before": before or "No removed wording detected.",
            "after": after or "No added wording detected.",
            "legal_implication": implication,
            "page_citation": "Policy snapshot diff",
            "severity": severity,
            "risk_points": str(risk_score),
        }
    ]


CONTRACT_PATTERNS = [
    (
        "Confidentiality / non-disclosure",
        ("confidential", "non-disclosure", "nondisclosure", "disclose", "recipient"),
        "Restricts disclosure of confidential information. Check scope, exclusions, and permitted recipients.",
        16,
    ),
    (
        "Data sharing / processors",
        ("personal data", "third-party", "third party", "processor", "subprocessor", "share data"),
        "Allows data handling or sharing. Review consent, security duties, cross-border processing, and processor controls.",
        18,
    ),
    (
        "Penalty / liquidated damages",
        ("penalty", "liquidated damages", "fine", "service fee", "processing fee"),
        "Creates financial exposure. Verify whether the amount is reasonable, capped, and enforceable.",
        18,
    ),
    (
        "Indemnity",
        ("indemnify", "indemnification", "hold harmless", "defend"),
        "May shift legal costs and third-party claims. Look for caps, control of defense, and carve-outs.",
        16,
    ),
    (
        "Limitation of liability",
        ("limitation of liability", "liability shall not exceed", "consequential damages", "indirect damages"),
        "Limits recovery if something goes wrong. Check whether confidentiality, IP, data breach, and payment claims are excluded.",
        14,
    ),
    (
        "IP ownership / license",
        ("intellectual property", "ip ownership", "license", "work product", "derivative"),
        "May affect ownership or use of created materials. Confirm assignment, retained rights, and license duration.",
        16,
    ),
    (
        "Arbitration / dispute resolution",
        ("arbitration", "sole arbitrator", "dispute resolution", "venue", "jurisdiction"),
        "Changes how disputes are handled. Check seat, venue, governing law, costs, and injunctive relief carve-outs.",
        14,
    ),
    (
        "Termination / survival",
        ("terminate", "termination", "survive", "survival", "expiration"),
        "Affects exit rights and post-termination duties. Check notice period and survival of confidentiality/payment terms.",
        10,
    ),
    (
        "Non-compete / non-solicit",
        ("non-compete", "non compete", "non-solicit", "non solicit", "solicit employees"),
        "Restricts future business activity. Review duration, geography, and enforceability.",
        15,
    ),
    (
        "Data privacy / GDPR compliance",
        ("gdpr", "data protection", "privacy policy", "data subject", "consent", "data processing"),
        "Addresses data protection requirements. Check compliance with privacy regulations and user rights.",
        17,
    ),
    (
        "Warranty / representation",
        ("warrant", "represent", "warranty", "guarantee", "merchantability", "fitness for purpose"),
        "Makes promises about quality or performance. Check limitations and exclusions.",
        12,
    ),
    (
        "Force majeure",
        ("force majeure", "act of god", "unforeseeable", "beyond control"),
        "Excuses performance due to uncontrollable events. Check scope and notice requirements.",
        10,
    ),
    (
        "Governing law / jurisdiction",
        ("governing law", "jurisdiction", "applicable law", "choice of law"),
        "Determines which country's laws apply. Check for favorable or unfavorable jurisdictions.",
        13,
    ),
    (
        "Assignment / transfer",
        ("assign", "assignment", "transfer", "successor", "affiliate"),
        "Controls whether rights can be transferred. Check restrictions on assignment.",
        11,
    ),
    (
        "Entire agreement / merger",
        ("entire agreement", "integration", "merger", "amend", "modify"),
        "Limits what constitutes the full agreement. Check for integration clauses and amendment procedures.",
        9,
    ),
    (
        "Severability",
        ("severable", "severability", "invalid", "unenforceable", "void"),
        "Determines what happens if part of agreement is invalid. Check for severability provisions.",
        8,
    ),
]


def _snippets(text: str, terms: tuple[str, ...], limit: int = 2) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    snippets: list[str] = []
    for term in terms:
        match = re.search(rf".{{0,130}}\b{re.escape(term)}\b.{{0,180}}", compact, flags=re.I)
        if match:
            snippet = match.group(0).strip()
            if snippet not in snippets:
                snippets.append(snippet)
        if len(snippets) >= limit:
            break
    return snippets


def contract_clauses(text: str) -> list[dict[str, str]]:
    clauses: list[dict[str, str]] = []
    for name, terms, implication, points in CONTRACT_PATTERNS:
        snippets = _snippets(text, terms)
        if not snippets:
            continue
        severity = "HIGH" if points >= 16 else "MEDIUM" if points >= 12 else "LOW"
        clauses.append(
            {
                "clause": name,
                "before": "Contract document",
                "after": "\n\n".join(snippets),
                "legal_implication": implication,
                "page_citation": "Extracted PDF text",
                "severity": severity,
                "risk_points": str(points),
            }
        )
    if clauses:
        return clauses
    preview = re.sub(r"\s+", " ", text).strip()[:500]
    return [
        {
            "clause": "General contract review",
            "before": "Contract document",
            "after": preview or "No readable clause text found.",
            "legal_implication": "No high-signal risk clause was detected by the local reviewer. Manual review is still recommended.",
            "page_citation": "Extracted PDF text",
            "severity": "LOW",
            "risk_points": "8",
        }
    ]


def _docx_xml(title: str, clauses: list[dict[str, str]], summary: str | None = None) -> str:
    lines = [title, "", summary or "Clause Review", ""]
    for index, clause in enumerate(clauses, start=1):
        lines.extend(
            [
                "",
                f"{index}. {clause.get('clause', 'Clause')}",
                f"Risk: {clause.get('severity', 'REVIEW')} ({clause.get('risk_points', 'n/a')} pts)",
                f"Extract: {clause.get('after', '')}",
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


def write_docx(title: str, clauses: list[dict[str, str]], path: Path, summary: str | None = None) -> None:
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
        docx.writestr("word/document.xml", _docx_xml(title, clauses, summary))


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
                "severity": str(item.get("severity") or "REVIEW"),
                "risk_points": str(item.get("risk_points") or item.get("points") or "8"),
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
    local_clauses = contract_clauses(text)
    try:
        response = _post_json(
            "http://localhost:3001/api/analyze",
            {"document": text[:12000], "mode": "contract_review", "service": filename},
        )
        clauses = _normalise_clauses(response) or local_clauses
        write_docx(
            f"Silent Witness Contract Review - {filename}",
            clauses,
            report_path,
            "Mike tabular extraction with clause-level risk findings.",
        )
        return MikeResult(clauses, str(report_path), "mike")
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        clauses = local_clauses
        write_docx(
            f"Silent Witness Local Contract Review - {filename}",
            clauses,
            report_path,
            "Local clause extraction because Mike backend was unavailable.",
        )
        return MikeResult(clauses, str(report_path), "local-fallback", str(exc))
