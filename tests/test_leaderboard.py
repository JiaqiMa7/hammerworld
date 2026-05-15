"""Tests for leaderboard: src/hub/leaderboard.py"""
from __future__ import annotations

import unittest
import random

from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry, RandomDrawResult
from src.engine.models import (
    Combination, Method, Problem, AIAnalysis, EvalScore,
    EvalDimension, Domain, MethodLevel,
)


def _make_analyzed_combo(
    combo_id: str,
    method_name: str = "TestMethod",
    method_domain: str = "Test",
    method_level: int = 2,
    problem_title: str = "TestProblem",
    problem_domain: str = "medicine",
    scores_dict: dict | None = None,
) -> Combination:
    m = Method(id=f"m_{combo_id}", name=method_name, domain=method_domain,
               level=MethodLevel(method_level), description="")
    p = Problem(id=f"p_{combo_id}", title=problem_title, domain=Domain(problem_domain),
                description="")
    combo = Combination(id=combo_id, method=m, problem=p)

    if scores_dict is None:
        scores_dict = {
            EvalDimension.ELEGANCE: 5.0,
            EvalDimension.WEIRDNESS: 5.0,
            EvalDimension.HUMAN_FEASIBILITY: 5.0,
            EvalDimension.AI_FEASIBILITY: 5.0,
            EvalDimension.NOVELTY: 5.0,
            EvalDimension.ANALOGY_DISTANCE: 5.0,
            EvalDimension.SCALING_POTENTIAL: 5.0,
            EvalDimension.SIDE_EFFECTS: 5.0,
        }
    scores = [EvalScore(d, s, "") for d, s in scores_dict.items()]
    combo.analyses.append(AIAnalysis(
        scores=scores, analysis_text="test",
        model_name="test", model_version="0",
        inference_hash=f"hash_{combo_id}",
    ))
    return combo


