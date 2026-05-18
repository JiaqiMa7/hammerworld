"""Tests for STC Operator module."""
from __future__ import annotations

import unittest
from src.triz import stc_operator


class TestSTCOperator(unittest.TestCase):
    def test_six_dimensions(self):
        result = stc_operator.analyze("A bridge that is too expensive")
        self.assertEqual(len(result.dimensions), 6)

    def test_dimension_types(self):
        result = stc_operator.analyze("test")
        dims = {(d.dimension, d.extreme) for d in result.dimensions}
        for dim in ["size", "time", "cost"]:
            self.assertIn((dim, "plus"), dims)
            self.assertIn((dim, "minus"), dims)

    def test_insights_generated(self):
        result = stc_operator.analyze("A fast processor generates too much heat")
        for d in result.dimensions:
            self.assertTrue(len(d.insight) > 0)

    def test_empty_description(self):
        result = stc_operator.analyze("")
        self.assertEqual(len(result.dimensions), 6)

    def test_key_insights(self):
        result = stc_operator.analyze("A complex machine")
        self.assertIsInstance(result.key_insights, list)


if __name__ == "__main__":
    unittest.main()
