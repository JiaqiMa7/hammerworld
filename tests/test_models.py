"""Tests for core data models: src/engine/models.py"""
from __future__ import annotations

import unittest

from src.engine.models import (
    Method, Problem, Combination, AIAnalysis, EvalScore, Submission,
    MethodLevel, ProblemMaturity, ConstraintType, EvalDimension, Domain,
)


class TestMethodLevel(unittest.TestCase):
    def test_values(self):
        self.assertEqual(MethodLevel(1), MethodLevel.BASIC_HEURISTIC)
        self.assertEqual(MethodLevel(2), MethodLevel.STRUCTURED)
        self.assertEqual(MethodLevel(3), MethodLevel.DOMAIN_SPECIFIC)
        self.assertEqual(MethodLevel(4), MethodLevel.COMPOSITE)

    def test_from_int(self):
        self.assertIs(MethodLevel(2), MethodLevel.STRUCTURED)


class TestDomain(unittest.TestCase):
    def test_all_six_domains(self):
        domains = list(Domain)
        self.assertEqual(len(domains), 6)
        self.assertIn(Domain.MEDICINE, domains)
        self.assertIn(Domain.ENERGY, domains)
        self.assertIn(Domain.ENVIRONMENT, domains)
        self.assertIn(Domain.INFORMATION, domains)
        self.assertIn(Domain.MATERIALS, domains)
        self.assertIn(Domain.SOCIETY, domains)

    def test_from_string(self):
        self.assertEqual(Domain("medicine"), Domain.MEDICINE)
        self.assertEqual(Domain("energy"), Domain.ENERGY)

    def test_invalid_domain_raises(self):
        with self.assertRaises(ValueError):
            Domain("nonexistent")


class TestEvalDimension(unittest.TestCase):
    def test_all_eight_dimensions(self):
        dims = list(EvalDimension)
        self.assertEqual(len(dims), 8)

    def test_from_string(self):
        self.assertEqual(EvalDimension("weirdness"), EvalDimension.WEIRDNESS)
        self.assertEqual(EvalDimension("elegance"), EvalDimension.ELEGANCE)
        self.assertEqual(EvalDimension("novelty"), EvalDimension.NOVELTY)


class TestConstraintType(unittest.TestCase):
    def test_from_string(self):
        self.assertEqual(ConstraintType("time"), ConstraintType.TIME)
        self.assertEqual(ConstraintType("ethical"), ConstraintType.ETHICAL)


class TestProblemMaturity(unittest.TestCase):
    def test_values(self):
        self.assertEqual(ProblemMaturity(1), ProblemMaturity.NO_SOLUTION)
        self.assertEqual(ProblemMaturity(4), ProblemMaturity.BOTTLENECK_KNOWN)


class TestMethod(unittest.TestCase):
    def test_create(self):
        m = Method(
            id="method_test_001", name="Test Method", domain="Testing",
            level=MethodLevel(2), description="A test method",
            trigger_conditions=["condition1"], examples=["example1"],
            prerequisites=["method_x"], compatible_with=["method_y"],
        )
        self.assertEqual(m.id, "method_test_001")
        self.assertEqual(m.name, "Test Method")
        self.assertEqual(m.domain, "Testing")
        self.assertEqual(m.level, MethodLevel.STRUCTURED)
        self.assertEqual(m.trigger_conditions, ["condition1"])
        self.assertEqual(m.examples, ["example1"])
        self.assertEqual(m.prerequisites, ["method_x"])
        self.assertEqual(m.compatible_with, ["method_y"])

    def test_make_id(self):
        self.assertEqual(Method.make_id("triz", 3), "method_triz_003")
        self.assertEqual(Method.make_id("ml", 42), "method_ml_042")

    def test_defaults(self):
        m = Method(id="m1", name="M", domain="D", level=MethodLevel(1), description="")
        self.assertEqual(m.trigger_conditions, [])
        self.assertEqual(m.examples, [])
        self.assertEqual(m.prerequisites, [])
        self.assertEqual(m.compatible_with, [])


class TestProblem(unittest.TestCase):
    def test_create(self):
        p = Problem(
            id="problem_test_001", title="Test Problem",
            domain=Domain.MEDICINE, description="A test problem",
            constraint_types=[ConstraintType.TIME],
            maturity=ProblemMaturity.PARTIAL_POOR,
        )
        self.assertEqual(p.id, "problem_test_001")
        self.assertEqual(p.title, "Test Problem")
        self.assertEqual(p.domain, Domain.MEDICINE)
        self.assertEqual(p.constraint_types, [ConstraintType.TIME])
        self.assertEqual(p.maturity, ProblemMaturity.PARTIAL_POOR)
        self.assertIsNone(p.triz_standardized)

    def test_make_id(self):
        self.assertEqual(Problem.make_id("medicine", 1), "problem_medicine_001")
        self.assertEqual(Problem.make_id("energy", 7), "problem_energy_007")

    def test_with_triz(self):
        ctx = {"contradiction": {"improving": "X", "worsening": "Y"}, "ifr": "Z"}
        p = Problem(id="p1", title="P", domain=Domain.ENERGY, description="D",
                     triz_standardized=ctx)
        self.assertEqual(p.triz_standardized, ctx)

    def test_maturity_default(self):
        p = Problem(id="p1", title="P", domain=Domain.MEDICINE, description="D")
        self.assertEqual(p.maturity, ProblemMaturity.NO_SOLUTION)
        self.assertEqual(p.constraint_types, [])


