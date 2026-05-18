"""Su-Field (Substance-Field) analysis for TRIZ."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.triz.prompts import SU_FIELD_PROMPT


@dataclass
class SuFieldModel:
    """Substance-Field model of a technical system."""
    substance1: str
    substance2: str
    field: str
    interaction_type: str = "unknown"  # useful/harmful/insufficient/excessive
    is_complete: bool = False
    missing_elements: list[str] = field(default_factory=list)
    transformation_suggestions: list[str] = field(default_factory=list)
    ai_insight: str = ""


_SUBJECT_ACTION_REGEX = [
    (r"(\w+)\s+(?:applies?|uses?|provides?|delivers?)\s+(\w+)", "field"),
    (r"(\w+)\s+(?:heats?|cools?|moves?|rotates?|drives?)\s+(\w+)", "mechanical"),
    (r"(\w+)\s+(?:cleans?|dries?|separates?|filter\w*)", "field"),
    (r"(\w+)\s+(?:damages?|breaks?|corrodes?|wears?)\s+(\w+)", "harmful"),
]

_INTERACTION_KEYWORDS = {
    "heats": ("thermal", "heat"),
    "cools": ("thermal", "cold"),
    "moves": ("mechanical", "movement"),
    "rotates": ("mechanical", "rotation"),
    "drives": ("mechanical", "force"),
    "cleans": ("chemical", "reaction"),
    "separates": ("mechanical", "separation"),
    "dries": ("thermal", "evaporation"),
    "heats and cools": ("thermal", "dual"),
    "applies": ("mechanical", "pressure"),
    "uses": ("unspecified", "generic"),
    "provides": ("unspecified", "generic"),
    "delivers": ("unspecified", "generic"),
}

_HARMFUL_KEYWORDS = ["damage", "break", "corrode", "wear", "friction", "heat loss",
                     "vibration", "noise", "waste", "pollute", "contaminate", "leak"]
_INSUFFICIENT_KEYWORDS = ["slow", "weak", "inefficient", "poor", "low", "barely",
                          "hard to", "difficult"]
_EXCESSIVE_KEYWORDS = ["too much", "excessive", "overheat", "overshoot", "overload",
                       "too fast", "too strong"]


def _classify_interaction(desc_lower: str) -> str:
    """Classify the interaction type based on keywords."""
    for kw in _HARMFUL_KEYWORDS:
        if kw in desc_lower:
            return "harmful"
    for kw in _INSUFFICIENT_KEYWORDS:
        if kw in desc_lower:
            return "insufficient"
    for kw in _EXCESSIVE_KEYWORDS:
        if kw in desc_lower:
            return "excessive"
    return "useful"


def analyze(description: str, ai_provider=None) -> SuFieldModel:
    """Analyze a problem description using Su-Field modeling."""
    desc_lower = description.lower()

    # Rule-based: extract S1, S2, field from text patterns
    s1, s2, field = "", "", ""
    for pattern, default_field in _SUBJECT_ACTION_REGEX:
        import re
        m = re.search(pattern, desc_lower)
        if m:
            s1 = m.group(1)
            s2 = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
            field = default_field
            break

    if not s1:
        words = desc_lower.split()
        s1 = words[0] if len(words) > 0 else "system"
        s2 = words[-1] if len(words) > 2 else "environment"

    if ai_provider:
        prompt = SU_FIELD_PROMPT.format(description=description)
        response = ai_provider.generate("You are a TRIZ Su-Field expert.", prompt)
        ai_insight = response[:500]
    else:
        ai_insight = ""

    interaction = _classify_interaction(desc_lower)
    missing = []
    if not s1:
        missing.append("Substance 1 (tool)")
    if not s2:
        missing.append("Substance 2 (object)")
    if not field:
        missing.append("Field (energy interaction)")

    suggestions = []
    if interaction == "harmful":
        suggestions.append("Introduce a third substance S3 to block the harmful interaction")
        suggestions.append("Use a competing field to cancel the harmful effect")
    elif interaction == "insufficient":
        suggestions.append("Increase field intensity or change field type")
        suggestions.append("Add a modifying substance to S1 or S2 to improve interaction")
    elif interaction == "excessive":
        suggestions.append("Introduce a field-regulating substance")
        suggestions.append("Use a damping field to reduce intensity")

    return SuFieldModel(
        substance1=s1, substance2=s2, field=field,
        interaction_type=interaction,
        is_complete=len(missing) == 0,
        missing_elements=missing,
        transformation_suggestions=suggestions,
        ai_insight=ai_insight,
    )
