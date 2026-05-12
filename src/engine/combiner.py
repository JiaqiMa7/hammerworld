"""Combination engine: random shuffle + pairing with anti-duplicate."""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from typing import Optional

from src.engine.models import Method, Problem, Combination


def _deterministic_seed(block_height: int, user_address: str, nonce: int) -> int:
    """Create a deterministic seed from blockchain-like parameters."""
    material = f"{block_height}:{user_address}:{nonce}"
    digest = hashlib.sha256(material.encode()).digest()
    return int.from_bytes(digest[:8], "big")


def fisher_yates_shuffle(items: list, seed: int) -> list:
    """Deterministic Fisher-Yates shuffle."""
    rng = random.Random(seed)
    result = list(items)
    for i in range(len(result) - 1, 0, -1):
        j = rng.randint(0, i)
        result[i], result[j] = result[j], result[i]
    return result


# Small primes for coprime search
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
                 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113)


def _is_coprime(a: int, b: int) -> bool:
    return math.gcd(a, b) == 1


def _find_coprime_near(n: int, target: int) -> int:
    """Find a number coprime to n, close to target (at least 2)."""
    target = max(2, min(target, n - 1))
    # Search outwards from target
    for d in range(0, n):
        for sign in (1, -1):
            candidate = target + sign * d
            if 2 <= candidate < n and _is_coprime(candidate, n):
                return candidate
    return 1  # fallback, never reached for n > 1


def _auto_tune_steps(nm: int, np: int, batch_size: int) -> tuple[int, int, int, int]:
    """Auto-select stepping parameters based on matrix dimensions.

    Returns (method_step, problem_step, problem_offset, max_attempts_mult).
    """
    # Step: target ~size/5 so each traversal crosses ~5 items, but coprime to avoid short cycles
    method_step = _find_coprime_near(nm, max(2, nm // 5))
    problem_step = _find_coprime_near(np, max(2, np // 5))

    # Offset: a small prime coprime to np
    problem_offset = 13
    if not _is_coprime(problem_offset, np):
        for p in _SMALL_PRIMES:
            if _is_coprime(p, np):
                problem_offset = p
                break

    # More attempts for larger matrices, but bounded
    matrix_size = nm * np
    max_attempts_mult = max(3, min(20, matrix_size // (batch_size * 5) + 3))

    return method_step, problem_step, problem_offset, max_attempts_mult


def generate_combinations(
    methods: list[Method],
    problems: list[Problem],
    block_height: int,
    user_address: str,
    nonce: int,
    batch_size: int = 10,
    seen_ids: Optional[set[str]] = None,
    method_step: int = 0,
    problem_step: int = 0,
    problem_offset: int = 0,
    max_attempts_mult: int = 0,
) -> list[Combination]:
    """Generate a batch of method-problem combinations.

    Uses deterministic shuffle based on (block_height, user_address, nonce)
    to ensure reproducibility while preventing duplicate work across users.

    Stepping parameters default to 0 (auto-tune based on matrix size).
    Pass explicit values to override.

    Args:
        methods: All methods in the matrix.
        problems: All problems in the matrix.
        block_height: Current block height (or equivalent epoch).
        user_address: Miner's address for uniqueness.
        nonce: Incremented per batch, like a blockchain nonce.
        batch_size: Number of combinations per batch.
        seen_ids: Previously generated combination IDs to skip.
        method_step: 0 = auto-tune. Multiplier for method index stepping.
        problem_step: 0 = auto-tune. Multiplier for problem index stepping.
        problem_offset: 0 = auto-tune. Base offset into the problem list.
        max_attempts_mult: 0 = auto-tune. Max attempts = max(nm, np) * this value.

    Returns:
        List of Combination objects.
    """
    seen = seen_ids or set()
    seed = _deterministic_seed(block_height, user_address, nonce)

    shuffled_methods = fisher_yates_shuffle(methods, seed)
    shuffled_problems = fisher_yates_shuffle(problems, seed + 1)

    nm, np = len(shuffled_methods), len(shuffled_problems)

    # Auto-tune if any stepping param is 0
    if method_step == 0 or problem_step == 0 or problem_offset == 0 or max_attempts_mult == 0:
        ms, ps, po, ma = _auto_tune_steps(nm, np, batch_size)
        if method_step == 0:
            method_step = ms
        if problem_step == 0:
            problem_step = ps
        if problem_offset == 0:
            problem_offset = po
        if max_attempts_mult == 0:
            max_attempts_mult = ma

    combinations: list[Combination] = []
    max_attempts = max(nm, np) * max_attempts_mult

    i = 0
    while len(combinations) < batch_size and i < max_attempts:
        m = shuffled_methods[(nonce * method_step + i) % nm]
        p = shuffled_problems[(nonce * problem_offset + i * problem_step) % np]
        combo_id = Combination.make_id(m.id, p.id)

        if combo_id not in seen and combo_id not in {c.id for c in combinations}:
            combinations.append(Combination(id=combo_id, method=m, problem=p))
            seen.add(combo_id)

        i += 1

    return combinations


@dataclass
class MiningState:
    """Tracks a user's mining progress to avoid re-mining."""
    user_address: str
    nonce: int = 0
    seen_combinations: set[str] = field(default_factory=set)
    total_mined: int = 0

    def mine_batch(
        self,
        methods: list[Method],
        problems: list[Problem],
        block_height: int,
        batch_size: int = 10,
        method_step: int = 0,
        problem_step: int = 0,
        problem_offset: int = 0,
        max_attempts_mult: int = 0,
    ) -> list[Combination]:
        """Mine one batch of combinations."""
        combos = generate_combinations(
            methods, problems, block_height,
            self.user_address, self.nonce, batch_size,
            self.seen_combinations,
            method_step=method_step,
            problem_step=problem_step,
            problem_offset=problem_offset,
            max_attempts_mult=max_attempts_mult,
        )
        for c in combos:
            self.seen_combinations.add(c.id)
        self.nonce += 1
        self.total_mined += len(combos)
        return combos
