"""ARIZ Part 4: Mobilize and utilize resources (steps 4.1-4.6)."""
from __future__ import annotations

from src.triz.ariz.base import ARIZState, ARIZPhase


_RESOURCE_TYPES = [
    "substance", "field", "space", "time", "information", "energy", "function",
]


def execute(state: ARIZState, ai=None) -> ARIZState:
    """4.1-4.6: Scan for 7 types of resources in the system and environment."""
    state.current_phase = ARIZPhase.RESOURCES
    desc_lower = state.original_problem.lower()

    if ai:
        prompt = _PART4_PROMPT.format(
            problem=state.original_problem, oz=state.operating_zone,
        )
        resp = ai.generate("ARIZ Part 4: Resource Mobilization", prompt)
        state.resources = _extract_resources(resp)
    else:
        state.resources = []
        for rtype in _RESOURCE_TYPES:
            # Simple heuristic: if related words exist in problem, flag the resource
            found = _match_resource_type(desc_lower, rtype)
            if found:
                state.resources.append(f"{rtype}: {found}")
        if not state.resources:
            state.resources = [
                "substance: materials already in the system",
                "field: energy forms present in the operating zone",
                "time: pauses and idle intervals in the process",
            ]

    return state


def _match_resource_type(text: str, rtype: str) -> str:
    """Find resource-related words in the text."""
    keywords = {
        "substance": ["material", "liquid", "gas", "solid", "water", "air", "metal"],
        "field": ["heat", "cold", "force", "pressure", "electric", "magnetic", "light"],
        "space": ["gap", "hole", "cavity", "space", "area", "surface", "between"],
        "time": ["time", "delay", "wait", "cycle", "period", "interval", "before"],
        "information": ["signal", "data", "measure", "reading", "status", "feedback"],
        "energy": ["energy", "power", "fuel", "waste", "heat loss", "kinetic"],
        "function": ["flow", "transport", "separate", "mix", "filter", "store", "hold"],
    }
    matches = [kw for kw in keywords.get(rtype, []) if kw in text]
    return ", ".join(matches[:3]) if matches else ""


def _extract_resources(text: str) -> list[str]:
    return [l.strip() for l in text.split("\n") if "resource" in l.lower() or ":" in l][:7]


_PART4_PROMPT = """Problem: {problem}
Operating Zone: {oz}

Identify available resources (4.1-4.6):
- Substance resources
- Field resources
- Space resources
- Time resources
- Information resources
- Energy resources
- Function resources

Include resources in the system AND in the environment.
"""
