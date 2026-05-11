"""Load and query method/problem matrices from JSON data files."""

from __future__ import annotations

import json
import os
from typing import Optional

from src.engine.models import Method, Problem, MethodLevel, ProblemMaturity, ConstraintType, Domain

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def load_methods(filepath: Optional[str] = None) -> list[Method]:
    """Load methods from JSON file."""
    path = filepath or os.path.join(_DATA_DIR, "methods.json")
    with open(path) as f:
        data = json.load(f)
    return [
        Method(
            id=m["id"],
            name=m["name"],
            domain=m["domain"],
            level=MethodLevel(m["level"]),
            description=m["description"],
            trigger_conditions=m.get("trigger_conditions", []),
            examples=m.get("examples", []),
            prerequisites=m.get("prerequisites", []),
            compatible_with=m.get("compatible_with", []),
        )
        for m in data["methods"]
    ]


def load_problems(filepath: Optional[str] = None) -> list[Problem]:
    """Load problems from JSON file."""
    path = filepath or os.path.join(_DATA_DIR, "problems.json")
    with open(path) as f:
        data = json.load(f)
    return [
        Problem(
            id=p["id"],
            title=p["title"],
            domain=Domain(p["domain"]),
            description=p["description"],
            constraint_types=[ConstraintType(c) for c in p.get("constraint_types", [])],
            maturity=ProblemMaturity(p.get("maturity", 1)),
            triz_standardized=p.get("triz_standardized"),
        )
        for p in data["problems"]
    ]


def filter_methods(methods: list[Method], *,
                   level: Optional[MethodLevel] = None,
                   domain: Optional[str] = None) -> list[Method]:
    """Filter methods by level and/or domain."""
    result = methods
    if level is not None:
        result = [m for m in result if m.level == level]
    if domain is not None:
        result = [m for m in result if m.domain.lower() == domain.lower()]
    return result


def filter_problems(problems: list[Problem], *,
                    domain: Optional[Domain] = None,
                    maturity: Optional[ProblemMaturity] = None) -> list[Problem]:
    """Filter problems by domain and/or maturity."""
    result = problems
    if domain is not None:
        result = [p for p in result if p.domain == domain]
    if maturity is not None:
        result = [p for p in result if p.maturity == maturity]
    return result
