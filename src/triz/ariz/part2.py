"""ARIZ Part 2: Analyze the problem model (steps 2.1-2.6)."""
from __future__ import annotations

from src.triz.ariz.base import ARIZState, ARIZPhase


def execute(state: ARIZState, ai=None) -> ARIZState:
    """2.1-2.6: Build conflict model, identify technical contradiction."""
    state.current_phase = ARIZPhase.MODEL

    if ai:
        prompt = _PART2_PROMPT.format(
            problem=state.original_problem,
            conflict=state.conflicting_pair,
            oz=state.operating_zone,
        )
        resp = ai.generate("ARIZ Part 2: Problem Model", prompt)
        state.technical_contradiction = resp[:200]
    else:
        state.technical_contradiction = (
            f"If we improve {state.conflicting_pair.split('worsens')[0].replace('Improving ', '').strip()}, "
            f"then {state.conflicting_pair.split('worsens')[1].strip() if 'worsens' in state.conflicting_pair else 'another parameter'} degrades"
        )

    return state


_PART2_PROMPT = """Problem: {problem}
Conflict: {conflict}
Operating Zone: {oz}

Build the conflict model:
2.1-2.3: Diagram the conflict as a technical contradiction
2.4-2.6: Identify which parameter improves and which worsens

Output the technical contradiction clearly.
"""
