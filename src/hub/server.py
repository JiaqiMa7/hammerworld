"""HTTP API server for hub peer-to-peer sync."""
from __future__ import annotations

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Callable

from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry
from src.hub.peer import PeerManager, PeerConfig, _entry_to_json, _json_to_entry


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for concurrent peer connections."""
    daemon_threads = True


class _HubHandler(BaseHTTPRequestHandler):
    """Request handler that routes to HubAPI methods."""

    # Set by HubServer before starting
    api: Optional[HubAPI] = None
    db: Optional[LeaderboardDB] = None
    peer_manager: Optional[PeerManager] = None

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _send_html(self, html: str, status: int = 200):
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict | list, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        if length > 1_048_576:  # 1MB limit
            return b""
        return self.rfile.read(length)

    def do_GET(self):
        assert self.api is not None
        path = self.path.split("?", 1)[0]

        # P2P API endpoints
        if self.path == "/health":
            self._send_json(self.api.handle_health())
        elif self.path == "/stats":
            self._send_json(self.api.handle_stats())
        elif self.path == "/peers":
            self._send_json(self.api.handle_get_peers())
        elif self.path.startswith("/combinations"):
            self._send_json(self.api.handle_get_combinations(self.path))
        # Web UI endpoints
        elif self.path == "/" or path == "/web":
            self._serve_web("dashboard")
        elif path.startswith("/web/"):
            self._serve_web(path)
        else:
            self._send_json({"error": "not found"}, 404)

    def _serve_web(self, path: str):
        from src.hub.web import (
            render_dashboard, render_leaderboard, render_search,
            render_random, render_peers, render_entry,
        )
        db = self.db
        pm = self.peer_manager
        assert db is not None and pm is not None

        if path in ("/", "/web", "dashboard"):
            html = render_dashboard(db, pm)
        elif path.startswith("/web/leaderboard"):
            html = render_leaderboard(db, self.path)
        elif path.startswith("/web/search"):
            html = render_search(db, self.path)
        elif path.startswith("/web/random"):
            html = render_random(db, self.path)
        elif path.startswith("/web/peers"):
            html = render_peers(pm)
        elif path.startswith("/web/entry/"):
            combo_id = path.split("/web/entry/", 1)[1]
            html = render_entry(db, combo_id)
        else:
            self._send_json({"error": "not found"}, 404)
            return
        self._send_html(html)

    def do_POST(self):
        assert self.api is not None
        body = self._read_body()
        if self.path == "/combinations":
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, 400)
                return
            result = self.api.handle_post_combinations(data)
            self._send_json(result)
        elif self.path == "/peers/announce":
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, 400)
                return
            result = self.api.handle_announce(data)
            self._send_json(result)
        else:
            self._send_json({"error": "not found"}, 404)


class HubAPI:
    """REST API logic — separated from HTTP transport for testability."""

    def __init__(self, db: LeaderboardDB, peer_manager: PeerManager):
        self.db = db
        self.peer_manager = peer_manager

    def handle_health(self) -> dict:
        return {
            "status": "ok",
            "peer_id": self.peer_manager.peer_id,
            "entries": self.db.total_entries(),
        }

    def handle_stats(self) -> dict:
        return {
            "peer_id": self.peer_manager.peer_id,
            "entries": self.db.total_entries(),
            "peers": len(self.peer_manager.get_peers()),
            "uptime": self.peer_manager.uptime,
        }

    def handle_get_peers(self) -> dict:
        peers = self.peer_manager.get_peers()
        return {
            "peer_id": self.peer_manager.peer_id,
            "peers": [
                {"peer_id": p.peer_id, "address": p.address, "port": p.port}
                for p in peers
            ],
        }

    def handle_get_combinations(self, path: str) -> dict:
        # Parse query string from path
        params: dict[str, str] = {}
        if "?" in path:
            qs = path.split("?", 1)[1]
            for pair in qs.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v

        since = float(params.get("since", 0))
        limit = min(int(params.get("limit", 100)), 500)
        entries = self.db.get_since(since, limit)
        return {
            "entries": [_entry_to_json(e) for e in entries],
            "ttl": [3] * len(entries),
        }

    def handle_post_combinations(self, data: dict) -> dict:
        entries_data = data.get("entries", [])
        ttl_list = data.get("ttl", [])
        accepted = 0
        for i, entry_data in enumerate(entries_data):
            entry = _json_to_entry(entry_data)
            if entry is None:
                continue
            try:
                is_new = self.db.insert_from_sync(entry)
                if is_new:
                    accepted += 1
                    # Re-broadcast to other peers
                    ttl = ttl_list[i] if i < len(ttl_list) else 0
                    if ttl > 0:
                        self.peer_manager.broadcast(entry, ttl)
            except Exception:
                pass
        return {"accepted": accepted}

    def handle_announce(self, data: dict) -> dict:
        peer_id = data.get("peer_id", "")
        address = data.get("address", "127.0.0.1")
        port = data.get("port", 8765)
        self.peer_manager.add_peer(address, port, peer_id)
        return {
            "peer_id": self.peer_manager.peer_id,
            "peers": [
                {"peer_id": p.peer_id, "address": p.address, "port": p.port}
                for p in self.peer_manager.get_peers()
            ],
        }


class HubServer:
    """HTTP server wrapping HubAPI + PeerManager for P2P hub operation."""

    def __init__(
        self,
        db: LeaderboardDB,
        config: PeerConfig | None = None,
    ):
        self.config = config or PeerConfig()
        self.db = db
        self.peer_manager = PeerManager(db, self.config)
        self.api = HubAPI(db, self.peer_manager)

    def start(self):
        self.peer_manager.start()
        _HubHandler.api = self.api
        _HubHandler.db = self.db
        _HubHandler.peer_manager = self.peer_manager
        self._http = _ThreadingHTTPServer(("0.0.0.0", self.config.port), _HubHandler)
        # Run server in daemon thread so shutdown() works from signal handler
        import threading
        self._server_thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._server_thread.start()
        self._server_thread.join()

    def stop(self):
        self.peer_manager.stop()
        self._http.shutdown()
        self._http.server_close()
