from __future__ import annotations

import argparse
import cgi
import json
import mimetypes
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

from contract_analyzer import analyze_pdf
from simulate_change import simulate
from silent_witness import run_heartbeat
from utils import REPORTS_DIR, UPLOADS_DIR, json_ready_row, load_dotenv, read_watchlist, slug
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
    input[type="file"] {
      width: min(100%, 360px);
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      border-radius: 6px;
      padding: 8px;
      min-height: 40px;
    }
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
    .upload { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
    .upload form { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
    .upload-result { margin-top: 12px; color: var(--muted); font-size: 14px; white-space: pre-wrap; }
    .clause-list { display: grid; gap: 10px; margin-top: 12px; }
    .clause-item { border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #151a21; }
    .clause-item strong { display: block; margin-bottom: 8px; color: var(--text); font-size: 15px; }
    .clause-item .meta { display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
    .clause-item .severity { padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .clause-item .severity.HIGH { background: rgba(255,93,115,.3); color: #ffb6c1; }
    .clause-item .severity.MEDIUM { background: rgba(244,185,66,.3); color: #ffdc8a; }
    .clause-item .severity.LOW { background: rgba(88,214,141,.3); color: #9bf0bd; }
    .clause-item .risk-points { color: var(--muted); font-size: 12px; }
    .clause-item .source { color: var(--blue); font-size: 12px; font-weight: 600; }
    .clause-item .diff { margin-top: 8px; }
    .clause-item .before { background: rgba(255,93,115,.1); border-left: 3px solid var(--red); padding: 6px 8px; margin-bottom: 4px; font-size: 13px; }
    .clause-item .after { background: rgba(88,214,141,.1); border-left: 3px solid var(--green); padding: 6px 8px; margin-bottom: 4px; font-size: 13px; }
    .clause-item .implication { background: rgba(107,114,128,.1); padding: 8px; border-radius: 4px; margin-top: 8px; font-size: 13px; color: var(--text); }
    .clause-item .citation { color: var(--muted); font-size: 12px; margin-top: 4px; }
    a.download { display: inline-flex; align-items: center; min-height: 36px; margin-top: 10px; padding: 0 12px; border-radius: 6px; background: var(--green); color: #07130c; text-decoration: none; font-weight: 800; }
    .status-card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
    .status-card dl { display: grid; grid-template-columns: auto 1fr; gap: 8px 12px; margin: 0; }
    .status-card dt { color: var(--muted); }
    .status-card dd { margin: 0; overflow-wrap: anywhere; }
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
        <section class="upload">
          <h2>Analyze PDF</h2>
          <form id="pdfForm">
            <input id="pdfFile" name="pdf" type="file" accept="application/pdf,.pdf" required>
            <button class="primary" type="submit">Upload PDF</button>
          </form>
          <div id="uploadResult" class="upload-result"></div>
        </section>
        <section>
          <h2>Watchlist</h2>
          <div id="watchlist" class="watchlist"></div>
        </section>
        <section class="log">
          <h2>Mike Status</h2>
          <div id="mikeStatus" class="status-card">Checking Mike service...</div>
        </section>
        <section class="log">
          <h2>Latest Run</h2>
          <div id="latestRun" class="status-card">Loading...</div>
        </section>
        <section class="log">
          <h2>Latest PDF</h2>
          <div id="latestPdf" class="status-card">No PDF analyzed yet.</div>
        </section>
      </div>
    </div>
  </main>
  <script>
    const el = (id) => document.getElementById(id);
    async function api(path, options) {
      const response = await fetch(path, options);
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }
    function pill(value) { return `<span class="pill ${value}">${value || "n/a"}</span>`; }
    async function refresh() {
      const data = await api("/api/status");
      el("mChanges").textContent = data.stats.changes;
      el("mCritical").textContent = data.stats.critical;
      el("mContracts").textContent = data.stats.contracts;
      el("mRuns").textContent = data.stats.runs;
      el("service").innerHTML = data.watchlist.map(item => `<option value="${item.service}">${item.service}</option>`).join("");
      el("watchlist").innerHTML = data.watchlist.map(item => `<div class="service"><strong>${item.service}</strong><span>${item.url}</span></div>`).join("");
      el("changes").innerHTML = data.changes.map(row => `<tr>
        <td>${row.detected_at || ""}</td>
        <td>${row.service || ""}</td>
        <td>${pill(row.severity)}</td>
        <td>${row.risk_score ?? ""}</td>
        <td>${row.summary || ""}</td>
      </tr>`).join("") || `<tr><td colspan="5">No changes logged yet.</td></tr>`;
      
      // Check Mike status
      try {
        const mikeResponse = await fetch("http://localhost:3001/health", { method: "GET", signal: AbortSignal.timeout(2000) });
        if (mikeResponse.ok) {
          const mikeData = await mikeResponse.json();
          el("mikeStatus").innerHTML = `<dl><dt>Status</dt><dd>✅ Online</dd><dt>Service</dt><dd>${mikeData.service || "mike-compat"}</dd></dl>`;
        } else {
          el("mikeStatus").innerHTML = `<dl><dt>Status</dt><dd>❌ Offline</dd><dt>Port</dt><dd>3001</dd></dl>`;
        }
      } catch (error) {
        el("mikeStatus").innerHTML = `<dl><dt>Status</dt><dd>❌ Offline</dd><dt>Error</dt><dd>${error.message}</dd></dl>`;
      }
      
      const run = data.runs[0];
      if (run) {
        el("latestRun").innerHTML = `
          <dl>
            <dt>Status</dt><dd>${run.status}</dd>
            <dt>Started</dt><dd>${run.started_at || ""}</dd>
            <dt>Finished</dt><dd>${run.finished_at || ""}</dd>
            <dt>Crawled</dt><dd>${run.crawled}</dd>
            <dt>Failed</dt><dd>${run.failed}</dd>
            <dt>Diffs</dt><dd>${run.diffs}</dd>
            <dt>Alerts</dt><dd>${run.alerts}</dd>
          </dl>
        `;
      } else {
        el("latestRun").textContent = "No heartbeat run yet.";
      }
      const pdf = data.contracts[0];
      if (pdf) {
        const clauses = (pdf.clauses || []).map((clause) => `
          <div class="clause-item">
            <strong>${clause.clause || "Clause"}</strong>
            <div class="meta">
              <span class="severity ${clause.severity || 'REVIEW'}">${clause.severity || "REVIEW"}</span>
              <span class="risk-points">${clause.risk_points || "n/a"} pts</span>
              <span class="source">${pdf.source || "mike"}</span>
            </div>
            ${clause.before ? `<div class="before"><strong>Before:</strong> ${clause.before}</div>` : ''}
            ${clause.after ? `<div class="after"><strong>After:</strong> ${clause.after}</div>` : ''}
            ${clause.legal_implication ? `<div class="implication">${clause.legal_implication}</div>` : ''}
            ${clause.page_citation ? `<div class="citation">Citation: ${clause.page_citation}</div>` : ''}
          </div>
        `).join("");
        const download = pdf.report_path ? `<a class="download" href="/api/download?path=${encodeURIComponent(pdf.report_path)}">Download DOCX report</a>` : "";
        el("latestPdf").innerHTML = `
          <dl>
            <dt>File</dt><dd>${pdf.filename}</dd>
            <dt>Uploaded</dt><dd>${pdf.uploaded_at}</dd>
            <dt>Risk</dt><dd>${pdf.severity} (${pdf.risk_score}/100)</dd>
            <dt>Analysis Source</dt><dd>${pdf.source || "mike"}</dd>
            <dt>Summary</dt><dd>${pdf.summary}</dd>
          </dl>
          ${download}
          <div class="clause-list">${clauses}</div>
        `;
      } else {
        el("latestPdf").textContent = "No PDF analyzed yet.";
      }
    }
    el("run").onclick = async () => {
      el("latestRun").textContent = "Running heartbeat...";
      try { await api("/api/run", { method: "POST" }); await refresh(); }
      catch (error) { el("latestRun").textContent = error.message; }
    };
    el("simulate").onclick = async () => {
      try { await api(`/api/simulate?service=${encodeURIComponent(el("service").value || "spotify")}`, { method: "POST" }); await refresh(); }
      catch (error) { el("latestRun").textContent = error.message; }
    };
    el("refresh").onclick = refresh;
    el("pdfForm").onsubmit = async (event) => {
      event.preventDefault();
      const file = el("pdfFile").files[0];
      if (!file) return;
      el("uploadResult").textContent = "Analyzing PDF with Mike...";
      const body = new FormData();
      body.append("pdf", file);
      try {
        const result = await api("/api/upload-pdf", { method: "POST", body });
        const clauses = (result.clauses || []).map((clause) => `
          <div class="clause-item">
            <strong>${clause.clause || "Clause"}</strong>
            <div class="meta">
              <span class="severity ${clause.severity || 'REVIEW'}">${clause.severity || "REVIEW"}</span>
              <span class="risk-points">${clause.risk_points || "n/a"} pts</span>
              <span class="source">${result.source || "mike"}</span>
            </div>
            ${clause.before ? `<div class="before"><strong>Before:</strong> ${clause.before}</div>` : ''}
            ${clause.after ? `<div class="after"><strong>After:</strong> ${clause.after}</div>` : ''}
            ${clause.legal_implication ? `<div class="implication">${clause.legal_implication}</div>` : ''}
            ${clause.page_citation ? `<div class="citation">Citation: ${clause.page_citation}</div>` : ''}
          </div>
        `).join("");
        const download = result.download_url ? `<a class="download" href="${result.download_url}">Download DOCX report</a>` : "";
        el("uploadResult").innerHTML = `
          <dl>
            <dt>Risk</dt><dd>${result.severity} (${result.risk_score}/100)</dd>
            <dt>Analysis Source</dt><dd>${result.source || "mike"}</dd>
            <dt>Summary</dt><dd>${result.summary}</dd>
          </dl>
          ${download}
          <div class="clause-list">${clauses}</div>
        `;
        await refresh();
      } catch (error) {
        el("uploadResult").textContent = error.message;
      }
    };
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
        if parsed.path == "/api/download":
            self._handle_download(parsed)
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
        if parsed.path == "/api/upload-pdf":
            self._handle_pdf_upload()
            return
        self.send_error(404)

    def _handle_pdf_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._json({"error": "Expected multipart/form-data upload."}, 400)
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )
        file_item = form["pdf"] if "pdf" in form else None
        if file_item is None or not getattr(file_item, "filename", ""):
            self._json({"error": "Upload a PDF file in the 'pdf' field."}, 400)
            return

        filename = slug(file_item.filename.rsplit(".", 1)[0]) + ".pdf"
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        path = UPLOADS_DIR / filename
        with path.open("wb") as handle:
            handle.write(file_item.file.read())

        try:
            result = analyze_pdf(path, "dashboard")
            if result.get("report_path"):
                result["download_url"] = "/api/download?path=" + quote(str(result["report_path"]))
            self._json(result)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    def _handle_download(self, parsed) -> None:
        query = parse_qs(parsed.query)
        raw_path = unquote(query.get("path", [""])[0])
        if not raw_path:
            self.send_error(400, "Missing path")
            return

        requested = Path(raw_path).resolve()
        allowed_roots = [REPORTS_DIR.resolve(), UPLOADS_DIR.resolve()]
        if not any(requested == root or root in requested.parents for root in allowed_roots):
            self.send_error(403, "Refusing to download files outside report/upload folders")
            return
        if not requested.exists() or not requested.is_file():
            self.send_error(404, "File not found")
            return

        body = requested.read_bytes()
        content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{requested.name}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
