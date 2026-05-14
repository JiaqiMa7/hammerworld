"""CLI tools for the Idea Mining Network."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from src.engine.config import HammerConfig

_ADDR_UNSET = object()


def _get_user_address(args, fallback: str = "0xMINER", auto_generate: bool = True) -> str:
    """Return the user's address: CLI flag > config file > auto-generate > fallback default.

    On first run, generates an Ed25519 keypair and derives a unique address from
    the public key: ``0x + SHA-256(pubkey)[:40]``.  The private key is stored in
    ``~/.hammerworld/identity`` (mode 0600) so the user can prove ownership.
    Falls back to a random seed if the ``cryptography`` library is not installed.
    """
    addr = getattr(args, 'address', _ADDR_UNSET)
    if addr is not _ADDR_UNSET and addr is not None and addr != "":
        return addr
    val = HammerConfig.load().address
    if val:
        return val
    if auto_generate:
        from src.hub.user_identity import ensure_user_identity, get_user_address
        identity = ensure_user_identity()
        new_addr = get_user_address(identity)
        _save_user_config("HAMMERWORLD_ADDRESS", new_addr)
        return new_addr
    return fallback


def _save_user_config(key: str, value: str) -> None:
    """Write or update a key=value pair in ~/.hammerworld/config."""
    config_path = Path.home() / ".hammerworld"
    config_path.mkdir(parents=True, exist_ok=True)
    config_file = config_path / "config"
    lines = []
    found = False
    if config_file.exists():
        for line in config_file.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _ = stripped.split("=", 1)
                if k.strip() == key:
                    lines.append(f"{key}={value}")
                    found = True
                    continue
            lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    config_file.write_text("\n".join(lines) + "\n")
    # Invalidate the global singleton so subsequent reads get fresh data
    from src.engine.config import HammerConfig as _hc
    _hc.reload()


def _make_triz_agent():
    """Create a TRIZAgent, with AI provider if API key is configured, else rule-based."""
    from src.triz.agent import TRIZAgent
    from src.evaluation.providers import OpenAIProvider, get_api_key, get_api_base
    cfg = HammerConfig.load()
    api_key = cfg.api_key
    if api_key:
        ai = OpenAIProvider(api_key=api_key, api_base=cfg.api_base, model=cfg.get_model("triz"))
        return TRIZAgent(ai_provider=ai)
    return TRIZAgent()


def cmd_mine(args):
    """Run the mining combination engine with evaluation and DB storage."""
    import sys
    from src.engine.config import HammerConfig
    from src.engine.loader import load_methods, load_problems
    from src.engine.combiner import generate_combinations
    from src.evaluation.scorer import EvaluationPipeline
    from src.evaluation.providers import OpenAIProvider, get_api_key
    from src.hub.leaderboard import LeaderboardDB

    # Require API key
    api_key = get_api_key()
    if not api_key:
        cfg_example = Path.home() / ".hammerworld" / "config"
        print("ERROR: No API key configured.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Set the HAMMERWORLD_API_KEY environment variable:", file=sys.stderr)
        print("  export HAMMERWORLD_API_KEY=sk-...", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Or create {cfg_example} with:", file=sys.stderr)
        print("  api_key=sk-...", file=sys.stderr)
        print("  api_base=https://api.openai.com/v1   # optional, defaults to OpenAI", file=sys.stderr)
        print("  mining_model=gpt-4o                   # optional, per-task model", file=sys.stderr)
        print("", file=sys.stderr)
        print("Compatible providers: OpenAI, Anthropic (via compatible proxy), local LLM, etc.", file=sys.stderr)
        sys.exit(1)

    address = _get_user_address(args, "0xMINER")

    # Open DB for collection loading and later saving
    db = LeaderboardDB(args.db)

    # Load methods: collection > custom file > default
    if args.methods_collection:
        coll = db.find_collection_by_name("method", args.methods_collection)
        if not coll:
            print(f"ERROR: Method collection '{args.methods_collection}' not found.", file=sys.stderr)
            sys.exit(1)
        methods_data = json.loads(coll["methods_json"])
        from src.engine.models import Method, MethodLevel
        methods = [
            Method(
                id=m.get("id", m.get("name", f"m{i}")),
                name=m["name"],
                domain=m.get("domain", "other"),
                level=MethodLevel(m.get("level", 1)),
                description=m.get("description", ""),
                trigger_conditions=m.get("trigger_conditions", []),
                examples=m.get("examples", []),
                prerequisites=m.get("prerequisites", []),
                compatible_with=m.get("compatible_with", []),
            )
            for i, m in enumerate(methods_data)
        ]
        db.increment_import("method", coll["id"])
        print(f"Loaded {len(methods)} methods from collection '{args.methods_collection}'")
    else:
        methods = load_methods(args.methods or None)

    # Load problems: collection > custom file > default
    if args.problems_collection:
        coll = db.find_collection_by_name("problem", args.problems_collection)
        if not coll:
            print(f"ERROR: Problem collection '{args.problems_collection}' not found.", file=sys.stderr)
            sys.exit(1)
        problems_data = json.loads(coll["problems_json"])
        from src.engine.models import Problem, Domain, ProblemMaturity, ConstraintType
        problems = [
            Problem(
                id=p.get("id", p.get("title", f"p{i}")),
                title=p["title"],
                domain=Domain(p.get("domain", "other")),
                description=p.get("description", ""),
                constraint_types=[ConstraintType(c) for c in p.get("constraint_types", [])],
                maturity=ProblemMaturity(p.get("maturity", 1)),
                triz_standardized=p.get("triz_standardized"),
            )
            for i, p in enumerate(problems_data)
        ]
        db.increment_import("problem", coll["id"])
        print(f"Loaded {len(problems)} problems from collection '{args.problems_collection}'")
    else:
        problems = load_problems(args.problems or None)

    print(f"Matrix: {len(methods)} methods × {len(problems)} problems ({len(methods) * len(problems)} possible pairs)")
    combos = generate_combinations(
        methods, problems,
        block_height=args.block_height,
        user_address=_get_user_address(args, "0xMINER"),
        nonce=args.nonce,
        batch_size=args.batch,
        method_step=args.method_step,
        problem_step=args.problem_step,
        problem_offset=args.problem_offset,
        max_attempts_mult=args.max_attempts,
    )
    if args.method_step == 0 or args.problem_step == 0:
        print("Stepping: auto-tuned (pass --method-step/--problem-step to override)")

    # Evaluate with real AI (parallel)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    cfg = HammerConfig.load()
    api_base = args.api_base or cfg.api_base
    model = args.model or cfg.get_model("mining")
    workers = getattr(args, "parallel", 1)
    provider = OpenAIProvider(api_key=api_key, api_base=api_base, model=model)
    print(f"API: {api_base}  model: {model}  workers: {workers}")
    print(f"Evaluating {len(combos)} combinations...")
    pipeline = EvaluationPipeline(
        provider,
        threshold=args.threshold,
        model_name=model,
        model_version="api",
    )

    results_by_index: dict[int, object] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(pipeline.evaluate, combo): i
            for i, combo in enumerate(combos)
        }
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            combo = combos[i]
            label = f"{combo.method.name[:30]} × {combo.problem.title[:35]}"
            try:
                result = future.result()
                best = result.combination.best_dimension
                print(f"  [{i+1}/{len(combos)}] {label} → best={best.value if best else '?'}={result.combination.best_score or 0:.1f}")
                results_by_index[i] = result
            except Exception as exc:
                print(f"  [{i+1}/{len(combos)}] {label} → FAILED: {exc}")

    # Collect results in original order
    results = [results_by_index[i] for i in sorted(results_by_index)]

    # Save to leaderboard
    saved = 0
    for r in results:
        try:
            db.insert(r.combination, miner_addr=address)
            saved += 1
            dims = [d.value for d in r.high_dimensions]
            print(f"  [{r.combination.id}] {r.combination.method.name} × {r.combination.problem.title} "
                  f"→ best={r.combination.best_dimension.value if r.combination.best_dimension else '?'}"
                  f"={r.combination.best_score or 0:.1f} "
                  f"high={dims}")
        except Exception as exc:
            print(f"  [{r.combination.id}] error: {exc}")

    print(f"Saved {saved}/{len(combos)} combinations to {args.db}")


def cmd_top(args):
    """Show leaderboard rankings."""
    from src.engine.models import EvalDimension, Domain, MethodLevel
    from src.hub.leaderboard import LeaderboardDB

    dim = EvalDimension(args.dimension) if args.dimension else None
    dom = Domain(args.domain) if args.domain else None
    lvl = MethodLevel(int(args.level)) if args.level else None

    db = LeaderboardDB(args.db)
    entries = db.get_top(dimension=dim, domain=dom, method_level=lvl, limit=args.limit)

    print(f"{'Rank':<5} {'Score':<7} {'Dim':<18} {'Method':<25} {'Problem':<30}")
    print("-" * 85)
    for e in entries:
        print(f"{e.rank:<5} {e.best_score:<7.2f} {e.best_dimension:<18} {e.method_name[:24]:<25} {e.problem_title[:29]:<30}")


def cmd_search(args):
    """Search the leaderboard."""
    from src.engine.models import EvalDimension
    from src.hub.leaderboard import LeaderboardDB

    dim = EvalDimension(args.dimension) if args.dimension else None
    db = LeaderboardDB(args.db)
    entries = db.search(args.query, dimension=dim, limit=args.limit)

    print(f"Search results for '{args.query}':")
    for e in entries:
        print(f"  [{e.best_dimension}={e.best_score:.1f}] {e.method_name} × {e.problem_title}")


def cmd_random(args):
    """Random draw from a leaderboard."""
    from src.engine.models import EvalDimension, Domain
    from src.hub.leaderboard import LeaderboardDB

    dim = EvalDimension(args.dimension) if args.dimension else None
    dom = Domain(args.domain) if args.domain else None
    db = LeaderboardDB(args.db)
    result = db.random_draw(dimension=dim, domain=dom, draw_count=args.count, viewer_addr=_get_user_address(args, "0xVIEWER"))

    print(f"Random draw from {result.board_name} board ({result.total_in_board} available):")
    for e in result.entries:
        print(f"  [{e.best_dimension}={e.best_score:.1f}] {e.method_name} × {e.problem_title}")


def cmd_submit_method(args):
    """Submit a new thinking method to the matrix."""
    import json
    from src.hub.leaderboard import LeaderboardDB

    data = {
        "name": args.name,
        "domain": args.domain,
        "level": args.level,
        "description": args.description,
        "examples": [e.strip() for e in (args.examples or "").split(",") if e.strip()],
        "prerequisites": [p.strip() for p in (args.prerequisites or "").split(",") if p.strip()],
        "compatible_with": [c.strip() for c in (args.compatible_with or "").split(",") if c.strip()],
    }
    db = LeaderboardDB(args.db)
    sub_id = db.submit("method", data, args.submitter)
    print(f"Method submitted. ID: {sub_id}")
    print(f"  Name: {data['name']}")
    print(f"  Domain: {data['domain']} (level {data['level']})")
    print(f"Status: pending review")


def cmd_submit_problem(args):
    """Submit a new unsolved problem to the matrix."""
    import json
    from src.hub.leaderboard import LeaderboardDB

    data = {
        "title": args.title,
        "domain": args.domain,
        "description": args.description,
        "constraint_types": [c.strip() for c in (args.constraints or "").split(",") if c.strip()],
        "maturity": args.maturity,
    }

    agent = _make_triz_agent()
    try:
        problem = agent.standardize(args.description, args.domain)
        if problem.triz_standardized:
            data["triz_standardized"] = problem.triz_standardized
            tp = problem.triz_standardized.get("triz_params", [])
            ifr = problem.triz_standardized.get("ifr", "")
            print(f"TRIZ: {len(tp)} principles recommended, IFR: {ifr[:80]}...")
    except Exception as e:
        print(f"TRIZ standardization skipped ({e})")

    db = LeaderboardDB(args.db)
    sub_id = db.submit("problem", data, args.submitter)
    print(f"Problem submitted. ID: {sub_id}")
    print(f"  Title: {data['title']}")
    print(f"  Domain: {data['domain']} (maturity {data['maturity']})")
    print(f"Status: pending review")


def cmd_triz_analyze(args):
    """Run TRIZ standardization on a problem description and display results."""
    agent = _make_triz_agent()
    print(f"Analyzing: {args.description[:100]}...")
    print(f"Domain: {args.domain}")
    mode = "AI" if agent.ai_provider else "rule-based keyword matching"
    print(f"Mode: {mode}")
    print()

    problem = agent.standardize(args.description, args.domain)
    ctx = problem.triz_standardized or {}

    # Contradictions
    contradiction = ctx.get("contradiction", {})
    if contradiction.get("improving") or contradiction.get("worsening"):
        print("=== Technical Contradiction ===")
        print(f"  Improving: {contradiction.get('improving', 'N/A')}")
        print(f"  Worsening: {contradiction.get('worsening', 'N/A')}")
        print()

    # IFR
    ifr = ctx.get("ifr", "")
    if ifr:
        print("=== Ideal Final Result (IFR) ===")
        print(f"  {ifr}")
        print()

    # Recommended Principles
    principles = ctx.get("triz_params", [])
    if principles:
        from src.triz.knowledge import INVENTIVE_PRINCIPLES
        print(f"=== Recommended Principles ({len(principles)}) ===")
        for pid in principles[:10]:
            if pid in INVENTIVE_PRINCIPLES:
                p = INVENTIVE_PRINCIPLES[pid]
                print(f"  [{pid}] {p.name}")
                print(f"      {p.description[:100]}...")
                if p.examples:
                    print(f"      Examples: {', '.join(p.examples[:2])}")
        print()

    # Functional Model
    fm = ctx.get("functional_model", {})
    actors = fm.get("actors", [])
    useful = fm.get("useful_functions", [])
    harmful = fm.get("harmful_functions", [])

    def _fmt_items(items):
        """Format list items that may be strings or dicts."""
        result = []
        for item in items:
            if isinstance(item, dict):
                parts = [f"{k}={v}" for k, v in item.items()]
                result.append("{" + ", ".join(parts) + "}")
            else:
                result.append(str(item))
        return result

    if actors or useful or harmful:
        print("=== Functional Model ===")
        if actors:
            print(f"  Actors: {', '.join(_fmt_items(actors))}")
        if useful:
            print(f"  Useful: {', '.join(_fmt_items(useful))}")
        if harmful:
            print(f"  Harmful: {', '.join(_fmt_items(harmful))}")
        print()

    # Inferred constraints
    print(f"=== Inferred ===")
    print(f"  Domain: {problem.domain.value}")
    print(f"  Constraints: {[c.value for c in problem.constraint_types]}")


def cmd_keygen(args):
    """Generate an ed25519 identity key pair for signed P2P announcements."""
    from pathlib import Path
    from src.hub.identity import IdentityManager
    import base64

    path = args.output or "identity.key"
    if Path(path).exists() and not args.force:
        print(f"ERROR: {path} already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    im = IdentityManager(path)
    if not im.available:
        print("ERROR: cryptography library not installed. Install with: pip install cryptography",
              file=sys.stderr)
        sys.exit(1)

    print(f"Generated Ed25519 identity key pair:")
    print(f"  Public key (base64): {base64.b64encode(im.public_key_bytes).decode()}")
    print(f"  Peer ID:             {im.peer_id}")
    print(f"  Path:                {path}")
    print(f"  Algorithm:           Ed25519")
    print(f"")
    print(f"Use with:  --identity {path}")

    if args.set_identity:
        import hashlib, shutil
        addr = "0x" + hashlib.sha256(im.public_key_bytes).hexdigest()[:40]
        _save_user_config("HAMMERWORLD_ADDRESS", addr)
        # Also copy the private key to ~/.hammerworld/identity
        identity_path = Path.home() / ".hammerworld" / "identity"
        identity_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, str(identity_path))
        os.chmod(str(identity_path), 0o600)
        print(f"Address derived from key: {addr}")
        print(f"Identity key: {identity_path}")
        print(f"Stored in ~/.hammerworld/config")


def cmd_identity(args):
    """Show or set the current user identity address."""
    config_path = Path.home() / ".hammerworld" / "config"
    identity_path = Path.home() / ".hammerworld" / "identity"

    if args.set_address:
        _save_user_config("HAMMERWORLD_ADDRESS", args.set_address)
        print(f"Identity set: {args.set_address}")
        print(f"Stored in: {config_path}")
        print(f"NOTE: This manually-set address is NOT backed by a private key.")
        print(f"      For a key-backed address, use: hammerworld keygen --set-identity")
    else:
        addr = HammerConfig.load().address
        if addr:
            has_key = identity_path.exists()
            print(f"Current address: {addr}")
            if has_key:
                print(f"Backed by: Ed25519 private key ({identity_path})")
            else:
                print(f"Backed by: none (no private key found)")
                print(f"Generate a key-backed address with: hammerworld keygen --set-identity")
        else:
            print("No address configured.")
            print(f"Set one with: hammerworld identity set <address>")
        print(f"Config file: {config_path}")


def cmd_hub(args):
    """Start a P2P hub server."""
    from src.hub.leaderboard import LeaderboardDB
    from src.hub.peer import PeerConfig
    from src.hub.server import HubServer

    db = LeaderboardDB(args.db)
    config = PeerConfig(
        port=args.port,
        bootstrap=args.bootstrap or [],
        discovery_urls=args.discovery_urls or [],
        gossip_interval=args.gossip_interval,
        peer_timeout=args.peer_timeout,
        max_peers=args.max_peers,
        identity_key_path=getattr(args, "identity", None),
    )
    server = HubServer(db, config)

    def _shutdown(signum, frame):
        print("\nShutting down hub...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    is_web = getattr(args, "web", False)
    if is_web:
        print(f"Web UI: http://localhost:{args.port}/")
        print(f"API:    http://localhost:{args.port}/health")
    print(f"Hub started on port {args.port} (peer_id: {server.peer_manager.peer_id})")
    print(f"Database: {args.db}")
    if args.bootstrap:
        print(f"Bootstrap peers: {args.bootstrap}")
    print("Press Ctrl+C to stop.\n")

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


def cmd_math_mine(args):
    """Run mining for math zone gate unlock — auto-grants access."""
    from src.engine.config import HammerConfig
    from src.engine.loader import load_methods
    from src.engine.combiner import generate_combinations
    from src.evaluation.scorer import EvaluationPipeline
    from src.evaluation.providers import OpenAIProvider, get_api_key
    from src.hub.leaderboard import LeaderboardDB
    from src.engine.models import Method, MethodLevel, Problem, Domain, ProblemMaturity, ConstraintType

    api_key = get_api_key()
    if not api_key:
        print("ERROR: No API key configured.", file=sys.stderr)
        sys.exit(1)

    address = _get_user_address(args, "0xMINER")
    db = LeaderboardDB(args.db)

    # Load math problem
    problem_entry = db.get_math_problem(args.problem_id)
    if not problem_entry:
        print(f"ERROR: Math problem #{args.problem_id} not found.", file=sys.stderr)
        sys.exit(1)

    # Load method collection
    coll = db.find_collection_by_name("method", args.methods_collection)
    if not coll:
        print(f"ERROR: Method collection '{args.methods_collection}' not found.", file=sys.stderr)
        sys.exit(1)
    methods_data = json.loads(coll["methods_json"])
    methods = [
        Method(
            id=m.get("id", m.get("name", f"m{i}")),
            name=m["name"],
            domain=m.get("domain", "mathematics"),
            level=MethodLevel(m.get("level", 1)),
            description=m.get("description", ""),
            trigger_conditions=m.get("trigger_conditions", []),
            examples=m.get("examples", []),
            prerequisites=m.get("prerequisites", []),
            compatible_with=m.get("compatible_with", []),
        )
        for i, m in enumerate(methods_data)
    ]

    # Wrap problem as Problem object
    problem = Problem(
        id=str(problem_entry["id"]),
        title=problem_entry["title"],
        domain=Domain("mathematics"),
        description=problem_entry.get("description", ""),
        constraint_types=[],
        maturity=ProblemMaturity(1),
    )

    print(f"Math Mine: {len(methods)} methods × {problem.title}")
    print(f"Method Collection: {coll['name']}")

    combos = generate_combinations(
        methods, [problem],
        block_height=args.block_height,
        user_address=_get_user_address(args, "0xMINER"),
        nonce=args.nonce,
        batch_size=args.batch,
        method_step=args.method_step,
        problem_step=0,
        problem_offset=0,
        max_attempts_mult=args.max_attempts,
    )
    print(f"Generated {len(combos)} combination(s)")

    # Evaluate
    cfg = HammerConfig.load()
    api_base = args.api_base or cfg.api_base
    model = args.model or cfg.get_model("mining")
    workers = args.parallel
    provider = OpenAIProvider(api_key=api_key, api_base=api_base, model=model)
    print(f"API: {api_base}  model: {model}  workers: {workers}")

    pipeline = EvaluationPipeline(provider, threshold=args.threshold, model_name=model, model_version="api")

    from concurrent.futures import ThreadPoolExecutor, as_completed
    results_by_index: dict[int, object] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(pipeline.evaluate, combo): i
            for i, combo in enumerate(combos)
        }
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            combo = combos[i]
            label = f"{combo.method.name[:30]} × {combo.problem.title[:35]}"
            try:
                result = future.result()
                best = result.combination.best_dimension
                print(f"  [{i+1}/{len(combos)}] {label} → best={best.value if best else '?'}={result.combination.best_score or 0:.1f}")
                results_by_index[i] = result
            except Exception as exc:
                print(f"  [{i+1}/{len(combos)}] {label} → FAILED: {exc}")

    results = [results_by_index[i] for i in sorted(results_by_index)]

    # Save to leaderboard
    saved = 0
    access_granted = False
    for r in results:
        try:
            entry = db.insert(r.combination, miner_addr=address)
            saved += 1
            # Auto-grant access on first successful save
            if not access_granted:
                analysis_json = json.dumps({
                    "analysis_text": r.combination.analyses[-1].analysis_text if r.combination.analyses else "",
                    "best_dimension": str(r.combination.best_dimension.value) if r.combination.best_dimension else "",
                    "best_score": r.combination.best_score,
                }, ensure_ascii=False)
                db.grant_math_access(
                    problem_entry["id"], coll["id"],
                    address, r.combination.id, analysis_json,
                )
                access_granted = True
                print(f"  Access granted! You can now view: /web/math/{problem_entry['id']}/{coll['id']}")
                # Auto-create root tree node
                try:
                    db.get_root_node(problem_entry["id"], coll["id"])
                except Exception:
                    pass  # root creation is best-effort
        except Exception as exc:
            print(f"  error saving: {exc}")

    print(f"Saved {saved}/{len(combos)} combinations to {args.db}")
    if not access_granted and saved == 0:
        print("WARNING: No combinations were saved. Access was NOT granted.")
    db.increment_import("method", coll["id"])


def cmd_math_submit(args):
    """Submit or fork a math solution."""
    from src.hub.leaderboard import LeaderboardDB

    db = LeaderboardDB(args.db)

    # Verify problem and collection exist
    problem = db.get_math_problem(args.problem_id)
    if not problem:
        print(f"ERROR: Math problem #{args.problem_id} not found.", file=sys.stderr)
        sys.exit(1)
    coll = db.get_collection("method", args.method_collection_id)
    if not coll:
        print(f"ERROR: Method collection #{args.method_collection_id} not found.", file=sys.stderr)
        sys.exit(1)

    # Parse steps
    try:
        steps = json.loads(args.steps_json)
        if not isinstance(steps, list):
            print("ERROR: --steps-json must be a JSON array.", file=sys.stderr)
            sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in --steps-json: {e}", file=sys.stderr)
        sys.exit(1)

    sid = db.submit_math_solution(
        problem_id=args.problem_id,
        method_collection_id=args.method_collection_id,
        user_address=_get_user_address(args, "0xSOLVER"),
        steps=steps,
        parent_id=args.parent_id,
    )
    print(f"Solution submitted. ID: {sid}")
    if args.parent_id:
        print(f"  Forked from solution #{args.parent_id}")
    print(f"  Problem: {problem['title']}")
    print(f"  Method: {coll['name']}")
    print(f"  Steps: {len(steps)}")
    print(f"  Max correct step: {db._calc_max_correct_step(steps)}")


def cmd_math_tree_add(args):
    """Add a child node to an existing MCTS tree node."""
    from src.hub.leaderboard import LeaderboardDB

    db = LeaderboardDB(args.db)
    parent = db.get_tree_node(args.parent_node_id)
    if not parent:
        print(f"ERROR: Parent node #{args.parent_node_id} not found.", file=sys.stderr)
        sys.exit(1)

    reward = args.reward if args.reward is not None else (
        1.0 if args.type == "terminal_success" else 0.0)

    node_id = db.create_tree_node(
        problem_id=parent["problem_id"],
        method_collection_id=parent["method_collection_id"],
        user_address=_get_user_address(args, "0xEXPLORER"),
        content=args.content,
        node_type=args.type,
        reward=reward,
    )
    edge_id = db.create_tree_edge(
        parent_node_id=args.parent_node_id,
        child_node_id=node_id,
        action_label=args.action,
        action_description=args.description or "",
    )
    print(f"Created node #{node_id} (edge #{edge_id}) under node #{args.parent_node_id}")
    print(f"  Content: {args.content[:60]}")
    print(f"  Type: {args.type}")
    print(f"  Action: {args.action}")

    if args.type in ("terminal_success", "terminal_failure"):
        db.backpropagate(node_id, reward)
        print(f"  Backpropagated reward={reward} to root")


def cmd_math_tree_status(args):
    """Show MCTS tree statistics for a (problem, method) zone."""
    from src.hub.leaderboard import LeaderboardDB

    db = LeaderboardDB(args.db)
    nodes = db.get_tree_nodes_for_zone(args.problem_id, args.method_collection_id)
    root = db.get_root_node(args.problem_id, args.method_collection_id)
    terminals = db.get_terminal_nodes(args.problem_id, args.method_collection_id)
    success_terminals = [n for n in terminals if n["node_type"] == "terminal_success"]

    print(f"Tree for problem #{args.problem_id} / method #{args.method_collection_id}:")
    print(f"  Total nodes: {len(nodes)}")
    print(f"  Root node: #{root['id'] if root else 'N/A'}")
    print(f"  Terminal nodes: {len(terminals)} ({len(success_terminals)} success)")
    if root:
        print(f"  Root Q-value: {root['q_value']:.4f}")
        print(f"  Root visits: {root['visit_count']}")

    # Show UCT for root children
    if root:
        uct = db.get_uct_scores(root["id"])
        if uct:
            print(f"  Children (UCT order):")
            for c in uct[:5]:
                uct_str = f"{c.get('uct_score', 0):.3f}" if c.get("uct_score") != float('inf') else "inf"
                print(f"    #{c['child_id']}: {c['action_label'][:30]} "
                      f"Q={c['child_q_value']:.3f} N={c['child_visit_count']} UCT={uct_str}")


def cmd_buffer_submit(args):
    """Submit an AI analysis to the blockchain buffer zone."""
    from src.hub.leaderboard import LeaderboardDB
    from src.blockchain.contracts import SimulatedToken, StakingContract
    from src.blockchain.buffer import BufferZone

    address = _get_user_address(args, "0xBUFFER")
    db = LeaderboardDB(args.db)
    token = SimulatedToken(db)
    staking = StakingContract(db, token)
    buffer_zone = BufferZone(db, token, staking)

    analysis_json = args.analysis_json
    if args.analysis_file:
        try:
            analysis_json = Path(args.analysis_file).read_text()
        except FileNotFoundError:
            print(f"ERROR: File not found: {args.analysis_file}", file=sys.stderr)
            sys.exit(1)

    sub_id = buffer_zone.submit_analysis(
        combo_id=args.combo_id,
        method_id=args.method_id,
        method_name=args.method_name,
        problem_id=args.problem_id,
        problem_title=args.problem_title,
        submitter=address,
        analysis_json=analysis_json,
        analysis_text=args.analysis_text,
    )
    print(f"Submission sent to buffer zone.")
    print(f"  Submission ID: {sub_id}")
    print(f"  Combo: {args.combo_id}")
    print(f"  Status: pending")
    print(f"  Staked: {BufferZone.STAKE_PER_SUBMISSION} IDEA")


def cmd_buffer_classify(args):
    """Classify a pending buffer submission."""
    from src.hub.leaderboard import LeaderboardDB
    from src.blockchain.contracts import SimulatedToken, StakingContract
    from src.blockchain.buffer import BufferZone

    address = _get_user_address(args, "0xCLASSIFIER")
    db = LeaderboardDB(args.db)
    token = SimulatedToken(db)
    staking = StakingContract(db, token)
    buffer_zone = BufferZone(db, token, staking)

    result = buffer_zone.classify(
        submission_id=args.submission_id,
        classifier_addr=address,
        domain_label=args.domain,
        is_nsfw=args.nsfw,
        is_spam=args.spam,
        notes=args.notes,
    )
    if not result.get("ok"):
        print(f"ERROR: {result.get('error', 'classification failed')}", file=sys.stderr)
        sys.exit(1)

    consensus = result.get("consensus", {})
    print(f"Classification submitted.")
    print(f"  Submission: {args.submission_id}")
    print(f"  Classifier: {address}")
    print(f"  Domain: {args.domain}")
    print(f"  Votes: {consensus.get('total', 1)}")
    if consensus.get("reached"):
        print(f"  Consensus: REACHED ({consensus.get('domain', '')})")
    else:
        if consensus.get("total", 0) < BufferZone.MIN_CLASSIFICATIONS:
            needed = BufferZone.MIN_CLASSIFICATIONS - consensus.get("total", 0)
            print(f"  Consensus: Need {needed} more vote(s)")


def cmd_buffer_status(args):
    """Check buffer submission status."""
    from src.hub.leaderboard import LeaderboardDB

    address = _get_user_address(args, "0xVIEWER")
    db = LeaderboardDB(args.db)

    if args.submission_id:
        from src.blockchain.contracts import SimulatedToken, StakingContract
        from src.blockchain.buffer import BufferZone
        token = SimulatedToken(db)
        staking = StakingContract(db, token)
        buffer_zone = BufferZone(db, token, staking)

        status = buffer_zone.get_status(args.submission_id)
        if "error" in status:
            print(f"ERROR: {status['error']}", file=sys.stderr)
            sys.exit(1)
        print(f"Submission: {args.submission_id}")
        print(f"  Combo: {status.get('combo_id', '')}")
        print(f"  Submitter: {status.get('submitter', '')}")
        print(f"  Status: {status.get('status', 'unknown')}")
        print(f"  Classifiers: {status.get('classifier_count', 0)}")
        if status.get("consensus_domain"):
            print(f"  Consensus Domain: {status['consensus_domain']}")
        classifications = status.get("classifications", [])
        if classifications:
            print(f"  Votes:")
            for c in classifications:
                match = "✓" if c.get("matched_consensus") else "✗"
                print(f"    {c['classifier_addr'][:14]} | {c['domain_label']} | {match} | +{c.get('reward_earned', 0)}")
    elif args.address:
        entries = db.get_buffer_entries_by_submitter(address)
        if not entries:
            print(f"No submissions from {address}.")
        else:
            print(f"Submissions from {address} ({len(entries)}):")
            for e in entries:
                print(f"  {e['id']} | {e['status']:12} | {e['method_name']} × {e['problem_title']}")
    else:
        stats = [("Pending", db.count_buffer_by_status("pending")),
                  ("Classified", db.count_buffer_by_status("classified")),
                  ("Disputed", db.count_buffer_by_status("disputed")),
                  ("Published", db.count_buffer_by_status("published"))]
        print("Buffer Zone Stats:")
        for label, count in stats:
            print(f"  {label}: {count}")


def cmd_buffer_stake(args):
    """Manage token staking."""
    from src.hub.leaderboard import LeaderboardDB
    from src.blockchain.contracts import SimulatedToken, StakingContract

    address = _get_user_address(args, "0xVIEWER")
    db = LeaderboardDB(args.db)
    token = SimulatedToken(db)
    staking = StakingContract(db, token)

    if args.action == "stake":
        sid = staking.stake(address, args.amount)
        if sid < 0:
            print(f"ERROR: Insufficient balance. Current: {token.balance_of(address)} IDEA", file=sys.stderr)
            sys.exit(1)
        print(f"Staked {args.amount} IDEA (stake ID: {sid})")
        print(f"  Balance: {token.balance_of(address)} IDEA")
        print(f"  Total staked: {staking.get_active_stake(address)} IDEA")
    else:
        stakes = db.get_active_stakes(address)
        if not stakes:
            print(f"No active stakes for {address}.")
            return
        total_released = 0
        for s in stakes:
            if staking.release_stake(s["id"]):
                total_released += s["amount"]
        if total_released > 0:
            print(f"Released {total_released} IDEA from staking.")
            print(f"  Balance: {token.balance_of(address)} IDEA")
        else:
            print("No stakes to release.")


def cmd_buffer_tokens(args):
    """View token balance and classifier stats."""
    from src.hub.leaderboard import LeaderboardDB
    from src.blockchain.contracts import SimulatedToken, StakingContract
    from src.blockchain.buffer import BufferZone

    address = _get_user_address(args, "0xVIEWER")
    db = LeaderboardDB(args.db)
    token = SimulatedToken(db)
    staking = StakingContract(db, token)
    buffer_zone = BufferZone(db, token, staking)

    stats = buffer_zone.get_classifier_stats(address)
    print(f"Account: {address}")
    print(f"  Token: {token.name} ({token.symbol})")
    print(f"  Balance: {stats['balance']} {token.symbol}")
    print(f"  Staked: {stats['staked']} {token.symbol}")
    print(f"  Total Earned: {stats['total_earned']} {token.symbol}")
    print(f"  Total Slashed: {stats['total_slashed']} {token.symbol}")
    print(f"  Classifications: {stats['total_classifications']} ({stats['correct_classifications']} correct)")
    print(f"  Streak: {stats['consecutive_correct']}")


def cmd_pay_view(args):
    """Pay to view an AI analysis."""
    from src.hub.leaderboard import LeaderboardDB
    from src.blockchain.contracts import SimulatedToken
    from src.hub.token_layer import TokenGate

    address = _get_user_address(args, "0xVIEWER")
    db = LeaderboardDB(args.db)
    token = SimulatedToken(db)
    tg = TokenGate(db, token)

    result = tg.pay_for_view(address, args.combo_id)
    if not result.get("ok"):
        print(f"ERROR: {result.get('error', 'pay failed')}", file=sys.stderr)
        sys.exit(1)
    bal = token.balance_of(address)
    print(f"Payment: {TokenGate.VIEW_FEE_N} IDEA")
    print(f"  Status: {result.get('status', 'paid')}")
    print(f"  Combo: {args.combo_id}")
    print(f"  Remaining Balance: {bal} IDEA")


def cmd_pay_leaderboard(args):
    """Pay to unlock a leaderboard for 24h."""
    from src.hub.leaderboard import LeaderboardDB
    from src.blockchain.contracts import SimulatedToken
    from src.hub.token_layer import TokenGate

    address = _get_user_address(args, "0xVIEWER")
    db = LeaderboardDB(args.db)
    token = SimulatedToken(db)
    tg = TokenGate(db, token)

    board_name = f"{args.dimension}_{args.domain}"
    result = tg.pay_for_leaderboard(address, board_name)
    if not result.get("ok"):
        print(f"ERROR: {result.get('error', 'pay failed')}", file=sys.stderr)
        sys.exit(1)
    bal = token.balance_of(address)
    print(f"Payment: {TokenGate.LEADERBOARD_FEE_P} IDEA")
    print(f"  Board: {board_name}")
    print(f"  Status: {result.get('status', 'unlocked')}")
    print(f"  Duration: 24 hours")
    print(f"  Remaining Balance: {bal} IDEA")


def cmd_pay_draw(args):
    """Pay for a random draw."""
    from src.hub.leaderboard import LeaderboardDB
    from src.blockchain.contracts import SimulatedToken
    from src.hub.token_layer import TokenGate

    address = _get_user_address(args, "0xVIEWER")
    db = LeaderboardDB(args.db)
    token = SimulatedToken(db)
    tg = TokenGate(db, token)

    result = tg.pay_for_random_draw(address)
    if not result.get("ok"):
        print(f"ERROR: {result.get('error', 'pay failed')}", file=sys.stderr)
        sys.exit(1)
    bal = token.balance_of(address)
    print(f"Payment: {TokenGate.DRAW_FEE_Q} IDEA")
    print(f"  Status: {result.get('status', 'paid')}")
    print(f"  Remaining Balance: {bal} IDEA")

    # If a draw was also requested, run it now
    if args.dimension or args.domain:
        from src.engine.models import EvalDimension, Domain
        dim = EvalDimension(args.dimension) if args.dimension else None
        dom = Domain(args.domain) if args.domain else None
        draw = db.random_draw(dimension=dim, domain=dom,
                             draw_count=args.count, viewer_addr=address)
        print(f"\nRandom draw from {draw.board_name} board ({draw.total_in_board} available):")
        for e in draw.entries:
            print(f"  [{e.best_dimension}={e.best_score:.1f}] {e.method_name} × {e.problem_title}")


def cmd_token_balance(args):
    """Check token balance and viewer summary."""
    from src.hub.leaderboard import LeaderboardDB
    from src.blockchain.contracts import SimulatedToken
    from src.hub.token_layer import TokenGate

    address = _get_user_address(args, "0xVIEWER")
    db = LeaderboardDB(args.db)
    token = SimulatedToken(db)
    tg = TokenGate(db, token)

    summary = tg.get_viewer_summary(address)
    print(f"Account: {address}")
    print(f"  Token: {token.name} ({token.symbol})")
    print(f"  Balance: {summary['balance']} {token.symbol}")
    print(f"  Staked: {summary['staked']} {token.symbol}")
    print(f"  Total Earned: {summary['total_earned']} {token.symbol}")
    print(f"  Total Slashed: {summary['total_slashed']} {token.symbol}")
    print(f"  Total Spent: {summary['total_spent']} {token.symbol}")
    print(f"  Payments: {summary['total_payments']}")


def main():
    parser = argparse.ArgumentParser(description="Idea Mining Network CLI")
    sub = parser.add_subparsers(dest="command")

    p_mine = sub.add_parser("mine", help="Generate method×problem combinations (requires API key)")
    p_mine.add_argument("--address", default=None, help="Miner address (reads from config if not set)")
    p_mine.add_argument("--block-height", type=int, default=1, help="Block height for seed")
    p_mine.add_argument("--nonce", type=int, default=0, help="Nonce")
    p_mine.add_argument("--batch", type=int, default=10, help="Batch size")
    p_mine.add_argument("--db", default="data/leaderboard.db", help="Leaderboard database path")
    p_mine.add_argument("--threshold", type=float, default=8.0, help="Score threshold for 'high' dimensions")
    p_mine.add_argument("--model", default=None, help="Override model name (default: gpt-4o)")
    p_mine.add_argument("--api-base", default=None, help="Override API base URL")
    p_mine.add_argument("--parallel", type=int, default=1, help="Parallel API workers (default: 1, sequential)")
    p_mine.add_argument("--methods", default=None, help="Custom methods JSON file path")
    p_mine.add_argument("--problems", default=None, help="Custom problems JSON file path")
    p_mine.add_argument("--methods-collection", default=None, help="Load methods from a named collection in the DB")
    p_mine.add_argument("--problems-collection", default=None, help="Load problems from a named collection in the DB")
    p_mine.add_argument("--method-step", type=int, default=0, help="Method stepping (0=auto-tune based on matrix size)")
    p_mine.add_argument("--problem-step", type=int, default=0, help="Problem stepping (0=auto-tune based on matrix size)")
    p_mine.add_argument("--problem-offset", type=int, default=0, help="Base offset into shuffled problem list (0=auto)")
    p_mine.add_argument("--max-attempts", type=int, default=0, help="Max attempts multiplier (0=auto-tune based on matrix size)")

    p_top = sub.add_parser("top", help="Show top-N leaderboard")
    p_top.add_argument("--dimension", default=None, help="Filter by dimension (elegance, weirdness, etc.)")
    p_top.add_argument("--domain", default=None, help="Filter by problem domain")
    p_top.add_argument("--level", default=None, help="Filter by method level (1-4)")
    p_top.add_argument("--limit", type=int, default=20)
    p_top.add_argument("--db", default="data/leaderboard.db")

    p_search = sub.add_parser("search", help="Search combinations")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--dimension", default=None)
    p_search.add_argument("--limit", type=int, default=20)
    p_search.add_argument("--db", default="data/leaderboard.db")

    p_random = sub.add_parser("random", help="Random draw from leaderboard")
    p_random.add_argument("--dimension", default=None)
    p_random.add_argument("--domain", default=None)
    p_random.add_argument("--count", type=int, default=10)
    p_random.add_argument("--address", default=None, help="Viewer address (reads from config if not set)")
    p_random.add_argument("--db", default="data/leaderboard.db")

    p_hub = sub.add_parser("hub", help="Start a P2P hub server")
    p_hub.add_argument("--port", type=int, default=8765, help="HTTP port (default 8765)")
    p_hub.add_argument("--bootstrap", action="append", default=None,
                       help="Bootstrap peer address (host:port), repeatable")
    p_hub.add_argument("--discovery-url", action="append", default=None, dest="discovery_urls",
                       help="Discovery server URL (http://host:port), repeatable")
    p_hub.add_argument("--db", default="data/leaderboard.db", help="SQLite database path")
    p_hub.add_argument("--gossip-interval", type=float, default=30.0,
                       help="Gossip interval in seconds")
    p_hub.add_argument("--peer-timeout", type=float, default=300.0,
                       help="Peer timeout in seconds")
    p_hub.add_argument("--max-peers", type=int, default=50, help="Maximum peers")
    p_hub.add_argument("--identity", default=None,
                       help="Path to ed25519 identity key file for signed announcements")

    p_web = sub.add_parser("web", help="Start a hub with Web UI")
    p_web.add_argument("--port", type=int, default=8765, help="HTTP port (default 8765)")
    p_web.add_argument("--bootstrap", action="append", default=None,
                       help="Bootstrap peer address (host:port), repeatable")
    p_web.add_argument("--discovery-url", action="append", default=None, dest="discovery_urls",
                       help="Discovery server URL (http://host:port), repeatable")
    p_web.add_argument("--db", default="data/leaderboard.db", help="SQLite database path")
    p_web.add_argument("--gossip-interval", type=float, default=30.0,
                       help="Gossip interval in seconds")
    p_web.add_argument("--peer-timeout", type=float, default=300.0,
                       help="Peer timeout in seconds")
    p_web.add_argument("--max-peers", type=int, default=50, help="Maximum peers")
    p_web.add_argument("--identity", default=None,
                       help="Path to ed25519 identity key file for signed announcements")

    p_keygen = sub.add_parser("keygen", help="Generate an ed25519 identity key pair")
    p_keygen.add_argument("--output", "-o", default="identity.key",
                          help="Output path for the private key file")
    p_keygen.add_argument("--force", "-f", action="store_true",
                          help="Overwrite existing file")
    p_keygen.add_argument("--set-identity", action="store_true",
                          help="After keygen, set derived address as HAMMERWORLD_ADDRESS in config")

    p_identity = sub.add_parser("identity", help="Show or set your identity address")
    p_identity.add_argument("--set", dest="set_address", default=None,
                            help="Set address (e.g. '0xABC123...'). Omit to show current.")

    p_smethod = sub.add_parser("submit-method", help="Submit a new method to the matrix")
    p_smethod.add_argument("--name", required=True, help="Method name")
    p_smethod.add_argument("--domain", required=True, help="Method domain (e.g. physics, biology)")
    p_smethod.add_argument("--level", type=int, required=True, choices=[1, 2, 3, 4], help="Method level (1-4)")
    p_smethod.add_argument("--description", required=True, help="Method description")
    p_smethod.add_argument("--examples", default="", help="Comma-separated examples")
    p_smethod.add_argument("--prerequisites", default="", help="Comma-separated prerequisite method IDs")
    p_smethod.add_argument("--compatible-with", default="", help="Comma-separated compatible method IDs")
    p_smethod.add_argument("--submitter", default="cli_user", help="Submitter address/name")
    p_smethod.add_argument("--db", default="data/leaderboard.db", help="Database path")

    p_sproblem = sub.add_parser("submit-problem", help="Submit a new problem to the matrix")
    p_sproblem.add_argument("--title", required=True, help="Problem title")
    p_sproblem.add_argument("--domain", required=True, help="Problem domain (e.g. energy, medicine)")
    p_sproblem.add_argument("--description", required=True, help="Problem description")
    p_sproblem.add_argument("--constraints", default="", help="Comma-separated constraint types")
    p_sproblem.add_argument("--maturity", type=int, default=1, choices=[1, 2, 3, 4], help="Problem maturity (1-4)")
    p_sproblem.add_argument("--submitter", default="cli_user", help="Submitter address/name")
    p_sproblem.add_argument("--db", default="data/leaderboard.db", help="Database path")

    p_triz_analyze = sub.add_parser("triz-analyze", help="Run TRIZ standardization on a problem description")
    p_triz_analyze.add_argument("--description", required=True, help="Problem description to analyze")
    p_triz_analyze.add_argument("--domain", default="medicine", help="Problem domain (default: medicine)")

    p_math_mine = sub.add_parser("math-mine", help="Generate seed analysis to unlock a math problem zone")
    p_math_mine.add_argument("--problem-id", type=int, required=True, help="Math problem ID")
    p_math_mine.add_argument("--methods-collection", required=True, help="Math method collection name")
    p_math_mine.add_argument("--address", default=None, help="Miner address (reads from config if not set)")
    p_math_mine.add_argument("--block-height", type=int, default=1)
    p_math_mine.add_argument("--nonce", type=int, default=0)
    p_math_mine.add_argument("--batch", type=int, default=3, help="Number of combos to generate")
    p_math_mine.add_argument("--db", default="data/leaderboard.db")
    p_math_mine.add_argument("--threshold", type=float, default=8.0)
    p_math_mine.add_argument("--model", default=None)
    p_math_mine.add_argument("--api-base", default=None)
    p_math_mine.add_argument("--parallel", type=int, default=1)
    p_math_mine.add_argument("--method-step", type=int, default=0)
    p_math_mine.add_argument("--max-attempts", type=int, default=0)

    p_math_submit = sub.add_parser("math-submit", help="Submit a math solution for a (problem, method) zone")
    p_math_submit.add_argument("--problem-id", type=int, required=True)
    p_math_submit.add_argument("--method-collection-id", type=int, required=True)
    p_math_submit.add_argument("--steps-json", required=True, help="JSON array of solution steps")
    p_math_submit.add_argument("--parent-id", type=int, default=None, help="Solution ID to fork from")
    p_math_submit.add_argument("--address", default=None, help="Solver address (reads from config if not set)")
    p_math_submit.add_argument("--db", default="data/leaderboard.db")

    p_math_tree_add = sub.add_parser("math-tree-add", help="Add a child node in the MCTS tree")
    p_math_tree_add.add_argument("--parent-node-id", type=int, required=True, help="Parent node ID")
    p_math_tree_add.add_argument("--action", required=True, help="Action label (method/operation name)")
    p_math_tree_add.add_argument("--content", required=True, help="Mathematical content of the new node")
    p_math_tree_add.add_argument("--type", choices=["normal", "terminal_success", "terminal_failure", "pruned"], default="normal")
    p_math_tree_add.add_argument("--reward", type=float, default=None, help="Reward (1.0 success, 0.0 failure)")
    p_math_tree_add.add_argument("--description", default="", help="Edge description")
    p_math_tree_add.add_argument("--address", default=None, help="Explorer address (reads from config if not set)")
    p_math_tree_add.add_argument("--db", default="data/leaderboard.db")

    p_math_tree_status = sub.add_parser("math-tree-status", help="Show MCTS tree stats")
    p_math_tree_status.add_argument("--problem-id", type=int, required=True)
    p_math_tree_status.add_argument("--method-collection-id", type=int, required=True)
    p_math_tree_status.add_argument("--db", default="data/leaderboard.db")

    p_buf_submit = sub.add_parser("buffer-submit", help="Submit an AI analysis to the blockchain buffer zone")
    p_buf_submit.add_argument("--combo-id", required=True, help="Combination ID")
    p_buf_submit.add_argument("--method-id", default="", help="Method ID")
    p_buf_submit.add_argument("--method-name", default="", help="Method name")
    p_buf_submit.add_argument("--problem-id", default="", help="Problem ID")
    p_buf_submit.add_argument("--problem-title", default="", help="Problem title")
    p_buf_submit.add_argument("--analysis-json", default="{}", help="Analysis JSON string")
    p_buf_submit.add_argument("--analysis-file", default=None, help="Read analysis JSON from file")
    p_buf_submit.add_argument("--analysis-text", default="", help="Analysis summary text")
    p_buf_submit.add_argument("--address", default=None, help="Submitter address (reads from config if not set)")
    p_buf_submit.add_argument("--db", default="data/leaderboard.db")

    p_buf_classify = sub.add_parser("buffer-classify", help="Classify a pending buffer submission")
    p_buf_classify.add_argument("--submission-id", required=True, help="Buffer submission ID to classify")
    p_buf_classify.add_argument("--domain", required=True, help="Domain label (e.g. medicine, energy)")
    p_buf_classify.add_argument("--nsfw", action="store_true", help="Mark as NSFW")
    p_buf_classify.add_argument("--spam", action="store_true", help="Mark as spam / AI hallucination")
    p_buf_classify.add_argument("--notes", default="", help="Optional classification notes")
    p_buf_classify.add_argument("--address", default=None, help="Classifier address (reads from config if not set)")
    p_buf_classify.add_argument("--db", default="data/leaderboard.db")

    p_buf_status = sub.add_parser("buffer-status", help="Check submission status in buffer zone")
    p_buf_status.add_argument("--submission-id", default=None, help="Specific submission ID to check")
    p_buf_status.add_argument("--address", default=None, help="Show submissions from this address")
    p_buf_status.add_argument("--db", default="data/leaderboard.db")

    p_buf_stake = sub.add_parser("buffer-stake", help="Manage token staking")
    p_buf_stake.add_argument("--address", default=None, help="Staker address (reads from config if not set)")
    p_buf_stake.add_argument("--amount", type=int, default=100, help="Amount to stake/unstake")
    p_buf_stake.add_argument("--action", choices=["stake", "unstake"], default="stake")
    p_buf_stake.add_argument("--db", default="data/leaderboard.db")

    p_buf_tokens = sub.add_parser("buffer-tokens", help="View token balance and classifier stats")
    p_buf_tokens.add_argument("--address", default=None, help="Address to query (reads from config if not set)")
    p_buf_tokens.add_argument("--db", default="data/leaderboard.db")

    p_pay_view = sub.add_parser("pay-view", help="Pay IDEA tokens to view an AI analysis")
    p_pay_view.add_argument("--combo-id", required=True, help="Combo ID to view")
    p_pay_view.add_argument("--address", default=None, help="Viewer address (reads from config if not set)")
    p_pay_view.add_argument("--db", default="data/leaderboard.db")

    p_pay_leaderboard = sub.add_parser("pay-leaderboard", help="Pay IDEA tokens to unlock a leaderboard for 24h")
    p_pay_leaderboard.add_argument("--dimension", default="elegance", help="Leaderboard dimension (default: elegance)")
    p_pay_leaderboard.add_argument("--domain", default="medicine", help="Leaderboard domain (default: medicine)")
    p_pay_leaderboard.add_argument("--address", default=None, help="Viewer address (reads from config if not set)")
    p_pay_leaderboard.add_argument("--db", default="data/leaderboard.db")

    p_pay_draw = sub.add_parser("pay-draw", help="Pay IDEA tokens for a random draw")
    p_pay_draw.add_argument("--dimension", default=None, help="Optional dimension filter")
    p_pay_draw.add_argument("--domain", default=None, help="Optional domain filter")
    p_pay_draw.add_argument("--count", type=int, default=10, help="Number of entries to draw (default: 10)")
    p_pay_draw.add_argument("--address", default=None, help="Viewer address (reads from config if not set)")
    p_pay_draw.add_argument("--db", default="data/leaderboard.db")

    p_token_balance = sub.add_parser("token-balance", help="Check token balance and viewer summary")
    p_token_balance.add_argument("--address", default=None, help="Address to query (reads from config if not set)")
    p_token_balance.add_argument("--db", default="data/leaderboard.db")

    args = parser.parse_args()
    if args.command == "mine":
        cmd_mine(args)
    elif args.command == "top":
        cmd_top(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "random":
        cmd_random(args)
    elif args.command == "hub":
        cmd_hub(args)
    elif args.command == "keygen":
        cmd_keygen(args)
    elif args.command == "identity":
        cmd_identity(args)
    elif args.command == "web":
        args.web = True
        cmd_hub(args)
    elif args.command == "submit-method":
        cmd_submit_method(args)
    elif args.command == "submit-problem":
        cmd_submit_problem(args)
    elif args.command == "triz-analyze":
        cmd_triz_analyze(args)
    elif args.command == "math-mine":
        cmd_math_mine(args)
    elif args.command == "math-submit":
        cmd_math_submit(args)
    elif args.command == "math-tree-add":
        cmd_math_tree_add(args)
    elif args.command == "math-tree-status":
        cmd_math_tree_status(args)
    elif args.command == "buffer-submit":
        cmd_buffer_submit(args)
    elif args.command == "buffer-classify":
        cmd_buffer_classify(args)
    elif args.command == "buffer-status":
        cmd_buffer_status(args)
    elif args.command == "buffer-stake":
        cmd_buffer_stake(args)
    elif args.command == "buffer-tokens":
        cmd_buffer_tokens(args)
    elif args.command == "pay-view":
        cmd_pay_view(args)
    elif args.command == "pay-leaderboard":
        cmd_pay_leaderboard(args)
    elif args.command == "pay-draw":
        cmd_pay_draw(args)
    elif args.command == "token-balance":
        cmd_token_balance(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
