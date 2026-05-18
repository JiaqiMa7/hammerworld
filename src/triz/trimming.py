"""Trimming algorithm for TRIZ: eliminate components while preserving function."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.triz.prompts import TRIMMING_PROMPT


@dataclass
class TrimmingResult:
    """Result of trimming analysis on a system."""
    components: list[str] = field(default_factory=list)
    trimming_candidates: list[dict] = field(default_factory=list)
    # Each candidate: {component, function, replacement_strategy, feasibility}
    preserved_functions: list[str] = field(default_factory=list)
    ai_insight: str = ""


def analyze(description: str, ai_provider=None) -> TrimmingResult:
    """Identify components and suggest trimming candidates."""
    import re
    desc_lower = description.lower()
    result = TrimmingResult()

    # Extract potential components (nouns with context)
    # Simple heuristic: look for words that appear as subjects or objects
    component_patterns = re.findall(
        r"(?:the|a|an)\s+(\w+(?:\s+\w+)?)\s+(?:is|has|uses|provides|creates|needs)",
        desc_lower,
    )
    result.components = sorted(set(component_patterns))

    # Also find things that could be nouns in a list
    if not result.components:
        conj_patterns = re.findall(r"(\w+(?:\s+\w+)?)\s+and\s+(\w+(?:\s+\w+)?)", desc_lower)
        result.components = [cp[0] for cp in conj_patterns[:3]] + [cp[1] for cp in conj_patterns[:3]]
        result.components = sorted(set(result.components))

    if not result.components:
        words = desc_lower.split()
        result.components = [w for w in words[:5] if len(w) > 3]

    # Generate trimming candidates with replacement strategies
    strategies = [
        "Merge with another component",
        "Relocate function to super-system",
        "Relocate function to sub-system",
        "Eliminate and use available resources",
        "Replace with self-service function",
    ]

    for comp in result.components[:5]:
        candidate = {
            "component": comp,
            "function": f"Provides related {comp} functionality",
            "replacement_strategy": strategies[len(result.trimming_candidates) % len(strategies)],
            "feasibility": "medium",
        }
        result.trimming_candidates.append(candidate)

    result.preserved_functions = [
        f"Maintain core function of {c['component']} via {c['replacement_strategy'].lower()}"
        for c in result.trimming_candidates
    ]

    if ai_provider:
        prompt = TRIMMING_PROMPT.format(description=description)
        response = ai_provider.generate("You are a TRIZ trimming expert.", prompt)
        result.ai_insight = response[:500]

    return result
