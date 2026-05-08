from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SNAPSHOTS_DIR = ROOT / "snapshots"
REPORTS_DIR = SNAPSHOTS_DIR / "reports"
WATCHLIST_PATH = SNAPSHOTS_DIR / "watchlist.md"
VAULT_PATH = ROOT / "vault.db"
MEMORY_DIR = ROOT / "memory"


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower())
    return cleaned.strip("-")


def today_iso() -> str:
    from datetime import date

    return date.today().isoformat()


def read_watchlist(path: Path = WATCHLIST_PATH) -> list[tuple[str, str]]:
    if not path.exists():
        return []

    rows: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line or "Service" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0] and cells[1].startswith(("http://", "https://")):
            rows.append((slug(cells[0]), cells[1]))
    return rows


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag in {"p", "br", "li", "tr", "h1", "h2", "h3", "h4", "section", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "li", "tr", "h1", "h2", "h3", "h4", "section", "div"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*", "\n", text)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        sentences = re.split(r"(?<=[.;:!?])\s+", line)
        lines.extend(sentence.strip() for sentence in sentences if sentence.strip())
    return "\n".join(lines).strip()


def strip_noisy_html(html: str) -> str:
    html = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", "", html, flags=re.I | re.S)
    return html.strip()


def snapshot_path(service: str, day: str) -> Path:
    return SNAPSHOTS_DIR / f"{slug(service)}_{day}.html"


def snapshots_for(service: str) -> list[Path]:
    return sorted(SNAPSHOTS_DIR.glob(f"{slug(service)}_*.html"))


def load_dotenv(path: Path | None = None) -> None:
    import os

    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def json_ready_row(row) -> dict:
    import json

    data = dict(row)
    if isinstance(data.get("dpdp_flags"), str):
        try:
            data["dpdp_flags"] = json.loads(data["dpdp_flags"])
        except json.JSONDecodeError:
            data["dpdp_flags"] = []
    if isinstance(data.get("mike_clauses"), str):
        try:
            data["mike_clauses"] = json.loads(data["mike_clauses"])
        except json.JSONDecodeError:
            data["mike_clauses"] = []
    if isinstance(data.get("details"), str):
        try:
            data["details"] = json.loads(data["details"])
        except json.JSONDecodeError:
            pass
    return data
