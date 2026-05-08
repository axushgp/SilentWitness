from __future__ import annotations


def check(diff_text: str) -> list[dict[str, str]]:
    lowered = diff_text.lower()
    flags: list[dict[str, str]] = []

    if any(term in lowered for term in {"consent", "agree", "permission", "lawful"}):
        flags.append(
            {
                "section": "6",
                "risk": "Consent clarity",
                "implication": "Consent-related language changed and should remain free, specific, informed, and unconditional.",
            }
        )
    if any(term in lowered for term in {"share", "third-party", "third party", "processor", "partner"}):
        flags.append(
            {
                "section": "8",
                "risk": "Data fiduciary obligations",
                "implication": "Expanded sharing may increase obligations around security, accuracy, and deletion.",
            }
        )
    if any(term in lowered for term in {"transfer", "outside india", "cross-border", "global"}):
        flags.append(
            {
                "section": "16",
                "risk": "Cross-border transfer",
                "implication": "Transfer language changed and may affect India-specific data transfer risk.",
            }
        )
    if any(term in lowered for term in {"withdraw", "delete", "erase", "opt out", "opt-out"}):
        flags.append(
            {
                "section": "11",
                "risk": "Withdrawal rights",
                "implication": "Opt-out, withdrawal, or deletion terms changed for users.",
            }
        )

    return flags
