from __future__ import annotations

import urllib.parse
import urllib.request

from utils import load_dotenv


def opt_out_instructions(diff_text: str) -> str:
    lowered = diff_text.lower()
    if "spotify" in lowered:
        return "Open Spotify Privacy Settings, review tailored ads/data sharing, and disable optional personalization where available."
    if "opt out" in lowered or "opt-out" in lowered:
        return "Use the opt-out or privacy controls named in the updated policy before the stated deadline."
    if "delete" in lowered or "withdraw" in lowered:
        return "Use account privacy settings to withdraw consent or request deletion where offered."
    return "No direct opt-out mechanism was detected in the changed wording."


def compose_alert(service: str, classification, risk, dpdp_flags: list[dict[str, str]], diff_text: str = "", mike_report: str | None = None) -> str:
    dpdp = (
        f"Section {dpdp_flags[0]['section']} - {dpdp_flags[0]['implication']}"
        if dpdp_flags
        else "No India-specific regulatory risk detected"
    )
    report_line = f"\n*Mike report:* {mike_report}" if mike_report else ""
    return "\n".join(
        [
            "*Silent Witness Alert*",
            f"!! *{classification.severity}* - {service.upper()}",
            "",
            "*What changed:*",
            classification.summary,
            "",
            f"*Risk Score:* {risk.total_score}/100 - {risk.primary_driver}",
            "",
            f"*DPDP:* {dpdp}",
            "",
            f"*Opt-out:* {opt_out_instructions(diff_text)}",
            f"*Deadline:* {classification.deadline or 'None stated'}{report_line}",
        ]
    )


def send_telegram(message: str) -> bool:
    import os

    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False

    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    ).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with urllib.request.urlopen(url, data=data, timeout=15) as response:
        return 200 <= getattr(response, "status", 200) < 300
