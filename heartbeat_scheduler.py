from __future__ import annotations

import time

from silent_witness import run_heartbeat
from utils import load_dotenv


def main() -> int:
    load_dotenv()
    print("Silent Witness scheduler running; heartbeat interval is 2 hours.")
    while True:
        run_heartbeat()
        time.sleep(2 * 60 * 60)


if __name__ == "__main__":
    raise SystemExit(main())
