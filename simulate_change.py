from __future__ import annotations

import sys

from utils import snapshot_path, snapshots_for, today_iso


DEMO_APPENDIX = """

<section>
  <h2>Demo critical update</h2>
  <p>
    We may share personal data with third-party advertising partners,
    charge new service fees, and use user content to improve AI training
    unless you opt out before May 30, 2026.
    Accounts may be suspended if the updated terms are rejected.
  </p>
</section>
"""


def simulate(service: str) -> str:
    target = snapshot_path(service, today_iso())
    candidates = [path for path in snapshots_for(service) if path != target]
    if not candidates:
        raise FileNotFoundError(f"No existing snapshots found for {service}")

    source = candidates[-1]
    target.write_text(
        source.read_text(encoding="utf-8", errors="replace") + DEMO_APPENDIX,
        encoding="utf-8",
    )
    return str(target)


if __name__ == "__main__":
    service_name = sys.argv[1] if len(sys.argv) > 1 else "spotify"
    print(simulate(service_name))
