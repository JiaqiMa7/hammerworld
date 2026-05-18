"""9-Windows (System Operator) for TRIZ multi-level system thinking."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.triz.prompts import NINE_WINDOWS_PROMPT


@dataclass
class NineWindowPanel:
    """3x3 matrix: System / Supersystem / Subsystem × Past / Present / Future."""
    supersystem_past: str = ""
    supersystem_present: str = ""
    supersystem_future: str = ""
    system_past: str = ""
    system_present: str = ""
    system_future: str = ""
    current_system: str = ""
    ai_insight: str = ""

    @property
    def as_grid(self) -> dict[str, dict[str, str]]:
        """Return the 9-window view as a nested dict: {level: {time: content}}."""
        return {
            "supersystem": {
                "past": self.supersystem_past,
                "present": self.supersystem_present,
                "future": self.supersystem_future,
            },
            "system": {
                "past": self.system_past,
                "present": self.system_present,
                "future": self.system_future,
            },
            "subsystem": {
                "past": "",
                "present": "",
                "future": "",
            },
        }


_WINDOW_TEMPLATES = {
    "supersystem_past": ("Before {system}, the broader environment was: {desc}"),
    "supersystem_present": ("The broader environment includes {system} as a part, with {desc}"),
    "supersystem_future": ("In the future, the broader environment will evolve: {desc}"),
    "system_past": ("Before {system}, the system was: {desc}"),
    "system_present": ("The current system {system} has {desc}"),
    "system_future": ("The future system derived from {system} will have {desc}"),
}


def analyze(description: str, ai_provider=None) -> NineWindowPanel:
    """Fill the 9-windows based on a problem description."""
    desc_lower = description.lower()
    words = desc_lower.split()
    system = words[0] if words else "the system"
    # Find the likely system name (first noun-like word)
    for word in words:
        if len(word) > 3 and word not in ("this", "that", "there", "these"):
            system = word
            break

    result = NineWindowPanel(current_system=system)

    # Generate rule-based fallback content for each window
    for key, template in _WINDOW_TEMPLATES.items():
        level, time = key.split("_", 1)
        if time == "present":
            setattr(result, key, f"Current: {system} operates with {description[:80]}")
        elif time == "past":
            setattr(result, key, f"Earlier version of the {level} had simpler configuration")
        elif time == "future":
            setattr(result, key, f"Improved {level} with enhanced capabilities")

    # Subsystem defaults (we don't know enough from one description)
    result.subsystem_past = "Earlier internal components"
    result.subsystem_present = f"Internal parts of {system}"
    result.subsystem_future = "Miniaturized, integrated sub-components"

    if ai_provider:
        prompt = NINE_WINDOWS_PROMPT.format(description=description, system=system)
        response = ai_provider.generate("You are a TRIZ system operator expert.", prompt)
        result.ai_insight = response[:500]

    return result
