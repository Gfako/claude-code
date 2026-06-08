#!/usr/bin/env python3
"""PageCopy local server — static files + POST /api/save → index.html.

Usage:  python3 server.py [port]   (default 8000, run from the page directory)
"""
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

INDEX = "index.html"
SAVE_PATH = "/api/save"
MAX_BYTES = 50 * 1024 * 1024  # 50MB cap

class Handler(SimpleHTTPRequestHandler):
    # Silence default request logging
    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        if self.path != SAVE_PATH:
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BYTES:
            self.send_error(400, "Invalid Content-Length")
            return
        body = self.rfile.read(length)
        try:
            with open(INDEX, "wb") as f:
                f.write(body)
        except OSError as e:
            self.send_error(500, f"Write failed: {e}")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    addr = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(addr, Handler)
    print(f"PageCopy server on http://localhost:{port} (cwd={os.getcwd()})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == "__main__":
    main()
