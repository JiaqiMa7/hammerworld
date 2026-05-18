"""Tests for 9-Windows analysis module."""
from __future__ import annotations

import unittest
from src.triz import nine_windows


class TestNineWindows(unittest.TestCase):
    def test_system_detected(self):
        result = nine_windows.analyze("A coffee cup keeps drinks hot")
        self.assertEqual(result.current_system, "coffee")
        self.assertTrue(len(result.system_present) > 0)

    def test_all_windows_filled(self):
        result = nine_windows.analyze("An electric car battery")
        for key in ["supersystem_past", "supersystem_present", "supersystem_future",
                     "system_past", "system_present", "system_future",
                     "subsystem_past", "subsystem_present", "subsystem_future"]:
            self.assertTrue(hasattr(result, key))

    def test_empty_description(self):
        result = nine_windows.analyze("")
        self.assertTrue(len(result.system_present) > 0)

    def test_as_grid(self):
        result = nine_windows.analyze("A simple machine")
        grid = result.as_grid
        self.assertIn("supersystem", grid)
        self.assertIn("system", grid)
        self.assertIn("subsystem", grid)

    def test_short_description(self):
        result = nine_windows.analyze("car")
        self.assertEqual(result.current_system, "car")


if __name__ == "__main__":
    unittest.main()
