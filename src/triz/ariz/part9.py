"""ARIZ Part 9: Meta-analysis of problem-solving process (steps 9.1-9.10)."""
from __future__ import annotations

from src.triz.ariz.base import ARIZState, ARIZPhase


def execute(state: ARIZState, ai=None) -> ARIZState:
    """9.1-9.10: Reflect on the process and abstract the solution."""
    state.current_phase = ARIZPhase.META

    if ai:
        prompt = _PART9_PROMPT.format(
            problem=state.original_problem,
            solution=state.solution_concept,
            steps=", ".join(state.evaluation_notes[:3]),
        )
        resp = ai.generate("ARIZ Part 9: Meta-Analysis", prompt)
        state.meta_reflection = resp[:300]
    else:
        state.meta_reflection = (
            f"Abstract principle: The contradiction was resolved by "
            f"{'separating conflicting requirements in time' if 'time' in state.original_problem.lower() else 'using available resources'}.\n"
            f"This principle can be applied to similar problems in other domains."
        )

    return state


_PART9_PROMPT = """Original Problem: {problem}
Solution: {solution}
Evaluation: {steps}

Reflect on the process (9.1-9.10):
9.1-9.3: What was the key insight?
9.4-9.6: Can this solution principle be abstracted?
9.7-9.8: What other problems could this solve?
9.9-9.10: What did we learn about the problem-solving process?
"""
