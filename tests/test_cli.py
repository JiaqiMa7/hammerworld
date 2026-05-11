"""Tests for CLI: src/cli/main.py"""
from __future__ import annotations

import unittest
import argparse
import sys
import io
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli.main import cmd_mine, cmd_top, cmd_search, cmd_random


class _Args:
    """Fake argparse namespace."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestCLIMine(unittest.TestCase):
    def test_mine_output(self):
        args = _Args(
            address="0xTEST", block_height=100,
            nonce=0, batch=5,
        )
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_mine(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("Generated", output)
        self.assertIn("combinations", output)

    def test_mine_different_nonce(self):
        args = _Args(address="0xTEST", block_height=100, nonce=5, batch=3)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_mine(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("3 combinations", output)


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
