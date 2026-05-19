# Math Research Zone — Documentation

The Math Research Zone is a structured environment for collaborative mathematical problem solving, proof exploration, and solution mining. It combines a **problem catalog**, **method collections**, **method pool**, **MCTS tree exploration**, and **token-incentivized mining** into a unified workflow.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Problems](#problems)
3. [Method Collections](#method-collections)
4. [Method Pool](#method-pool)
5. [Star Mechanism](#star-mechanism)
6. [Access Control & Mining](#access-control--mining)
7. [Solutions](#solutions)
8. [Auto-Tree Expansion on Submit](#auto-tree-expansion-on-submit)
9. [MCTS Tree Exploration](#mcts-tree-exploration)
10. [CLI Commands](#cli-commands)
11. [Database Schema](#database-schema)
12. [Integration with Formal Proof Agents](#integration-with-formal-proof-agents)

---

## Architecture Overview

```
Math Research Zone
│
├── Problems ───── categorized (number_theory, analysis, algebra, ...)
│
├── Method Collections ── reusable toolkits (e.g. "Complex Analysis Tools")
│   │
│   ├── Method Pool ── per-problem store of successfully mined methods
│   │   └── each entry: method + AI analysis + best score + star count
│   │
│   ├── Solutions ── step-by-step proof attempts with verification tracking
│   │   └── Submitting a solution auto-expands the MCTS tree
│   │
│   └── MCTS Tree ── tree-based proof state exploration (Q-learning)
│       ├── Nodes ── mathematical states / subgoals
│       ├── Edges ── tactic applications or method uses
│       │   └── First-level children auto-created from method pool on submit
│       └── Terminal ── success (proof found) or failure (dead end)
│
└── Token Mining ── run math-mine to unlock zones (results go to method pool, not leaderboard)
```

The zone is backed by SQLite via `LeaderboardDB` and exposed through both a web UI (`src/hub/web/math.py`) and a CLI (`src/cli/main.py`).

---

## Problems

Problems are the top-level unit of the Math Research Zone. Each problem represents an open or solved mathematical question.

**Categories:** `number_theory`, `analysis`, `algebra`, `geometry`, `topology`, `combinatorics`, `logic`, `other`

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Auto-increment primary key |
| `title` | str | Problem title |
| `description` | str | Full problem statement |
| `category` | str | One of the 8 categories above |
| `creator` | str | Address or name of the creator |
| `status` | str | `active` (default) or `solved` |
| `created_at` | int | Unix timestamp |

**DB methods** (`LeaderboardDB`):
- `create_math_problem(title, description, category, creator)` → `pid`
- `get_math_problem(pid)` → `dict`
- `get_math_problems(status)` → `list[dict]`
- `update_math_problem_status(pid, status)`

---

## Method Collections

Method collections are curated sets of mathematical tools, theorems, or techniques that can be applied to problems. They act as the "action space" for proof attempts.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Auto-increment primary key |
| `name` | str | Collection name (e.g. "Complex Analysis Tools") |
| `category` | str | Must be `"mathematics"` for math zones |
| `methods_json` | str | JSON array of method objects |
| `stars` | int | Popularity rating |

Each method in the JSON array has:
```json
{
  "name": "Contour Integration",
  "domain": "mathematics",
  "level": 3,
  "description": "..."
}
```

---

## Method Pool

Each problem has its own **method pool** — a per-problem store of successfully mined methods with full AI analysis. When `math-mine` finds a combination where any AI evaluation dimension scores ≥ 8.0, the method is recorded in the pool **instead of** the general leaderboard.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Auto-increment primary key |
| `problem_id` | int | FK to math_problems |
| `method_collection_id` | int | FK to method collections |
| `method_name` | str | Name of the mined method |
| `method_data` | str | JSON: full method object |
| `analysis_json` | str | JSON: complete AI evaluation output |
| `best_score` | real | Highest score across all dimensions |
| `best_dimension` | str | Dimension that achieved best_score |
| `miner_address` | str | Address of the miner who discovered this |
| `stars` | int | Star count (aggregated from math_method_pool_stars) |
| `created_at` | real | Unix timestamp |

**DB methods:**
- `add_to_method_pool(problem_id, method_collection_id, method, analysis_json, best_score, best_dimension, miner_address)` → `pool_id`
- `get_method_pool(problem_id)` → `list[dict]` (with star counts)
- `get_method_pool_entry(pool_id)` → `dict` (including raw analysis JSON)

### Listing Pool Methods

```bash
# List all methods in a problem's pool
python3 -m src.cli.main math-pool-list 1

# Show full details including AI analysis for a specific entry
python3 -m src.cli.main math-pool-show 1
```

---

## Star Mechanism

Users can star both **pool methods** and **solution steps** to signal quality. Starring is a toggle — starring again removes the star.

### Method Stars

Anyone can star a method pool entry to indicate it is a promising approach. The total star count is displayed in `math-pool-list` and on the web UI.

```bash
python3 -m src.cli.main math-star-method 1 --address 0xALICE
```

### Step Stars

Individual steps within a solution can be starred — useful for highlighting particularly insightful reasoning. The star count per step is available via `get_step_star_count`.

```bash
python3 -m src.cli.main math-star-step 1 3 --address 0xALICE
```

**DB tables:**
- `math_method_pool_stars (method_pool_id, starrer, starred_at)` — per-user star records for pool entries
- `math_step_stars (solution_id, step_num, starrer, starred_at)` — per-user star records for solution steps

**DB methods:**
- `toggle_method_pool_star(pool_id, starrer)` → `int` (new star count)
- `toggle_step_star(solution_id, step_num, starrer)` → `int` (new star count)
- `get_step_star_count(solution_id, step_num)` → `int`

---

## Access Control & Mining

Access to a solution zone is gated by **math-mine**: a user must run a mining operation on a problem-method pair to unlock it.

**Mining flow:**
1. The combiner generates novel method-problem combinations using deterministic shuffle
2. Each combination is evaluated by an AI provider on 8 dimensions
3. If any dimension scores ≥ 8.0 (asymmetric threshold):
   - The method is saved to the **method pool** (not the general leaderboard)
   - Access is recorded in `math_access_log`
   - A root MCTS tree node is auto-created for the zone
4. Access is checked before viewing solutions

**DB methods:**
- `check_math_access(problem_id, method_collection_id, user_address)` → `bool`
- `grant_math_access(problem_id, method_collection_id, user_address, combo_id, analysis_json)`
- `get_math_access_log(problem_id, user_address)` → `list[dict]`

---

## Solutions

Solutions are step-by-step proof attempts with verification tracking. Each step is a JSON object: `{step_num, content, verified}`.

**Key concepts:**
- **max_correct_step** — the highest step number where all preceding steps are verified. If step 3 is unverified, `max_correct_step = 2`. This provides a quality metric for partial solutions.
- **Forking** — any user can fork an existing solution to create a derived version, preserving the parent chain. This enables collaborative improvement of partial proofs.
- **Auto-Tree Expansion** — when a solution is submitted using a method that exists in the problem's method pool, a first-level child node is automatically added to the MCTS tree (see [Auto-Tree Expansion](#auto-tree-expansion-on-submit)).

**DB methods:**
- `submit_math_solution(problem_id, method_collection_id, user_address, steps)` → `sid`
- `get_math_solutions(problem_id, method_collection_id)` → `list[dict]` (sorted by max_correct_step DESC)
- `get_math_solution(sid)` → `dict`
- `fork_math_solution(sid, user_address)` → `new_sid`
- `update_math_solution(sid, steps)`

---

## Auto-Tree Expansion on Submit

When a solution is submitted via `math-submit`, the system automatically checks the problem's method pool and expands the MCTS tree:

1. **Lookup**: queries `get_method_pool(problem_id)` for a matching method name
2. **Dedup**: checks if a tree child with the same `action_label` already exists under the root
3. **Create**: if no duplicate, creates a first-level child node:
   - Parent = root node of the zone
   - Content = method name + AI insight summary
   - Action label = method name
   - Node type = `normal`

This means every method that has been successfully mined and then used in a solution submission automatically becomes part of the MCTS tree, building a bridge between the method pool and the tree exploration system.

```bash
# Mine a method → it goes to the pool
python3 -m src.cli.main math-mine 1 "Complex Analysis" --address 0xMINER

# Submit a solution → auto-creates tree node for the method
python3 -m src.cli.main math-submit 1 1 \
  --steps-json '[{"step_num":1,"content":"Apply contour integration","verified":true}]' \
  --address 0xAGENT

# View the tree — the method appears as a child of the root
python3 -m src.cli.main math-tree-show 1 1
```

---

## MCTS Tree Exploration

The tree system implements a full **Monte Carlo Tree Search** for proof state exploration. It is the centerpiece of the Math Research Zone's support for formal proof agents.

### Tree Nodes

Each node represents a mathematical state (a goal, subgoal, or intermediate assertion):

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Auto-increment |
| `problem_id` | int | FK to math_problems |
| `method_collection_id` | int | FK to collections |
| `user_address` | str | Creator address |
| `content` | str | Mathematical state description |
| `node_type` | str | `normal`, `terminal_success`, `terminal_failure`, or `pruned` |
| `q_value` | float | Expected reward (cumulative average, range 0–1) |
| `visit_count` | int | Number of visits for UCB computation |
| `reward` | float | Immediate reward assigned at creation |
| `is_root` | int | Boolean flag for root nodes |
| `created_at` | int | Unix timestamp |

### Tree Edges

Edges connect parent nodes to child nodes, labeled with the action taken:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Auto-increment |
| `parent_node_id` | int | FK to tree_nodes |
| `child_node_id` | int | FK to tree_nodes |
| `action_label` | str | The tactic/method applied |
| `action_description` | str | Optional detailed description |

Cycle prevention is enforced: `_is_ancestor` checks before edge creation.

### MCTS Algorithm

The tree system implements all four phases of MCTS:

1. **Selection** — `get_uct_scores(node_id)` computes UCB1 scores for all children:
   ```
   UCT = Q(child) + C * sqrt(ln(N_parent) / N_child)
   ```
   Unvisited children (N = 0) receive UCT = ∞ (guaranteed selection).

2. **Expansion** — `create_tree_node` + `create_tree_edge` add new states.

3. **Rollout** — Simulated implicitly via step-by-step solution submission.

4. **Backpropagation** — `backpropagate(node_id, reward)` propagates reward up to the root:
   ```
   Q(n) = (Q(n) * N(n) + reward) / (N(n) + 1)
   N(n) = N(n) + 1
   ```

### Terminal Nodes & Pruning

- **`terminal_success`** — a proof has been found from this state. Backpropagates reward (default 1.0).
- **`terminal_failure`** — a dead end. Backpropagates reward (default 0.0).
- **`pruned`** — explicitly pruned by user. Backpropagates neutral reward.

### DB Methods

| Method | Purpose |
|--------|---------|
| `create_tree_node(pid, mid, user, content, type, q, n, reward)` | Create a new state |
| `get_tree_node(node_id)` | Get node by ID |
| `get_root_node(pid, mid)` | Get or auto-create root node |
| `get_tree_nodes_for_zone(pid, mid)` | List all nodes in a zone |
| `update_tree_node(node_id, **kwargs)` | Update Q, N, type, reward |
| `get_terminal_nodes(pid, mid)` | List all terminal states |
| `create_tree_edge(parent, child, label, desc)` | Add an edge |
| `get_children(node_id)` | List children with UCT scores |
| `count_children(node_id)` | Count direct children |
| `_get_parent_node(child_id)` | Get the parent node |
| `_get_path_to_root(node_id)` | Breadcrumb path to root |
| `backpropagate(node_id, reward)` | Backpropagate reward up the tree |
| `get_uct_scores(node_id, C)` | Compute UCB1 scores |
| `prune_node(node_id)` | Mark node as pruned + backpropagate |

---

## CLI Commands

All commands are accessible via `python -m src.cli.main <command>`.

### View Commands

| Command | Description | Output |
|---------|-------------|--------|
| `math-collection-list [--json]` | List all method collections | Table or JSON |
| `math-problem-list [--search TERM] [--json]` | List problems | Table or JSON |
| `math-problem-show <problem_id> [--address] [--json]` | Show problem details + zones | Table or JSON |
| `math-zone <problem_id> <method_collection_id> [--address] [--json]` | Show solutions in a zone | Table or JSON |
| `math-solution-show <solution_id> [--json]` | Show solution detail | Table or JSON |
| `math-tree-show <problem_id> <method_collection_id> [--json]` | Show tree stats + recursive tree | Table or JSON |
| `math-tree-node <node_id> [--json]` | Show node detail | Table or JSON |
| `math-search <query> [--scope] [--json]` | Search problems, solutions, nodes | Table or JSON |
| `math-pool-list <problem_id> [--json]` | List methods in a problem's method pool | Table or JSON |
| `math-pool-show <pool_id> [--json]` | Show pool entry with AI analysis | Table or JSON |

### Action Commands

| Command | Description |
|---------|-------------|
| `math-problem-create <title> [--description] [--category] [--creator]` | Create a new problem |
| `math-mine <problem_id> <methods_collection> --address ADDR` | Run AI mining to unlock a zone (results go to method pool) |
| `math-unlock <problem_id> <method_collection_id> <combo_id> --address ADDR` | Manual unlock |
| `math-submit <problem_id> <method_collection_id> <steps_json> [--parent_id] --address ADDR` | Submit a solution (auto-expands MCTS tree) |
| `math-tree-add <problem_id> <method_collection_id> --parent PARENT --content CONTENT [--action-label] [--node-type] [--reward]` | Add a tree node |
| `math-tree-backpropagate <node_id> --type (terminal_success|terminal_failure)` | Backpropagate reward |
| `math-tree-prune <node_id>` | Prune a node |
| `math-pull <problem_id> <method_collection_id> --output PATH [--best-only]` | Export zone data to JSON |
| `math-tree-status [--problem-id]` | Show tree status across all zones |
| `math-star-method <pool_id> --address ADDR` | Toggle star on a method pool entry |
| `math-star-step <solution_id> <step_num> --address ADDR` | Toggle star on a solution step |

### CLI JSON Output Contract

All view commands support `--json` for machine-readable output. The JSON output follows this structure:

```json
{
  "problem": {"id": 1, "title": "...", "category": "...", "solution_count": 3},
  "method_zones": [{"id": 1, "name": "...", "tool_count": 5, "unlocked": true, "top_step": 5}],
  "solutions": [{"id": 1, "user_address": "0x...", "max_correct_step": 3, "step_count": 5}],
  "steps": [{"step_num": 1, "content": "...", "verified": true}],
  "tree": {"stats": {"nodes": 10, "proofs": 2, "max_depth": 5, "root_q": 0.75, "root_n": 20}},
  "node": {"id": 1, "content": "...", "q_value": 0.75, "visit_count": 10, "node_type": "normal"},
  "pool": [{"id": 1, "method_name": "...", "best_score": 8.5, "stars": 3}],
  "pool_entry": {"id": 1, "method_name": "...", "analysis_json": "{...}", "best_score": 8.5}
}
```

---

## Database Schema

Tables are auto-created by `LeaderboardDB.__init__`:
- `math_problems` — problem catalog
- `math_solutions` — step-based proof attempts
- `math_access_log` — unlock records
- `math_tree_nodes` — MCTS states
- `math_tree_edges` — MCTS transitions
- `math_method_pool` — per-problem store of successfully mined methods with AI analysis
- `math_method_pool_stars` — per-user star records for pool entries
- `math_step_stars` — per-user star records for solution steps

All tables live in a single SQLite file (default: `data/leaderboard.db`).

---

## Integration with Formal Proof Agents

The Math Research Zone is designed to interface naturally with formal theorem proving agents (e.g., Lean 4 agents):

### MCTS for Proof Search

The tree infrastructure maps directly to Lean proof states:
- Each **node** = a Lean goal or subgoal
- Each **edge** = a tactic application or lemma invocation
- **Terminal success** = `exact` / `done` — the goal is closed
- **Backpropagation** = reward signal for successful proof paths
- **UCT scores** = guide exploration toward promising proof branches

### Method Pool for Tactic Discovery

The method pool serves as a discovered-tactic repository:
- Agents mine for method-problem combinations → successful ones land in the pool
- Agents can list the pool to see which methods have proven useful for a problem
- Pool entries include full AI analysis explaining why a method is promising
- Star counts indicate community/agent consensus on method quality

### Solution Forking for Iterative Improvement

Agents can fork existing partial solutions, apply repair strategies (similar to the numina-lean-agent's `repair-proofs` approach), and submit improved versions. The `max_correct_step` metric provides a natural scoring signal.

### Auto-Tree Expansion Bridges Pool and Tree

When an agent submits a solution using a pooled method, the system automatically expands the MCTS tree — creating a first-level child node under the root. This connects the static method pool with the dynamic tree exploration, enabling agents to navigate from high-level methods down to specific proof states.

### Mining as Automated Proof Attempts

The mining pipeline — method-problem combination → AI evaluation → access grant — can be repurposed as:
1. **Tactic selection**: method collection → available tactics/lemmas
2. **Proof attempt**: combination engine → generate proof strategy
3. **Evaluation**: verification agent → success/failure signal
4. **Access**: successful proof → unlock solution zone

### JSON Export for External Agents

The `math-pull` command exports full problem-solution-tree data as JSON, which external agents can consume directly. Conversely, `math-submit` accepts JSON-formatted steps from any automated pipeline.

---

## Quick Reference

```bash
# Create a problem
python3 -m src.cli.main math-problem-create "Riemann Hypothesis" --category number_theory

# Mine to unlock + populate method pool
python3 -m src.cli.main math-mine 1 "Complex Analysis" --address 0xMINER

# List pooled methods
python3 -m src.cli.main math-pool-list 1

# Submit a solution + auto-expand tree
python3 -m src.cli.main math-submit 1 1 \
  --steps-json '[{"step_num":1,"content":"Define zeta function","verified":true}]' \
  --address 0xAGENT

# Star a useful method
python3 -m src.cli.main math-star-method 1 --address 0xALICE

# Star a clever step
python3 -m src.cli.main math-star-step 1 3 --address 0xALICE

# View the MCTS tree
python3 -m src.cli.main math-tree-show 1 1
```

For implementation details, see:
- `src/hub/web/math.py` — web page rendering
- `src/hub/leaderboard.py` — DB layer
- `src/cli/main.py` — CLI commands
- `tests/test_math_zone.py` — comprehensive test suite
