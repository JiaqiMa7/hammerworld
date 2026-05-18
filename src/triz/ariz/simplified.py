"""Simplified ARIZ: ~30 condensed steps across all phases."""
from __future__ import annotations

from typing import Optional

from src.triz.ariz.base import ARIZState, ARIZResult, ARIZPhase
from src.triz.ariz import part1, part3, part4, part5, part6, part7, part9


def run_simplified(description: str, ai_provider=None) -> ARIZResult:
    """Run a condensed ~30-step ARIZ analysis."""
    state = ARIZState(original_problem=description)
    completed = []

    # Step 1-4: Mini-problem (condensed from Part 1)
    state = part1.execute(state, ai_provider)
    completed.append("Mini-problem formulation")
    state.mini_problem = f"Resolve: {_first_sentence(description)} without adding harmful complexity"

    # Step 5-10: Conflict & IFR (condensed from Parts 2-3)
    state.current_phase = ARIZPhase.IFR
    state.technical_contradiction = (
        f"The system's {_extract_noun(description)} must improve "
        f"but {_extract_noun(description, offset=1)} worsens as a result"
    )
    state.ifr_levels = [
        f"IFR: {_first_sentence(description)} with zero harmful effects",
        "IFR: Uses only resources already in the system",
        "IFR: No increase in system complexity",
    ]
    state.physical_contradiction = "The parameter must satisfy two opposing requirements"
    completed.append("IFR & Contradiction definition")

    # Step 11-15: Resources & Standards (condensed from Parts 4-5)
    state = part4.execute(state, ai_provider)
    state = part5.execute(state, ai_provider)
    completed.append("Resource & Standard Solutions scan")

    # Step 16-20: Reformulation (condensed from Part 6)
    state = part6.execute(state, ai_provider)
    completed.append("Problem reformulation")

    # Step 21-25: Evaluate (condensed from Part 7)
    state = part7.execute(state, ai_provider)
    completed.append("Solution quality check")

    # Step 26-30: Meta (condensed from Parts 8-9)
    state = part9.execute(state, ai_provider)
    completed.append("Meta-reflection & abstraction")

    return ARIZResult(
        original_problem=state.original_problem,
        mini_problem=state.mini_problem,
        conflict_description=state.technical_contradiction,
        ifr=state.ifr_levels[0] if state.ifr_levels else "",
        physical_contradiction=state.physical_contradiction,
        resource_summary=", ".join(state.resources) if state.resources else "",
        solution_concept=state.solution_concept or state.meta_reflection,
        steps_completed=30,
        phases_completed=completed,
        rule_based=ai_provider is None,
    )


def _first_sentence(text: str) -> str:
    sentences = text.replace("?", ".").replace("!", ".").split(".")
    return sentences[0].strip() if sentences else text[:80]


def _extract_noun(text: str, offset: int = 0) -> str:
    words = [w for w in text.split() if len(w) > 4]
    if len(words) > offset:
        return words[offset]
    return "parameter"
