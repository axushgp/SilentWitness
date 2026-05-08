from __future__ import annotations

import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mike_bridge import fallback_clauses, write_docx
from utils import REPORTS_DIR, slug


class MikeCompatHandler(BaseHTTPRequestHandler):
    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(body or "{}")

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"ok": True, "service": "mike-compat"})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/analyze":
            payload = self._read_json()
            diff_text = str(payload.get("diff") or payload.get("document") or "")
            clauses = fallback_clauses(diff_text)
            self._json({"clauses": clauses})
            return

        if self.path == "/api/export/docx":
            payload = self._read_json()
            service = slug(str(payload.get("service") or "review"))
            clauses = payload.get("clauses") or fallback_clauses(str(payload.get("document") or ""))
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            path = REPORTS_DIR / f"{service}_{date.today().isoformat()}.docx"
            write_docx(f"Mike Compatible Review - {service}", clauses, path)
            self._json({"path": str(path), "clauses": clauses})
            return

        self.send_error(404)

    def log_message(self, format: str, *args) -> None:
        print(f"mike-compat: {format % args}")


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 3001), MikeCompatHandler)
    print("Mike-compatible adapter running at http://127.0.0.1:3001")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
