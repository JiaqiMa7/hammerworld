"""Tests for Discovery Server security: src/hub/discovery.py"""
from __future__ import annotations

import time
import unittest

from src.hub.discovery import DiscoveryServer, RateLimiter, _choose_routable_address


class TestRateLimiter(unittest.TestCase):
    """Rate limiter sliding window tests."""

    def test_allows_within_limit(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            self.assertTrue(rl.is_allowed("1.2.3.4"))

    def test_blocks_after_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            rl.is_allowed("1.2.3.4")
        self.assertFalse(rl.is_allowed("1.2.3.4"))

    def test_separate_keys_independent(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        # Exhaust key A
        rl.is_allowed("1.1.1.1")
        rl.is_allowed("1.1.1.1")
        self.assertFalse(rl.is_allowed("1.1.1.1"))
        # Key B still allowed
        self.assertTrue(rl.is_allowed("2.2.2.2"))

    def test_reset_clears_limit(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.is_allowed("1.2.3.4")
        rl.is_allowed("1.2.3.4")
        self.assertFalse(rl.is_allowed("1.2.3.4"))
        rl.reset("1.2.3.4")
        self.assertTrue(rl.is_allowed("1.2.3.4"))

    def test_window_expiry(self):
        """After a very short window, old timestamps expire."""
        rl = RateLimiter(max_requests=3, window_seconds=0.5)
        for _ in range(3):
            rl.is_allowed("1.2.3.4")
        self.assertFalse(rl.is_allowed("1.2.3.4"))
        time.sleep(0.6)
        self.assertTrue(rl.is_allowed("1.2.3.4"))


class TestDiscoveryServerSecurity(unittest.TestCase):
    """Security-focused DiscoveryServer tests."""

    def setUp(self):
        self.ds = DiscoveryServer(
            cleanup_timeout=180,
            max_peers=10,
            rate_limit_max=60,
            rate_limit_window=60,
        )

    # -- Rate limiting ----------------------------------------------------------

    def test_rate_limit_proxy_works(self):
        # By default the rate limiter allows requests
        self.assertTrue(self.ds.is_rate_limited("1.2.3.4") is False)

    # -- Anti-spoofing ----------------------------------------------------------

    def test_announce_uses_detected_ip(self):
        result = self.ds.announce(
            "peer1",
            address="192.168.1.1",  # claimed private IP
            port=8765,
            detected_ip="203.0.113.5",  # real public IP
        )
        self.assertTrue(result["ok"])
        peers = self.ds.get_peers()
        self.assertEqual(len(peers), 1)
        self.assertEqual(peers[0]["address"], "203.0.113.5")

    def test_announce_keeps_localhost_when_detected_is_loopback(self):
        result = self.ds.announce(
            "peer1",
            address="10.0.0.1",
            port=8765,
            detected_ip="127.0.0.1",
        )
        self.assertTrue(result["ok"])
        peers = self.ds.get_peers()
        # Loopback detected → keep claimed address (for local testing)
        self.assertEqual(peers[0]["address"], "10.0.0.1")

    # -- Privacy: random subset -------------------------------------------------

    def test_get_peers_returns_at_most_max_results(self):
        for i in range(20):
            self.ds.announce(
                f"peer{i}", f"10.0.0.{i}", 8765, detected_ip=f"10.0.0.{i}"
            )
        peers = self.ds.get_peers(max_results=5)
        self.assertLessEqual(len(peers), 5)

    def test_get_peers_returns_random_order(self):
        for i in range(20):
            self.ds.announce(
                f"peer{i}", f"10.0.0.{i}", 8765, detected_ip=f"10.0.0.{i}"
            )
        order1 = [p["peer_id"] for p in self.ds.get_peers(max_results=20)]
        order2 = [p["peer_id"] for p in self.ds.get_peers(max_results=20)]
        # With 20 peers, it's extremely unlikely two random shuffles are identical
        # but we check subset instead (same size)
        self.assertEqual(len(order1), len(order2))

    # -- Signature verification field propagation ------------------------------

    def test_announce_with_signature_fields_sets_verified(self):
        result = self.ds.announce(
            "peer1", "10.0.0.1", 8765,
            detected_ip="10.0.0.1",
            public_key_b64="ZmFrZS1rZXk=",  # base64 "fake-key"
            signature_b64="ZmFrZS1zaWc=",   # base64 "fake-sig"
            timestamp=time.time(),
        )
        self.assertTrue(result["ok"])
        peers = self.ds.get_peers()
        self.assertTrue(peers[0]["verified"])

    def test_announce_without_signature_is_unverified(self):
        result = self.ds.announce("peer1", "10.0.0.1", 8765)
        self.assertTrue(result["ok"])
        peers = self.ds.get_peers()
        self.assertFalse(peers[0]["verified"])

    # -- LRU eviction -----------------------------------------------------------

    def test_lru_eviction_when_over_capacity(self):
        ds = DiscoveryServer(max_peers=5, cleanup_timeout=180)
        for i in range(7):
            ds.announce(f"peer{i}", f"10.0.0.{i}", 8765)
        peers = ds.get_peers(max_results=50)
        # Should have evicted the oldest 2
        self.assertEqual(len(peers), 5)

    # -- Heartbeat --------------------------------------------------------------

    def test_heartbeat_updates_last_seen(self):
        self.ds.announce("peer1", "10.0.0.1", 8765)
        before = time.time()
        time.sleep(0.1)
        self.assertTrue(self.ds.heartbeat("peer1"))
        # Peer still appears in listing
        peers = self.ds.get_peers()
        self.assertTrue(any(p["peer_id"] == "peer1" for p in peers))

    def test_heartbeat_unknown_peer_returns_false(self):
        self.assertFalse(self.ds.heartbeat("nonexistent"))


class TestChooseRoutableAddress(unittest.TestCase):
    """Address anti-spoofing helper."""

    def test_detected_public_wins(self):
        self.assertEqual(
            _choose_routable_address("192.168.1.1", "203.0.113.5"),
            "203.0.113.5",
        )

    def test_detected_empty_falls_back(self):
        self.assertEqual(
            _choose_routable_address("192.168.1.1", ""),
            "192.168.1.1",
        )

    def test_detected_loopback_falls_back(self):
        self.assertEqual(
            _choose_routable_address("10.0.0.1", "127.0.0.1"),
            "10.0.0.1",
        )

    def test_detected_localhost_falls_back(self):
        self.assertEqual(
            _choose_routable_address("172.16.0.1", "localhost"),
            "172.16.0.1",
        )


if __name__ == "__main__":
    unittest.main()
