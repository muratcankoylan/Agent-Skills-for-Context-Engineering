"""Private loopback operator API. Cloud ingress must add TLS and user identity.

The token belongs to a trusted server-side client, never browser JavaScript.
No CORS, cookies, source fetches, model calls, or arbitrary file path parameters.
"""

from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re

from .contracts import ServiceError
from .store import Store
from .workflow import make_manifest


def handler(store: Store, root: Path, token: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
        raise ServiceError("STRONG_OPERATOR_TOKEN_REQUIRED")
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Never log Authorization, private query strings or payloads.

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def respond(self, status, body):
            data = json.dumps(body, ensure_ascii=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            headers = self.headers.get_all("Authorization") or []
            if len(headers) != 1 or not hmac.compare_digest(headers[0], "Bearer " + token):
                self.respond(401, {"error": "UNAUTHORIZED"})
                return False
            # Same-origin browser integration must go through a server-side proxy.
            if self.headers.get("Origin") is not None or self.headers.get("Transfer-Encoding") is not None:
                self.respond(403, {"error": "DIRECT_BROWSER_OR_STREAMING_DENIED"})
                return False
            return True

        def do_GET(self):
            if not self.authorized():
                return
            if self.path not in {"/v1/status", "/v1/runtime", "/healthz"}:
                self.respond(404, {"error": "NOT_FOUND"})
                return
            try:
                if self.path == "/v1/runtime":
                    from .codex_campaign import sdk_status
                    self.respond(200, sdk_status(store))
                    return
                result = store.status()
                self.respond(200, result if self.path == "/v1/status" else {"alive": True, "paused": result["paused"]})
            except ServiceError as exc:
                self.respond(503, {"error": exc.code})

        def do_POST(self):
            if not self.authorized():
                return
            try:
                lengths = self.headers.get_all("Content-Length") or []
                if (len(lengths) != 1 or not lengths[0].isdigit()
                        or int(lengths[0]) > 4096 or self.headers.get_content_type() != "application/json"):
                    raise ServiceError("INVALID_REQUEST")
                raw = self.rfile.read(int(lengths[0]))
                if len(raw) != int(lengths[0]):
                    raise ServiceError("INCOMPLETE_REQUEST")
                from researcher.scripts.schema_contract import parse_json_strict
                data = parse_json_strict(raw.decode())
                if self.path == "/v1/pause" and isinstance(data, dict) and set(data) == {"paused"}:
                    store.pause(data["paused"])
                    self.respond(200, store.status())
                elif self.path == "/v1/jobs" and isinstance(data, dict) and set(data) == {"schedule", "operation_id"}:
                    if store.config.get("schema") == "openai-budget-authority/v1":
                        raise ServiceError("SOURCE_ADMISSION_API_REQUIRED")
                    if not isinstance(data["operation_id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", data["operation_id"]):
                        raise ServiceError("INVALID_OPERATION_ID")
                    choices = [s for s in store.config["schedules"] if s["id"] == data["schedule"]]
                    if len(choices) != 1:
                        raise ServiceError("UNKNOWN_SCHEDULE")
                    admitted = store.enqueue("api:" + data["operation_id"], make_manifest(root, store.config, choices[0]))
                    self.respond(202, {"admitted": admitted})
                else:
                    self.respond(404, {"error": "NOT_FOUND"})
            except (ValueError, UnicodeError, OSError) as exc:
                self.respond(400, {"error": exc.code if isinstance(exc, ServiceError) else "INVALID_REQUEST"})
    return Handler


def serve_api(store: Store, root: Path, host: str, port: int, token: str):
    if host not in {"127.0.0.1", "localhost"} or not 1 <= port <= 65535:
        raise ServiceError("LOOPBACK_INGRESS_REQUIRED")
    server = ThreadingHTTPServer((host, port), handler(store, root, token))
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
