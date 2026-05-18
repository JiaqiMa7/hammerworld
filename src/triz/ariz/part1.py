"""ARIZ Part 1: Analyze the problem (steps 1.1-1.8)."""
from __future__ import annotations

from src.triz.ariz.base import ARIZState, ARIZPhase


def execute(state: ARIZState, ai=None) -> ARIZState:
    """1.1-1.8: Formulate mini-problem, identify conflict, define operating zone."""
    state.current_phase = ARIZPhase.ANALYSIS
    desc = state.original_problem

    if ai:
        prompt = _PART1_PROMPT.format(problem=desc)
        resp = ai.generate("ARIZ Part 1: Problem Analysis", prompt)
        state.mini_problem = resp[:200]
        state.conflicting_pair = _extract_conflict(resp)
        state.operating_zone = _extract_oz(resp)
        state.operating_time = "Before, during, and after the conflict"
    else:
        state.mini_problem = f"Find a way to resolve '{desc[:80]}...' without adding complexity"
        state.conflicting_pair = _rule_conflict(desc)
        state.operating_zone = "The region where conflicting elements interact"
        state.operating_time = "The time interval when the conflict occurs"

    return state


def _extract_conflict(text: str) -> str:
    """Extract conflict pair from AI response."""
    lines = [l for l in text.split("\n") if "conflict" in l.lower() or "contradiction" in l.lower()]
    return lines[0] if lines else "Need to improve A without worsening B"


def _extract_oz(text: str) -> str:
    """Extract operating zone from AI response."""
    lines = [l for l in text.split("\n") if "zone" in l.lower() or "area" in l.lower()]
    return lines[0] if lines else "Intersection of conflicting components"


def _rule_conflict(desc: str) -> str:
    """Rule-based conflict identification."""
    desc_l = desc.lower()
    pairs = []
    for a in ["speed", "weight", "strength", "reliability", "cost", "complexity"]:
        for b in ["speed", "weight", "strength", "reliability", "cost", "complexity"]:
            if a != b and a in desc_l and b in desc_l:
                pairs.append(f"Improving {a} worsens {b}")
    return pairs[0] if pairs else "Generic conflict between performance parameters"


_PART1_PROMPT = """Analyze the following problem for ARIZ-85C Part 1:
Problem: {problem}

Identify:
1. The mini-problem (conflict without adding complexity)
2. The conflicting pair (what conflicts with what)
3. The operating zone (where the conflict occurs)
4. The operating time (when the conflict occurs)
"""
