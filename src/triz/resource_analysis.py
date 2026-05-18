"""Resource analysis for TRIZ: identify available resources in the system."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.triz.prompts import RESOURCE_ANALYSIS_PROMPT


@dataclass
class ResourcePool:
    """Resources available in the system, classified by type."""
    substances: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    space: list[str] = field(default_factory=list)
    time: list[str] = field(default_factory=list)
    information: list[str] = field(default_factory=list)
    function: list[str] = field(default_factory=list)
    ai_insight: str = ""


_RESOURCE_KEYWORDS: dict[str, list[str]] = {
    "substances": ["material", "substance", "liquid", "gas", "solid", "powder",
                   "metal", "plastic", "water", "air", "chemical", "compound"],
    "fields": ["electric", "magnetic", "thermal", "kinetic", "pressure",
               "gravity", "vibration", "sound", "light", "radiation", "field"],
    "space": ["empty", "gap", "space", "cavity", "hole", "surface", "area",
              "volume", "container", "chamber"],
    "time": ["pause", "wait", "interval", "break", "idle", "cycle", "delay",
             "before", "after", "during", "simultaneous"],
    "information": ["data", "signal", "indicator", "measurement", "reading",
                    "feedback", "information", "status", "log"],
    "function": ["flow", "transport", "mix", "separate", "store", "hold",
                 "guide", "protect", "convert", "absorb"],
}

_FIELD_TYPES = ["mechanical", "thermal", "chemical", "electric", "magnetic",
                "electromagnetic", "acoustic", "optical", "capillary", "biological"]


def analyze(description: str, ai_provider=None) -> ResourcePool:
    """Scan description and classify available resources."""
    desc_lower = description.lower()
    result = ResourcePool()

    for rtype, keywords in _RESOURCE_KEYWORDS.items():
        found = set()
        for kw in keywords:
            if kw in desc_lower:
                found.add(kw)
        # Extract surrounding noun phrases for matched keywords
        setattr(result, rtype, sorted(found))

    # Also scan for field type keywords
    found_fields = []
    for ft in _FIELD_TYPES:
        if ft in desc_lower:
            found_fields.append(ft)
    result.fields = sorted(set(result.fields + found_fields))

    if ai_provider:
        prompt = RESOURCE_ANALYSIS_PROMPT.format(description=description)
        response = ai_provider.generate("You are a TRIZ resource analysis expert.", prompt)
        result.ai_insight = response[:500]

    return result
