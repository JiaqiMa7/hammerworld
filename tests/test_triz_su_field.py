"""Tests for Su-Field analysis module."""
from __future__ import annotations

import unittest
from src.triz import su_field


class TestSuFieldAnalyze(unittest.TestCase):
    def test_harmful_interaction(self):
        result = su_field.analyze("The engine vibration damages the mounting bracket")
        self.assertIn(result.substance1, ["engine", "vibration", "bracket", "the"])
        self.assertEqual(result.interaction_type, "harmful")
        self.assertTrue(len(result.transformation_suggestions) > 0)
        self.assertIn("harmful", str(result.transformation_suggestions).lower())

    def test_useful_interaction(self):
        result = su_field.analyze("A motor rotates the wheel smoothly")
        self.assertIn(result.interaction_type, ["useful", "insufficient"])
        self.assertTrue(len(result.substance1) > 0)

    def test_empty_description(self):
        result = su_field.analyze("")
        self.assertTrue(len(result.substance1) > 0)
        self.assertIsInstance(result.is_complete, bool)

    def test_transformation_suggestions(self):
        result = su_field.analyze("The fast car damages the road surface")
        self.assertEqual(result.interaction_type, "harmful")
        self.assertGreater(len(result.transformation_suggestions), 0)

    def test_insufficient_interaction(self):
        result = su_field.analyze("The pump barely moves water, the flow is too slow")
        self.assertEqual(result.interaction_type, "insufficient")


if __name__ == "__main__":
    unittest.main()
