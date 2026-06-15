"""
Dependency-free local test server for K230 network probes.

Run on the Mac:
    python3 server/mini_server_stdlib.py
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
import json
import os
import socket


HOST = "0.0.0.0"
PORT = 8080


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ping":
            self._send_json({
                "status": "ok",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "server": "mini_server_stdlib",
            })
            return
        self._send_json({"status": "error", "message": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        if self.path == "/echo":
            try:
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                data = {"raw_size": len(raw)}
            self._send_json({"status": "ok", "received": data, "size": len(raw)})
            return
        self._send_json({"status": "error", "message": "not found"}, 404)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def local_ip():
    return os.environ.get("K230_SERVER_IP", "192.168.1.8")


if __name__ == "__main__":
    ip = local_ip()
    print("=" * 50)
    print("K230 mini test server")
    print("cwd:", os.getcwd())
    print("url:", "http://%s:%d" % (ip, PORT))
    print("endpoints: GET /ping, POST /echo")
    print("=" * 50)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
