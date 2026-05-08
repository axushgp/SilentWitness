from __future__ import annotations

from pathlib import Path

from mike_bridge import analyze_contract_text
from vault import add_contract


def extract_pdf_text(path: str | Path) -> str:
    pdf_path = Path(path)
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required for PDF ingestion. Install with: pip install pymupdf") from exc

    parts: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            parts.append(page.get_text())
    return "\n".join(parts).strip()


def _contract_summary(clauses: list[dict[str, str]]) -> tuple[str, str, int]:
    total = sum(int(clause.get("risk_points", 8)) for clause in clauses)
    risk_score = min(100, max(5, total))
    high = [clause["clause"] for clause in clauses if clause.get("severity") == "HIGH"]
    medium = [clause["clause"] for clause in clauses if clause.get("severity") == "MEDIUM"]
    if risk_score >= 65 or len(high) >= 3:
        severity = "CRITICAL"
    elif risk_score >= 30 or high or len(medium) >= 2:
        severity = "MODERATE"
    else:
        severity = "LOW"

    top = high[:3] or medium[:3] or [clause["clause"] for clause in clauses[:3]]
    summary = (
        f"Found {len(clauses)} reviewable clause(s). "
        f"Top risk areas: {', '.join(top)}."
    )
    return severity, summary, risk_score


def analyze_pdf(path: str | Path, uploaded_by: str | None = None) -> dict:
    pdf_path = Path(path)
    text = extract_pdf_text(pdf_path)
    if not text:
        raise RuntimeError("No extractable text found in the PDF.")

    mike = analyze_contract_text(pdf_path.name, text)
    severity, summary, risk_score = _contract_summary(mike.clauses)
    extracted_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())[:6000]
    contract_id = add_contract(
        pdf_path.name,
        uploaded_by,
        severity,
        summary,
        risk_score,
        extracted_text,
        mike.report_path,
        mike.clauses,
    )
    return {
        "id": contract_id,
        "filename": pdf_path.name,
        "severity": severity,
        "summary": summary,
        "risk_score": risk_score,
        "report_path": mike.report_path,
        "clauses": mike.clauses,
        "source": mike.source,
    }
