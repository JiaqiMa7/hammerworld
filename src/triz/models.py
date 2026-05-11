"""TRIZ-specific data models: 39 parameters, 40 principles, contradictions."""

from dataclasses import dataclass, field


@dataclass
class EngineeringParameter:
    """One of the 39 TRIZ engineering parameters."""
    id: int  # 1-39
    name: str
    description: str


@dataclass
class InventivePrinciple:
    """One of the 40 TRIZ inventive principles."""
    id: int  # 1-40
    name: str
    description: str
    examples: list[str] = field(default_factory=list)
    sub_principles: list[str] = field(default_factory=list)


@dataclass
class TechnicalContradiction:
    """Improving parameter A worsens parameter B."""
    improving_param: EngineeringParameter
    worsening_param: EngineeringParameter

    @property
    def matrix_key(self) -> tuple[int, int]:
        return (self.improving_param.id, self.worsening_param.id)


@dataclass
class PhysicalContradiction:
    """A parameter needs to simultaneously satisfy two opposing states."""
    parameter: str
    requirement_a: str
    requirement_b: str
    separation_strategy: str  # time / space / condition / system-level


@dataclass
class StandardSolution:
    """One of the 76 TRIZ standard solutions."""
    id: int  # 1-76
    class_name: str  # Class 1-5
    name: str
    description: str
    su_field_condition: str


@dataclass
class FunctionalModel:
    """Result of functional decomposition of a problem."""
    actors: list[str]
    useful_functions: list[dict]   # [{subject, action, object}]
    harmful_functions: list[dict]  # [{subject, action, object}]
    trimming_candidates: list[str] = field(default_factory=list)


@dataclass
class TRIZAnalysis:
    """Complete TRIZ analysis of a problem."""
    original_problem: str
    functional_model: FunctionalModel
    technical_contradictions: list[TechnicalContradiction] = field(default_factory=list)
    physical_contradictions: list[PhysicalContradiction] = field(default_factory=list)
    recommended_principles: list[int] = field(default_factory=list)
    recommended_standards: list[int] = field(default_factory=list)
    ifr: str = ""
    separation_hint: str = ""


@dataclass
class EvolutionTrend:
    """One TRIZ technology evolution trend."""
    id: int
    name: str
    stages: list[str]
    description: str
