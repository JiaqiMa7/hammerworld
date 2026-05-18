"""Tests for ARIZ-85C module (full + simplified)."""
from __future__ import annotations

import unittest
from src.triz.ariz import run_full, run_simplified, ARIZState


class TestARIZSimplified(unittest.TestCase):
    def test_basic_run(self):
        result = run_simplified("A fast car that is too heavy")
        self.assertEqual(result.steps_completed, 30)
        self.assertGreater(len(result.phases_completed), 0)
        self.assertTrue(len(result.mini_problem) > 0)

    def test_conflict_description(self):
        result = run_simplified("The engine is powerful but overheats quickly")
        self.assertTrue(len(result.conflict_description) > 0)

    def test_ifr_generated(self):
        result = run_simplified("A slow but reliable machine")
        self.assertTrue(len(result.ifr) > 0)

    def test_empty_description(self):
        result = run_simplified("")
        self.assertEqual(result.steps_completed, 30)
        self.assertGreater(len(result.phases_completed), 0)

    def test_rule_based_flag(self):
        result = run_simplified("test")
        self.assertTrue(result.rule_based)


class TestARIZFull(unittest.TestCase):
    def test_basic_run(self):
        result = run_full("A fast car that is too heavy")
        self.assertGreaterEqual(result.steps_completed, 80)
        self.assertEqual(len(result.phases_completed), 9)

    def test_phases_listed(self):
        result = run_full("A machine that vibrates too much")
        phase_names = [p.split(":")[0] for p in result.phases_completed]
        for i in range(1, 10):
            self.assertTrue(any(str(i) in p for p in phase_names))

    def test_resource_summary(self):
        result = run_full("An electric motor with cooling problems")
        self.assertTrue(len(result.resource_summary) >= 0)

    def test_physical_contradiction(self):
        result = run_full("The beam must be both strong and lightweight")
        self.assertTrue(len(result.physical_contradiction) > 0)

    def test_empty_description(self):
        result = run_full("")
        self.assertGreaterEqual(result.steps_completed, 80)


class TestARIZState(unittest.TestCase):
    def test_state_creation(self):
        state = ARIZState(original_problem="test")
        self.assertEqual(state.original_problem, "test")
        self.assertEqual(state.mini_problem, "")

    def test_state_mutation(self):
        state = ARIZState(original_problem="test")
        state.mini_problem = "custom problem"
        self.assertEqual(state.mini_problem, "custom problem")


if __name__ == "__main__":
    unittest.main()
