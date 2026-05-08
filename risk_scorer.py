from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskScore:
    total_score: int
    data_score: int
    financial_score: int
    ip_score: int
    continuity_score: int
    primary_driver: str


def _score(text: str, terms: set[str], high: int) -> int:
    hits = sum(1 for term in terms if term in text)
    return min(high, hits * 8)


def score(diff_text: str, severity: str) -> RiskScore:
    lowered = diff_text.lower()
    data = _score(lowered, {"data", "personal", "share", "third-party", "third party", "advertising", "tracking"}, 25)
    financial = _score(lowered, {"fee", "price", "penalty", "fine", "charge", "subscription", "arbitration"}, 25)
    ip = _score(lowered, {"content", "license", "ownership", "intellectual", "copyright", "ai training"}, 25)
    continuity = _score(lowered, {"terminate", "suspend", "throttle", "modify", "availability", "service"}, 25)

    if severity == "CRITICAL":
        data = max(data, 12)
    elif severity == "MODERATE":
        continuity = max(continuity, 8)

    scores = {
        "data rights exposure": data,
        "financial liability": financial,
        "IP risk": ip,
        "service continuity": continuity,
    }
    driver = max(scores, key=scores.get)
    total = min(100, data + financial + ip + continuity)
    explanation = f"Primary driver is {driver}."
    return RiskScore(total, data, financial, ip, continuity, explanation)
