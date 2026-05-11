"""Combination engine: random shuffle + pairing with anti-duplicate."""
from __future__ import annotations

import hashlib
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


def generate_combinations(
    methods: list[Method],
    problems: list[Problem],
    block_height: int,
    user_address: str,
    nonce: int,
    batch_size: int = 10,
    seen_ids: Optional[set[str]] = None,
) -> list[Combination]:
    """Generate a batch of method-problem combinations.

    Uses deterministic shuffle based on (block_height, user_address, nonce)
    to ensure reproducibility while preventing duplicate work across users.

    The step multiplier (i * 3) for problems ensures the method and problem
    indices walk the shuffled lists at different rates, creating diverse
    pairings rather than simple diagonal matching.

    Args:
        methods: All methods in the matrix.
        problems: All problems in the matrix.
        block_height: Current block height (or equivalent epoch).
        user_address: Miner's address for uniqueness.
        nonce: Incremented per batch, like a blockchain nonce.
        batch_size: Number of combinations per batch.
        seen_ids: Previously generated combination IDs to skip.

    Returns:
        List of Combination objects.
    """
    seen = seen_ids or set()
    seed = _deterministic_seed(block_height, user_address, nonce)

    shuffled_methods = fisher_yates_shuffle(methods, seed)
    shuffled_problems = fisher_yates_shuffle(problems, seed + 1)

    combinations: list[Combination] = []
    nm, np = len(shuffled_methods), len(shuffled_problems)

    i = 0
    while len(combinations) < batch_size and i < max(nm, np) * 3:
        m = shuffled_methods[(nonce * 7 + i) % nm]
        p = shuffled_problems[(nonce * 13 + i * 3) % np]
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
    ) -> list[Combination]:
        """Mine one batch of combinations."""
        combos = generate_combinations(
            methods, problems, block_height,
            self.user_address, self.nonce, batch_size,
            self.seen_combinations,
        )
        for c in combos:
            self.seen_combinations.add(c.id)
        self.nonce += 1
        self.total_mined += len(combos)
        return combos
