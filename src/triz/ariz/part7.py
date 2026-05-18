"""ARIZ Part 7: Analyze the solution quality (steps 7.1-7.6)."""
from __future__ import annotations

from src.triz.ariz.base import ARIZState, ARIZPhase


_CHECKS = [
    ("Substance check", "Does the solution require introducing a new substance?"),
    ("Field check", "Does the solution require a new field source?"),
    ("Complexity check", "Does the solution increase system complexity?"),
    ("Novelty check", "Is the solution non-obvious?"),
    ("Patent check", "Could the solution be patented?"),
    ("Secondary problem check", "Does the solution create new problems?"),
]


def execute(state: ARIZState, ai=None) -> ARIZState:
    """7.1-7.6: Evaluate solution quality and check for new problems."""
    state.current_phase = ARIZPhase.EVALUATE
    state.evaluation_notes = []

    if ai:
        prompt = _PART7_PROMPT.format(
            solution=state.solution_concept,
            problem=state.original_problem,
        )
        resp = ai.generate("ARIZ Part 7: Solution Analysis", prompt)
        state.evaluation_notes = [l.strip() for l in resp.split("\n") if l.strip()][:6]
    else:
        for name, _ in _CHECKS:
            state.evaluation_notes.append(f"{name}: Pending verification")

    return state


_PART7_PROMPT = """Solution Concept: {solution}
Original Problem: {problem}

Evaluate the solution (7.1-7.6):
7.1: Does it contain all necessary substances?
7.2: Does it contain all necessary fields?
7.3: Is the complexity justified?
7.4: Is it a novel solution?
7.5: Could it be patented?
7.6: Does it create secondary problems?
"""
