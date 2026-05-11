"""Tests for contradiction matrix: src/triz/contradiction_matrix.py"""
from __future__ import annotations

import unittest

from src.triz.contradiction_matrix import (
    query_matrix,
    CONTRADICTION_MATRIX,
    get_principle_recommendations,
)
from src.triz.knowledge import ENGINEERING_PARAMETERS


class TestQueryMatrix(unittest.TestCase):
    def test_valid_query(self):
        result = query_matrix(9, 25)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_known_mapping(self):
        """Speed(9) vs Loss of time(25) → [10, 37, 28, 35]"""
        result = query_matrix(9, 25)
        self.assertEqual(result, [10, 37, 28, 35])

    def test_known_mapping_2(self):
        """Weight of moving object(1) vs Speed(9) → [2, 28, 13, 38]"""
        result = query_matrix(1, 9)
        self.assertEqual(result, [2, 28, 13, 38])

    def test_empty_mapping(self):
        """Diagonal should be empty (improving=worsening same param)"""
        result = query_matrix(1, 1)
        self.assertEqual(result, [])

    def test_unpopulated_cell(self):
        """Some cells in the matrix are not populated"""
        for i in [2, 3, 4]:
            result = query_matrix(3, 16)
            # Just verify it doesn't crash - may or may not have data
            self.assertIsInstance(result, list)

    def test_invalid_param_high(self):
        with self.assertRaises(ValueError):
            query_matrix(40, 1)

    def test_invalid_param_low(self):
        with self.assertRaises(ValueError):
            query_matrix(0, 1)

    def test_invalid_param_zero(self):
        with self.assertRaises(ValueError):
            query_matrix(0, 25)

    def test_invalid_param_negative(self):
        with self.assertRaises(ValueError):
            query_matrix(-1, 25)

    def test_result_in_range(self):
        """All returned principle IDs should be valid (1-40)."""
        for (imp, wors), principles in CONTRADICTION_MATRIX.items():
            for p in principles:
                self.assertTrue(1 <= p <= 40,
                                f"Invalid principle {p} at ({imp},{wors})")

    def test_all_params_referenced(self):
        """Check that the matrix keys use only valid parameter IDs."""
        for imp, wors in CONTRADICTION_MATRIX:
            self.assertIn(imp, ENGINEERING_PARAMETERS)
            self.assertIn(wors, ENGINEERING_PARAMETERS)


class TestGetPrincipleRecommendations(unittest.TestCase):
    def test_by_name(self):
        result = get_principle_recommendations(
            "Speed", "Loss of time", ENGINEERING_PARAMETERS)
        self.assertEqual(result, [10, 37, 28, 35])

    def test_case_insensitive(self):
        result = get_principle_recommendations(
            "speed", "LOSS OF TIME", ENGINEERING_PARAMETERS)
        self.assertEqual(result, [10, 37, 28, 35])

    def test_unknown_name(self):
        result = get_principle_recommendations(
            "NonexistentParam", "Speed", ENGINEERING_PARAMETERS)
        self.assertEqual(result, [])

    def test_both_unknown(self):
        result = get_principle_recommendations(
            "Foo", "Bar", ENGINEERING_PARAMETERS)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
