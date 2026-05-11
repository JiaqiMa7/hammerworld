"""Multi-dimensional AI evaluation pipeline for idea mining."""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field

from src.engine.models import (
    Combination, AIAnalysis, EvalScore, EvalDimension,
    Submission, Method, Problem,
)
from src.triz.prompts import EVALUATION_PROMPT_TEMPLATE, SYSTEM_PROMPT
from src.triz.agent import AIProvider


DEFAULT_THRESHOLD = 8.0

DIMENSION_NAMES = {
    EvalDimension.ELEGANCE: "Elegance",
    EvalDimension.WEIRDNESS: "Weirdness",
    EvalDimension.HUMAN_FEASIBILITY: "Human Feasibility",
    EvalDimension.AI_FEASIBILITY: "AI Feasibility",
    EvalDimension.NOVELTY: "Novelty",
    EvalDimension.ANALOGY_DISTANCE: "Analogy Distance",
    EvalDimension.SCALING_POTENTIAL: "Scaling Potential",
    EvalDimension.SIDE_EFFECTS: "Side Effects",
}


@dataclass
class EvaluationResult:
    """Result of evaluating one combination."""
    combination: Combination
    analysis: AIAnalysis
    passed_threshold: bool
    high_dimensions: list[EvalDimension]


class EvaluationPipeline:
    """Pipeline that runs AI evaluation on method-problem combinations."""

    def __init__(
        self,
        ai_provider: AIProvider,
        threshold: float = DEFAULT_THRESHOLD,
        model_name: str = "unknown",
        model_version: str = "unknown",
    ):
        self.ai_provider = ai_provider
        self.threshold = threshold
        self.model_name = model_name
        self.model_version = model_version

    def evaluate(self, combination: Combination) -> EvaluationResult:
        """Run AI evaluation on a single combination."""
        prompt = self._build_prompt(combination.method, combination.problem)

        response_text = self.ai_provider.generate(SYSTEM_PROMPT, prompt)
        analysis = self._parse_response(response_text, combination)

        combination.analyses.append(analysis)

        return EvaluationResult(
            combination=combination,
            analysis=analysis,
            passed_threshold=analysis.is_high_score(self.threshold),
            high_dimensions=analysis.high_dimensions(self.threshold),
        )

    def evaluate_batch(
        self, combinations: list[Combination]
    ) -> list[EvaluationResult]:
        """Evaluate multiple combinations."""
        results = []
        for combo in combinations:
            result = self.evaluate(combo)
            results.append(result)
        return results

    def evaluate_and_filter(
        self, combinations: list[Combination]
    ) -> tuple[list[EvaluationResult], list[EvaluationResult]]:
        """Evaluate and split into passed/failed based on asymmetric threshold."""
        results = self.evaluate_batch(combinations)
        passed = [r for r in results if r.passed_threshold]
        failed = [r for r in results if not r.passed_threshold]
        return passed, failed

    def create_submission(
        self, result: EvaluationResult, submitter: str
    ) -> Submission:
        """Create a buffer-zone submission from an evaluation result."""
        sub = Submission(
            method_id=result.combination.method.id,
            problem_id=result.combination.problem.id,
            submitter=submitter,
        )
        sub.combination = result.combination
        sub.analysis = result.analysis
        return sub

    def _build_prompt(self, method: Method, problem: Problem) -> str:
        """Build the evaluation prompt for a method-problem pair."""
        triz_context = ""
        if problem.triz_standardized:
            ctx = problem.triz_standardized
            triz_context = (
                f"TRIZ Contradiction: {ctx.get('contradiction', {})}\n"
                f"Ideal Final Result: {ctx.get('ifr', '')}\n"
            )

        return EVALUATION_PROMPT_TEMPLATE.format(
            method_name=method.name,
            method_domain=method.domain,
            method_level=method.level.value,
            method_description=method.description,
            method_examples=", ".join(method.examples[:3]),
            problem_title=problem.title,
            problem_domain=problem.domain.value,
            problem_description=problem.description,
            triz_context=triz_context,
        )

    def _parse_response(
        self, response_text: str, combination: Combination
    ) -> AIAnalysis:
        """Parse AI response with fallback to simulated evaluation."""
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                json_match = re.search(r'\{[\s\S]*"scores"[\s\S]*\}', response_text)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    raise ValueError("No JSON found in response")

            scores = []
            for s in data.get("scores", []):
                dim_name = s.get("dimension", "").lower().replace(" ", "_")
                try:
                    dim = EvalDimension(dim_name)
                except ValueError:
                    continue
                score = float(s.get("score", 5.0))
                score = max(1.0, min(10.0, score))
                scores.append(EvalScore(
                    dimension=dim,
                    score=score,
                    explanation=s.get("explanation", ""),
                ))

            analysis_text = data.get("analysis_text", response_text[:500])

        except (json.JSONDecodeError, ValueError, KeyError):
            # Fallback: generate basic scores from the raw text
            scores = self._fallback_scores(response_text)
            analysis_text = response_text[:500]

        inference_hash = hashlib.sha256(
            f"{combination.id}:{json.dumps([(s.dimension.value, s.score) for s in scores])}".encode()
        ).hexdigest()[:16]

        return AIAnalysis(
            scores=scores,
            analysis_text=analysis_text,
            model_name=self.model_name,
            model_version=self.model_version,
            inference_hash=inference_hash,
        )

    def _fallback_scores(self, text: str) -> list[EvalScore]:
        """Generate basic scores from text analysis when JSON parsing fails."""
        text_lower = text.lower()
        scores: list[EvalScore] = []

        # Simple keyword-based scoring as fallback
        novelty_keywords = ["novel", "new", "unique", "unprecedented", "original"]
        weirdness_keywords = ["strange", "weird", "unusual", "surprising", "unexpected"]
        feasibility_keywords = ["practical", "feasible", "implementable", "realistic"]

        novelty = min(10, sum(1 for k in novelty_keywords if k in text_lower) * 2 + 3)
        weirdness = min(10, sum(1 for k in weirdness_keywords if k in text_lower) * 2 + 3)
        feasibility = min(10, sum(1 for k in feasibility_keywords if k in text_lower) * 2 + 3)

        scores = [
            EvalScore(EvalDimension.NOVELTY, novelty, "Keyword-based fallback"),
            EvalScore(EvalDimension.WEIRDNESS, weirdness, "Keyword-based fallback"),
            EvalScore(EvalDimension.HUMAN_FEASIBILITY, feasibility, "Keyword-based fallback"),
            EvalScore(EvalDimension.ELEGANCE, 5.0, "Keyword-based fallback (default)"),
            EvalScore(EvalDimension.AI_FEASIBILITY, 5.0, "Keyword-based fallback (default)"),
            EvalScore(EvalDimension.ANALOGY_DISTANCE, 5.0, "Keyword-based fallback (default)"),
            EvalScore(EvalDimension.SCALING_POTENTIAL, 5.0, "Keyword-based fallback (default)"),
            EvalScore(EvalDimension.SIDE_EFFECTS, 5.0, "Keyword-based fallback (default)"),
        ]
        return scores
