"""ARIZ Part 6: Change the problem (steps 6.1-6.8)."""
from __future__ import annotations

from src.triz.ariz.base import ARIZState, ARIZPhase


def execute(state: ARIZState, ai=None) -> ARIZState:
    """6.1-6.8: Reformulate, invert, or reframe the problem."""
    state.current_phase = ARIZPhase.REFORMULATE
    fc = state.conflicting_pair

    if ai:
        prompt = _PART6_PROMPT.format(
            problem=state.original_problem,
            conflict=fc,
            pc=state.physical_contradiction,
        )
        resp = ai.generate("ARIZ Part 6: Problem Reformulation", prompt)
        state.solution_concept = resp[:300]
    else:
        # Rule-based reformulation: try the inverse problem
        inverse_approaches = [
            f"What if we reverse the relationship: {fc.replace('Improving', 'Worsening') if 'Improving' in fc else 'do the opposite'}",
            "What if the system performs the opposite function?",
            "What if we eliminate the component causing the conflict?",
            "What if we combine the conflicting requirements in time?",
            "What if we combine the conflicting requirements in space?",
        ]
        state.solution_concept = inverse_approaches[0]

    return state


_PART6_PROMPT = """Problem: {problem}
Conflict: {conflict}
Physical Contradiction: {pc}

Reformulate the problem (6.1-6.8):
6.1: Try the inverse problem
6.2: Reformulate at system level
6.3: Reformulate at supersystem level
6.4: Try combining conflicting requirements in TIME
6.5: Try combining conflicting requirements in SPACE
6.6-6.8: Apply separation principles

Propose a solution concept.
"""
