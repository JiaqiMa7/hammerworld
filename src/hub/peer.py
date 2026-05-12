"""P2P peer management and gossip protocol for hub sync."""
from __future__ import annotations

import hashlib
import json
import random
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry


@dataclass
class PeerInfo:
    peer_id: str
    address: str
    port: int
    last_seen: float = field(default_factory=time.time)

    @property
    def base_url(self) -> str:
        return f"http://{self.address}:{self.port}"


@dataclass
class PeerConfig:
    port: int = 8765
    bootstrap: list[str] = field(default_factory=list)  # ["host:port", ...]
    discovery_urls: list[str] = field(default_factory=list)  # ["http://discovery:port", ...]
    gossip_interval: float = 30.0
    peer_exchange_interval: float = 300.0
    peer_timeout: float = 300.0
    max_peers: int = 50
    request_timeout: float = 10.0
    identity_key_path: Optional[str] = None


class PeerManager:
    """Manages peer discovery, gossip push/pull, and sync with remote hubs."""

    def __init__(self, db: LeaderboardDB, config: PeerConfig | None = None):
        self.db = db
        self.config = config or PeerConfig()

        # Identity: ed25519 keypair or random fallback
        from src.hub.identity import IdentityManager
        self._identity = IdentityManager(self.config.identity_key_path)
        if self._identity.available:
            self._peer_id = self._identity.peer_id
        else:
            self._peer_id = hashlib.sha256(
                f"{time.time()}:{random.random()}".encode()
            ).hexdigest()[:16]

        self._peers: dict[str, PeerInfo] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_sync: dict[str, float] = {}  # peer_id -> last sync timestamp
        self._start_time = time.time()
        self._external_ip: str = ""  # detected by discovery server

    @property
    def peer_id(self) -> str:
        return self._peer_id

    @property
    def port(self) -> int:
        return self.config.port

    @property
    def uptime(self) -> float:
        return time.time() - self._start_time

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Discovery: fetch peer list from discovery servers, then announce self
        from src.hub.discovery import discover_peers, announce_to_discovery
        for url in self.config.discovery_urls:
            # Discover peers first (before announcing, to avoid self-loop)
            peers = discover_peers(url)
            for p in peers:
                self.add_peer(p["address"], p["port"], p.get("peer_id", ""))
                # Also add as bootstrap target for initial data pull
                try:
                    self._announce_and_join(p["address"], p["port"])
                except Exception:
                    pass
            # Announce ourselves to the discovery server (signed if identity available)
            result = announce_to_discovery(
                url, self._peer_id, "127.0.0.1", self.config.port,
                identity_manager=self._identity,
            )
            # Remember our external IP if the server tells us
            if isinstance(result, dict):
                detected = result.get("detected_ip", "")
                if detected and detected not in ("127.0.0.1", "::1", ""):
                    self._external_ip = detected

        # Bootstrap: announce to initial peers (may include discovery-found peers)
        for addr in self.config.bootstrap:
            try:
                host, port_str = addr.rsplit(":", 1)
                port = int(port_str)
            except (ValueError, TypeError):
                host, port = addr, 8765
            self._announce_and_join(host, port)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    # ------------------------------------------------------------------
    # Peer management
    # ------------------------------------------------------------------

    def add_peer(self, address: str, port: int, peer_id: str = "") -> Optional[PeerInfo]:
        with self._lock:
            if len(self._peers) >= self.config.max_peers:
                return None
            if not peer_id:
                peer_id = hashlib.sha256(f"{address}:{port}".encode()).hexdigest()[:16]
            if peer_id == self._peer_id:
                return None
            if peer_id in self._peers:
                self._peers[peer_id].last_seen = time.time()
                return self._peers[peer_id]
            peer = PeerInfo(peer_id=peer_id, address=address, port=port)
            self._peers[peer_id] = peer
            return peer

    def remove_peer(self, peer_id: str):
        with self._lock:
            self._peers.pop(peer_id, None)
            self._last_sync.pop(peer_id, None)

    def get_peers(self) -> list[PeerInfo]:
        with self._lock:
            return list(self._peers.values())

    def get_peer_ids(self) -> list[str]:
        with self._lock:
            return list(self._peers.keys())

    # ------------------------------------------------------------------
    # Gossip
    # ------------------------------------------------------------------

    def broadcast(self, entry: LeaderboardEntry, ttl: int = 3):
        """Push a new entry to all known peers."""
        if ttl <= 0:
            return
        data = _entry_to_json(entry)
        body = json.dumps({"entries": [data], "ttl": [ttl - 1]}).encode()
        peers = self.get_peers()
        for peer in peers:
            self._post_json(peer, "/combinations", body)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_loop(self):
        last_peer_exchange = time.time()
        last_discovery_heartbeat = time.time()
        while self._running:
            try:
                # Pull from a random peer
                peers = self.get_peers()
                if peers:
                    target = random.choice(peers)
                    self._pull_from_peer(target)
            except Exception:
                pass

            # Peer exchange every N seconds
            now = time.time()
            if now - last_peer_exchange > self.config.peer_exchange_interval:
                last_peer_exchange = now
                try:
                    peers = self.get_peers()
                    if peers:
                        target = random.choice(peers)
                        self._exchange_peers(target)
                except Exception:
                    pass

            # Heartbeat to discovery servers every 120s
            if now - last_discovery_heartbeat > 120.0:
                last_discovery_heartbeat = now
                from src.hub.discovery import heartbeat_to_discovery
                for url in self.config.discovery_urls:
                    try:
                        heartbeat_to_discovery(url, self._peer_id)
                    except Exception:
                        pass

            # Clean up stale peers
            self._cleanup_stale_peers()
            time.sleep(self.config.gossip_interval)

    def _announce_and_join(self, host: str, port: int):
        """Announce ourselves to a bootstrap peer and fetch its peer list."""
        temp_id = hashlib.sha256(f"{host}:{port}".encode()).hexdigest()[:16]
        temp_peer = PeerInfo(peer_id=temp_id, address=host, port=port)
        announce_data = {
            "peer_id": self._peer_id,
            "address": "127.0.0.1",  # self-reported; peers use the connecting IP
            "port": self.config.port,
        }
        resp = self._post_json(temp_peer, "/peers/announce", json.dumps(announce_data).encode())
        if resp:
            try:
                data = json.loads(resp)
                real_peer_id = data.get("peer_id", temp_id)
                # Add the bootstrap peer with its real ID
                self.add_peer(host, port, real_peer_id)
                # Add all other peers from the response
                for p in data.get("peers", []):
                    self.add_peer(p["address"], p["port"], p.get("peer_id", ""))
                # Pull initial data
                self._pull_from_peer(PeerInfo(peer_id=real_peer_id, address=host, port=port))
            except json.JSONDecodeError:
                pass

    def _pull_from_peer(self, peer: PeerInfo):
        """GET /combinations?since=<ts> to pull new entries."""
        since = self._last_sync.get(peer.peer_id, 0)
        url = f"{peer.base_url}/combinations?since={since}&limit=100"
        resp = self._get(peer, url)
        if resp:
            try:
                data = json.loads(resp)
                entries = data.get("entries", [])
                ttl_list = data.get("ttl", [])
                for i, entry_data in enumerate(entries):
                    entry = _json_to_entry(entry_data)
                    if entry:
                        try:
                            self.db.insert_from_sync(entry)
                        except Exception:
                            pass  # duplicate or invalid
                    # Re-broadcast with decremented TTL
                    ttl = ttl_list[i] if i < len(ttl_list) else 0
                    if ttl > 0:
                        self.broadcast(entry, ttl)
                self._last_sync[peer.peer_id] = time.time()
            except json.JSONDecodeError:
                pass

    def _exchange_peers(self, peer: PeerInfo):
        """GET /peers to exchange peer lists."""
        url = f"{peer.base_url}/peers"
        resp = self._get(peer, url)
        if resp:
            try:
                data = json.loads(resp)
                for p in data.get("peers", []):
                    self.add_peer(p["address"], p["port"], p.get("peer_id", ""))
            except json.JSONDecodeError:
                pass

    def _cleanup_stale_peers(self):
        now = time.time()
        with self._lock:
            stale = [
                pid for pid, p in self._peers.items()
                if now - p.last_seen > self.config.peer_timeout
            ]
        for pid in stale:
            self.remove_peer(pid)

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, peer: PeerInfo, url: str) -> Optional[str]:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.config.request_timeout) as resp:
                peer.last_seen = time.time()
                return resp.read().decode()
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def _post_json(self, peer: PeerInfo, path: str, body: bytes) -> Optional[str]:
        url = f"{peer.base_url}{path}"
        try:
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=self.config.request_timeout) as resp:
                peer.last_seen = time.time()
                return resp.read().decode()
        except (urllib.error.URLError, OSError, ValueError):
            return None


