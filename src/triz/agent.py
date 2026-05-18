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
from src.triz.prompts import (
    PROBLEM_STANDARDIZATION_TEMPLATE, SYSTEM_PROMPT,
    SU_FIELD_PROMPT, RESOURCE_ANALYSIS_PROMPT, CAUSE_EFFECT_PROMPT,
    NINE_WINDOWS_PROMPT, TRIMMING_PROMPT, FUNCTION_RANKING_PROMPT,
    STC_OPERATOR_PROMPT, SMART_LITTLE_PEOPLE_PROMPT,
)
from src.triz import su_field, resource_analysis, cause_effect
from src.triz import nine_windows, trimming, function_ranking
from src.triz import stc_operator, smart_little_people
from src.triz.ariz import run_full, run_simplified
from src.triz.standard_solutions import STANDARD_SOLUTIONS, StandardSolution


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

        In AI mode, also runs Su-Field, cause-effect, and resource analysis
        to enrich triz_standardized with deeper TRIZ context.
        """
        analysis = self._ai_analyze_from_text(problem_description, domain) if self.ai_provider \
                   else self._rule_based_from_text(problem_description, domain)

        triz_std = {
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
        }

        # AI mode: enrich with Su-Field, cause-effect, resource analysis
        if self.ai_provider:
            sf = self.su_field_analysis(problem_description)
            triz_std["su_field"] = {
                "s1": sf.substance1, "s2": sf.substance2, "field": sf.field,
                "interaction_type": sf.interaction_type,
                "is_complete": sf.is_complete,
                "transformation_suggestions": sf.transformation_suggestions,
            }
            ce = self.cause_effect_analysis(problem_description)
            triz_std["cause_effect"] = {
                "root_causes": [str(l.cause) for l in ce.chain],
                "final_effects": [str(l.effect) for l in ce.chain],
            }
            res = self.resource_analysis(problem_description)
            triz_std["resources"] = {
                "substances": list(res.substances),
                "fields": list(res.fields),
                "space": list(res.space),
                "time": list(res.time),
                "information": list(res.information),
                "function": list(res.function),
            }

        return Problem(
            id="",
            title=problem_description[:80],
            domain=self._guess_domain(domain),
            description=problem_description,
            constraint_types=self._infer_constraints(analysis),
            maturity=ProblemMaturity.NO_SOLUTION,
            triz_standardized=triz_std,
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

    # -- New TRIZ tool methods (delegate to specialized modules) --

    def su_field_analysis(self, description: str) -> su_field.SuFieldModel:
        """Model the problem as a Substance-Field system."""
        return su_field.analyze(description, self.ai_provider)

    def cause_effect_analysis(self, description: str) -> cause_effect.CauseEffectChain:
        """Trace cause-effect relationships to find root causes."""
        return cause_effect.analyze(description, self.ai_provider)

    def resource_analysis(self, description: str) -> resource_analysis.ResourcePool:
        """Identify available resources (substance, field, space, time, etc.)."""
        return resource_analysis.analyze(description, self.ai_provider)

    def nine_windows(self, description: str) -> nine_windows.NineWindowPanel:
        """Apply 9-Windows system operator thinking."""
        return nine_windows.analyze(description, self.ai_provider)

    def trimming_analysis(self, description: str) -> trimming.TrimmingResult:
        """Identify components that can be eliminated while preserving function."""
        return trimming.analyze(description, self.ai_provider)

    def function_ranking(self, description: str) -> function_ranking.FunctionRankingResult:
        """Rank functions by usefulness, cost, and harm."""
        return function_ranking.analyze(description, self.ai_provider)

    def stc_operator(self, description: str) -> stc_operator.STCResult:
        """Apply Size-Time-Cost extreme thinking."""
        return stc_operator.analyze(description, self.ai_provider)

    def smart_little_people(self, description: str) -> smart_little_people.SLPResult:
        """Model the problem using Smart Little People."""
        return smart_little_people.analyze(description, self.ai_provider)

    def ariz_analyze(self, description: str, simplified: bool = False) -> dict:
        """Run ARIZ-85C (full or simplified) and return structured results."""
        from dataclasses import asdict
        runner = run_simplified if simplified else run_full
        result = runner(description, self.ai_provider)
        return asdict(result)

    def query_standard_solutions(
        self, class_id: int | None = None
    ) -> list[StandardSolution]:
        """Query standard solutions by class (1-5). Returns all 76 if class_id is None."""
        if class_id is None:
            return list(STANDARD_SOLUTIONS.values())
        return [s for s in STANDARD_SOLUTIONS.values() if s.class_name == str(class_id)]

    def match_standard_solutions(
        self, description: str,
        su_field_result: su_field.SuFieldModel | None = None,
    ) -> dict:
        """Auto-match standard solutions based on Su-Field result or description keywords.

        Returns {"matched": list[dict], "recommended_class": int} where each
        matched solution is serialized via asdict() for JSON compatibility.
        """
        matched: list[StandardSolution] = []
        recommended_class = 1

        # Su-Field driven matching (highest priority)
        if su_field_result and su_field_result.interaction_type:
            it = su_field_result.interaction_type
            if it == "harmful":
                matched = [STANDARD_SOLUTIONS[i] for i in (2, 3) if i in STANDARD_SOLUTIONS]
                recommended_class = 1
            elif it == "insufficient":
                matched = [STANDARD_SOLUTIONS[i] for i in (4, 5) if i in STANDARD_SOLUTIONS]
                recommended_class = 1
            elif it == "excessive":
                m = STANDARD_SOLUTIONS.get(6)
                matched = [m] if m else []
                recommended_class = 1

        # Keyword-based fallback
        if not matched:
            dl = description.lower()
            if any(w in dl for w in ("measure", "detect", "sensor", "monitor", "inspect")):
                recommended_class = 4
            elif any(w in dl for w in ("complex", "many part", "simplif", "reduce")):
                recommended_class = 5
            elif any(w in dl for w in ("evolve", "upgrade", "enhance")):
                recommended_class = 2
            elif any(w in dl for w in ("supersystem", "integrate", "combine")):
                recommended_class = 3
            class_sols = [s for s in STANDARD_SOLUTIONS.values()
                          if s.class_name == str(recommended_class)]
            matched = class_sols[:3]

        from dataclasses import asdict
        return {
            "matched": [asdict(s) for s in matched if s],
            "recommended_class": recommended_class,
        }

    def full_analysis(self, description: str, domain: str = "") -> dict:
        """Run all TRIZ tools and return an integrated analysis report."""
        from dataclasses import asdict
        problem = self.standardize(description, domain)
        report = {"standardized_problem": problem.triz_standardized or {}}

        sf = su_field.analyze(description, self.ai_provider)
        report["su_field"] = sf
        report["cause_effect"] = cause_effect.analyze(description, self.ai_provider)
        report["resources"] = resource_analysis.analyze(description, self.ai_provider)
        report["nine_windows"] = nine_windows.analyze(description, self.ai_provider)
        report["trimming"] = trimming.analyze(description, self.ai_provider)
        report["function_ranking"] = function_ranking.analyze(description, self.ai_provider)
        report["stc"] = stc_operator.analyze(description, self.ai_provider)
        report["slp"] = smart_little_people.analyze(description, self.ai_provider)
        report["standard_solutions"] = self.match_standard_solutions(description, sf)
        report["ariz"] = asdict(run_simplified(description, self.ai_provider))

        # Cross-tool integration insights
        insights = []
        if hasattr(sf, 'interaction_type') and sf.interaction_type in ("harmful", "excessive"):
            insights.append(
                f"Su-Field {sf.interaction_type} interaction detected: "
                "consider Class 1 standard solutions to eliminate/modulate the field"
            )
        if report.get("standard_solutions", {}).get("recommended_class"):
            insights.append(
                f"Recommended standard solutions Class "
                f'{report["standard_solutions"]["recommended_class"]}'
            )
        report["_meta"] = {"tool_count": 11, "integration_insights": insights}
        return report
