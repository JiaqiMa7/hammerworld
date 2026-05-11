"""Tests for evaluation pipeline: src/evaluation/scorer.py"""
from __future__ import annotations

import unittest
import json

from src.evaluation.scorer import (
    EvaluationPipeline, EvaluationResult, DIMENSION_NAMES,
)
from src.engine.models import (
    Method, Problem, Combination, EvalDimension, Domain, MethodLevel,
    EvalScore, AIAnalysis,
)


MOCK_RESPONSE = json.dumps({
    "scores": [
        {"dimension": "elegance", "score": 7.0,
         "explanation": "Moderately elegant"},
        {"dimension": "weirdness", "score": 9.5,
         "explanation": "Very weird and surprising"},
        {"dimension": "human_feasibility", "score": 5.0,
         "explanation": "Somewhat feasible"},
        {"dimension": "ai_feasibility", "score": 6.0,
         "explanation": "AI could contribute"},
        {"dimension": "novelty", "score": 8.5,
         "explanation": "Quite novel"},
        {"dimension": "analogy_distance", "score": 7.0,
         "explanation": "Moderate distance"},
        {"dimension": "scaling_potential", "score": 4.0,
         "explanation": "Limited scale"},
        {"dimension": "side_effects", "score": 6.0,
         "explanation": "Some side effects"},
    ],
    "analysis_text": "This is a novel approach combining...",
})


class MockAIProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return MOCK_RESPONSE


def _make_combo() -> Combination:
    m = Method(id="m1", name="Test Method", domain="Test",
               level=MethodLevel(2), description="A test method",
               examples=["ex1"])
    p = Problem(id="p1", title="Test Problem", domain=Domain.MEDICINE,
                description="A test problem")
    return Combination(id="combo_m1_p1", method=m, problem=p)


class TestEvaluationPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = EvaluationPipeline(
            ai_provider=MockAIProvider(),
            threshold=8.0,
            model_name="test-model",
            model_version="1.0",
        )

    def test_init(self):
        self.assertEqual(self.pipeline.threshold, 8.0)
        self.assertEqual(self.pipeline.model_name, "test-model")

    def test_evaluate(self):
        combo = _make_combo()
        result = self.pipeline.evaluate(combo)
        self.assertIsInstance(result, EvaluationResult)
        self.assertEqual(len(result.analysis.scores), 8)
        self.assertTrue(len(result.analysis.analysis_text) > 0)
        self.assertTrue(len(result.analysis.inference_hash) > 0)

    def test_evaluate_batch(self):
        combos = [_make_combo() for _ in range(3)]
        results = self.pipeline.evaluate_batch(combos)
        self.assertEqual(len(results), 3)

    def test_evaluate_and_filter(self):
        combos = [_make_combo() for _ in range(3)]
        passed, failed = self.pipeline.evaluate_and_filter(combos)
        total = len(passed) + len(failed)
        self.assertEqual(total, 3)

    def test_threshold(self):
        pipeline_low = EvaluationPipeline(MockAIProvider(), threshold=9.9)
        combo = _make_combo()
        result = pipeline_low.evaluate(combo)
        # With threshold 9.9, only weirdness (9.5) should still pass
        self.assertFalse(result.passed_threshold)

    def test_create_submission(self):
        combo = _make_combo()
        result = self.pipeline.evaluate(combo)
        sub = self.pipeline.create_submission(result, submitter="0xMINER")
        self.assertEqual(sub.submitter, "0xMINER")
        self.assertEqual(sub.status, "pending")


class TestEvaluationResult(unittest.TestCase):
    def _eval(self, **scores):
        combo = _make_combo()
        eval_scores = [EvalScore(EvalDimension(k), s, "") for k, s in scores.items()]
        analysis = AIAnalysis(scores=eval_scores, analysis_text="",
                               model_name="m", model_version="v",
                               inference_hash="h")
        return EvaluationResult(
            combination=combo, analysis=analysis,
            passed_threshold=analysis.is_high_score(8.0),
            high_dimensions=analysis.high_dimensions(8.0),
        )

    def test_passed_when_high(self):
        r = self._eval(elegance=5.0, weirdness=9.0, novelty=6.0)
        self.assertTrue(r.passed_threshold)

    def test_failed_when_low(self):
        r = self._eval(elegance=5.0, weirdness=7.0, novelty=6.0)
        self.assertFalse(r.passed_threshold)

    def test_high_dimensions(self):
        r = self._eval(elegance=9.0, weirdness=3.0, novelty=8.5)
        self.assertIn(EvalDimension.ELEGANCE, r.high_dimensions)
        self.assertIn(EvalDimension.NOVELTY, r.high_dimensions)
        self.assertEqual(len(r.high_dimensions), 2)


class TestDimensionNames(unittest.TestCase):
    def test_all_eight_named(self):
        self.assertEqual(len(DIMENSION_NAMES), 8)
        for dim in EvalDimension:
            self.assertIn(dim, DIMENSION_NAMES)


class TestFallbackScores(unittest.TestCase):
    def setUp(self):
        self.pipeline = EvaluationPipeline(MockAIProvider())

    def test_simulated_eval_has_eight_dims(self):
        # Even with a bad response, fallback gives 8 dimensions
        class BadProvider:
            def generate(self, s, p):
                return "garbage text without json novel weird practical"
        pipeline = EvaluationPipeline(BadProvider())
        combo = _make_combo()
        result = pipeline.evaluate(combo)
        self.assertEqual(len(result.analysis.scores), 8)


if __name__ == "__main__":
    unittest.main()
