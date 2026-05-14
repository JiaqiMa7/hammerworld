"""Tests for CLI: src/cli/main.py"""
from __future__ import annotations

import os
import unittest
import argparse
import sys
import io
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))


class _Args:
    """Fake argparse namespace."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


from src.cli.main import cmd_top, cmd_search, cmd_random


class TestCLIMine(unittest.TestCase):
    def setUp(self):
        # Ensure fake API key is set and config is fresh
        os.environ["HAMMERWORLD_API_KEY"] = "sk-test-cli"
        from src.engine.config import HammerConfig
        HammerConfig.reload()
        # Patch the OpenAIProvider to avoid real API calls
        import src.evaluation.providers as p
        self._orig_provider = p.OpenAIProvider
        class _FakeProvider:
            def __init__(self, api_key=None, api_base=None, model=None):
                pass
            def generate(self, system_prompt, user_prompt):
                return '```json\n{"scores": [{"dimension": "elegance", "score": 7.5, "explanation": "test"}], "analysis_text": "Test analysis."}\n```'
        p.OpenAIProvider = _FakeProvider

    def tearDown(self):
        import src.evaluation.providers as p
        p.OpenAIProvider = self._orig_provider
        os.environ.pop("HAMMERWORLD_API_KEY", None)

    def test_mine_output(self):
        from src.cli.main import cmd_mine
        args = _Args(
            address="0xTEST", block_height=100,
            nonce=0, batch=3, db=":memory:",
            api_base=None, model=None, parallel=1, threshold=8.0,
            methods=None, problems=None,
            methods_collection=None, problems_collection=None,
            method_step=0, problem_step=0, problem_offset=0, max_attempts=0,
        )
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_mine(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("Matrix", output)
        self.assertIn("combinations", output.lower())

    def test_mine_different_nonce(self):
        from src.cli.main import cmd_mine
        args = _Args(
            address="0xTEST", block_height=100, nonce=5, batch=3, db=":memory:",
            api_base=None, model=None, parallel=1, threshold=8.0,
            methods=None, problems=None,
            methods_collection=None, problems_collection=None,
            method_step=0, problem_step=0, problem_offset=0, max_attempts=0,
        )
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_mine(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("Saved", output)


class TestCLITop(unittest.TestCase):
    def test_top_empty_db(self):
        import tempfile
        db_path = tempfile.mktemp(suffix=".db")
        args = _Args(dimension=None, domain=None, level=None,
                      limit=10, db=db_path)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_top(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        # Should not crash, just print header even if empty
        self.assertIn("Rank", output)

    def test_top_with_dimension(self):
        import tempfile
        db_path = tempfile.mktemp(suffix=".db")
        args = _Args(dimension="weirdness", domain=None, level=None,
                      limit=5, db=db_path)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_top(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("Rank", output)


class TestCLISearch(unittest.TestCase):
    def test_search_no_match(self):
        import tempfile
        db_path = tempfile.mktemp(suffix=".db")
        args = _Args(query="nothing", dimension=None, limit=5, db=db_path)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_search(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("results", output.lower())


class TestCLIRandom(unittest.TestCase):
    def test_random_from_empty(self):
        import tempfile
        db_path = tempfile.mktemp(suffix=".db")
        args = _Args(dimension=None, domain=None, count=5,
                      address="0xV", db=db_path)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_random(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("Random draw", output)


class TestCLIIdentity(unittest.TestCase):
    def setUp(self):
        self._saved_config = _load_user_config()
        self._had_address = "HAMMERWORLD_ADDRESS" in self._saved_config
        self._identity_path = Path.home() / ".hammerworld" / "identity"
        self._had_identity = self._identity_path.exists()
        if self._had_identity:
            self._saved_identity_bytes = self._identity_path.read_bytes()
        # Clear for test isolation
        self._clear_config_key("HAMMERWORLD_ADDRESS")
        if self._identity_path.exists():
            self._identity_path.unlink()
        from src.engine.config import HammerConfig
        HammerConfig.reload()

    @staticmethod
    def _clear_config_key(key):
        """Remove a key from ~/.hammerworld/config entirely."""
        config_path = Path.home() / ".hammerworld" / "config"
        if not config_path.exists():
            return
        lines = config_path.read_text().splitlines()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _ = stripped.split("=", 1)
                if k.strip() == key:
                    continue
            new_lines.append(line)
        config_path.write_text("\n".join(new_lines) + "\n")

    def tearDown(self):
        from src.cli.main import _save_user_config
        self._clear_config_key("HAMMERWORLD_ADDRESS")
        if self._identity_path.exists():
            self._identity_path.unlink()
        if self._had_address:
            addr = self._saved_config.get("HAMMERWORLD_ADDRESS", "")
            if addr:
                _save_user_config("HAMMERWORLD_ADDRESS", addr)
        if self._had_identity:
            self._identity_path.write_bytes(self._saved_identity_bytes)
            os.chmod(str(self._identity_path), 0o600)
        from src.engine.config import HammerConfig
        HammerConfig.reload()

    def test_identity_show_no_config(self):
        from src.cli.main import cmd_identity
        args = _Args(set_address=None)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_identity(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("No address configured", output)

    def test_identity_set_and_show(self):
        from src.cli.main import cmd_identity
        args_set = _Args(set_address="0xTEST123")
        args_show = _Args(set_address=None)

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_identity(args_set)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("Identity set: 0xTEST123", output)

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_identity(args_show)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("0xTEST123", output)

    def test_get_user_address_from_config(self):
        from src.cli.main import _get_user_address, _save_user_config
        from src.engine.config import HammerConfig
        _save_user_config("HAMMERWORLD_ADDRESS", "0xCONFIGADDR")
        HammerConfig.reload()
        try:
            args = _Args(address=None)
            addr = _get_user_address(args, "0xFALLBACK")
            self.assertEqual(addr, "0xCONFIGADDR")
        finally:
            _save_user_config("HAMMERWORLD_ADDRESS", "")
            HammerConfig.reload()

    def test_get_user_address_explicit_flag(self):
        from src.cli.main import _get_user_address
        args = _Args(address="0xEXPLICIT")
        addr = _get_user_address(args, "0xFALLBACK")
        self.assertEqual(addr, "0xEXPLICIT")

    def test_get_user_address_fallback(self):
        from src.cli.main import _get_user_address
        from src.engine.config import HammerConfig
        args = _Args(address=None)
        addr = _get_user_address(args, "0xFALLBACK", auto_generate=False)
        self.assertEqual(addr, "0xFALLBACK")
        # Reload in case auto-generate from another test polluted config
        HammerConfig.reload()

    def test_get_user_address_empty_string(self):
        from src.cli.main import _get_user_address
        from src.engine.config import HammerConfig
        args = _Args(address="")
        addr = _get_user_address(args, "0xFALLBACK", auto_generate=False)
        self.assertEqual(addr, "0xFALLBACK")
        HammerConfig.reload()

    def test_get_user_address_auto_generate(self):
        from src.cli.main import _get_user_address
        self._clear_config_key("HAMMERWORLD_ADDRESS")
        try:
            args = _Args(address=None)
            addr = _get_user_address(args, "0xFALLBACK", auto_generate=True)
            self.assertTrue(addr.startswith("0x"))
            self.assertEqual(len(addr), 42)  # 0x + 40 hex chars
            # Verify it was persisted in config
            config = _load_user_config()
            self.assertEqual(config.get("HAMMERWORLD_ADDRESS"), addr)
            # Verify identity file was created
            self.assertTrue(self._identity_path.exists(), "Identity file should be created")
            self.assertEqual(len(self._identity_path.read_bytes()), 32)
        finally:
            self._clear_config_key("HAMMERWORLD_ADDRESS")

    def test_auto_generate_creates_key_file_with_correct_permissions(self):
        """Auto-generation should create ~/.hammerworld/identity with 0600 perms."""
        from src.cli.main import _get_user_address
        self._clear_config_key("HAMMERWORLD_ADDRESS")
        try:
            args = _Args(address=None)
            _get_user_address(args, "0xFALLBACK", auto_generate=True)
            self.assertTrue(self._identity_path.exists())
            stat = os.stat(self._identity_path)
            self.assertEqual(stat.st_mode & 0o777, 0o600)
        finally:
            self._clear_config_key("HAMMERWORLD_ADDRESS")

    def test_auto_generate_address_matches_identity_key(self):
        """Address in config must match address derived from the identity file."""
        from src.cli.main import _get_user_address
        from src.hub.user_identity import ensure_user_identity, get_user_address
        self._clear_config_key("HAMMERWORLD_ADDRESS")
        try:
            args = _Args(address=None)
            cli_addr = _get_user_address(args, "0xFALLBACK", auto_generate=True)
            identity = ensure_user_identity()
            key_addr = get_user_address(identity)
            self.assertEqual(cli_addr, key_addr)
        finally:
            self._clear_config_key("HAMMERWORLD_ADDRESS")

    def test_identity_shows_key_status(self):
        """cmd_identity should show 'Backed by: Ed25519 private key' when key exists."""
        from src.cli.main import _get_user_address
        self._clear_config_key("HAMMERWORLD_ADDRESS")
        try:
            # First generate the key-backed identity
            args = _Args(address=None)
            _get_user_address(args, "0xFALLBACK", auto_generate=True)
            # Now run cmd_identity to show it
            from src.cli.main import cmd_identity
            show_args = _Args(set_address=None)
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                cmd_identity(show_args)
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            self.assertIn("Backed by: Ed25519 private key", output)
        finally:
            self._clear_config_key("HAMMERWORLD_ADDRESS")

    def test_identity_shows_no_key_when_manually_set(self):
        """Manually-set address should say 'not backed by key'."""
        from src.cli.main import cmd_identity
        self._clear_config_key("HAMMERWORLD_ADDRESS")
        try:
            # Set address manually (no key file)
            set_args = _Args(set_address="0xMANUAL12345678901234567890123456789012345678")
            cmd_identity(set_args)
            # Now show
            show_args = _Args(set_address=None)
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                cmd_identity(show_args)
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            self.assertIn("Backed by: none", output)
        finally:
            self._clear_config_key("HAMMERWORLD_ADDRESS")

    def test_keygen_set_identity_creates_identity_file(self):
        """cmd_keygen --set-identity should copy key to ~/.hammerworld/identity."""
        import tempfile
        from src.cli.main import cmd_keygen
        self._clear_config_key("HAMMERWORLD_ADDRESS")
        tmp = tempfile.mktemp(suffix=".key")
        try:
            args = _Args(output=tmp, force=True, set_identity=True)
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                cmd_keygen(args)
            finally:
                sys.stdout = old_stdout
            self.assertTrue(self._identity_path.exists(), "Identity file should be created")
            self.assertEqual(len(self._identity_path.read_bytes()), 32)
            stat = os.stat(self._identity_path)
            self.assertEqual(stat.st_mode & 0o777, 0o600)
        finally:
            self._clear_config_key("HAMMERWORLD_ADDRESS")
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_load_save_user_config(self):
        from src.cli.main import _save_user_config
        from src.engine.config import HammerConfig
        _save_user_config("HAMMERWORLD_ADDRESS", "0xSAVETEST")
        try:
            HammerConfig.reload()
            self.assertEqual(HammerConfig.load().address, "0xSAVETEST")
        finally:
            _save_user_config("HAMMERWORLD_ADDRESS", "")

    def test_keygen_with_set_identity(self):
        import tempfile, os, base64
        from src.cli.main import cmd_keygen
        tmp = tempfile.mktemp(suffix=".key")
        args = _Args(output=tmp, force=True, set_identity=True)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_keygen(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
            os.unlink(tmp) if os.path.exists(tmp) else None
        self.assertIn("Address derived from key:", output)
        self.assertIn("Stored in ~/.hammerworld/config", output)


def _load_user_config():
    """Local helper to load config without importing from main."""
    config = {}
    config_path = Path.home() / ".hammerworld" / "config"
    if config_path.exists():
        for line in config_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            config[k.strip()] = v.strip().strip('"').strip("'")
    return config


if __name__ == "__main__":
    unittest.main()
