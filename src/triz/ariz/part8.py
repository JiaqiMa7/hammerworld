"""ARIZ Part 8: Apply the solution (steps 8.1-8.4)."""
from __future__ import annotations

from src.triz.ariz.base import ARIZState, ARIZPhase


def execute(state: ARIZState, ai=None) -> ARIZState:
    """8.1-8.4: Develop implementation plan and handle side effects."""
    state.current_phase = ARIZPhase.APPLY
    sc = state.solution_concept

    if ai:
        prompt = _PART8_PROMPT.format(solution=sc, resources=", ".join(state.resources))
        resp = ai.generate("ARIZ Part 8: Application Plan", prompt)
        state.solution_concept = sc + "\n" + resp[:300]
    else:
        state.solution_concept = (
            f"Implementation approach: {sc[:100]}...\n"
            f"Use available resources: {', '.join(state.resources[:3])}\n"
            f"Monitor for secondary problems during implementation"
        )

    return state


_PART8_PROMPT = """Solution: {solution}
Available Resources: {resources}

Develop implementation plan (8.1-8.4):
8.1: Break solution into sub-problems
8.2: Identify resources needed for each sub-problem
8.3: Plan for side effects
8.4: Create implementation timeline
"""
