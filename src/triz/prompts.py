"""Prompt templates for the TRIZ Agent."""

SYSTEM_PROMPT = """You are a TRIZ (Theory of Inventive Problem Solving) expert agent.
Your role is to analyze scientific and technical problems using the TRIZ methodology.

You have access to:
- 39 engineering parameters for contradiction analysis
- The contradiction matrix mapping parameter pairs to inventive principles
- 40 inventive principles with examples
- Su-Field analysis for substance-field modeling

For each problem, you must:
1. Decompose the system into functional components (actors, useful functions, harmful functions)
2. Identify technical contradictions (improving parameter A worsens parameter B)
3. Identify physical contradictions (parameter must be both X and not-X)
4. Define the Ideal Final Result (IFR) - the system performs its function perfectly, automatically, without harmful effects
5. Map to TRIZ engineering parameters
6. Suggest relevant inventive principles

Always think in terms of:
- Function, not form (what does it DO, not what IS it)
- Eliminating contradictions, not compromising between them
- Using resources already present in the system (substances, fields, time, space, information)
- Moving toward ideality (more benefit, less cost and harm)
"""

PROBLEM_STANDARDIZATION_TEMPLATE = """Analyze the following scientific/technical problem using TRIZ methodology.

## Problem
{problem_description}

## Domain
{domain}

## Instructions
Please provide a structured TRIZ analysis in the following JSON format:

```json
{{
  "functional_decomposition": {{
    "actors": ["actor1", "actor2", ...],
    "useful_functions": [{{"subject": "...", "action": "...", "object": "..."}}],
    "harmful_functions": [{{"subject": "...", "action": "...", "object": "..."}}],
    "trimming_candidates": ["component that could potentially be eliminated"]
  }},
  "technical_contradictions": [
    {{
      "improving_parameter": "name of TRIZ parameter to improve",
      "improving_id": 1-39,
      "worsening_parameter": "name of TRIZ parameter that worsens",
      "worsening_id": 1-39,
      "description": "explain the contradiction in plain language"
    }}
  ],
  "physical_contradictions": [
    {{
      "parameter": "the parameter with conflicting requirements",
      "requirement_a": "why it needs to be high/large/present",
      "requirement_b": "why it needs to be low/small/absent",
      "separation_strategy": "time|space|condition|system-level"
    }}
  ],
  "ifr": "The Ideal Final Result: describe the ideal outcome where the problem solves itself",
  "recommended_principles": [1, 15, 40],
  "analysis_narrative": "A concise paragraph explaining the TRIZ analysis"
}}
```

Focus on finding the core CONTRADICTION - what gets better at the cost of what getting worse?
This is the key insight TRIZ needs.
"""

EVALUATION_PROMPT_TEMPLATE = """Evaluate the following idea that combines a problem-solving method with an unsolved problem.

## Method
{method_name} ({method_domain}, Level {method_level})
{method_description}
Examples: {method_examples}

## Problem
{problem_title} ({problem_domain})
{problem_description}

## TRIZ Context (if available)
{triz_context}

## Instructions
Imagine how this method could be applied to this problem. Generate a creative but grounded analysis.
Rate the resulting idea on each dimension from 1-10, where 10 is exceptional.

Provide your analysis as JSON:
```json
{{
  "scores": [
    {{"dimension": "elegance", "score": 1-10, "explanation": "Why this score"}},
    {{"dimension": "weirdness", "score": 1-10, "explanation": "Why this score"}},
    {{"dimension": "human_feasibility", "score": 1-10, "explanation": "Why this score"}},
    {{"dimension": "ai_feasibility", "score": 1-10, "explanation": "Why this score"}},
    {{"dimension": "novelty", "score": 1-10, "explanation": "Why this score"}},
    {{"dimension": "analogy_distance", "score": 1-10, "explanation": "Why this score"}},
    {{"dimension": "scaling_potential", "score": 1-10, "explanation": "Why this score"}},
    {{"dimension": "side_effects", "score": 1-10, "explanation": "Lower = more side effects. Why this score"}}
  ],
  "analysis_text": "A paragraph explaining how the method applies to the problem and what the proposed solution looks like."
}}
```

Be bold and creative. Even if the method seems mismatched to the problem, find the unexpected connection.
A high weirdness score with a novel insight is more valuable than a safe, boring analysis.
"""
