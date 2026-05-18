"""Tests for Smart Little People module."""
from __future__ import annotations

import unittest
from src.triz import smart_little_people


class TestSmartLittlePeople(unittest.TestCase):
    def test_characters_created(self):
        result = smart_little_people.analyze("Two teams working on the same code")
        self.assertGreater(len(result.characters), 0)

    def test_ideal_configuration(self):
        result = smart_little_people.analyze("A noisy engine")
        self.assertTrue(len(result.ideal_configuration) > 0)

    def test_empty_description(self):
        result = smart_little_people.analyze("")
        self.assertGreater(len(result.characters), 0)

    def test_character_structure(self):
        result = smart_little_people.analyze("A hot motor")
        if result.characters:
            c = result.characters[0]
            self.assertTrue(hasattr(c, "role"))
            self.assertTrue(hasattr(c, "behavior"))
            self.assertTrue(hasattr(c, "conflict"))

    def test_key_insight(self):
        result = smart_little_people.analyze("A system with friction problems")
        self.assertTrue(len(result.key_insight) > 0)


if __name__ == "__main__":
    unittest.main()
