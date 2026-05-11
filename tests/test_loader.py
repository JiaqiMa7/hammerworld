"""Tests for data loader: src/engine/loader.py"""
from __future__ import annotations

import unittest

from src.engine.loader import load_methods, load_problems, filter_methods, filter_problems
from src.engine.models import Method, Problem, MethodLevel, Domain, ProblemMaturity


class TestLoadMethods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.methods = load_methods()

    def test_load(self):
        self.assertIsInstance(self.methods, list)
        self.assertTrue(len(self.methods) > 0)
        for m in self.methods:
            self.assertIsInstance(m, Method)

    def test_count(self):
        self.assertGreaterEqual(len(self.methods), 30,
                                "Should have at least 30 methods")

    def test_first_method_fields(self):
        m = self.methods[0]
        self.assertTrue(len(m.id) > 0)
        self.assertTrue(len(m.name) > 0)
        self.assertTrue(len(m.domain) > 0)
        self.assertTrue(len(m.description) > 0)

    def test_all_levels_present(self):
        levels = {m.level for m in self.methods}
        for lvl in MethodLevel:
            self.assertIn(lvl, levels,
                          f"Level {lvl} has no methods")

    def test_no_duplicate_ids(self):
        ids = [m.id for m in self.methods]
        self.assertEqual(len(ids), len(set(ids)),
                         "Method IDs must be unique")


class TestLoadProblems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.problems = load_problems()

    def test_load(self):
        self.assertIsInstance(self.problems, list)
        self.assertTrue(len(self.problems) > 0)
        for p in self.problems:
            self.assertIsInstance(p, Problem)

    def test_count(self):
        self.assertGreaterEqual(len(self.problems), 20,
                                "Should have at least 20 problems")

    def test_all_domains_present(self):
        domains = {p.domain for p in self.problems}
        for d in Domain:
            self.assertIn(d, domains,
                          f"Domain {d} has no problems")

    def test_some_have_triz_standardized(self):
        triz_count = sum(1 for p in self.problems if p.triz_standardized)
        self.assertGreater(triz_count, 0,
                           "At least one problem should have triz_standardized")


class TestFilterMethods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.methods = load_methods()

    def test_filter_by_level(self):
        result = filter_methods(self.methods, level=MethodLevel.DOMAIN_SPECIFIC)
        self.assertTrue(len(result) > 0)
        for m in result:
            self.assertEqual(m.level, MethodLevel.DOMAIN_SPECIFIC)

    def test_filter_by_domain(self):
        result = filter_methods(self.methods, domain="TRIZ")
        self.assertTrue(len(result) > 0)
        for m in result:
            self.assertEqual(m.domain, "TRIZ")

    def test_combined_filter(self):
        result = filter_methods(self.methods,
                                level=MethodLevel.STRUCTURED,
                                domain="TRIZ")
        self.assertTrue(len(result) > 0)
        for m in result:
            self.assertEqual(m.level, MethodLevel.STRUCTURED)
            self.assertEqual(m.domain, "TRIZ")

    def test_filter_no_match(self):
        result = filter_methods(self.methods, domain="NonexistentDomain")
        self.assertEqual(len(result), 0)


class TestFilterProblems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.problems = load_problems()

    def test_filter_by_domain(self):
        result = filter_problems(self.problems, domain=Domain.MEDICINE)
        self.assertTrue(len(result) > 0)
        for p in result:
            self.assertEqual(p.domain, Domain.MEDICINE)

    def test_filter_by_maturity(self):
        result = filter_problems(self.problems, maturity=ProblemMaturity.NO_SOLUTION)
        for p in result:
            self.assertEqual(p.maturity, ProblemMaturity.NO_SOLUTION)

    def test_combined_filter(self):
        result = filter_problems(self.problems,
                                 domain=Domain.MEDICINE,
                                 maturity=ProblemMaturity.PARTIAL_POOR)
        for p in result:
            self.assertEqual(p.domain, Domain.MEDICINE)


if __name__ == "__main__":
    unittest.main()
