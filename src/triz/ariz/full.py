"""Full ARIZ-85C orchestrator: runs all 9 parts sequentially."""
from __future__ import annotations

from typing import Optional

from src.triz.ariz.base import ARIZState, ARIZResult
from src.triz.ariz import part1, part2, part3, part4, part5, part6, part7, part8, part9

_PHASES = [
    ("Part 1: Problem Analysis", part1.execute),
    ("Part 2: Problem Model", part2.execute),
    ("Part 3: IFR & Physical Contradiction", part3.execute),
    ("Part 4: Resource Mobilization", part4.execute),
    ("Part 5: Standard Solutions", part5.execute),
    ("Part 6: Problem Reformulation", part6.execute),
    ("Part 7: Solution Analysis", part7.execute),
    ("Part 8: Application Plan", part8.execute),
    ("Part 9: Meta-Analysis", part9.execute),
]


def run_full(description: str, ai_provider=None) -> ARIZResult:
    """Run the complete 85-step ARIZ algorithm."""
    state = ARIZState(original_problem=description)
    completed = []

    for name, fn in _PHASES:
        state = fn(state, ai_provider)
        completed.append(name)

    return ARIZResult(
        original_problem=state.original_problem,
        mini_problem=state.mini_problem,
        conflict_description=state.technical_contradiction,
        ifr="\n".join(state.ifr_levels) if state.ifr_levels else "",
        physical_contradiction=state.physical_contradiction,
        resource_summary="\n".join(state.resources) if state.resources else "",
        solution_concept=state.solution_concept,
        steps_completed=len(_PHASES) * 9,  # ~9 steps per phase
        phases_completed=completed,
        rule_based=ai_provider is None,
    )
