"""Tests for Trimming analysis module."""
from __future__ import annotations

import unittest
from src.triz import trimming


class TestTrimming(unittest.TestCase):
    def test_components_detected(self):
        result = trimming.analyze("A car has an engine, transmission, and wheels")
        self.assertGreater(len(result.components), 0)

    def test_trimming_candidates(self):
        result = trimming.analyze("A system with an engine and a radiator")
        self.assertGreater(len(result.trimming_candidates), 0)

    def test_empty_description(self):
        result = trimming.analyze("")
        self.assertIsInstance(result, trimming.TrimmingResult)

    def test_candidate_structure(self):
        result = trimming.analyze("A machine with a motor")
        if result.trimming_candidates:
            c = result.trimming_candidates[0]
            self.assertIn("component", c)
            self.assertIn("replacement_strategy", c)
            self.assertIn("feasibility", c)

    def test_preserved_functions(self):
        result = trimming.analyze("A pump moves water")
        if result.preserved_functions:
            self.assertTrue(len(result.preserved_functions[0]) > 0)


if __name__ == "__main__":
    unittest.main()
