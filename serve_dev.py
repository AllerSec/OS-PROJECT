"""Local dev server for the docs/ folder with COOP/COEP enabled.

Run:  python serve_dev.py
URL:  http://localhost:8000/

GitHub Pages itself does NOT set these headers — the client-side
coi-serviceworker shim handles that in production. This script is only
for local development so SharedArrayBuffer works on the first page load
without needing a service-worker reload.
"""
import http.server
import socketserver
from pathlib import Path

DOCS = Path(__file__).resolve().parent / "docs"
PORT = 8000


class COIHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        super().end_headers()

    def log_message(self, fmt, *args):
        # quieter logs
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main():
    handler = lambda *a, **kw: COIHandler(*a, directory=str(DOCS), **kw)
    with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
        print(f"serving {DOCS} on http://127.0.0.1:{PORT}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
