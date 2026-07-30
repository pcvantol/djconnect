"""Private read-only Engineering Status dashboard; no transaction authority."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _status(root: Path) -> bytes:
    try:
        return (root / ".djconnect" / "status" / "status.json").read_bytes()
    except OSError:
        return (
            b'{"watcher_state":"REMOTE_ENGINEERING_DEGRADED","diagnostic":"Status is unavailable."}'
        )


def handler(root: Path):
    class DashboardHandler(BaseHTTPRequestHandler):
        def _send(self, content: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'"
            )
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self) -> None:
            if self.path == "/api/status":
                return self._send(_status(root), "application/json; charset=utf-8")
            if self.path == "/api/health":
                return self._send(b'{"health":"ok"}', "application/json; charset=utf-8")
            if self.path == "/":
                return self._send(
                    '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>DJConnect Engineering</title><style>body{margin:0;background:#121217;color:#f7f3ee;font:16px system-ui;padding:20px}pre{white-space:pre-wrap;background:#24242d;border-radius:14px;padding:16px;color:#d9c7ff}</style><h1>DJConnect Engineering</h1><pre id="s">Loading</pre><script>fetch("/api/status").then(r=>r.json()).then(x=>s.textContent=JSON.stringify(x,null,2)).catch(()=>s.textContent="Status unavailable")</script>'.encode(),
                    "text/html; charset=utf-8",
                )
            self.send_error(404)

        def log_message(self, *_: object) -> None:
            pass

    return DashboardHandler


def run(root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    ThreadingHTTPServer((host, port), handler(root)).serve_forever()
