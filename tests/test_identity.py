"""Tests for P2P identity management: src/hub/identity.py"""
from __future__ import annotations

import base64
import os
import tempfile
import time
import unittest

from src.hub.identity import (
    IdentityManager,
    IdentityNotAvailableError,
    verify_announce_payload,
    _CRYPTOGRAPHY_AVAILABLE,
)


class TestIdentityManagerGenerate(unittest.TestCase):
    """Key generation and persistence."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".key", delete=False)
        self.keypath = self.tmp.name
        self.tmp.close()
        os.unlink(self.keypath)  # Remove so IdentityManager creates it

    def tearDown(self):
        try:
            os.unlink(self.keypath)
        except OSError:
            pass

    def test_generate_creates_file(self):
        im = IdentityManager(self.keypath)
        if not _CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("cryptography not installed")
        self.assertTrue(im.available)
        self.assertTrue(os.path.exists(self.keypath))
        self.assertEqual(os.stat(self.keypath).st_size, 32)

    def test_generate_stable_peer_id(self):
        if not _CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("cryptography not installed")
        im = IdentityManager(self.keypath)
        pid1 = im.peer_id
        self.assertEqual(len(pid1), 40)

    def test_public_key_bytes(self):
        if not _CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("cryptography not installed")
        im = IdentityManager(self.keypath)
        pk = im.public_key_bytes
        self.assertEqual(len(pk), 32)

    def test_reload_same_key(self):
        if not _CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("cryptography not installed")
        im1 = IdentityManager(self.keypath)
        im2 = IdentityManager(self.keypath)
        self.assertEqual(im1.peer_id, im2.peer_id)
        self.assertEqual(im1.public_key_bytes, im2.public_key_bytes)


class TestIdentityManagerSign(unittest.TestCase):
    """Signing operations."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".key", delete=False)
        self.keypath = self.tmp.name
        self.tmp.close()
        os.unlink(self.keypath)

    def tearDown(self):
        try:
            os.unlink(self.keypath)
        except OSError:
            pass

    def test_sign_returns_bytes(self):
        if not _CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("cryptography not installed")
        im = IdentityManager(self.keypath)
        sig = im.sign(b"hello")
        self.assertIsInstance(sig, bytes)
        self.assertEqual(len(sig), 64)  # ed25519 signature is 64 bytes

    def test_announce_payload_has_required_keys(self):
        if not _CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("cryptography not installed")
        im = IdentityManager(self.keypath)
        payload = im.get_announce_payload("10.0.0.1", 8765)
        for key in ("timestamp", "public_key", "signature"):
            self.assertIn(key, payload)

    def test_announce_payload_empty_when_degraded(self):
        im = IdentityManager(None)  # No key path → degraded
        payload = im.get_announce_payload("10.0.0.1", 8765)
        self.assertEqual(payload, {})


class TestVerifyAnnouncePayload(unittest.TestCase):
    """Signature verification."""

    def setUp(self):
        if not _CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("cryptography not installed")
        self.tmp = tempfile.NamedTemporaryFile(suffix=".key", delete=False)
        self.keypath = self.tmp.name
        self.tmp.close()
        os.unlink(self.keypath)
        self.im = IdentityManager(self.keypath)
        self.payload = self.im.get_announce_payload("10.0.0.1", 8765)

    def tearDown(self):
        try:
            os.unlink(self.keypath)
        except OSError:
            pass

    def test_valid_signature_passes(self):
        ok, reason = verify_announce_payload(
            self.im.peer_id, "10.0.0.1", 8765,
            self.payload["timestamp"],
            self.payload["public_key"],
            self.payload["signature"],
        )
        self.assertTrue(ok, f"expected OK, got: {reason}")

    def test_replay_expired_timestamp(self):
        old_ts = time.time() - 120  # 120s ago, beyond 60s window
        ok, reason = verify_announce_payload(
            self.im.peer_id, "10.0.0.1", 8765,
            old_ts,
            self.payload["public_key"],
            self.payload["signature"],
        )
        self.assertFalse(ok)
        self.assertIn("timestamp", reason.lower())

    def test_wrong_peer_id_rejected(self):
        ok, _ = verify_announce_payload(
            "0000000000000000000000000000000000000000",
            "10.0.0.1", 8765,
            self.payload["timestamp"],
            self.payload["public_key"],
            self.payload["signature"],
        )
        self.assertFalse(ok)

    def test_wrong_public_key_rejected(self):
        # Generate a different keypair
        tmp2 = tempfile.NamedTemporaryFile(suffix=".key", delete=False)
        kp2 = tmp2.name
        tmp2.close()
        os.unlink(kp2)
        try:
            im2 = IdentityManager(kp2)
            ok, _ = verify_announce_payload(
                self.im.peer_id, "10.0.0.1", 8765,
                self.payload["timestamp"],
                base64.b64encode(im2.public_key_bytes).decode(),
                self.payload["signature"],
            )
            self.assertFalse(ok)
        finally:
            os.unlink(kp2)

    def test_wrong_signature_rejected(self):
        # Alter one byte of the signature
        sig_bytes = bytearray(base64.b64decode(self.payload["signature"]))
        sig_bytes[0] ^= 0xFF
        bad_sig = base64.b64encode(bytes(sig_bytes)).decode()
        ok, _ = verify_announce_payload(
            self.im.peer_id, "10.0.0.1", 8765,
            self.payload["timestamp"],
            self.payload["public_key"],
            bad_sig,
        )
        self.assertFalse(ok)

    def test_invalid_base64_rejected(self):
        ok, _ = verify_announce_payload(
            self.im.peer_id, "10.0.0.1", 8765,
            self.payload["timestamp"],
            "!!!not-valid-base64!!!",
            self.payload["signature"],
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
