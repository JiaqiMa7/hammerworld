"""Smart Little People (SLP) modeling for TRIZ problem-solving."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.triz.prompts import SMART_LITTLE_PEOPLE_PROMPT


@dataclass
class SLPCharacter:
    """A type of 'little person' in the model."""
    role: str
    behavior: str
    conflict: str = ""


@dataclass
class SLPResult:
    """Result of a Smart Little People modeling session."""
    characters: list[SLPCharacter] = field(default_factory=list)
    ideal_configuration: str = ""
    key_insight: str = ""
    ai_insight: str = ""


def analyze(description: str, ai_provider=None) -> SLPResult:
    """Model the problem using Smart Little People perspective."""
    import re
    desc_lower = description.lower()
    result = SLPResult()

    # Extract actors/roles from description
    roles = re.findall(r"(\w+(?:\s+\w+)?)\s+(?:that|which|who)\s+(?:is|are|does|do)", desc_lower)
    if not roles:
        words = desc_lower.split()
        roles = [w for w in words if len(w) > 4][:3]
    if not roles:
        roles = ["system"]

    for i, role in enumerate(roles[:4]):
        behavior = f"Moves/resources according to original specification"
        conflict = f"Interacts with other elements"
        for kw in ["heat", "cold", "fast", "slow", "heavy", "light", "pressure", "force"]:
            if kw in desc_lower:
                behavior = f"Responds to {kw} by changing position/state"
                conflict = f"Clashes with neighbors when {kw} changes"
                break
        result.characters.append(SLPCharacter(
            role=role, behavior=behavior, conflict=conflict,
        ))

    result.ideal_configuration = (
        f"All {len(result.characters)} groups of little people cooperate harmoniously. "
        f"{result.characters[0].role if result.characters else 'The system'} "
        f"performs its function without conflict."
    )

    result.key_insight = (
        f"The conflict between little people reveals that the real problem is about "
        f"coordination, not about individual component limitations."
    )

    if ai_provider:
        prompt = SMART_LITTLE_PEOPLE_PROMPT.format(description=description)
        response = ai_provider.generate(
            "You are a TRIZ Smart Little People modeling expert.", prompt,
        )
        result.ai_insight = response[:500]

    return result
