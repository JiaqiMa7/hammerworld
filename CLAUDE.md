# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Idea Mining Network: decentralized creative problem-solving using TRIZ + AI + blockchain economics.
Methods Matrix × Problems Matrix → Random Combination → Multi-Dimension AI Evaluation → Leaderboards → Token Rewards.

## Build & Test

```bash
# No dependencies for core modules. Quick verification:
python3 -c "
from src.engine.loader import load_methods, load_problems
from src.engine.combiner import generate_combinations
from src.triz.agent import TRIZAgent
from src.triz.contradiction_matrix import query_matrix
methods = load_methods()
problems = load_problems()
print(f'{len(methods)} methods, {len(problems)} problems OK')
"
```

## Architecture

- `src/engine/` — Core data models, JSON loader, deterministic combination engine
- `src/triz/` — 39 parameters, 40 principles, contradiction matrix (39×39), TRIZ Agent
- `src/evaluation/` — 8-dimension scoring pipeline with asymmetric threshold (any dim ≥ 8.0 passes)
- `src/hub/` — Leaderboard (planned)
- `src/cli/` — CLI tools (planned)
- `data/` — methods.json (35 methods, 4 levels), problems.json (22 problems, 6 domains)

## Development Workflow

Always use git worktrees — never work directly on master:
```bash
git worktree add ../hammerworld-<module> -b <module-branch>
# ... work, commit ...
git merge <module-branch>
git worktree remove ../hammerworld-<module> --force
git branch -d <module-branch>
```

## Key Design Decisions

- Python 3.8+ with `from __future__ import annotations` for type hints
- Zero mandatory dependencies — AI providers are pluggable via `AIProvider` protocol
- Asymmetric threshold: any single dimension ≥ 8.0 passes (not average of all dimensions)
- Deterministic shuffle: `hash(block_height + address + nonce)` seeds Fisher-Yates
- Traditional Chinese for user-facing strings
- Full design spec in `DESIGN.md`
