"""Tests for HTTP API server: src/hub/server.py"""
from __future__ import annotations

import json
import threading
import time
import unittest
import urllib.request
import urllib.error

from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry
from src.hub.peer import PeerConfig
from src.hub.server import HubServer, HubAPI


def _find_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestHubAPI(unittest.TestCase):
    """Test HubAPI logic without HTTP transport."""

    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.config = PeerConfig(port=9999)
        from src.hub.peer import PeerManager
        self.pm = PeerManager(self.db, self.config)
        self.api = HubAPI(self.db, self.pm)

    def test_health(self):
        resp = self.api.handle_health()
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(len(resp["peer_id"]) > 0)
        self.assertEqual(resp["entries"], 0)

    def test_stats(self):
        resp = self.api.handle_stats()
        self.assertIn("peer_id", resp)
        self.assertIn("entries", resp)
        self.assertIn("peers", resp)
        self.assertIn("uptime", resp)

    def test_get_combinations_empty(self):
        resp = self.api.handle_get_combinations("/combinations?since=0")
        self.assertEqual(resp["entries"], [])

    def test_get_combinations_with_data(self):
        t = time.time()
        entry = LeaderboardEntry(
            rank=0, run_id="c1", combo_group_id="c1_g",
            method_name="M", method_domain="D",
            method_level=2, problem_title="P", problem_domain="medicine",
            best_dimension="elegance", best_score=9.0,
            elegance=9.0, weirdness=5.0, human_feasibility=5.0,
            ai_feasibility=5.0, novelty=5.0, analogy_distance=5.0,
            scaling_potential=5.0, side_effects=5.0,
            miner_address="0xM", created_at=t,
        )
        self.db.insert_from_sync(entry)
        resp = self.api.handle_get_combinations("/combinations?since=0&limit=10")
        self.assertEqual(len(resp["entries"]), 1)
        self.assertEqual(resp["entries"][0]["combo_id"], "c1")

    def test_post_combinations(self):
        data = {
            "entries": [{
                "combo_id": "remote_1",
                "method_name": "RemoteM", "method_domain": "Remote",
                "method_level": 1, "problem_title": "RemoteP",
                "problem_domain": "energy", "best_dimension": "novelty",
                "best_score": 8.5, "elegance": 5.0, "weirdness": 5.0,
                "human_feasibility": 5.0, "ai_feasibility": 5.0,
                "novelty": 8.5, "analogy_distance": 5.0,
                "scaling_potential": 5.0, "side_effects": 5.0,
                "miner_address": "0xREMOTE", "created_at": time.time(),
            }],
            "ttl": [3],
        }
        resp = self.api.handle_post_combinations(data)
        self.assertEqual(resp["accepted"], 1)
        self.assertEqual(self.db.total_entries(), 1)

    def test_post_combinations_invalid_skipped(self):
        data = {"entries": [{"bad": "data"}], "ttl": [3]}
        resp = self.api.handle_post_combinations(data)
        self.assertEqual(resp["accepted"], 0)

    def test_announce_adds_peer(self):
        resp = self.api.handle_announce({
            "peer_id": "peer_x", "address": "10.0.0.5", "port": 8765,
        })
        self.assertEqual(resp["peer_id"], self.pm.peer_id)
        self.assertEqual(len(self.pm.get_peers()), 1)


class TestHubServerIntegration(unittest.TestCase):
    """Start a real HTTP server and test it via urllib."""

    @classmethod
    def setUpClass(cls):
        cls.port = _find_free_port()
        cls.db = LeaderboardDB(":memory:")
        config = PeerConfig(port=cls.port)
        cls.server = HubServer(cls.db, config)
        cls._thread = threading.Thread(target=cls._serve, daemon=True)
        cls._thread.start()
        time.sleep(0.2)  # Wait for server to start

    @classmethod
    def _serve(cls):
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_health_endpoint(self):
        resp = urllib.request.urlopen(self._url("/health"))
        data = json.loads(resp.read())
        self.assertEqual(data["status"], "ok")

    def test_stats_endpoint(self):
        resp = urllib.request.urlopen(self._url("/stats"))
        data = json.loads(resp.read())
        self.assertIn("entries", data)

    def test_get_combinations_empty(self):
        resp = urllib.request.urlopen(self._url("/combinations?since=0"))
        data = json.loads(resp.read())
        self.assertEqual(len(data["entries"]), 0)

    def test_post_and_get_combinations(self):
        body = json.dumps({
            "entries": [{
                "combo_id": "http_test_1",
                "method_name": "TestM", "method_domain": "TestD",
                "method_level": 1, "problem_title": "TestP",
                "problem_domain": "medicine", "best_dimension": "weirdness",
                "best_score": 9.2, "elegance": 5.0, "weirdness": 9.2,
                "human_feasibility": 5.0, "ai_feasibility": 5.0,
                "novelty": 5.0, "analogy_distance": 5.0,
                "scaling_potential": 5.0, "side_effects": 5.0,
                "miner_address": "0xHTTP", "created_at": time.time(),
            }],
            "ttl": [2],
        }).encode()
        req = urllib.request.Request(self._url("/combinations"), data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        self.assertEqual(data["accepted"], 1)

        # Now GET should return it
        resp2 = urllib.request.urlopen(self._url("/combinations?since=0"))
        data2 = json.loads(resp2.read())
        self.assertEqual(len(data2["entries"]), 1)

    def test_peers_endpoint(self):
        resp = urllib.request.urlopen(self._url("/peers"))
        data = json.loads(resp.read())
        self.assertIn("peers", data)

    def test_announce_endpoint(self):
        body = json.dumps({
            "peer_id": "announce_test", "address": "10.0.0.99", "port": 9876,
        }).encode()
        req = urllib.request.Request(self._url("/peers/announce"), data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        self.assertIn("peer_id", data)

    def test_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self._url("/nonexistent"))
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
