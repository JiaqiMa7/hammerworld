"""Tests for TRIZ Agent: src/triz/agent.py"""
from __future__ import annotations

import unittest

from src.triz.agent import TRIZAgent
from src.triz.standard_solutions import STANDARD_SOLUTIONS
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


class TestNewTRIZMethods(unittest.TestCase):
    def setUp(self):
        self.agent = TRIZAgent()
        self.desc = "A fast car that is too heavy"

    def test_su_field_analysis(self):
        result = self.agent.su_field_analysis(self.desc)
        self.assertTrue(hasattr(result, "substance1"))
        self.assertTrue(hasattr(result, "interaction_type"))

    def test_cause_effect_analysis(self):
        result = self.agent.cause_effect_analysis(
            "The engine overheats because the cooling system is too small"
        )
        self.assertGreater(len(result.chain), 0)

    def test_resource_analysis(self):
        result = self.agent.resource_analysis("A metal engine with water cooling")
        self.assertTrue(hasattr(result, "substances"))
        self.assertTrue(hasattr(result, "fields"))

    def test_nine_windows(self):
        result = self.agent.nine_windows("A coffee cup")
        self.assertEqual(result.current_system, "coffee")
        self.assertTrue(hasattr(result, "system_present"))

    def test_trimming_analysis(self):
        result = self.agent.trimming_analysis("A car with an engine and wheels")
        self.assertTrue(hasattr(result, "trimming_candidates"))

    def test_function_ranking(self):
        result = self.agent.function_ranking("A pump moves water but uses too much energy")
        self.assertGreater(len(result.items), 0)

    def test_stc_operator(self):
        result = self.agent.stc_operator("A bridge too expensive to build")
        self.assertEqual(len(result.dimensions), 6)

    def test_smart_little_people(self):
        result = self.agent.smart_little_people("Two conflicting mechanisms")
        self.assertGreater(len(result.characters), 0)

    def test_ariz_simplified(self):
        result = self.agent.ariz_analyze(self.desc, simplified=True)
        self.assertEqual(result["steps_completed"], 30)
        self.assertGreater(len(result["phases_completed"]), 0)

    def test_ariz_full(self):
        result = self.agent.ariz_analyze(self.desc, simplified=False)
        self.assertGreaterEqual(result["steps_completed"], 80)

    def test_full_analysis(self):
        report = self.agent.full_analysis(self.desc)
        for key in ["su_field", "cause_effect", "resources", "nine_windows",
                     "trimming", "function_ranking", "stc", "slp", "ariz",
                     "standard_solutions", "standardized_problem", "_meta"]:
            self.assertIn(key, report)

    def test_query_standard_solutions_all(self):
        all_sols = self.agent.query_standard_solutions()
        self.assertEqual(len(all_sols), 76)

    def test_query_standard_solutions_class_1(self):
        sols = self.agent.query_standard_solutions(class_id=1)
        self.assertEqual(len(sols), 13)
        for s in sols:
            self.assertEqual(s.class_name, "1")

    def test_query_standard_solutions_class_4(self):
        sols = self.agent.query_standard_solutions(class_id=4)
        self.assertEqual(len(sols), 17)
        for s in sols:
            self.assertEqual(s.class_name, "4")
        # Check structure
        s = sols[0]
        self.assertTrue(hasattr(s, "name"))
        self.assertTrue(hasattr(s, "description"))
        self.assertTrue(hasattr(s, "su_field_condition"))

    def test_match_standard_solutions_harmful(self):
        from src.triz.su_field import SuFieldModel
        sf = SuFieldModel(
            substance1="vibration",
            substance2="component",
            field="mechanical",
            interaction_type="harmful",
            is_complete=True,
            transformation_suggestions=[],
        )
        result = self.agent.match_standard_solutions(
            "vibration damages the component", sf
        )
        self.assertEqual(result["recommended_class"], 1)
        self.assertGreater(len(result["matched"]), 0)

    def test_match_standard_solutions_insufficient(self):
        from src.triz.su_field import SuFieldModel
        sf = SuFieldModel(
            substance1="heater",
            substance2="room",
            field="thermal",
            interaction_type="insufficient",
            is_complete=True,
            transformation_suggestions=[],
        )
        result = self.agent.match_standard_solutions("weak heating", sf)
        self.assertEqual(result["recommended_class"], 1)
        self.assertGreater(len(result["matched"]), 0)

    def test_match_standard_solutions_keyword_measure(self):
        result = self.agent.match_standard_solutions(
            "need to detect temperature precisely"
        )
        self.assertEqual(result["recommended_class"], 4)
        self.assertGreater(len(result["matched"]), 0)

    def test_match_standard_solutions_keyword_complex(self):
        result = self.agent.match_standard_solutions(
            "too many parts make it complex"
        )
        self.assertEqual(result["recommended_class"], 5)
        self.assertGreater(len(result["matched"]), 0)

    def test_standardize_contains_basic_keys(self):
        """Rule-based standardize should still have the original 4 keys."""
        problem = self.agent.standardize("a heavy and slow machine", domain="energy")
        ctx = problem.triz_standardized or {}
        for key in ["contradiction", "ifr", "triz_params", "functional_model"]:
            self.assertIn(key, ctx)
        # Rule-based mode does NOT add enrichment keys (AI-only)
        self.assertNotIn("su_field", ctx)


if __name__ == "__main__":
    unittest.main()