class TestLeaderboardDB(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self._seed_data()

    def _seed_data(self):
        domains = ["medicine", "energy", "environment", "information", "materials", "society"]
        rng = random.Random(42)
        for i in range(20):
            dims = list(EvalDimension)
            # Make one dimension clearly high for each entry
            high_dim = dims[i % len(dims)]
            scores = {
                d: rng.uniform(2, 7) if d != high_dim else rng.uniform(8, 10)
                for d in dims
            }
            combo = _make_analyzed_combo(
                combo_id=f"combo_test_{i:03d}",
                method_name=f"Method {i}",
                method_domain=f"Domain{i%4}",
                method_level=(i % 4) + 1,
                problem_title=f"Problem {i}",
                problem_domain=domains[i % len(domains)],
                scores_dict=scores,
            )
            self.db.insert(combo, miner_addr=f"miner_{i}")

    def test_insert(self):
        combo = _make_analyzed_combo("combo_new", method_name="NewMethod")
        entry = self.db.insert(combo, miner_addr="miner_new")
        self.assertTrue(entry.combo_id.startswith("combo_new"))
        self.assertEqual(entry.combo_group_id, "combo_new")
        self.assertEqual(entry.method_name, "NewMethod")

    def test_insert_no_analysis(self):
        combo = Combination(
            id="combo_bad",
            method=Method(id="m", name="M", domain="D", level=MethodLevel(1), description=""),
            problem=Problem(id="p", title="P", domain=Domain.MEDICINE, description=""),
        )
        with self.assertRaises(ValueError):
            self.db.insert(combo)

    def test_get_top(self):
        entries = self.db.get_top(limit=5)
        self.assertEqual(len(entries), 5)
        # Should be sorted by best_score descending
        for i in range(len(entries) - 1):
            self.assertGreaterEqual(entries[i].best_score, entries[i + 1].best_score)

    def test_get_top_filter_by_dimension(self):
        entries = self.db.get_top(dimension=EvalDimension.WEIRDNESS, limit=5)
        self.assertEqual(len(entries), 5)
        # Should be sorted by weirdness now
        for i in range(len(entries) - 1):
            self.assertGreaterEqual(entries[i].weirdness, entries[i + 1].weirdness)

    def test_get_top_filter_by_domain(self):
        entries = self.db.get_top(domain=Domain.MEDICINE, limit=10)
        for e in entries:
            self.assertEqual(e.problem_domain, "medicine")

    def test_get_top_pagination(self):
        all_entries = self.db.get_top(limit=100)
        page1 = self.db.get_top(limit=5, offset=0)
        page2 = self.db.get_top(limit=5, offset=5)
        self.assertEqual(len(page1), 5)
        self.assertEqual(len(page2), 5)
        ids1 = {e.combo_id for e in page1}
        ids2 = {e.combo_id for e in page2}
        self.assertTrue(ids1.isdisjoint(ids2))

    def test_random_draw_count(self):
        draw = self.db.random_draw(draw_count=5, viewer_addr="0xV")
        self.assertLessEqual(len(draw.entries), 5)
        self.assertGreater(len(draw.entries), 0)

    def test_random_draw_no_duplicate(self):
        draw1 = self.db.random_draw(draw_count=5, viewer_addr="0xV")
        draw2 = self.db.random_draw(draw_count=5, viewer_addr="0xV")
        ids1 = {e.combo_id for e in draw1.entries}
        ids2 = {e.combo_id for e in draw2.entries}
        self.assertTrue(ids1.isdisjoint(ids2),
                        "Same viewer should not get duplicate draws")

    def test_random_draw_all_available(self):
        total = self.db.total_entries()
        draw = self.db.random_draw(draw_count=total + 10, viewer_addr="0xV")
        self.assertEqual(len(draw.entries), total)

    def test_search(self):
        results = self.db.search("Problem 5", limit=5)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIn("Problem", r.problem_title)

    def test_search_no_match(self):
        results = self.db.search("xyznonexistentzzz", limit=5)
        self.assertEqual(len(results), 0)

    def test_has_paid_false(self):
        self.assertFalse(self.db.has_paid("0xV", "combo_test_000"))

    def test_record_payment(self):
        self.db.record_payment("0xV", "combo_test_000")
        self.assertTrue(self.db.has_paid("0xV", "combo_test_000"))

    def test_total_entries(self):
        self.assertEqual(self.db.total_entries(), 20)

    def test_total_entries_domain(self):
        total_all = self.db.total_entries()
        total_per_domain = sum(
            self.db.total_entries(domain=d) for d in Domain
        )
        self.assertEqual(total_all, total_per_domain)


class TestLeaderboardEntry(unittest.TestCase):
    def test_fields(self):
        entry = LeaderboardEntry(
            rank=1, run_id="c1", combo_group_id="c1_g",
            method_name="M", method_domain="D",
            method_level=2, problem_title="P", problem_domain="medicine",
            best_dimension="elegance", best_score=9.0,
            elegance=9.0, weirdness=5.0, human_feasibility=6.0,
            ai_feasibility=5.0, novelty=4.0, analogy_distance=3.0,
            scaling_potential=2.0, side_effects=5.0,
            miner_address="0xMINER",
        )
        self.assertEqual(entry.rank, 1)
        self.assertEqual(entry.run_id, "c1")
        self.assertEqual(entry.combo_group_id, "c1_g")
        self.assertEqual(entry.combo_id, "c1")  # backward compat
        self.assertEqual(entry.best_score, 9.0)
        self.assertEqual(entry.miner_address, "0xMINER")


class TestRandomDrawResult(unittest.TestCase):
    def test_fields(self):
        result = RandomDrawResult(
            entries=[], board_name="test_board",
            total_in_board=100, draw_seed=42,
        )
        self.assertEqual(result.board_name, "test_board")
        self.assertEqual(result.total_in_board, 100)
        self.assertEqual(len(result.entries), 0)


if __name__ == "__main__":
    unittest.main()
