"""ARIZ Part 5: Apply standard solutions (steps 5.1-5.6)."""
from __future__ import annotations

from src.triz.ariz.base import ARIZState, ARIZPhase
from src.triz.standard_solutions import STANDARD_SOLUTIONS


def execute(state: ARIZState, ai=None) -> ARIZState:
    """5.1-5.6: Match problem to standard solutions."""
    state.current_phase = ARIZPhase.STANDARDS
    state.standard_solutions_applied = []

    # Seek relevant standards for the current contradiction
    is_harmful = any(kw in state.original_problem.lower()
                     for kw in ["harmful", "damage", "break", "waste", "pollute"])
    needs_measuring = any(kw in state.original_problem.lower()
                          for kw in ["measure", "detect", "sensor", "reading", "check"])
    simplification = any(kw in state.original_problem.lower()
                         for kw in ["complex", "expensive", "heavy", "many parts"])

    if is_harmful:
        state.standard_solutions_applied = [1, 2, 8]  # Block harmful interaction
    elif needs_measuring:
        state.standard_solutions_applied = [43, 44, 52]  # Detection standards
    elif simplification:
        state.standard_solutions_applied = [60, 62, 68]  # Simplification
    else:
        state.standard_solutions_applied = [3, 14, 37]  # General evolution

    if ai:
        prompt = _PART5_PROMPT.format(
            problem=state.original_problem,
            pc=state.physical_contradiction,
            resources=", ".join(state.resources),
        )
        resp = ai.generate("ARIZ Part 5: Standard Solutions", prompt)
        # Extract suggested standard IDs from AI response
        for sid in range(1, 77):
            if str(sid) in resp and sid not in state.standard_solutions_applied:
                state.standard_solutions_applied.append(sid)

    return state


_PART5_PROMPT = """Problem: {problem}
Physical Contradiction: {pc}
Available Resources: {resources}

Apply 76 Standard Solutions (5.1-5.6):
Which standard solutions from Classes 1-5 are most applicable?
List specific standard IDs (1-76) and explain why each applies.
"""
