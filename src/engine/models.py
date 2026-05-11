"""Core data models for the Idea Mining Network."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import uuid
import time


class MethodLevel(Enum):
    BASIC_HEURISTIC = 1
    STRUCTURED = 2
    DOMAIN_SPECIFIC = 3
    COMPOSITE = 4


class ProblemMaturity(Enum):
    NO_SOLUTION = 1
    PARTIAL_POOR = 2
    TOO_EXPENSIVE = 3
    BOTTLENECK_KNOWN = 4


class ConstraintType(Enum):
    PHYSICAL_LIMIT = "physical_limit"
    RESOURCE = "resource"
    TIME = "time"
    COMPLEXITY = "complexity"
    ETHICAL = "ethical"


class EvalDimension(Enum):
    ELEGANCE = "elegance"
    WEIRDNESS = "weirdness"
    HUMAN_FEASIBILITY = "human_feasibility"
    AI_FEASIBILITY = "ai_feasibility"
    NOVELTY = "novelty"
    ANALOGY_DISTANCE = "analogy_distance"
    SCALING_POTENTIAL = "scaling_potential"
    SIDE_EFFECTS = "side_effects"


class Domain(Enum):
    MEDICINE = "medicine"
    ENERGY = "energy"
    ENVIRONMENT = "environment"
    INFORMATION = "information"
    MATERIALS = "materials"
    SOCIETY = "society"


@dataclass
class Method:
    id: str
    name: str
    domain: str
    level: MethodLevel
    description: str
    trigger_conditions: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    compatible_with: list[str] = field(default_factory=list)

    @staticmethod
    def make_id(domain: str, index: int) -> str:
        return f"method_{domain}_{index:03d}"


@dataclass
class Problem:
    id: str
    title: str
    domain: Domain
    description: str
    constraint_types: list[ConstraintType] = field(default_factory=list)
    maturity: ProblemMaturity = ProblemMaturity.NO_SOLUTION
    triz_standardized: Optional[dict] = None

    @staticmethod
    def make_id(domain: str, index: int) -> str:
        return f"problem_{domain}_{index:03d}"


@dataclass
class EvalScore:
    dimension: EvalDimension
    score: float  # 1.0 - 10.0
    explanation: str


@dataclass
class AIAnalysis:
    scores: list[EvalScore]
    analysis_text: str
    model_name: str
    model_version: str
    inference_hash: str

    def is_high_score(self, threshold: float = 8.0) -> bool:
        return any(s.score >= threshold for s in self.scores)

    def high_dimensions(self, threshold: float = 8.0) -> list[EvalDimension]:
        return [s.dimension for s in self.scores if s.score >= threshold]


@dataclass
class Combination:
    id: str
    method: Method
    problem: Problem
    analyses: list[AIAnalysis] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @staticmethod
    def make_id(method_id: str, problem_id: str) -> str:
        return f"combo_{method_id}_{problem_id}"

    @property
    def best_score(self) -> Optional[float]:
        if not self.analyses:
            return None
        return max(max(s.score for s in a.scores) for a in self.analyses)

    @property
    def best_dimension(self) -> Optional[EvalDimension]:
        best = None
        best_score = -1
        for a in self.analyses:
            for s in a.scores:
                if s.score > best_score:
                    best_score = s.score
                    best = s.dimension
        return best


@dataclass
class Submission:
    """A submission to the blockchain buffer zone."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    combination: Combination = field(init=False)
    method_id: str = ""
    problem_id: str = ""
    analysis: AIAnalysis = field(init=False)
    submitter: str = ""
    status: str = "pending"  # pending -> classified -> published
    classifications: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
