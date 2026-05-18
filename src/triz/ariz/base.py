"""ARIZ-85C state and result types."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ARIZPhase(Enum):
    ANALYSIS = 1
    MODEL = 2
    IFR = 3
    RESOURCES = 4
    STANDARDS = 5
    REFORMULATE = 6
    EVALUATE = 7
    APPLY = 8
    META = 9


@dataclass
class ARIZState:
    """Mutable state threaded through all ARIZ phases."""
    original_problem: str = ""
    mini_problem: str = ""
    conflicting_pair: str = ""
    operating_zone: str = ""
    operating_time: str = ""
    technical_contradiction: str = ""
    physical_contradiction: str = ""
    ifr_levels: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    standard_solutions_applied: list[int] = field(default_factory=list)
    solution_concept: str = ""
    evaluation_notes: list[str] = field(default_factory=list)
    meta_reflection: str = ""
    current_phase: ARIZPhase = ARIZPhase.ANALYSIS


@dataclass
class ARIZResult:
    """Final result of an ARIZ run."""
    original_problem: str
    mini_problem: str
    conflict_description: str
    ifr: str
    physical_contradiction: str
    resource_summary: str
    solution_concept: str
    steps_completed: int
    phases_completed: list[str]
    rule_based: bool = True
