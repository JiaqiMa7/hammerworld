"""TRIZ Agent for problem standardization and contradiction analysis."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from src.engine.models import Problem, Domain, ProblemMaturity, ConstraintType
from src.triz.models import (
    TRIZAnalysis, FunctionalModel, TechnicalContradiction,
    PhysicalContradiction, EngineeringParameter,
)
from src.triz.knowledge import ENGINEERING_PARAMETERS, INVENTIVE_PRINCIPLES
from src.triz.contradiction_matrix import query_matrix
from src.triz.prompts import PROBLEM_STANDARDIZATION_TEMPLATE, SYSTEM_PROMPT


class AIProvider(Protocol):
    """Protocol for AI model providers. Users plug in their own API key."""
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...


@dataclass
class TRIZAgent:
    """Agent that standardizes problems using TRIZ methodology.

    The agent can work with or without an AI provider:
    - With AI: Uses LLM to deeply analyze problems
    - Without AI: Uses rule-based contradiction matrix matching
    """

    ai_provider: Optional[AIProvider] = None
    history: list[TRIZAnalysis] = field(default_factory=list)

    def analyze(self, problem: Problem) -> TRIZAnalysis:
        """Perform a full TRIZ analysis of a problem.

        If the problem already has triz_standardized data, use that as a base.
        Otherwise, analyze from scratch.
        """
        if problem.triz_standardized:
            return self._from_standardized(problem)

        if self.ai_provider:
            return self._ai_analyze(problem)
        else:
            return self._rule_based_analyze(problem)

    def standardize(self, problem_description: str, domain: str = "") -> Problem:
        """Standardize a raw problem description into a Problem with TRIZ analysis.

        This is the main entry point for adding new problems to the matrix.
        """
        analysis = self._ai_analyze_from_text(problem_description, domain) if self.ai_provider \
                   else self._rule_based_from_text(problem_description, domain)

        return Problem(
            id="",  # Will be assigned by the loader
            title=problem_description[:80],
            domain=self._guess_domain(domain),
            description=problem_description,
            constraint_types=self._infer_constraints(analysis),
            maturity=ProblemMaturity.NO_SOLUTION,
            triz_standardized={
                "contradiction": {
                    "improving": analysis.technical_contradictions[0].improving_param.name
                        if analysis.technical_contradictions else "",
                    "worsening": analysis.technical_contradictions[0].worsening_param.name
                        if analysis.technical_contradictions else "",
                },
                "ifr": analysis.ifr,
                "triz_params": analysis.recommended_principles,
                "functional_model": {
                    "actors": analysis.functional_model.actors,
                    "useful_functions": analysis.functional_model.useful_functions,
                    "harmful_functions": analysis.functional_model.harmful_functions,
                },
            },
        )

    def get_principle_recommendations(self, improving_id: int, worsening_id: int) -> dict:
        """Query the contradiction matrix and return principle details."""
        principle_ids = query_matrix(improving_id, worsening_id)
        return {
            "principle_ids": principle_ids,
            "principles": [
                {
                    "id": pid,
                    "name": INVENTIVE_PRINCIPLES[pid].name,
                    "description": INVENTIVE_PRINCIPLES[pid].description,
                    "examples": INVENTIVE_PRINCIPLES[pid].examples[:3],
                }
                for pid in principle_ids
            ],
        }

    def _from_standardized(self, problem: Problem) -> TRIZAnalysis:
        """Build TRIZAnalysis from pre-standardized problem data."""
        ctx = problem.triz_standardized or {}
        fm_data = ctx.get("functional_model", {})

        return TRIZAnalysis(
            original_problem=problem.description,
            functional_model=FunctionalModel(
                actors=fm_data.get("actors", []),
                useful_functions=fm_data.get("useful_functions", []),
                harmful_functions=fm_data.get("harmful_functions", []),
            ),
            ifr=ctx.get("ifr", ""),
            recommended_principles=ctx.get("triz_params", []),
        )

    def _ai_analyze(self, problem: Problem) -> TRIZAnalysis:
        return self._ai_analyze_from_text(problem.description, problem.domain.value)

    def _ai_analyze_from_text(self, description: str, domain: str) -> TRIZAnalysis:
        if not self.ai_provider:
            raise RuntimeError("No AI provider configured")

        prompt = PROBLEM_STANDARDIZATION_TEMPLATE.format(
            problem_description=description,
            domain=domain or "unspecified",
        )
        response = self.ai_provider.generate(SYSTEM_PROMPT, prompt)
        return self._parse_ai_response(response, description)

    def _parse_ai_response(self, response: str, original: str) -> TRIZAnalysis:
        """Extract JSON from AI response and build TRIZAnalysis."""
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = {}

        fm = data.get("functional_decomposition", {})
        tcs = data.get("technical_contradictions", [])
        pcs = data.get("physical_contradictions", [])

        return TRIZAnalysis(
            original_problem=original,
            functional_model=FunctionalModel(
                actors=fm.get("actors", []),
                useful_functions=fm.get("useful_functions", []),
                harmful_functions=fm.get("harmful_functions", []),
                trimming_candidates=fm.get("trimming_candidates", []),
            ),
            technical_contradictions=[
                TechnicalContradiction(
                    improving_param=EngineeringParameter(
                        id=tc.get("improving_id", 0),
                        name=tc.get("improving_parameter", ""),
                        description="",
                    ),
                    worsening_param=EngineeringParameter(
                        id=tc.get("worsening_id", 0),
                        name=tc.get("worsening_parameter", ""),
                        description="",
                    ),
                )
                for tc in tcs
            ],
            physical_contradictions=[
                PhysicalContradiction(
                    parameter=pc.get("parameter", ""),
                    requirement_a=pc.get("requirement_a", ""),
                    requirement_b=pc.get("requirement_b", ""),
                    separation_strategy=pc.get("separation_strategy", ""),
                )
                for pc in pcs
            ],
            recommended_principles=data.get("recommended_principles", []),
            ifr=data.get("ifr", ""),
        )

    def _rule_based_analyze(self, problem: Problem) -> TRIZAnalysis:
        return self._rule_based_from_text(problem.description, problem.domain.value)

    def _rule_based_from_text(self, description: str, domain: str) -> TRIZAnalysis:
        """Fallback: basic rule-based TRIZ analysis using keyword matching."""
        # Simple keyword-to-parameter mapping for common problem types
        keyword_map = {
            "speed": (9, [2, 28, 13, 38]),
            "fast": (9, [2, 28, 13, 38]),
            "slow": (9, [2, 28, 13, 38]),
            "weight": (1, [15, 8, 29, 34]),
            "heavy": (1, [15, 8, 29, 34]),
            "light": (1, [2, 28, 13, 38]),
            "strength": (14, [28, 27, 18, 40]),
            "strong": (14, [28, 27, 18, 40]),
            "weak": (14, [28, 27, 18, 40]),
            "reliable": (27, [11, 35, 27, 28]),
            "failure": (27, [11, 35, 27, 28]),
            "accurate": (28, [28, 32, 1, 24]),
            "precision": (28, [28, 32, 1, 24]),
            "cost": (32, [28, 29, 26, 27]),
            "expensive": (32, [28, 29, 26, 27]),
            "complex": (36, [26, 30, 36, 34]),
            "temperature": (17, [35, 21, 28, 10]),
            "energy": (19, [35, 12, 34, 31]),
            "power": (21, [12, 36, 18, 31]),
            "waste": (22, [6, 2, 34, 19]),
            "loss": (22, [6, 2, 34, 19]),
            "harmful": (31, [22, 35, 31, 8]),
            "dangerous": (31, [22, 35, 31, 8]),
            "adapt": (35, [1, 6, 15, 8]),
            "flexible": (35, [1, 6, 15, 8]),
        }

        description_lower = description.lower()
        found_keywords: list[tuple[str, int, list[int]]] = []
        for keyword, (param_id, principles) in keyword_map.items():
            if keyword in description_lower:
                found_keywords.append((keyword, param_id, principles))

        contradictions: list[TechnicalContradiction] = []
        all_principles: list[int] = []

        for i in range(0, len(found_keywords) - 1, 2):
            kw1, pid1, pr1 = found_keywords[i]
            kw2, pid2, pr2 = found_keywords[i + 1]
            if pid1 and pid2:
                params = ENGINEERING_PARAMETERS
                contradictions.append(TechnicalContradiction(
                    improving_param=params[pid1],
                    worsening_param=params[pid2],
                ))
                matrix_principles = query_matrix(pid1, pid2)
                all_principles.extend(matrix_principles if matrix_principles else pr1)

        if not contradictions and found_keywords:
            kw, pid, principles = found_keywords[0]
            params = ENGINEERING_PARAMETERS
            contradictions.append(TechnicalContradiction(
                improving_param=params.get(pid, params[1]),
                worsening_param=params.get(32, params[32]),
            ))
            all_principles = principles

        # Deduplicate while preserving order
        seen = set()
        all_principles = [p for p in all_principles if not (p in seen or seen.add(p))]

        return TRIZAnalysis(
            original_problem=description,
            functional_model=FunctionalModel(
                actors=[],
                useful_functions=[],
                harmful_functions=[],
            ),
            technical_contradictions=contradictions,
            recommended_principles=all_principles[:5],
            ifr=f"Problem '{description[:60]}...' is solved automatically with no harmful effects",
        )

    @staticmethod
    def _guess_domain(domain: str) -> Domain:
        try:
            return Domain(domain.lower())
        except ValueError:
            return Domain.MEDICINE

    @staticmethod
    def _infer_constraints(analysis: TRIZAnalysis) -> list[ConstraintType]:
        constraints: list[ConstraintType] = []
        if analysis.physical_contradictions:
            constraints.append(ConstraintType.PHYSICAL_LIMIT)
        if len(analysis.technical_contradictions) > 1:
            constraints.append(ConstraintType.COMPLEXITY)
        return constraints
