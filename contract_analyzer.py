from __future__ import annotations

from pathlib import Path

from classifier import classify
from mike_bridge import analyze_contract_text
from risk_scorer import score
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


def analyze_pdf(path: str | Path, uploaded_by: str | None = None) -> dict:
    pdf_path = Path(path)
    text = extract_pdf_text(pdf_path)
    if not text:
        raise RuntimeError("No extractable text found in the PDF.")

    diff_text = "\n".join(f"+{line.strip()}" for line in text.splitlines() if line.strip())[:6000]
    classification = classify(diff_text)
    risk = score(diff_text, classification.severity)
    mike = analyze_contract_text(pdf_path.name, text)
    contract_id = add_contract(
        pdf_path.name,
        uploaded_by,
        classification.severity,
        classification.summary,
        risk.total_score,
        diff_text,
        mike.report_path,
        mike.clauses,
    )
    return {
        "id": contract_id,
        "filename": pdf_path.name,
        "severity": classification.severity,
        "summary": classification.summary,
        "risk_score": risk.total_score,
        "report_path": mike.report_path,
        "clauses": mike.clauses,
        "source": mike.source,
    }
