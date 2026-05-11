"""Tests for TRIZ Agent: src/triz/agent.py"""
from __future__ import annotations

import unittest

from src.triz.agent import TRIZAgent
from src.engine.models import Problem, Domain


class TestTRIZAgentInit(unittest.TestCase):
    def test_default_init(self):
        agent = TRIZAgent()
        self.assertIsNone(agent.ai_provider)
        self.assertEqual(len(agent.history), 0)

    def test_with_provider(self):
        class MockAI:
            def generate(self, system, prompt):
                return "{}"
        agent = TRIZAgent(ai_provider=MockAI())
        self.assertIsNotNone(agent.ai_provider)


class TestRuleBasedAnalyze(unittest.TestCase):
    def setUp(self):
        self.agent = TRIZAgent()

    def test_keyword_speed(self):
        analysis = self.agent._rule_based_from_text(
            "We need a faster system", "engineering")
        # Should find "fast" → parameter 9
        self.assertGreater(len(analysis.recommended_principles), 0)

    def test_keyword_reliable(self):
        analysis = self.agent._rule_based_from_text(
            "We need a more reliable machine", "engineering")
        self.assertGreater(len(analysis.recommended_principles), 0)

    def test_keyword_energy(self):
        analysis = self.agent._rule_based_from_text(
            "This process wastes too much energy", "engineering")
        self.assertGreater(len(analysis.recommended_principles), 0)

    def test_multiple_keywords(self):
        analysis = self.agent._rule_based_from_text(
            "We need faster, more reliable, lighter equipment", "engineering")
        self.assertGreater(len(analysis.recommended_principles), 0)
        self.assertGreaterEqual(len(analysis.technical_contradictions), 0)

    def test_no_keywords(self):
        analysis = self.agent._rule_based_from_text(
            "xyzzy qwerty blarg", "engineering")
        self.assertEqual(len(analysis.technical_contradictions), 0)
        self.assertEqual(len(analysis.recommended_principles), 0)

    def test_ifr_generated(self):
        analysis = self.agent._rule_based_from_text(
            "The machine breaks down too often", "engineering")
        self.assertTrue(len(analysis.ifr) > 0)


class TestFromStandardized(unittest.TestCase):
    def setUp(self):
        self.agent = TRIZAgent()

    def test_uses_triz_standardized(self):
        p = Problem(
            id="p1", title="Test", domain=Domain.MEDICINE,
            description="Some problem",
            triz_standardized={
                "contradiction": {"improving": "Speed", "worsening": "Loss"},
                "ifr": "Problem solves itself",
                "triz_params": [1, 15],
                "functional_model": {
                    "actors": ["A", "B"],
                    "useful_functions": [],
                    "harmful_functions": [],
                },
            },
        )
        analysis = self.agent.analyze(p)
        self.assertEqual(analysis.ifr, "Problem solves itself")
        self.assertEqual(analysis.recommended_principles, [1, 15])
        self.assertEqual(analysis.functional_model.actors, ["A", "B"])

    def test_fields_populated(self):
        p = Problem(
            id="p2", title="Test", domain=Domain.ENERGY,
            description="desc",
            triz_standardized={
                "ifr": "Ideal state",
                "triz_params": [40],
                "functional_model": {
                    "actors": [], "useful_functions": [], "harmful_functions": [],
                },
            },
        )
        analysis = self.agent.analyze(p)
        self.assertEqual(analysis.ifr, "Ideal state")


class TestGetPrincipleRecommendations(unittest.TestCase):
    def setUp(self):
        self.agent = TRIZAgent()

    def test_valid_ids(self):
        result = self.agent.get_principle_recommendations(9, 25)
        self.assertIn("principle_ids", result)
        self.assertIn("principles", result)
        self.assertEqual(result["principle_ids"], [10, 37, 28, 35])
        self.assertEqual(len(result["principles"]), 4)
        p0 = result["principles"][0]
        self.assertIn("id", p0)
        self.assertIn("name", p0)
        self.assertIn("description", p0)
        self.assertIn("examples", p0)

    def test_invalid_ids(self):
        result = self.agent.get_principle_recommendations(1, 1)
        self.assertEqual(result["principle_ids"], [])
        self.assertEqual(result["principles"], [])


class TestStandardize(unittest.TestCase):
    def setUp(self):
        self.agent = TRIZAgent()

    def test_rule_based(self):
        problem = self.agent.standardize(
            "We need a faster engine that is more reliable",
            domain="energy",
        )
        self.assertIsInstance(problem, Problem)

    def test_returns_problem(self):
        problem = self.agent.standardize("A very slow system", domain="information")
        self.assertEqual(problem.domain, Domain.INFORMATION)

    def test_triz_field_set(self):
        problem = self.agent.standardize(
            "We need a faster and more reliable spaceship",
            domain="energy",
        )
        self.assertIsNotNone(problem.triz_standardized)
        self.assertIn("contradiction", problem.triz_standardized)
        self.assertIn("ifr", problem.triz_standardized)
        self.assertIn("triz_params", problem.triz_standardized)
        self.assertIn("functional_model", problem.triz_standardized)


class TestAIAnalyzeWithoutProvider(unittest.TestCase):
    def test_raises_error(self):
        agent = TRIZAgent()  # no AI provider
        p = Problem(id="p1", title="T", domain=Domain.MEDICINE,
                     description="D")
        # Without triz_standardized and without AI provider,
        # falls back to rule-based (no error)
        analysis = agent.analyze(p)
        self.assertIsNotNone(analysis)


if __name__ == "__main__":
    unittest.main()
