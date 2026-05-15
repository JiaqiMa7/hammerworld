"""Tests for P2P peer management: src/hub/peer.py"""
from __future__ import annotations

import unittest
import time

from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry
from src.hub.peer import (
    PeerManager, PeerConfig, PeerInfo,
    _entry_to_json, _json_to_entry,
)


class TestPeerInfo(unittest.TestCase):
    def test_create(self):
        pi = PeerInfo(peer_id="abc", address="1.2.3.4", port=8765)
        self.assertEqual(pi.peer_id, "abc")
        self.assertEqual(pi.address, "1.2.3.4")
        self.assertEqual(pi.port, 8765)
        self.assertGreater(pi.last_seen, 0)

    def test_base_url(self):
        pi = PeerInfo(peer_id="x", address="10.0.0.1", port=9999)
        self.assertEqual(pi.base_url, "http://10.0.0.1:9999")


class TestEntrySerialization(unittest.TestCase):
    def test_roundtrip(self):
        entry = LeaderboardEntry(
            rank=0, run_id="c1", combo_group_id="c1_g",
            method_name="M", method_domain="D",
            method_level=2, problem_title="P", problem_domain="medicine",
            best_dimension="weirdness", best_score=9.0,
            elegance=5.0, weirdness=9.0, human_feasibility=6.0,
            ai_feasibility=5.0, novelty=7.0, analogy_distance=3.0,
            scaling_potential=4.0, side_effects=5.0,
            miner_address="0xMINER", created_at=123456.0,
        )
        data = _entry_to_json(entry)
        restored = _json_to_entry(data)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.run_id, "c1")
        self.assertEqual(restored.combo_id, "c1")  # backward compat
        self.assertEqual(restored.combo_group_id, "c1_g")
        self.assertEqual(restored.best_score, 9.0)
        self.assertEqual(restored.miner_address, "0xMINER")

    def test_roundtrip_old_format(self):
        """Old peers send only combo_id — should be treated as both run_id and combo_group_id."""
        data = {"combo_id": "old_1", "method_name": "M", "method_domain": "D",
                "method_level": 2, "problem_title": "P", "problem_domain": "energy",
                "best_dimension": "novelty", "best_score": 7.0}
        entry = _json_to_entry(data)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.run_id, "old_1")
        self.assertEqual(entry.combo_group_id, "old_1")

    def test_invalid_json(self):
        self.assertIsNone(_json_to_entry({}))
        self.assertIsNone(_json_to_entry({"combo_id": "x"}))


class TestPeerManager(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.config = PeerConfig(port=9999)
        self.manager = PeerManager(self.db, self.config)

    def test_init(self):
        self.assertTrue(len(self.manager.peer_id) > 0)
        self.assertEqual(self.manager.port, 9999)
        self.assertEqual(len(self.manager.get_peers()), 0)

    def test_add_peer(self):
        peer = self.manager.add_peer("10.0.0.1", 8765)
        self.assertIsNotNone(peer)
        self.assertEqual(len(self.manager.get_peers()), 1)

    def test_add_peer_same_id_returns_none(self):
        # Adding self should be rejected
        peer = self.manager.add_peer("127.0.0.1", 9999, self.manager.peer_id)
        self.assertIsNone(peer)

    def test_add_peer_duplicate_updates_last_seen(self):
        self.manager.add_peer("10.0.0.1", 8765)
        self.assertEqual(len(self.manager.get_peers()), 1)
        # Adding same peer should not create a new entry
        self.manager.add_peer("10.0.0.1", 8765)
        self.assertEqual(len(self.manager.get_peers()), 1)
        # last_seen should be recent
        peer = self.manager.get_peers()[0]
        self.assertLess(time.time() - peer.last_seen, 1.0)

    def test_remove_peer(self):
        peer = self.manager.add_peer("10.0.0.1", 8765)
        self.assertEqual(len(self.manager.get_peers()), 1)
        self.manager.remove_peer(peer.peer_id)
        self.assertEqual(len(self.manager.get_peers()), 0)

    def test_insert_from_sync(self):
        entry = LeaderboardEntry(
            rank=0, run_id="sync_test", combo_group_id="sync_test_g",
            method_name="M", method_domain="D",
            method_level=2, problem_title="P", problem_domain="medicine",
            best_dimension="elegance", best_score=8.5,
            elegance=8.5, weirdness=5.0, human_feasibility=5.0,
            ai_feasibility=5.0, novelty=5.0, analogy_distance=5.0,
            scaling_potential=5.0, side_effects=5.0,
            miner_address="0xREMOTE", created_at=time.time(),
        )
        result = self.db.insert_from_sync(entry)
        self.assertTrue(result)
        self.assertEqual(self.db.total_entries(), 1)

    def test_insert_from_sync_duplicate_returns_false(self):
        t = time.time()
        entry = LeaderboardEntry(
            rank=0, run_id="dup_test", combo_group_id="dup_test_g",
            method_name="M", method_domain="D",
            method_level=2, problem_title="P", problem_domain="medicine",
            best_dimension="elegance", best_score=8.0,
            elegance=8.0, weirdness=5.0, human_feasibility=5.0,
            ai_feasibility=5.0, novelty=5.0, analogy_distance=5.0,
            scaling_potential=5.0, side_effects=5.0,
            miner_address="0xR", created_at=t,
        )
        self.assertTrue(self.db.insert_from_sync(entry))
        # Same entry with older timestamp should be rejected
        entry2 = LeaderboardEntry(
            rank=0, run_id="dup_test", combo_group_id="dup_test_g",
            method_name="M", method_domain="D",
            method_level=2, problem_title="P", problem_domain="medicine",
            best_dimension="elegance", best_score=7.0,
            elegance=7.0, weirdness=5.0, human_feasibility=5.0,
            ai_feasibility=5.0, novelty=5.0, analogy_distance=5.0,
            scaling_potential=5.0, side_effects=5.0,
            miner_address="0xR2", created_at=t - 10,
        )
        self.assertFalse(self.db.insert_from_sync(entry2))
        self.assertEqual(self.db.total_entries(), 1)

    def test_get_since(self):
        t0 = time.time()
        for i in range(3):
            entry = LeaderboardEntry(
                rank=0, run_id=f"since_test_{i}", combo_group_id=f"since_test_g_{i}",
                method_name="M", method_domain="D",
                method_level=2, problem_title="P", problem_domain="medicine",
                best_dimension="elegance", best_score=5.0 + i,
                elegance=5.0, weirdness=5.0, human_feasibility=5.0,
                ai_feasibility=5.0, novelty=5.0, analogy_distance=5.0,
                scaling_potential=5.0, side_effects=5.0,
                miner_address="0xR", created_at=t0 + i,
            )
            self.db.insert_from_sync(entry)
        # get_since should return entries after the timestamp
        got = self.db.get_since(t0 + 0.5, limit=10)
        self.assertEqual(len(got), 2)  # indices 1 and 2

    def test_get_peer_ids(self):
        self.manager.add_peer("10.0.0.1", 8765)
        self.manager.add_peer("10.0.0.2", 8766)
        ids = self.manager.get_peer_ids()
        self.assertEqual(len(ids), 2)


if __name__ == "__main__":
    unittest.main()
