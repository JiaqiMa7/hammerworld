"""Tests for TRIZ knowledge base: src/triz/knowledge.py"""
from __future__ import annotations

import unittest

from src.triz.knowledge import ENGINEERING_PARAMETERS, INVENTIVE_PRINCIPLES


class TestEngineeringParameters(unittest.TestCase):
    def test_count(self):
        self.assertEqual(len(ENGINEERING_PARAMETERS), 39,
                         "Must have exactly 39 engineering parameters")

    def test_ids_continuous(self):
        for i in range(1, 40):
            self.assertIn(i, ENGINEERING_PARAMETERS,
                          f"Missing engineering parameter {i}")

    def test_each_has_name(self):
        for pid, param in ENGINEERING_PARAMETERS.items():
            self.assertTrue(len(param.name) > 0,
                            f"Parameter {pid} has empty name")
            self.assertTrue(len(param.description) > 0,
                            f"Parameter {pid} has empty description")

    def test_param_structure(self):
        for pid, param in ENGINEERING_PARAMETERS.items():
            self.assertEqual(param.id, pid)
            self.assertIsInstance(param.name, str)
            self.assertIsInstance(param.description, str)


class TestInventivePrinciples(unittest.TestCase):
    def test_count(self):
        self.assertEqual(len(INVENTIVE_PRINCIPLES), 40,
                         "Must have exactly 40 inventive principles")

    def test_ids_continuous(self):
        for i in range(1, 41):
            self.assertIn(i, INVENTIVE_PRINCIPLES,
                          f"Missing inventive principle {i}")

    def test_each_has_examples(self):
        for pid, principle in INVENTIVE_PRINCIPLES.items():
            self.assertTrue(len(principle.examples) >= 1,
                            f"Principle {pid} '{principle.name}' has no examples")

    def test_each_has_sub_principles(self):
        for pid, principle in INVENTIVE_PRINCIPLES.items():
            self.assertTrue(len(principle.sub_principles) >= 1,
                            f"Principle {pid} '{principle.name}' has no sub-principles")

    def test_principle_structure(self):
        for pid, principle in INVENTIVE_PRINCIPLES.items():
            self.assertEqual(principle.id, pid)
            self.assertTrue(len(principle.name) > 0)
            self.assertTrue(len(principle.description) > 0)


if __name__ == "__main__":
    unittest.main()
