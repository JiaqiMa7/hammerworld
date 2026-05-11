"""CLI tools for the Idea Mining Network."""

import argparse
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def cmd_mine(args):
    """Run the mining combination engine."""
    from src.engine.loader import load_methods, load_problems
    from src.engine.combiner import generate_combinations

    methods = load_methods()
    problems = load_problems()
    combos = generate_combinations(
        methods, problems,
        block_height=args.block_height,
        user_address=args.address,
        nonce=args.nonce,
        batch_size=args.batch,
    )
    print(f"Generated {len(combos)} combinations:")
    for c in combos:
        print(f"  [{c.id}] {c.method.name} × {c.problem.title}")


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
    result = db.random_draw(dimension=dim, domain=dom, draw_count=args.count, viewer_addr=args.address)

    print(f"Random draw from {result.board_name} board ({result.total_in_board} available):")
    for e in result.entries:
        print(f"  [{e.best_dimension}={e.best_score:.1f}] {e.method_name} × {e.problem_title}")


def cmd_hub(args):
    """Start a P2P hub server."""
    from src.hub.leaderboard import LeaderboardDB
    from src.hub.peer import PeerConfig
    from src.hub.server import HubServer

    db = LeaderboardDB(args.db)
    config = PeerConfig(
        port=args.port,
        bootstrap=args.bootstrap or [],
        gossip_interval=args.gossip_interval,
        peer_timeout=args.peer_timeout,
        max_peers=args.max_peers,
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


def main():
    parser = argparse.ArgumentParser(description="Idea Mining Network CLI")
    sub = parser.add_subparsers(dest="command")

    p_mine = sub.add_parser("mine", help="Generate method×problem combinations")
    p_mine.add_argument("--address", default="0xMINER", help="Miner address")
    p_mine.add_argument("--block-height", type=int, default=1, help="Block height for seed")
    p_mine.add_argument("--nonce", type=int, default=0, help="Nonce")
    p_mine.add_argument("--batch", type=int, default=10, help="Batch size")

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
    p_random.add_argument("--address", default="0xVIEWER")
    p_random.add_argument("--db", default="data/leaderboard.db")

    p_hub = sub.add_parser("hub", help="Start a P2P hub server")
    p_hub.add_argument("--port", type=int, default=8765, help="HTTP port (default 8765)")
    p_hub.add_argument("--bootstrap", action="append", default=None,
                       help="Bootstrap peer address (host:port), repeatable")
    p_hub.add_argument("--db", default="data/leaderboard.db", help="SQLite database path")
    p_hub.add_argument("--gossip-interval", type=float, default=30.0,
                       help="Gossip interval in seconds")
    p_hub.add_argument("--peer-timeout", type=float, default=300.0,
                       help="Peer timeout in seconds")
    p_hub.add_argument("--max-peers", type=int, default=50, help="Maximum peers")

    p_web = sub.add_parser("web", help="Start a hub with Web UI")
    p_web.add_argument("--port", type=int, default=8765, help="HTTP port (default 8765)")
    p_web.add_argument("--bootstrap", action="append", default=None,
                       help="Bootstrap peer address (host:port), repeatable")
    p_web.add_argument("--db", default="data/leaderboard.db", help="SQLite database path")
    p_web.add_argument("--gossip-interval", type=float, default=30.0,
                       help="Gossip interval in seconds")
    p_web.add_argument("--peer-timeout", type=float, default=300.0,
                       help="Peer timeout in seconds")
    p_web.add_argument("--max-peers", type=int, default=50, help="Maximum peers")

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
    elif args.command == "web":
        args.web = True
        cmd_hub(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
