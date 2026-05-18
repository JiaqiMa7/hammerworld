"""Cause-Effect Chain Analysis for TRIZ root cause identification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.triz.prompts import CAUSE_EFFECT_PROMPT


@dataclass
class CauseEffectLink:
    """A single cause-effect relationship."""
    cause: str
    effect: str
    confidence: float = 1.0  # 0.0-1.0

    def __str__(self) -> str:
        return f"{self.cause} → {self.effect}"


@dataclass
class CauseEffectChain:
    """Complete causal chain from root cause to final symptom."""
    chain: list[CauseEffectLink] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)
    final_effects: list[str] = field(default_factory=list)
    ai_insight: str = ""


_CAUSE_INDICATORS = [
    "because", "since", "due to", "caused by", "results from",
    "comes from", "originates", "as a result of", "on account of",
]
_EFFECT_INDICATORS = [
    "therefore", "thus", "leads to", "results in", "causes",
    "produces", "creates", "triggers", "generates", "so that",
    "consequently", "hence", "so",
]
_PARAGRAPH_SEPS = [". ", "; ", ", but ", ", and ", ", so "]


def analyze(description: str, ai_provider=None) -> CauseEffectChain:
    """Extract cause-effect relationships from the description."""
    import re
    desc_lower = description.lower()
    chain: list[CauseEffectLink] = []

    sentences = re.split(r"[.!?]\s+", desc_lower)
    for sentence in sentences:
        cause, effect = "", ""
        for indicator in _CAUSE_INDICATORS:
            if indicator in sentence:
                parts = re.split(rf"\b{indicator}\b", sentence, maxsplit=1)
                if len(parts) == 2:
                    effect, cause = parts[0].strip(), parts[1].strip()
                    break
        for indicator in _EFFECT_INDICATORS:
            if indicator in sentence:
                parts = re.split(rf"\b{indicator}\b", sentence, maxsplit=1)
                if len(parts) == 2 and not cause:
                    cause, effect = parts[0].strip(), parts[1].strip()
                    break
        if cause and effect:
            chain.append(CauseEffectLink(cause=cause, effect=effect))

    all_causes = [link.cause for link in chain]
    all_effects = [link.effect for link in chain]
    root_causes = [c for c in all_causes if c not in all_effects]
    final_effects = [e for e in all_effects if e not in all_causes]

    if not root_causes and chain:
        root_causes = [chain[0].cause]
    if not final_effects and chain:
        final_effects = [chain[-1].effect]

    if ai_provider:
        prompt = CAUSE_EFFECT_PROMPT.format(description=description)
        response = ai_provider.generate("You are a TRIZ cause-effect expert.", prompt)
        ai_insight = response[:500]
    else:
        ai_insight = ""

    return CauseEffectChain(
        chain=chain, root_causes=root_causes,
        final_effects=final_effects, ai_insight=ai_insight,
    )
