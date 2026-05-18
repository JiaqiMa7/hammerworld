"""STC (Size-Time-Cost) Operator for TRIZ extreme thinking."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.triz.prompts import STC_OPERATOR_PROMPT


@dataclass
class STCDimension:
    """A single STC dimension exploration."""
    dimension: str  # size / time / cost
    extreme: str    # plus / minus
    question: str
    insight: str = ""


@dataclass
class STCResult:
    """Results of applying the STC operator."""
    dimensions: list[STCDimension] = field(default_factory=list)
    key_insights: list[str] = field(default_factory=list)
    ai_insight: str = ""


_STC_QUESTIONS = [
    ("size", "plus", "What if the system were infinitely large?"),
    ("size", "minus", "What if the system were infinitesimally small?"),
    ("time", "plus", "What if the process took infinitely long?"),
    ("time", "minus", "What if the process happened instantaneously?"),
    ("cost", "plus", "What if the system cost infinite resources?"),
    ("cost", "minus", "What if the system cost zero resources?"),
]


def analyze(description: str, ai_provider=None) -> STCResult:
    """Apply the STC operator to generate extreme perspective insights."""
    result = STCResult()

    for dim, extreme, question in _STC_QUESTIONS:
        # Generate rule-based insight based on the question template
        insight = _generate_insight(description, dim, extreme)
        result.dimensions.append(STCDimension(
            dimension=dim, extreme=extreme,
            question=question, insight=insight,
        ))

    result.key_insights = [
        d.insight for d in result.dimensions if "eliminate" in d.insight.lower()
        or "reveal" in d.insight.lower() or "simplif" in d.insight.lower()
    ]

    if ai_provider:
        prompt = STC_OPERATOR_PROMPT.format(description=description)
        response = ai_provider.generate("You are a TRIZ STC operator expert.", prompt)
        result.ai_insight = response[:500]

    return result


def _generate_insight(desc: str, dim: str, extreme: str) -> str:
    """Generate a rule-based insight for an STC dimension."""
    if dim == "size":
        if extreme == "plus":
            return f"At infinite size, the system becomes massive—revealing scalability bottlenecks and resource constraints"
        return f"At microscopic size, non-obvious surface effects and quantum phenomena dominate"
    elif dim == "time":
        if extreme == "plus":
            return f"With infinite time, all wear and degradation effects become visible—revealing long-term failure modes"
        return f"At instantaneous speed, parallel processing and elimination of sequential steps become possible"
    else:  # cost
        if extreme == "plus":
            return f"With infinite cost, the ideal materials and precision become available—removing budget constraints"
        return f"At zero cost, the solution must use only free resources—revealing essential core functions"
