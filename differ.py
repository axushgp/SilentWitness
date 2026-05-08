from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from utils import html_to_text, read_watchlist, snapshot_path, snapshots_for, today_iso


@dataclass
class DiffResult:
    service: str
    status: str
    diff_text: str = ""
    current_path: str | None = None
    baseline_path: str | None = None


def _changed_lines(diff_lines: list[str]) -> list[str]:
    changed: list[str] = []
    for line in diff_lines:
        if line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith(("+", "-")) and line[1:].strip():
            changed.append(line)
    return changed[:100]


def _read_text(path: Path) -> list[str]:
    return html_to_text(path.read_text(encoding="utf-8", errors="replace")).splitlines()


def diff_service(service: str, day: str | None = None) -> DiffResult:
    day = day or today_iso()
    current = snapshot_path(service, day)

    if current.exists():
        candidates = [path for path in snapshots_for(service) if path != current]
        if not candidates:
            return DiffResult(service, "no_baseline", current_path=str(current))
        baseline = candidates[-1]
    else:
        candidates = snapshots_for(service)
        if len(candidates) < 2:
            return DiffResult(service, "no_baseline")
        baseline, current = candidates[-2], candidates[-1]

    diff_lines = list(
        difflib.unified_diff(
            _read_text(baseline),
            _read_text(current),
            fromfile=baseline.name,
            tofile=current.name,
            lineterm="",
        )
    )
    changed = _changed_lines(diff_lines)
    if len(changed) <= 1:
        return DiffResult(service, "no_change", current_path=str(current), baseline_path=str(baseline))

    return DiffResult(
        service=service,
        status="diff_found",
        diff_text="\n".join(changed),
        current_path=str(current),
        baseline_path=str(baseline),
    )


def diff_all(day: str | None = None) -> list[DiffResult]:
    return [diff_service(service, day) for service, _url in read_watchlist()]


if __name__ == "__main__":
    for result in diff_all():
        print(f"{result.service}: {result.status}")
        if result.diff_text:
            print(result.diff_text[:1000])
