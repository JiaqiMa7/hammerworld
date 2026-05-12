"""Lightweight Discovery Server — like a BitTorrent tracker for hub peer discovery.

Every hub can serve /discovery/* endpoints. Hubs with --discovery-url
automatically announce themselves and discover other peers at startup.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Optional


class DiscoveryServer:
    """In-memory peer registry with heartbeat-based liveness."""

    def __init__(self, cleanup_timeout: float = 180.0):
        self._peers: dict[str, dict] = {}  # peer_id → {peer_id, address, port, last_seen}
        self._lock = threading.Lock()
        self._cleanup_timeout = cleanup_timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def announce(self, peer_id: str, address: str, port: int) -> None:
        """Register or refresh a peer."""
        with self._lock:
            self._peers[peer_id] = {
                "peer_id": peer_id,
                "address": address,
                "port": port,
                "last_seen": time.time(),
            }

    def heartbeat(self, peer_id: str) -> bool:
        """Refresh liveness. Returns False if peer unknown."""
        with self._lock:
            if peer_id not in self._peers:
                return False
            self._peers[peer_id]["last_seen"] = time.time()
            return True

    def get_peers(self, exclude_peer_id: str = "") -> list[dict]:
        """Return currently live peers (optionally excluding the caller)."""
        self._cleanup_stale()
        with self._lock:
            return [
                {
                    "peer_id": p["peer_id"],
                    "address": p["address"],
                    "port": p["port"],
                }
                for p in self._peers.values()
                if p["peer_id"] != exclude_peer_id
            ]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cleanup_stale(self) -> None:
        now = time.time()
        with self._lock:
            stale = [
                pid
                for pid, p in self._peers.items()
                if now - p["last_seen"] > self._cleanup_timeout
            ]
            for pid in stale:
                del self._peers[pid]


# ------------------------------------------------------------------
# Module-level singleton (shared across HubAPI + HubServer)
# ------------------------------------------------------------------

_discovery_server: Optional[DiscoveryServer] = None


def get_discovery_server() -> DiscoveryServer:
    global _discovery_server
    if _discovery_server is None:
        _discovery_server = DiscoveryServer()
    return _discovery_server


# ------------------------------------------------------------------
# HTTP helpers (stdlib only, same pattern as peer.py)
# ------------------------------------------------------------------

_REQUEST_TIMEOUT = 10


def _http_post_json(url: str, body: dict) -> dict:
    """POST JSON and return decoded response dict. Raises on failure."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read())


def _http_get_json(url: str) -> dict:
    """GET and return decoded response dict. Raises on failure."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read())


# ------------------------------------------------------------------
# Discovery client helpers (called from PeerManager)
# ------------------------------------------------------------------


def discover_peers(discovery_url: str) -> list[dict]:
    """Query a discovery server for its peer list.

    Returns list of {peer_id, address, port} dicts.
    """
    url = discovery_url.rstrip("/") + "/discovery/peers"
    try:
        data = _http_get_json(url)
        return data.get("peers", [])
    except Exception:
        return []


def announce_to_discovery(discovery_url: str, peer_id: str, address: str, port: int) -> bool:
    """Announce this hub to a discovery server."""
    url = discovery_url.rstrip("/") + "/discovery/announce"
    try:
        _http_post_json(url, {"peer_id": peer_id, "address": address, "port": port})
        return True
    except Exception:
        return False


def heartbeat_to_discovery(discovery_url: str, peer_id: str) -> bool:
    """Send heartbeat to discovery server."""
    url = discovery_url.rstrip("/") + "/discovery/heartbeat"
    try:
        _http_post_json(url, {"peer_id": peer_id})
        return True
    except Exception:
        return False
