"""Prompt templates for the TRIZ Agent and all sub-tools."""
from __future__ import annotations

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

SU_FIELD_PROMPT = """Model the following problem as a Substance-Field (Su-Field) system:

{description}

Identify:
1. Substance S1 (the object being acted upon)
2. Substance S2 (the tool/object doing the acting)
3. Field F (the energy/interaction between S1 and S2)
4. Is the Su-Field complete?
5. What type of interaction exists (useful, harmful, insufficient, excessive)?
6. Suggest transformations to build a complete and effective Su-Field.
"""

RESOURCE_ANALYSIS_PROMPT = """Analyze the following problem and identify ALL available resources:

{description}

Categorize resources by type:
1. Substance resources (materials, compounds, environmental substances)
2. Field resources (energy types: mechanical, thermal, chemical, electric, magnetic, etc.)
3. Space resources (empty spaces, cavities, surfaces, gradients)
4. Time resources (pauses, waiting periods, cycles, pre/post-processing)
5. Information resources (signals, data, status indicators, feedback)
6. Function resources (existing useful flows, transport, storage)

Include both system resources and environmental/supersystem resources.
"""

CAUSE_EFFECT_PROMPT = """Identify cause-effect relationships in the following problem:

{description}

Map out:
1. The causal chain from root cause to final symptom
2. Root causes (originating factors)
3. Intermediate effects
4. Final effects (the observable problems)
5. Feedback loops if any

Present as a clear chain: Cause → Effect → Effect → ...
"""

NINE_WINDOWS_PROMPT = """Apply the 9-Windows (System Operator) to the following problem:

{description}

Fill out a 3x3 matrix:
- Rows: Supersystem / System / Subsystem
- Columns: Past / Present / Future

For each cell, describe:
- What exists in that level and time frame
- How it relates to the current problem
- What resources or constraints are available
"""

TRIMMING_PROMPT = """Apply TRIZ Trimming analysis to the following system:

{description}

For each component identified:
1. What function does it perform?
2. Can the function be performed by another existing component?
3. Can the function be performed by the supersystem?
4. Can the function be performed by the object itself (self-service)?
5. Recommend trimming strategy.
"""

FUNCTION_RANKING_PROMPT = """Rank the functions in the following system:

{description}

For each function, evaluate:
1. Usefulness (0-10): How valuable is this function?
2. Cost (0-10): How much resource does it consume?
3. Harm (0-10): What negative side effects does it produce?
4. Replaceability (0-10): How easily can it be replaced?

Identify which functions should be trimmed, modified, or preserved.
"""

STC_OPERATOR_PROMPT = """Apply the STC (Size-Time-Cost) Operator to this problem:

{description}

Consider each extreme:
1. SIZE+: What if the system were infinitely large?
2. SIZE-: What if it were infinitesimally small?
3. TIME+: What if the process took infinitely long?
4. TIME-: What if it happened instantly?
5. COST+: What if cost were infinite (unlimited resources)?
6. COST-: What if the solution must cost nothing?

For each extreme, describe what new insights emerge.
"""

SMART_LITTLE_PEOPLE_PROMPT = """Model the following problem using Smart Little People (SLP):

{description}

1. Identify the roles/actors in the problem
2. Imagine each role as a group of "little people" with specific behaviors
3. Describe the conflicts between groups of little people
4. Imagine the ideal configuration where all little people cooperate
5. What does this ideal configuration tell you about the real solution?
"""
