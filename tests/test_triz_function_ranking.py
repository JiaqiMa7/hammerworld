"""Tests for Function Ranking module."""
from __future__ import annotations

import unittest
from src.triz import function_ranking


class TestFunctionRanking(unittest.TestCase):
    def test_items_created(self):
        result = function_ranking.analyze("A pump moves water but consumes too much energy")
        self.assertGreater(len(result.items), 0)

    def test_item_scores(self):
        result = function_ranking.analyze("A motor provides torque")
        if result.items:
            item = result.items[0]
            self.assertGreaterEqual(item.usefulness, 0)
            self.assertGreaterEqual(item.cost, 0)
            self.assertGreaterEqual(item.harm, 0)

    def test_empty_description(self):
        result = function_ranking.analyze("")
        self.assertGreater(len(result.items), 0)  # fallback items

    def test_trimming_recommendations(self):
        result = function_ranking.analyze("An expensive machine that pollutes")
        self.assertIsInstance(result.trimming_recommendations, list)

    def test_score_computation(self):
        item = function_ranking.FunctionRankItem("test", usefulness=8, cost=2, harm=1)
        self.assertAlmostEqual(item.score, 8 - 1 - 1)  # 8 - 2/2 - 1 = 6


if __name__ == "__main__":
    unittest.main()
