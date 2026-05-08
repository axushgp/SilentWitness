from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from simulate_change import simulate
from silent_witness import run_heartbeat
from utils import json_ready_row, load_dotenv, read_watchlist
from vault import all_changes, init_db, recent_contracts, recent_runs, stats


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Silent Witness Dashboard</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #111318;
      --panel: #1b2028;
      --panel-2: #202832;
      --text: #eef2f5;
      --muted: #a9b4be;
      --line: #36414d;
      --red: #ff5d73;
      --amber: #f4b942;
      --green: #58d68d;
      --blue: #6db7ff;
      --violet: #b89cff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      min-height: 28vh;
      display: grid;
      align-content: end;
      padding: 28px clamp(18px, 4vw, 48px);
      border-bottom: 1px solid var(--line);
      background:
        linear-gradient(100deg, rgba(17,19,24,.94), rgba(17,19,24,.64)),
        url("https://images.unsplash.com/photo-1450101499163-c8848c66ca85?auto=format&fit=crop&w=1600&q=80") center/cover;
    }
    h1 { margin: 0; font-size: clamp(34px, 5vw, 72px); line-height: 1; letter-spacing: 0; }
    .sub { max-width: 860px; margin: 14px 0 0; color: var(--muted); font-size: 17px; }
    main { padding: 24px clamp(18px, 4vw, 48px) 48px; }
    .toolbar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
    button, select {
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      min-height: 40px;
      border-radius: 6px;
      padding: 0 13px;
      font: inherit;
    }
    button { cursor: pointer; }
    button.primary { background: var(--blue); color: #09111a; border-color: var(--blue); font-weight: 700; }
    button.danger { background: var(--red); color: #21070b; border-color: var(--red); font-weight: 700; }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 20px; }
    .metric { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; min-width: 0; }
    .metric span { display: block; color: var(--muted); font-size: 13px; }
    .metric strong { display: block; margin-top: 8px; font-size: 30px; }
    .grid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(320px, .8fr); gap: 18px; align-items: start; }
    section { min-width: 0; }
    h2 { font-size: 18px; margin: 0 0 10px; }
    table { width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    th, td { text-align: left; padding: 11px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
    th { color: var(--muted); font-size: 12px; text-transform: uppercase; }
    td { font-size: 14px; }
    tr:last-child td { border-bottom: 0; }
    .pill { display: inline-flex; align-items: center; min-height: 24px; border-radius: 999px; padding: 0 9px; font-weight: 700; font-size: 12px; }
    .CRITICAL { background: rgba(255,93,115,.2); color: #ffb6c1; }
    .MODERATE { background: rgba(244,185,66,.2); color: #ffdc8a; }
    .LOW { background: rgba(88,214,141,.18); color: #9bf0bd; }
    .side { display: grid; gap: 18px; }
    .log { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
    .log pre { white-space: pre-wrap; margin: 0; color: var(--muted); font-size: 13px; max-height: 280px; overflow: auto; }
    .watchlist { display: grid; gap: 8px; }
    .service { display: flex; justify-content: space-between; gap: 10px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; }
    .service span { color: var(--muted); overflow-wrap: anywhere; }
    @media (max-width: 860px) {
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 520px) {
      .metrics { grid-template-columns: 1fr; }
      th:nth-child(4), td:nth-child(4) { display: none; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Silent Witness</h1>
    <p class="sub">Live local dashboard for OpenClaw heartbeat monitoring, policy diffs, legal risk scoring, Mike reports, Telegram alerts, and the contract vault.</p>
  </header>
  <main>
    <div class="toolbar">
      <button class="primary" id="run">Run heartbeat</button>
      <select id="service"></select>
      <button class="danger" id="simulate">Inject critical demo</button>
      <button id="refresh">Refresh</button>
    </div>
    <div class="metrics">
      <div class="metric"><span>Policy changes</span><strong id="mChanges">0</strong></div>
      <div class="metric"><span>Critical findings</span><strong id="mCritical">0</strong></div>
      <div class="metric"><span>Contract PDFs</span><strong id="mContracts">0</strong></div>
      <div class="metric"><span>Heartbeat runs</span><strong id="mRuns">0</strong></div>
    </div>
    <div class="grid">
      <section>
        <h2>Vault</h2>
        <table>
          <thead><tr><th>Time</th><th>Service</th><th>Severity</th><th>Risk</th><th>Summary</th></tr></thead>
          <tbody id="changes"></tbody>
        </table>
      </section>
      <div class="side">
        <section>
          <h2>Watchlist</h2>
          <div id="watchlist" class="watchlist"></div>
        </section>
        <section class="log">
          <h2>Latest Run</h2>
          <pre id="runs">Loading...</pre>
        </section>
      </div>
    </div>
  </main>
  <script>
    async function api(path, options) {
      const response = await fetch(path, options);
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }
    function pill(value) { return `<span class="pill ${value}">${value || "n/a"}</span>`; }
    async function refresh() {
      const data = await api("/api/status");
      mChanges.textContent = data.stats.changes;
      mCritical.textContent = data.stats.critical;
      mContracts.textContent = data.stats.contracts;
      mRuns.textContent = data.stats.runs;
      service.innerHTML = data.watchlist.map(item => `<option value="${item.service}">${item.service}</option>`).join("");
      watchlist.innerHTML = data.watchlist.map(item => `<div class="service"><strong>${item.service}</strong><span>${item.url}</span></div>`).join("");
      changes.innerHTML = data.changes.map(row => `<tr>
        <td>${row.detected_at || ""}</td>
        <td>${row.service || ""}</td>
        <td>${pill(row.severity)}</td>
        <td>${row.risk_score ?? ""}</td>
        <td>${row.summary || ""}</td>
      </tr>`).join("") || `<tr><td colspan="5">No changes logged yet.</td></tr>`;
      runs.textContent = JSON.stringify(data.runs[0] || {}, null, 2);
    }
    run.onclick = async () => { runs.textContent = "Running heartbeat..."; await api("/api/run", { method: "POST" }); await refresh(); };
    simulate.onclick = async () => { await api(`/api/simulate?service=${encodeURIComponent(service.value || "spotify")}`, { method: "POST" }); await refresh(); };
    refresh.onclick = refresh;
    refresh();
    setInterval(refresh, 15000);
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/status":
            watchlist = [{"service": service, "url": url} for service, url in read_watchlist()]
            self._json(
                {
                    "stats": stats(),
                    "watchlist": watchlist,
                    "changes": [json_ready_row(row) for row in all_changes(25)],
                    "contracts": [json_ready_row(row) for row in recent_contracts(10)],
                    "runs": [json_ready_row(row) for row in recent_runs(10)],
                }
            )
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            result = run_heartbeat()
            self._json(result.to_dict())
            return
        if parsed.path == "/api/simulate":
            query = parse_qs(parsed.query)
            service = query.get("service", ["spotify"])[0]
            self._json({"service": service, "path": simulate(service)})
            return
        self.send_error(404)

    def log_message(self, format: str, *args) -> None:
        print(f"dashboard: {format % args}")


def scheduler(interval_seconds: int) -> None:
    while True:
        time.sleep(interval_seconds)
        try:
            run_heartbeat()
        except Exception as exc:
            print(f"scheduled heartbeat failed: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Silent Witness local dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--schedule", action="store_true", help="Run heartbeat every 2 hours while dashboard is open")
    args = parser.parse_args()

    load_dotenv()
    init_db()
    if args.schedule:
        thread = threading.Thread(target=scheduler, args=(2 * 60 * 60,), daemon=True)
        thread.start()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Silent Witness dashboard running at http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
