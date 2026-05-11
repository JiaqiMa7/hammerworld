# Idea Mining Network (創意挖礦網絡)

A decentralized creative problem-solving network that combines TRIZ methodology, AI-powered cross-domain analysis, and blockchain economics to mine breakthrough ideas.

## Concept

**Methods Matrix × Problems Matrix → Random Combination → AI Multi-Dimension Evaluation → Leaderboards → Token Rewards**

Users ("miners") run a deterministic random combination engine that pairs problem-solving methods with unsolved scientific problems. Each combination is analyzed by AI across 8 dimensions. Any combination scoring high on ANY single dimension is uploaded to a federated hub network. Users earn tokens for mining, classifying, detecting poisoning, and uploading new methods/problems.

## Project Status

**Phase 1 (Single-machine Prototype)**: ~85% complete

| Module | Status | Description |
|--------|--------|-------------|
| Core Data Models | ✅ Done | Method, Problem, Combination, EvalScore, AIAnalysis, Submission |
| TRIZ Knowledge Base | ✅ Done | 39 parameters, 40 principles, contradiction matrix |
| Method Matrix | ✅ Done | 35 methods across 4 levels (heuristic → composite) |
| Problem Matrix | ✅ Done | 22 real unsolved problems across 6 domains |
| Combination Engine | ✅ Done | Fisher-Yates shuffle with deterministic anti-duplicate |
| TRIZ Agent | ✅ Done | Problem standardization, contradiction analysis |
| AI Evaluation Pipeline | ✅ Done | 8-dimension scoring with asymmetric threshold |
| Local Leaderboard | 🔜 In Progress | Ranking, filtering, search, random draw |
| CLI Interface | 🔜 Pending | Miner CLI, query CLI |
| Web UI | 🔜 Phase 2 | Browse, search, pay-to-view |

## Architecture

```
src/
├── engine/           # Core: models, combiner, loader
│   ├── models.py     #   Dataclasses for Method, Problem, Combination
│   ├── combiner.py   #   Deterministic Fisher-Yates shuffle + pairing
│   └── loader.py     #   JSON data loading with filtering
├── triz/             # TRIZ methodology
│   ├── models.py     #   EngineeringParameter, InventivePrinciple, etc.
│   ├── knowledge.py  #   39 parameters + 40 principles data
│   ├── contradiction_matrix.py  # 39×39 matrix with query API
│   ├── agent.py      #   Problem standardization agent
│   └── prompts.py    #   LLM prompt templates
├── evaluation/       # AI evaluation
│   └── scorer.py     #   8-dimension scoring pipeline
├── hub/              # Leaderboard (in progress)
├── cli/              # CLI tools (pending)
data/
├── methods.json      # 35 cross-domain methods
└── problems.json     # 22 unsolved problems
tests/
```

## Quick Start

```bash
# No dependencies required for data loading and rule-based analysis
python3 -c "
from src.engine.loader import load_methods, load_problems
from src.triz.contradiction_matrix import query_matrix
from src.triz.agent import TRIZAgent

methods = load_methods()
problems = load_problems()
print(f'{len(methods)} methods, {len(problems)} problems')

# Query the contradiction matrix
principles = query_matrix(9, 25)  # Speed vs Loss of time
print(f'Speed vs Time loss → principles {principles}')

# Run TRIZ analysis
agent = TRIZAgent()
for p in problems[:3]:
    result = agent.analyze(p)
    print(f'{p.title}: pr={result.recommended_principles}, ifr={result.ifr[:60]}...')
"
```

## Key Design Decisions

- **Python 3.8+** for max compatibility (uses `from __future__ import annotations`)
- **Zero mandatory dependencies** for core modules (AI providers are pluggable via protocol)
- **Asymmetric threshold**: any single dimension ≥ 8.0 passes (not average)
- **Deterministic shuffling**: `hash(block_height + address + nonce)` ensures reproducibility
- **All texts in Traditional Chinese** where user-facing

## Development Workflow

This project uses **git worktrees** for parallel module development:

```bash
# Create a worktree for your module
git worktree add ../hammerworld-<module> -b <module-branch>

# Work on it, commit, then merge back
git merge <module-branch>
git worktree remove ../hammerworld-<module> --force
git branch -d <module-branch>
```

Never work directly on `master`. Always create a worktree branch for each module.

## AI Provider Setup

Users bring their own API keys. Implement the `AIProvider` protocol:

```python
from src.triz.agent import AIProvider

class MyProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # Call your preferred AI API
        return response_text

agent = TRIZAgent(ai_provider=MyProvider())
```

## Design Document

See [DESIGN.md](DESIGN.md) for the complete system architecture, token economics, honor system, and implementation roadmap.
