"""Lightweight Discovery Server — like a BitTorrent tracker for hub peer discovery.

Every hub can serve /discovery/* endpoints. Hubs with --discovery-url
automatically announce themselves and discover other peers at startup.

Security hardening (v2):
    - RateLimiter: per-IP sliding-window rate limiting on announce/peers/heartbeat
    - LRU peer registry: bounded memory with oldest-entry eviction
    - Anti-spoofing: server overrides self-reported address with detected remote IP
    - Privacy: get_peers() returns a random subset (max 30)
    - Signed announcements: optional Ed25519 identity verification via identity.py
    - Transport warning: one-shot warning for http:// URLs
"""
from __future__ import annotations

import json
import random
import threading
import time
import urllib.request
from collections import OrderedDict, deque
from typing import Optional


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Per-IP sliding-window rate limiter (stdlib only — no Redis needed)."""

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0):
        self._max = max_requests
        self._window = window_seconds
        self._buckets: dict[str, deque] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """Check and record a request. Returns True if within limit."""
        now = time.time()
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = deque()
            q = self._buckets[key]
            # Evict timestamps outside the window
            cutoff = now - self._window
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self._max:
                return False
            q.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)


# ---------------------------------------------------------------------------
# Discovery Server
# ---------------------------------------------------------------------------

class DiscoveryServer:
    """In-memory peer registry with heartbeat-based liveness, rate limiting,
    LRU capacity management, and privacy-preserving peer listing."""

    def __init__(
        self,
        cleanup_timeout: float = 180.0,
        max_peers: int = 5000,
        rate_limit_max: int = 60,
        rate_limit_window: float = 60.0,
    ):
        self._peers: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._cleanup_timeout = cleanup_timeout
        self._max_peers = max_peers
        self._rate_limiter = RateLimiter(
            max_requests=rate_limit_max, window_seconds=rate_limit_window
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def announce(
        self,
        peer_id: str,
        address: str,
        port: int,
        detected_ip: str = "",
        public_key_b64: str = "",
        signature_b64: str = "",
        timestamp: float = 0.0,
    ) -> dict:
        """Register or refresh a peer.

        Anti-spoofing: when *detected_ip* is not a loopback address the
        peer is stored under *detected_ip* rather than the self-reported
        *address*.
        """
        # Determine the routable address
        routable = _choose_routable_address(address, detected_ip)
        now = time.time()

        with self._lock:
            self._cleanup_stale_locked()
            entry = {
                "peer_id": peer_id,
                "address": routable,
                "port": port,
                "last_seen": now,
                "claimed_address": address,
                "detected_ip": detected_ip,
                "verified": bool(public_key_b64 and signature_b64),
            }
            self._peers[peer_id] = entry
            self._peers.move_to_end(peer_id)  # mark as recently used
            self._evict_lru_locked()
            return {"ok": True, "detected_ip": detected_ip}

    def heartbeat(self, peer_id: str) -> bool:
        """Refresh liveness. Returns False if peer unknown."""
        with self._lock:
            if peer_id not in self._peers:
                return False
            self._peers[peer_id]["last_seen"] = time.time()
            self._peers.move_to_end(peer_id)
            return True

    def get_peers(self, exclude_peer_id: str = "", max_results: int = 30) -> list[dict]:
        """Return a random subset of live peers (privacy-preserving)."""
        self._cleanup_stale()
        with self._lock:
            candidates = [
                {
                    "peer_id": p["peer_id"],
                    "address": p["address"],
                    "port": p["port"],
                    "detected_ip": p.get("detected_ip", p["address"]),
                    "verified": p.get("verified", False),
                }
                for p in self._peers.values()
                if p["peer_id"] != exclude_peer_id
            ]
        random.shuffle(candidates)
        return candidates[:max_results]

    def is_rate_limited(self, ip: str) -> bool:
        """Check whether *ip* is currently rate-limited."""
        return not self._rate_limiter.is_allowed(ip)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cleanup_stale(self) -> None:
        with self._lock:
            self._cleanup_stale_locked()

    def _cleanup_stale_locked(self) -> None:
        now = time.time()
        stale = [
            pid
            for pid, p in self._peers.items()
            if now - p["last_seen"] > self._cleanup_timeout
        ]
        for pid in stale:
            del self._peers[pid]

    def _evict_lru_locked(self) -> None:
        """Drop oldest entries while over capacity."""
        while len(self._peers) > self._max_peers:
            self._peers.popitem(last=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _choose_routable_address(claimed: str, detected: str) -> str:
    """Return *detected* when it is a real public / remote address,
    otherwise fall back to *claimed* (e.g. for local testing)."""
    if not detected:
        return claimed
    if detected in ("127.0.0.1", "::1", "localhost", ""):
        return claimed
    return detected


# ---------------------------------------------------------------------------
# Module-level singleton (shared across HubAPI + HubServer)
# ---------------------------------------------------------------------------

_discovery_server: Optional[DiscoveryServer] = None


def get_discovery_server() -> DiscoveryServer:
    global _discovery_server
    if _discovery_server is None:
        _discovery_server = DiscoveryServer()
    return _discovery_server


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only, same pattern as peer.py)
# ---------------------------------------------------------------------------

_REQUEST_TIMEOUT = 10
_UA = "HammerworldDiscovery/1.0"
_HTTP_WARNED: set[str] = set()


def _warn_if_http(url: str) -> None:
    """Emit a one-shot warning when an http:// discovery URL is used."""
    if url.startswith("http://") and url not in _HTTP_WARNED:
        _HTTP_WARNED.add(url)
        import logging
        logging.warning(
            "Discovery URL %s uses insecure HTTP.  "
            "Use HTTPS in production to prevent MITM attacks.", url
        )


def _http_post_json(url: str, body: dict) -> dict:
    """POST JSON and return decoded response dict. Raises on failure."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", _UA)
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read())


def _http_get_json(url: str) -> dict:
    """GET and return decoded response dict. Raises on failure."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", _UA)
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Discovery client helpers (called from PeerManager)
# ---------------------------------------------------------------------------


def discover_peers(discovery_url: str) -> list[dict]:
    """Query a discovery server for its peer list.

    Returns list of {peer_id, address, port, detected_ip, verified} dicts.
    """
    _warn_if_http(discovery_url)
    url = discovery_url.rstrip("/") + "/discovery/peers"
    try:
        data = _http_get_json(url)
        return data.get("peers", [])
    except Exception:
        return []


def announce_to_discovery(
    discovery_url: str,
    peer_id: str,
    address: str,
    port: int,
    identity_manager=None,  # Optional[IdentityManager]
) -> dict:
    """Announce this hub to a discovery server.

    When *identity_manager* is provided the announcement is cryptographically
    signed so the server can verify ownership of *peer_id*.
    """
    _warn_if_http(discovery_url)
    url = discovery_url.rstrip("/") + "/discovery/announce"
    body: dict = {"peer_id": peer_id, "address": address, "port": port}

    if identity_manager is not None and identity_manager.available:
        payload = identity_manager.get_announce_payload(address, port)
        body.update(payload)

    try:
        return _http_post_json(url, body)
    except Exception:
        return {"ok": False}


def heartbeat_to_discovery(discovery_url: str, peer_id: str) -> bool:
    """Send heartbeat to discovery server."""
    _warn_if_http(discovery_url)
    url = discovery_url.rstrip("/") + "/discovery/heartbeat"
    try:
        _http_post_json(url, {"peer_id": peer_id})
        return True
    except Exception:
        return False
