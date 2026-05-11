"""Tests for combination engine: src/engine/combiner.py"""
from __future__ import annotations

import unittest

from src.engine.combiner import (
    _deterministic_seed,
    fisher_yates_shuffle,
    generate_combinations,
    MiningState,
)
from src.engine.models import Method, Problem, Domain, MethodLevel


def _make_method(i: int, domain: str = "D") -> Method:
    return Method(id=f"m{i}", name=f"Method{i}", domain=domain,
                   level=MethodLevel((i % 4) + 1), description="")


def _make_problem(i: int, domain: Domain = Domain.MEDICINE) -> Problem:
    return Problem(id=f"p{i}", title=f"Problem{i}", domain=domain,
                    description="")


def _make_matrices(n_methods: int = 10, n_problems: int = 10):
    return (
        [_make_method(i) for i in range(n_methods)],
        [_make_problem(i) for i in range(n_problems)],
    )


class TestDeterministicSeed(unittest.TestCase):
    def test_same_input_same_seed(self):
        s1 = _deterministic_seed(100, "0xAAA", 0)
        s2 = _deterministic_seed(100, "0xAAA", 0)
        self.assertEqual(s1, s2)

    def test_different_user_different_seed(self):
        s1 = _deterministic_seed(100, "0xAAA", 0)
        s2 = _deterministic_seed(100, "0xBBB", 0)
        self.assertNotEqual(s1, s2)

    def test_different_nonce_different_seed(self):
        s1 = _deterministic_seed(100, "0xAAA", 0)
        s2 = _deterministic_seed(100, "0xAAA", 1)
        self.assertNotEqual(s1, s2)

    def test_different_block_different_seed(self):
        s1 = _deterministic_seed(100, "0xAAA", 0)
        s2 = _deterministic_seed(101, "0xAAA", 0)
        self.assertNotEqual(s1, s2)

    def test_seed_is_integer(self):
        s = _deterministic_seed(100, "0xAAA", 0)
        self.assertIsInstance(s, int)


class TestFisherYatesShuffle(unittest.TestCase):
    def setUp(self):
        self.items = list(range(20))

    def test_same_length(self):
        result = fisher_yates_shuffle(self.items, 42)
        self.assertEqual(len(result), len(self.items))

    def test_deterministic(self):
        r1 = fisher_yates_shuffle(self.items, 42)
        r2 = fisher_yates_shuffle(self.items, 42)
        self.assertEqual(r1, r2)

    def test_different_seed_different_order(self):
        r1 = fisher_yates_shuffle(self.items, 42)
        r2 = fisher_yates_shuffle(self.items, 99)
        self.assertNotEqual(r1, r2)

    def test_no_duplicates(self):
        result = fisher_yates_shuffle(self.items, 42)
        self.assertEqual(len(result), len(set(result)))

    def test_original_unchanged(self):
        original = list(self.items)
        fisher_yates_shuffle(self.items, 42)
        self.assertEqual(self.items, original)


class TestGenerateCombinations(unittest.TestCase):
    def setUp(self):
        self.methods, self.problems = _make_matrices(10, 10)

    def test_batch_size(self):
        combos = generate_combinations(self.methods, self.problems,
                                        100, "0xAAA", 0, batch_size=5)
        self.assertEqual(len(combos), 5)

    def test_no_duplicate_within_batch(self):
        combos = generate_combinations(self.methods, self.problems,
                                        100, "0xAAA", 0, batch_size=20)
        ids = [c.id for c in combos]
        self.assertEqual(len(ids), len(set(ids)))

    def test_reproducible(self):
        c1 = generate_combinations(self.methods, self.problems,
                                    100, "0xAAA", 0, batch_size=5)
        c2 = generate_combinations(self.methods, self.problems,
                                    100, "0xAAA", 0, batch_size=5)
        self.assertEqual([c.id for c in c1], [c.id for c in c2])

    def test_different_users_different_combos(self):
        c1 = generate_combinations(self.methods, self.problems,
                                    100, "0xAAA", 0, batch_size=10)
        c2 = generate_combinations(self.methods, self.problems,
                                    100, "0xBBB", 0, batch_size=10)
        ids1 = {c.id for c in c1}
        ids2 = {c.id for c in c2}
        # Different users should get different combos
        self.assertNotEqual(ids1, ids2)

    def test_seen_ids_filtering(self):
        seen = set()
        c1 = generate_combinations(self.methods, self.problems,
                                    100, "0xAAA", 0, batch_size=5)
        seen.update(c.id for c in c1)
        seen_before = set(seen)  # snapshot before mutation
        c2 = generate_combinations(self.methods, self.problems,
                                    100, "0xAAA", 0, batch_size=5,
                                    seen_ids=seen)
        ids2 = {c.id for c in c2}
        self.assertTrue(seen_before.isdisjoint(ids2),
                        "seen_ids should prevent duplicate combos")

    def test_combinations_have_method_and_problem(self):
        combos = generate_combinations(self.methods, self.problems,
                                        100, "0xAAA", 0, batch_size=5)
        for c in combos:
            self.assertIsInstance(c.method, Method)
            self.assertIsInstance(c.problem, Problem)
            self.assertTrue(len(c.id) > 0)


class TestMiningState(unittest.TestCase):
    def setUp(self):
        self.methods, self.problems = _make_matrices(10, 10)

    def test_initial_state(self):
        state = MiningState(user_address="0xTEST")
        self.assertEqual(state.nonce, 0)
        self.assertEqual(state.total_mined, 0)
        self.assertEqual(len(state.seen_combinations), 0)

    def test_mine_batch_increments(self):
        state = MiningState(user_address="0xTEST")
        state.mine_batch(self.methods, self.problems, 100, batch_size=5)
        self.assertEqual(state.nonce, 1)
        self.assertEqual(state.total_mined, 5)

    def test_no_overlap_between_batches(self):
        state = MiningState(user_address="0xTEST")
        b1 = state.mine_batch(self.methods, self.problems, 100, batch_size=5)
        b2 = state.mine_batch(self.methods, self.problems, 100, batch_size=5)
        ids1 = {c.id for c in b1}
        ids2 = {c.id for c in b2}
        self.assertTrue(ids1.isdisjoint(ids2))

    def test_seen_combinations_grows(self):
        state = MiningState(user_address="0xTEST")
        state.mine_batch(self.methods, self.problems, 100, batch_size=5)
        seen_count = len(state.seen_combinations)
        state.mine_batch(self.methods, self.problems, 100, batch_size=5)
        self.assertGreater(len(state.seen_combinations), seen_count)


if __name__ == "__main__":
    unittest.main()
