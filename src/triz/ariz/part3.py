"""ARIZ Part 3: Define IFR and physical contradiction (steps 3.1-3.7)."""
from __future__ import annotations

from src.triz.ariz.base import ARIZState, ARIZPhase


def execute(state: ARIZState, ai=None) -> ARIZState:
    """3.1-3.7: Five levels of IFR, formulate physical contradiction."""
    state.current_phase = ARIZPhase.IFR

    if ai:
        prompt = _PART3_PROMPT.format(
            problem=state.original_problem, tc=state.technical_contradiction,
        )
        resp = ai.generate("ARIZ Part 3: IFR & Physical Contradiction", prompt)
        state.ifr_levels = _extract_ifr_levels(resp)
        state.physical_contradiction = _extract_pc(resp)
    else:
        tc = state.technical_contradiction
        state.ifr_levels = [
            f"IFR-1: {tc.split('then')[0] if 'then' in tc else 'System'} without any harmful effects",
            f"IFR-2: The system itself resolves the contradiction",
            f"IFR-3: The system uses only available resources",
            f"IFR-4: The system operates without increasing complexity",
            f"IFR-5: Ideal - the system does not exist but function is performed",
        ]
        state.physical_contradiction = (
            f"The system must have property X to {state.conflicting_pair}, "
            f"and NOT have property X to avoid degradation"
        )

    return state


def _extract_ifr_levels(text: str) -> list[str]:
    return [l.strip() for l in text.split("\n") if "IFR" in l or "ifr" in l][:5]


def _extract_pc(text: str) -> str:
    lines = [l for l in text.split("\n") if "physical" in l.lower() or "must" in l.lower()]
    return lines[0] if lines else "The parameter must be both high and low simultaneously"


_PART3_PROMPT = """Problem: {problem}
Technical Contradiction: {tc}

Define the Ideal Final Result (IFR) at 5 levels:
3.1: IFR-1 (no harmful effects)
3.2: IFR-2 (system resolves itself)
3.3: IFR-3 (uses available resources)
3.4: IFR-4 (no new complexity)
3.5: IFR-5 (ideal - function without system)

Then formulate the physical contradiction (3.6-3.7).
"""
