"""Tests for Resource Analysis module."""
from __future__ import annotations

import unittest
from src.triz import resource_analysis


class TestResourceAnalysis(unittest.TestCase):
    def test_detects_substances(self):
        result = resource_analysis.analyze("The metal engine uses water for cooling")
        self.assertGreater(len(result.substances), 0)

    def test_detects_fields(self):
        result = resource_analysis.analyze("Electric motor generates magnetic field with thermal losses")
        self.assertTrue(len(result.fields) > 0)

    def test_empty_description(self):
        result = resource_analysis.analyze("")
        total = sum(len(getattr(result, t, []))
                    for t in ["substances", "fields", "space", "time"])
        self.assertEqual(total, 0)

    def test_resource_types_present(self):
        result = resource_analysis.analyze("test system")
        for attr in ["substances", "fields", "space", "time", "information", "function"]:
            self.assertTrue(hasattr(result, attr))

    def test_no_keywords(self):
        result = resource_analysis.analyze("xyzzy qwerty blarg")
        self.assertEqual(len(result.substances), 0)


if __name__ == "__main__":
    unittest.main()
