"""Tests for Cause-Effect Chain Analysis module."""
from __future__ import annotations

import unittest
from src.triz import cause_effect


class TestCauseEffectChain(unittest.TestCase):
    def test_simple_cause_effect(self):
        result = cause_effect.analyze(
            "The engine overheats because the cooling system is too small"
        )
        self.assertGreater(len(result.chain), 0)
        self.assertGreater(len(result.root_causes), 0)

    def test_so_connector(self):
        result = cause_effect.analyze(
            "The bearing wore out, so the shaft vibrates excessively"
        )
        self.assertGreater(len(result.chain), 0)

    def test_empty_description(self):
        result = cause_effect.analyze("")
        self.assertEqual(len(result.chain), 0)
        self.assertEqual(len(result.root_causes), 0)

    def test_chain_structure(self):
        result = cause_effect.analyze("A causes B because C makes D")
        for link in result.chain:
            self.assertTrue(len(link.cause) > 0)
            self.assertTrue(len(link.effect) > 0)

    def test_no_causal_words(self):
        result = cause_effect.analyze("This is a simple description of a system")
        self.assertIsInstance(result, cause_effect.CauseEffectChain)


if __name__ == "__main__":
    unittest.main()