# ------------------------------------------------------------------
# JSON serialization helpers
# ------------------------------------------------------------------

def _entry_to_json(entry: LeaderboardEntry) -> dict:
    return {
        "combo_id": entry.combo_id,
        "method_name": entry.method_name,
        "method_domain": entry.method_domain,
        "method_level": entry.method_level,
        "problem_title": entry.problem_title,
        "problem_domain": entry.problem_domain,
        "best_dimension": entry.best_dimension,
        "best_score": entry.best_score,
        "elegance": entry.elegance,
        "weirdness": entry.weirdness,
        "human_feasibility": entry.human_feasibility,
        "ai_feasibility": entry.ai_feasibility,
        "novelty": entry.novelty,
        "analogy_distance": entry.analogy_distance,
        "scaling_potential": entry.scaling_potential,
        "side_effects": entry.side_effects,
        "miner_address": entry.miner_address,
        "created_at": entry.created_at,
        "analysis_text": entry.analysis_text,
    }


def _json_to_entry(data: dict) -> Optional[LeaderboardEntry]:
    try:
        return LeaderboardEntry(
            rank=0,
            combo_id=data["combo_id"],
            method_name=data["method_name"],
            method_domain=data["method_domain"],
            method_level=data["method_level"],
            problem_title=data["problem_title"],
            problem_domain=data["problem_domain"],
            best_dimension=data.get("best_dimension", ""),
            best_score=data.get("best_score", 0),
            elegance=data.get("elegance", 0),
            weirdness=data.get("weirdness", 0),
            human_feasibility=data.get("human_feasibility", 0),
            ai_feasibility=data.get("ai_feasibility", 0),
            novelty=data.get("novelty", 0),
            analogy_distance=data.get("analogy_distance", 0),
            scaling_potential=data.get("scaling_potential", 0),
            side_effects=data.get("side_effects", 0),
            miner_address=data.get("miner_address", ""),
            created_at=data.get("created_at", 0),
            analysis_text=data.get("analysis_text", ""),
        )
    except (KeyError, TypeError):
        return None
