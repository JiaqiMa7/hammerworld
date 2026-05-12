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
    @classmethod
    def setUpClass(cls):
        # Ensure fake API key is set so cmd_mine doesn't exit
        os.environ["HAMMERWORLD_API_KEY"] = "sk-test-cli"

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("HAMMERWORLD_API_KEY", None)

    def setUp(self):
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


if __name__ == "__main__":
    unittest.main()