class TestEvalScore(unittest.TestCase):
    def test_create(self):
        s = EvalScore(dimension=EvalDimension.ELEGANCE, score=7.5,
                       explanation="Quite elegant")
        self.assertEqual(s.dimension, EvalDimension.ELEGANCE)
        self.assertEqual(s.score, 7.5)
        self.assertEqual(s.explanation, "Quite elegant")


class TestAIAnalysis(unittest.TestCase):
    def _make_scores(self, *pairs):
        return [EvalScore(d, s, "") for d, s in pairs]

    def test_is_high_score_true(self):
        scores = self._make_scores(
            (EvalDimension.ELEGANCE, 5.0),
            (EvalDimension.WEIRDNESS, 8.5),
            (EvalDimension.NOVELTY, 6.0),
        )
        a = AIAnalysis(scores=scores, analysis_text="", model_name="m",
                        model_version="v", inference_hash="h")
        self.assertTrue(a.is_high_score())

    def test_is_high_score_false(self):
        scores = self._make_scores(
            (EvalDimension.ELEGANCE, 5.0),
            (EvalDimension.WEIRDNESS, 7.9),
        )
        a = AIAnalysis(scores=scores, analysis_text="", model_name="m",
                        model_version="v", inference_hash="h")
        self.assertFalse(a.is_high_score())

    def test_high_dimensions(self):
        scores = self._make_scores(
            (EvalDimension.ELEGANCE, 8.5),
            (EvalDimension.WEIRDNESS, 3.0),
            (EvalDimension.NOVELTY, 9.0),
        )
        a = AIAnalysis(scores=scores, analysis_text="", model_name="m",
                        model_version="v", inference_hash="h")
        high = a.high_dimensions()
        self.assertIn(EvalDimension.ELEGANCE, high)
        self.assertIn(EvalDimension.NOVELTY, high)
        self.assertNotIn(EvalDimension.WEIRDNESS, high)
        self.assertEqual(len(high), 2)

    def test_multiple_high_same_threshold(self):
        scores = self._make_scores(
            (EvalDimension.ELEGANCE, 8.0),
            (EvalDimension.WEIRDNESS, 8.0),
            (EvalDimension.NOVELTY, 8.0),
        )
        a = AIAnalysis(scores=scores, analysis_text="", model_name="m",
                        model_version="v", inference_hash="h")
        self.assertEqual(len(a.high_dimensions()), 3)


class TestCombination(unittest.TestCase):
    def _method(self, i=1):
        return Method(id=f"m{i}", name=f"Method{i}", domain="D",
                       level=MethodLevel(1), description="")

    def _problem(self, i=1):
        return Problem(id=f"p{i}", title=f"Problem{i}", domain=Domain.MEDICINE,
                        description="")

    def test_create(self):
        m = self._method()
        p = self._problem()
        c = Combination(id="combo_x", method=m, problem=p)
        self.assertEqual(c.id, "combo_x")
        self.assertEqual(c.method, m)
        self.assertEqual(c.problem, p)
        self.assertEqual(c.analyses, [])

    def test_make_id(self):
        cid = Combination.make_id("method_triz_001", "problem_medicine_003")
        self.assertEqual(cid, "combo_method_triz_001_problem_medicine_003")

    def test_best_score_none(self):
        c = Combination(id="c", method=self._method(), problem=self._problem())
        self.assertIsNone(c.best_score)

    def test_best_score(self):
        c = Combination(id="c", method=self._method(), problem=self._problem())
        scores1 = [EvalScore(EvalDimension.ELEGANCE, 4.0, "")]
        scores2 = [EvalScore(EvalDimension.WEIRDNESS, 9.0, "")]
        c.analyses = [
            AIAnalysis(scores=scores1, analysis_text="", model_name="m",
                        model_version="v", inference_hash="h1"),
            AIAnalysis(scores=scores2, analysis_text="", model_name="m",
                        model_version="v", inference_hash="h2"),
        ]
        self.assertEqual(c.best_score, 9.0)

    def test_best_dimension(self):
        c = Combination(id="c", method=self._method(), problem=self._problem())
        scores = [EvalScore(EvalDimension.NOVELTY, 8.5, "")]
        c.analyses = [
            AIAnalysis(scores=scores, analysis_text="", model_name="m",
                        model_version="v", inference_hash="h"),
        ]
        self.assertEqual(c.best_dimension, EvalDimension.NOVELTY)


class TestSubmission(unittest.TestCase):
    def test_create(self):
        s = Submission(method_id="m1", problem_id="p1", submitter="0xABC")
        self.assertEqual(s.method_id, "m1")
        self.assertEqual(s.problem_id, "p1")
        self.assertEqual(s.submitter, "0xABC")
        self.assertEqual(s.status, "pending")
        self.assertEqual(s.classifications, [])

    def test_id_generated(self):
        s = Submission(method_id="m1", problem_id="p1", submitter="0xABC")
        self.assertTrue(len(s.id) > 0)
        self.assertIsInstance(s.id, str)


if __name__ == "__main__":
    unittest.main()
