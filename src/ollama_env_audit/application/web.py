"""Minimal local web UI for rendering audit reports."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ollama_env_audit.application.services import InspectionService
from ollama_env_audit.reporting import HtmlReportRenderer, JsonReportRenderer


class LocalWebService:
    """Serve live HTML and JSON views of the current inspection report."""

    def __init__(self, inspection_service: InspectionService) -> None:
        self._inspection_service = inspection_service
        self._html_renderer = HtmlReportRenderer()
        self._json_renderer = JsonReportRenderer()

    def serve(self, host: str, port: int) -> None:
        inspection_service = self._inspection_service
        html_renderer = self._html_renderer
        json_renderer = self._json_renderer

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                report = inspection_service.inspect()
                if self.path in ("/", "/index.html"):
                    body = html_renderer.render(report).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                elif self.path == "/report.json":
                    body = json_renderer.render(report).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                else:
                    body = b"not found"
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

        server = ThreadingHTTPServer((host, port), Handler)
        try:
            server.serve_forever()
        finally:
            server.server_close()
