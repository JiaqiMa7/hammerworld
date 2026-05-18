"""Function ranking for TRIZ: prioritize functions by value and harm."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.triz.prompts import FUNCTION_RANKING_PROMPT


@dataclass
class FunctionRankItem:
    """A single function with its scores."""
    name: str
    usefulness: float  # 0-10
    cost: float       # 0-10
    harm: float       # 0-10 (higher = more harmful)
    replaceability: float = 5.0  # 0-10 (higher = easier to replace)
    score: float = 0.0  # computed: usefulness - cost/2 - harm

    def __post_init__(self):
        self.score = self.usefulness - (self.cost / 2) - self.harm


@dataclass
class FunctionRankingResult:
    """Ranked list of functions with trimming recommendations."""
    items: list[FunctionRankItem] = field(default_factory=list)
    trimming_recommendations: list[str] = field(default_factory=list)


_USEFUL_KEYWORDS = ["provide", "deliver", "create", "generate", "support",
                    "enable", "improve", "enhance", "increase", "produce"]
_COST_KEYWORDS = ["expensive", "cost", "consume", "energy", "power", "resource",
                  "fuel", "material", "maintenance", "labor"]
_HARM_KEYWORDS = ["pollute", "waste", "damage", "harm", "dangerous", "unsafe",
                  "toxic", "noise", "vibration", "heat loss", "friction"]


def analyze(description: str, ai_provider=None) -> FunctionRankingResult:
    """Rank functions identified in the description."""
    import re
    result = FunctionRankingResult()

    # Extract verb-noun pairs as candidate functions
    verb_patterns = re.findall(r"(\w+)\s+(?:the|a|an)?\s*(\w+)", description.lower())
    seen = set()
    for verb, noun in verb_patterns:
        if len(verb) > 3 and len(noun) > 3 and verb not in ("this", "that", "with"):
            func_name = f"{verb}_{noun}"
            if func_name not in seen:
                seen.add(func_name)
                usefulness = _score_byword(description, _USEFUL_KEYWORDS, 8)
                cost = _score_byword(description, _COST_KEYWORDS, 7)
                harm = _score_byword(description, _HARM_KEYWORDS, 6)
                result.items.append(FunctionRankItem(
                    name=func_name, usefulness=round(usefulness, 1),
                    cost=round(cost, 1), harm=round(harm, 1),
                ))

    if not result.items:
        result.items = [
            FunctionRankItem(name="primary_function", usefulness=5, cost=5, harm=3),
            FunctionRankItem(name="secondary_function", usefulness=3, cost=3, harm=2),
        ]

    for item in sorted(result.items, key=lambda x: x.score):
        if item.score < 0:
            result.trimming_recommendations.append(
                f"Consider trimming '{item.name}' (score={item.score:.1f})"
            )
        elif item.harm > 5:
            result.trimming_recommendations.append(
                f"Reduce harmful effect of '{item.name}' (harm={item.harm:.1f})"
            )

    return result


def _score_byword(desc: str, keywords: list[str], max_score: float) -> float:
    """Score based on keyword density."""
    desc_lower = desc.lower()
    count = sum(1 for kw in keywords if kw in desc_lower)
    if count == 0:
        return 1.0
    return min(max_score, 1.0 + (count * (max_score - 1.0) / max(count, 3)))
