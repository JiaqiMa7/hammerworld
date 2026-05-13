"""Local leaderboard with SQLite storage, ranking, search, and random draw."""
from __future__ import annotations

import json
import os
import random
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Optional

from src.engine.models import (
    Combination, EvalDimension, Domain, MethodLevel, AIAnalysis, EvalScore,
)


@dataclass
class LeaderboardEntry:
    """A ranked entry in the leaderboard."""
    rank: int
    combo_id: str
    method_name: str
    method_domain: str
    method_level: int
    problem_title: str
    problem_domain: str
    best_dimension: str
    best_score: float
    elegance: float = 0
    weirdness: float = 0
    human_feasibility: float = 0
    ai_feasibility: float = 0
    novelty: float = 0
    analogy_distance: float = 0
    scaling_potential: float = 0
    side_effects: float = 0
    miner_address: str = ""
    created_at: float = 0.0
    analysis_text: str = ""


@dataclass
class RandomDrawResult:
    """Result of a random draw from a leaderboard."""
    entries: list[LeaderboardEntry]
    board_name: str
    total_in_board: int
    draw_seed: int


class LeaderboardDB:
    """SQLite-backed leaderboard storage.

    Schema:
        combinations: combo_id, method_name, method_domain, method_level,
                      problem_title, problem_domain, best_dim, best_score,
                      elegance, weirdness, human_feas, ai_feas, novelty,
                      analogy_dist, scale_pot, side_eff,
                      miner_addr, created_at
        paid_views: viewer_addr, combo_id, paid_at
        user_draws: viewer_addr, board_name, drawn_combo_ids, draw_seed
    """

    def __init__(self, db_path: str = "data/leaderboard.db"):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self._persistent_conn = None  # Keep alive for :memory:
        # Each :memory: instance gets a unique URI so they don't share data
        if db_path == ":memory:":
            self._memory_uri = f"file:mem_{id(self):x}?mode=memory&cache=shared"
        else:
            self._memory_uri = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._memory_uri:
            conn = sqlite3.connect(self._memory_uri, uri=True)
        else:
            conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._connect()
        conn.executescript("""
                CREATE TABLE IF NOT EXISTS combinations (
                    combo_id TEXT PRIMARY KEY,
                    method_name TEXT NOT NULL,
                    method_domain TEXT NOT NULL,
                    method_level INTEGER NOT NULL,
                    problem_title TEXT NOT NULL,
                    problem_domain TEXT NOT NULL,
                    best_dim TEXT NOT NULL,
                    best_score REAL NOT NULL DEFAULT 0,
                    elegance REAL DEFAULT 0,
                    weirdness REAL DEFAULT 0,
                    human_feasibility REAL DEFAULT 0,
                    ai_feasibility REAL DEFAULT 0,
                    novelty REAL DEFAULT 0,
                    analogy_distance REAL DEFAULT 0,
                    scaling_potential REAL DEFAULT 0,
                    side_effects REAL DEFAULT 0,
                    miner_addr TEXT DEFAULT '',
                    created_at REAL DEFAULT 0,
                    analysis_text TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS paid_views (
                    viewer_addr TEXT NOT NULL,
                    combo_id TEXT NOT NULL,
                    paid_at REAL DEFAULT 0,
                    PRIMARY KEY (viewer_addr, combo_id)
                );
                CREATE TABLE IF NOT EXISTS user_draws (
                    viewer_addr TEXT NOT NULL,
                    board_name TEXT NOT NULL,
                    drawn_combo_ids TEXT NOT NULL,
                    draw_seed INTEGER NOT NULL,
                    drawn_at REAL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_best_dim ON combinations(best_dim);
                CREATE INDEX IF NOT EXISTS idx_best_score ON combinations(best_score DESC);
                CREATE INDEX IF NOT EXISTS idx_problem_domain ON combinations(problem_domain);
                CREATE INDEX IF NOT EXISTS idx_method_domain ON combinations(method_domain);
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    submitter TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    submitted_at REAL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS method_collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    category TEXT DEFAULT 'other',
                    creator TEXT DEFAULT '',
                    stars INTEGER DEFAULT 0,
                    import_count INTEGER DEFAULT 0,
                    methods_json TEXT NOT NULL,
                    created_at REAL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS problem_collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    category TEXT DEFAULT 'other',
                    creator TEXT DEFAULT '',
                    stars INTEGER DEFAULT 0,
                    import_count INTEGER DEFAULT 0,
                    problems_json TEXT NOT NULL,
                    created_at REAL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS collection_stars (
                    collection_type TEXT NOT NULL,
                    collection_id INTEGER NOT NULL,
                    starrer TEXT NOT NULL,
                    starred_at REAL DEFAULT 0,
                    PRIMARY KEY (collection_type, collection_id, starrer)
                );
                CREATE TABLE IF NOT EXISTS math_problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    category TEXT DEFAULT 'number_theory',
                    creator TEXT DEFAULT '',
                    status TEXT DEFAULT 'active',
                    created_at REAL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS math_solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id INTEGER NOT NULL,
                    method_collection_id INTEGER NOT NULL,
                    user_address TEXT DEFAULT '',
                    parent_solution_id INTEGER DEFAULT NULL,
                    steps_json TEXT NOT NULL,
                    max_correct_step INTEGER DEFAULT 0,
                    seed_combo_id TEXT DEFAULT '',
                    seed_analysis_json TEXT DEFAULT '',
                    created_at REAL DEFAULT 0,
                    updated_at REAL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS math_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id INTEGER NOT NULL,
                    method_collection_id INTEGER NOT NULL,
                    user_address TEXT NOT NULL,
                    combo_id TEXT NOT NULL,
                    analysis_json TEXT DEFAULT '',
                    created_at REAL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_math_solutions_lookup
                    ON math_solutions(problem_id, method_collection_id, max_correct_step DESC);
                CREATE INDEX IF NOT EXISTS idx_math_access_check
                    ON math_access_log(problem_id, method_collection_id, user_address);

                CREATE TABLE IF NOT EXISTS math_tree_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id INTEGER NOT NULL,
                    method_collection_id INTEGER NOT NULL,
                    user_address TEXT DEFAULT '',
                    content TEXT NOT NULL,
                    node_type TEXT NOT NULL DEFAULT 'normal',
                    q_value REAL NOT NULL DEFAULT 0.0,
                    visit_count INTEGER NOT NULL DEFAULT 0,
                    reward REAL DEFAULT 0.0,
                    is_root INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT DEFAULT '{}',
                    created_at REAL DEFAULT 0,
                    updated_at REAL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_tree_nodes_problem
                    ON math_tree_nodes(problem_id, method_collection_id);
                CREATE INDEX IF NOT EXISTS idx_tree_nodes_root
                    ON math_tree_nodes(problem_id, method_collection_id, is_root);

                CREATE TABLE IF NOT EXISTS math_tree_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_node_id INTEGER NOT NULL,
                    child_node_id INTEGER NOT NULL,
                    action_label TEXT NOT NULL,
                    action_description TEXT DEFAULT '',
                    created_at REAL DEFAULT 0,
                    FOREIGN KEY (parent_node_id) REFERENCES math_tree_nodes(id),
                    FOREIGN KEY (child_node_id) REFERENCES math_tree_nodes(id)
                );
                CREATE INDEX IF NOT EXISTS idx_tree_edges_parent
                    ON math_tree_edges(parent_node_id);
                CREATE INDEX IF NOT EXISTS idx_tree_edges_child
                    ON math_tree_edges(child_node_id);

                CREATE TABLE IF NOT EXISTS _schema_version (
                    version INTEGER PRIMARY KEY
                );
                INSERT OR IGNORE INTO _schema_version (version) VALUES (0);

                CREATE TABLE IF NOT EXISTS buffer_submissions (
                    id TEXT PRIMARY KEY,
                    combo_id TEXT NOT NULL,
                    method_id TEXT NOT NULL,
                    method_name TEXT DEFAULT '',
                    problem_id TEXT NOT NULL,
                    problem_title TEXT DEFAULT '',
                    submitter TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    analysis_json TEXT NOT NULL,
                    analysis_text TEXT DEFAULT '',
                    domain_label TEXT DEFAULT '',
                    nsfw INTEGER DEFAULT 0,
                    spam INTEGER DEFAULT 0,
                    classifier_count INTEGER DEFAULT 0,
                    consensus_domain TEXT DEFAULT '',
                    consensus_nsfw INTEGER DEFAULT 0,
                    consensus_spam INTEGER DEFAULT 0,
                    staked_amount INTEGER DEFAULT 0,
                    created_at REAL DEFAULT 0,
                    classified_at REAL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_buffer_status ON buffer_submissions(status);
                CREATE INDEX IF NOT EXISTS idx_buffer_submitter ON buffer_submissions(submitter);

                CREATE TABLE IF NOT EXISTS buffer_classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id TEXT NOT NULL,
                    classifier_addr TEXT NOT NULL,
                    domain_label TEXT NOT NULL,
                    is_nsfw INTEGER DEFAULT 0,
                    is_spam INTEGER DEFAULT 0,
                    notes TEXT DEFAULT '',
                    matched_consensus INTEGER DEFAULT 0,
                    reward_earned INTEGER DEFAULT 0,
                    created_at REAL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_class_submission ON buffer_classifications(submission_id);
                CREATE INDEX IF NOT EXISTS idx_class_classifier ON buffer_classifications(classifier_addr);

                CREATE TABLE IF NOT EXISTS token_accounts (
                    address TEXT PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    staked INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    total_slashed INTEGER DEFAULT 0,
                    consecutive_correct INTEGER DEFAULT 0,
                    total_classifications INTEGER DEFAULT 0,
                    correct_classifications INTEGER DEFAULT 0,
                    last_faucet_at REAL DEFAULT 0,
                    faucet_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS stake_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    status TEXT DEFAULT 'active',
                    submission_id TEXT DEFAULT '',
                    created_at REAL DEFAULT 0,
                    released_at REAL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_stake_address ON stake_records(address);
                CREATE INDEX IF NOT EXISTS idx_stake_status ON stake_records(status);
            """)
        # Migration: add analysis_text for existing databases
        try:
            conn.execute("ALTER TABLE combinations ADD COLUMN analysis_text TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists
        # Migration: token layer columns on paid_views
        for col, col_type in [("paid_amount", "INTEGER DEFAULT 0"),
                               ("analyzer_addr", "TEXT DEFAULT ''"),
                               ("protocol_addr", "TEXT DEFAULT ''")]:
            try:
                conn.execute(f"ALTER TABLE paid_views ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
        # Migration: leaderboard_access and viewer_ratings
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS leaderboard_access (
                viewer_addr TEXT NOT NULL,
                board_name TEXT NOT NULL,
                paid_at REAL DEFAULT 0,
                expires_at REAL DEFAULT 0,
                PRIMARY KEY (viewer_addr, board_name)
            );
            CREATE TABLE IF NOT EXISTS viewer_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                viewer_addr TEXT NOT NULL,
                combo_id TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                comment TEXT DEFAULT '',
                created_at REAL DEFAULT 0,
                UNIQUE(viewer_addr, combo_id)
            );
        """)
        # Migration: faucet tracking columns on token_accounts
        for col, col_type in [("last_faucet_at", "REAL DEFAULT 0"),
                               ("faucet_count", "INTEGER DEFAULT 0")]:
            try:
                conn.execute(f"ALTER TABLE token_accounts ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
        conn.commit()
        # Migration: convert math_solutions to tree nodes (schema v0 -> v1)
        self._migrate_math_to_tree(conn)
        conn.commit()
        if self.db_path == ":memory:":
            self._persistent_conn = conn
        else:
            conn.close()

    def insert(self, combo: Combination, miner_addr: str = "") -> LeaderboardEntry:
        """Insert or update a combination in the leaderboard."""
        if not combo.analyses:
            raise ValueError("Combination has no analyses")

        latest = combo.analyses[-1]
        scores_dict = {s.dimension.value: s.score for s in latest.scores}

        entry = LeaderboardEntry(
            rank=0,
            combo_id=combo.id,
            method_name=combo.method.name,
            method_domain=combo.method.domain,
            method_level=combo.method.level.value,
            problem_title=combo.problem.title,
            problem_domain=combo.problem.domain.value,
            best_dimension=combo.best_dimension.value if combo.best_dimension else "",
            best_score=combo.best_score or 0,
            elegance=scores_dict.get("elegance", 0),
            weirdness=scores_dict.get("weirdness", 0),
            human_feasibility=scores_dict.get("human_feasibility", 0),
            ai_feasibility=scores_dict.get("ai_feasibility", 0),
            novelty=scores_dict.get("novelty", 0),
            analogy_distance=scores_dict.get("analogy_distance", 0),
            scaling_potential=scores_dict.get("scaling_potential", 0),
            side_effects=scores_dict.get("side_effects", 0),
            miner_address=miner_addr,
            created_at=combo.created_at,
            analysis_text=latest.analysis_text,
        )

        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO combinations
                (combo_id, method_name, method_domain, method_level,
                 problem_title, problem_domain, best_dim, best_score,
                 elegance, weirdness, human_feasibility, ai_feasibility,
                 novelty, analogy_distance, scaling_potential, side_effects,
                 miner_addr, created_at, analysis_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.combo_id, entry.method_name, entry.method_domain,
                entry.method_level, entry.problem_title, entry.problem_domain,
                entry.best_dimension, entry.best_score,
                entry.elegance, entry.weirdness, entry.human_feasibility,
                entry.ai_feasibility, entry.novelty, entry.analogy_distance,
                entry.scaling_potential, entry.side_effects,
                entry.miner_address, entry.created_at,
                entry.analysis_text,
            ))

        return entry

    def insert_from_sync(self, entry: LeaderboardEntry) -> bool:
        """Insert or update an entry received from a remote peer. Returns True if new."""
        existing = self._get_by_id(entry.combo_id)
        if existing and existing.created_at >= entry.created_at:
            return False  # already have same or newer

        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO combinations
                (combo_id, method_name, method_domain, method_level,
                 problem_title, problem_domain, best_dim, best_score,
                 elegance, weirdness, human_feasibility, ai_feasibility,
                 novelty, analogy_distance, scaling_potential, side_effects,
                 miner_addr, created_at, analysis_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.combo_id, entry.method_name, entry.method_domain,
                entry.method_level, entry.problem_title, entry.problem_domain,
                entry.best_dimension, entry.best_score,
                entry.elegance, entry.weirdness, entry.human_feasibility,
                entry.ai_feasibility, entry.novelty, entry.analogy_distance,
                entry.scaling_potential, entry.side_effects,
                entry.miner_address, entry.created_at,
                entry.analysis_text,
            ))
        return True

    def _get_by_id(self, combo_id: str) -> Optional[LeaderboardEntry]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM combinations WHERE combo_id = ?", (combo_id,)
            ).fetchone()
            if row:
                return self._row_to_entry(0, row)
            return None

    def get_since(self, since: float, limit: int = 100) -> list[LeaderboardEntry]:
        """Get entries with created_at > since, for incremental sync."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM combinations WHERE created_at > ? ORDER BY created_at ASC LIMIT ?",
                (since, limit),
            ).fetchall()
        return [self._row_to_entry(0, row) for row in rows]

    def get_top(
        self,
        dimension: Optional[EvalDimension] = None,
        domain: Optional[Domain] = None,
        method_level: Optional[MethodLevel] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LeaderboardEntry]:
        """Get top-N entries by dimension, optionally filtered."""
        order_col = dimension.value if dimension else "best_score"
        where = []
        params: list = []

        if domain:
            where.append("problem_domain = ?")
            params.append(domain.value)
        if method_level:
            where.append("method_level = ?")
            params.append(method_level.value)

        where_clause = f"WHERE {' AND '.join(where)}" if where else ""

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM combinations {where_clause} "
                f"ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

        return [self._row_to_entry(i + 1 + offset, row) for i, row in enumerate(rows)]

    def random_draw(
        self,
        dimension: Optional[EvalDimension] = None,
        domain: Optional[Domain] = None,
        draw_count: int = 10,
        viewer_addr: str = "",
    ) -> RandomDrawResult:
        """Randomly draw N entries from a board, avoiding previously drawn ones."""
        board_name = f"{(dimension.value if dimension else 'best')}_{(domain.value if domain else 'all')}"
        order_col = dimension.value if dimension else "best_score"
        where = []
        params: list = []

        if domain:
            where.append("problem_domain = ?")
            params.append(domain.value)

        where_clause = f"WHERE {' AND '.join(where)}" if where else ""

        # Get previously drawn IDs for this viewer + board
        with self._connect() as conn:
            prev = conn.execute(
                "SELECT drawn_combo_ids FROM user_draws WHERE viewer_addr = ? AND board_name = ?",
                (viewer_addr, board_name),
            ).fetchall()

            previously_drawn: set[str] = set()
            for row in prev:
                previously_drawn.update(row[0].split(","))

            # Get all eligible entries
            rows = conn.execute(
                f"SELECT * FROM combinations {where_clause} ORDER BY {order_col} DESC",
                params,
            ).fetchall()

        # Filter out previously drawn
        available = [r for r in rows if r["combo_id"] not in previously_drawn]

        draw_seed = int(time.time() * 1000) % (2**31)
        rng = random.Random(draw_seed)

        count = min(draw_count, len(available))
        drawn = rng.sample(available, count) if count > 0 else []

        entries = [self._row_to_entry(0, r) for r in drawn]

        # Record this draw
        if viewer_addr:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO user_draws (viewer_addr, board_name, drawn_combo_ids, draw_seed, drawn_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (viewer_addr, board_name, ",".join(r["combo_id"] for r in drawn),
                     draw_seed, time.time()),
                )

        return RandomDrawResult(
            entries=entries,
            board_name=board_name,
            total_in_board=len(available),
            draw_seed=draw_seed,
        )

    def search(
        self,
        query: str,
        dimension: Optional[EvalDimension] = None,
        limit: int = 50,
    ) -> list[LeaderboardEntry]:
        """Search combinations by method name, problem title, or domain."""
        order_col = dimension.value if dimension else "best_score"
        like = f"%{query}%"

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM combinations WHERE "
                f"method_name LIKE ? OR problem_title LIKE ? OR "
                f"method_domain LIKE ? OR problem_domain LIKE ? OR "
                f"best_dim LIKE ? "
                f"ORDER BY {order_col} DESC LIMIT ?",
                (like, like, like, like, like, limit),
            ).fetchall()

        return [self._row_to_entry(i + 1, row) for i, row in enumerate(rows)]

    def has_paid(self, viewer_addr: str, combo_id: str) -> bool:
        """Check if a viewer has paid for an analysis."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM paid_views WHERE viewer_addr = ? AND combo_id = ?",
                (viewer_addr, combo_id),
            ).fetchone()
            return row is not None

    def record_payment(self, viewer_addr: str, combo_id: str,
                       paid_amount: int = 0, analyzer_addr: str = "",
                       protocol_addr: str = ""):
        """Record that a viewer paid to view an analysis."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO paid_views "
                "(viewer_addr, combo_id, paid_at, paid_amount, analyzer_addr, protocol_addr) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (viewer_addr, combo_id, time.time(), paid_amount,
                 analyzer_addr, protocol_addr),
            )

    def get_viewer_payments(self, viewer_addr: str) -> list[dict]:
        """Get all payment records for a viewer."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM paid_views WHERE viewer_addr = ? ORDER BY paid_at DESC",
                (viewer_addr,),
            ).fetchall()
            return [dict(r) for r in rows]

    def has_leaderboard_access(self, viewer_addr: str, board_name: str) -> bool:
        """Check if a viewer has active leaderboard access (24h window)."""
        now = time.time()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM leaderboard_access "
                "WHERE viewer_addr = ? AND board_name = ? AND expires_at > ?",
                (viewer_addr, board_name, now),
            ).fetchone()
            return row is not None

    def grant_leaderboard_access(self, viewer_addr: str, board_name: str,
                                 paid_amount: int = 0,
                                 duration_seconds: int = 86400) -> None:
        """Grant leaderboard access for 24h (or custom duration)."""
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO leaderboard_access "
                "(viewer_addr, board_name, paid_at, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (viewer_addr, board_name, now, now + duration_seconds),
            )

    def record_rating(self, viewer_addr: str, combo_id: str,
                      rating: int, comment: str = "") -> bool:
        """Record a viewer rating. Returns True if inserted, False if already rated."""
        now = time.time()
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO viewer_ratings (viewer_addr, combo_id, rating, comment, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (viewer_addr, combo_id, rating, comment, now),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def get_ratings_for_combo(self, combo_id: str) -> list[dict]:
        """Get all ratings for a combination."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM viewer_ratings WHERE combo_id = ? ORDER BY created_at DESC",
                (combo_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_avg_rating_for_combo(self, combo_id: str) -> float:
        """Get the average rating for a combination."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT AVG(rating) FROM viewer_ratings WHERE combo_id = ?",
                (combo_id,),
            ).fetchone()
            return round(row[0], 1) if row and row[0] else 0.0

    def total_entries(self, domain: Optional[Domain] = None) -> int:
        with self._connect() as conn:
            if domain:
                row = conn.execute(
                    "SELECT COUNT(*) FROM combinations WHERE problem_domain = ?",
                    (domain.value,),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM combinations").fetchone()
            return row[0] if row else 0

    @staticmethod
    def _row_to_entry(rank: int, row: sqlite3.Row) -> LeaderboardEntry:
        return LeaderboardEntry(
            rank=rank,
            combo_id=row["combo_id"],
            method_name=row["method_name"],
            method_domain=row["method_domain"],
            method_level=row["method_level"],
            problem_title=row["problem_title"],
            problem_domain=row["problem_domain"],
            best_dimension=row["best_dim"],
            best_score=row["best_score"],
            elegance=row["elegance"],
            weirdness=row["weirdness"],
            human_feasibility=row["human_feasibility"],
            ai_feasibility=row["ai_feasibility"],
            novelty=row["novelty"],
            analogy_distance=row["analogy_distance"],
            scaling_potential=row["scaling_potential"],
            side_effects=row["side_effects"],
            miner_address=row["miner_addr"],
            created_at=row["created_at"],
            analysis_text=row["analysis_text"] if "analysis_text" in row.keys() else "",
        )

    # ------------------------------------------------------------------
    # Community Submissions
    # ------------------------------------------------------------------

    def submit(self, stype: str, data: dict, submitter: str = "") -> int:
        """Submit a method or problem for review. Returns the submission id."""
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO submissions (type, data, submitter, status, submitted_at) "
                "VALUES (?, ?, ?, 'pending', ?)",
                (stype, json.dumps(data, ensure_ascii=False), submitter, time.time()),
            )
            return cur.lastrowid

    def get_pending_submissions(self, stype: str | None = None) -> list[dict]:
        """List pending submissions, optionally filtered by type."""
        with self._connect() as conn:
            if stype:
                rows = conn.execute(
                    "SELECT * FROM submissions WHERE status = 'pending' AND type = ? ORDER BY submitted_at DESC",
                    (stype,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM submissions WHERE status = 'pending' ORDER BY submitted_at DESC",
                ).fetchall()
        return [dict(r) for r in rows]

    def approve_submission(self, sub_id: int) -> dict | None:
        """Approve a pending submission and return its data."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM submissions WHERE id = ? AND status = 'pending'", (sub_id,)
            ).fetchone()
            if not row:
                return None
            conn.execute(
                "UPDATE submissions SET status = 'approved' WHERE id = ?", (sub_id,)
            )
            return json.loads(row["data"])

    def reject_submission(self, sub_id: int) -> bool:
        """Reject a pending submission. Returns True if found."""
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE submissions SET status = 'rejected' WHERE id = ? AND status = 'pending'",
                (sub_id,),
            )
            return cur.rowcount > 0

    def get_approved_methods(self) -> list[dict]:
        """Get all approved method submissions (for merging into matrix)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, data, submitter FROM submissions WHERE type = 'method' AND status = 'approved'"
            ).fetchall()
        return [{"id": r["id"], "submitter": r["submitter"], **json.loads(r["data"])} for r in rows]

    def get_approved_problems(self) -> list[dict]:
        """Get all approved problem submissions (for merging into matrix)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, data, submitter FROM submissions WHERE type = 'problem' AND status = 'approved'"
            ).fetchall()
        return [{"id": r["id"], "submitter": r["submitter"], **json.loads(r["data"])} for r in rows]

    def total_pending(self, stype: str | None = None) -> int:
        """Count pending submissions."""
        with self._connect() as conn:
            if stype:
                row = conn.execute(
                    "SELECT COUNT(*) FROM submissions WHERE status = 'pending' AND type = ?",
                    (stype,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM submissions WHERE status = 'pending'"
                ).fetchone()
            return row[0] if row else 0

    # ------------------------------------------------------------------
    # Matrix Marketplace — Collections
    # ------------------------------------------------------------------

    def create_collection(self, ctype: str, name: str, description: str,
                          category: str, creator: str, items: list[dict]) -> int:
        """Create a new method or problem collection. Returns the collection id."""
        items_json = json.dumps(items, ensure_ascii=False)
        table = "method_collections" if ctype == "method" else "problem_collections"
        col = "methods_json" if ctype == "method" else "problems_json"
        with self._connect() as conn:
            cur = conn.execute(
                f"INSERT INTO {table} (name, description, category, creator, {col}, created_at) "
                f"VALUES (?, ?, ?, ?, ?, ?)",
                (name, description, category, creator, items_json, time.time()),
            )
            return cur.lastrowid

    def get_collections(self, ctype: str, sort_by: str = "stars",
                        category: str | None = None) -> list[dict]:
        """List collections, optionally filtered and sorted."""
        table = "method_collections" if ctype == "method" else "problem_collections"
        sort_map = {
            "stars": "stars DESC",
            "imports": "import_count ASC",
            "newest": "created_at DESC",
        }
        order = sort_map.get(sort_by, "stars DESC")
        where = ""
        params: list = []
        if category:
            where = "WHERE category = ?"
            params.append(category)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {table} {where} ORDER BY {order}", params
            ).fetchall()
        return [dict(r) for r in rows]

    def get_collection(self, ctype: str, cid: int) -> dict | None:
        """Get a single collection by type and id."""
        table = "method_collections" if ctype == "method" else "problem_collections"
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {table} WHERE id = ?", (cid,)
            ).fetchone()
            return dict(row) if row else None

    def search_collections(self, ctype: str, query: str) -> list[dict]:
        """Search collections by name or description."""
        table = "method_collections" if ctype == "method" else "problem_collections"
        like = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE name LIKE ? OR description LIKE ? "
                f"ORDER BY stars DESC",
                (like, like),
            ).fetchall()
        return [dict(r) for r in rows]

    def toggle_star(self, ctype: str, cid: int, starrer: str) -> int:
        """Toggle a star on a collection. Returns the new star count."""
        table = "method_collections" if ctype == "method" else "problem_collections"
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM collection_stars WHERE collection_type = ? AND collection_id = ? AND starrer = ?",
                (ctype, cid, starrer),
            ).fetchone()
            if existing:
                conn.execute(
                    "DELETE FROM collection_stars WHERE collection_type = ? AND collection_id = ? AND starrer = ?",
                    (ctype, cid, starrer),
                )
                delta = -1
            else:
                conn.execute(
                    "INSERT INTO collection_stars (collection_type, collection_id, starrer, starred_at) "
                    "VALUES (?, ?, ?, ?)",
                    (ctype, cid, starrer, time.time()),
                )
                delta = 1
            conn.execute(
                f"UPDATE {table} SET stars = MAX(0, stars + ?) WHERE id = ?",
                (delta, cid),
            )
            row = conn.execute(
                f"SELECT stars FROM {table} WHERE id = ?", (cid,)
            ).fetchone()
            return row[0] if row else 0

    def increment_import(self, ctype: str, cid: int) -> None:
        """Increment the import count for a collection."""
        table = "method_collections" if ctype == "method" else "problem_collections"
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {table} SET import_count = import_count + 1 WHERE id = ?",
                (cid,),
            )

    def find_collection_by_name(self, ctype: str, name: str) -> dict | None:
        """Find a collection by exact name match."""
        table = "method_collections" if ctype == "method" else "problem_collections"
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {table} WHERE name = ?", (name,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Math Research Zone
    # ------------------------------------------------------------------

    def create_math_problem(self, title: str, description: str = "",
                            category: str = "number_theory",
                            creator: str = "") -> int:
        """Create a new math problem zone. Returns auto-increment id."""
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO math_problems (title, description, category, creator, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (title, description, category, creator, time.time()),
            )
            return cur.lastrowid

    def get_math_problems(self, status: str = "active") -> list[dict]:
        """List math problems, optionally filtered by status."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM math_problems WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_math_problem(self, pid: int) -> dict | None:
        """Get a single math problem by id."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM math_problems WHERE id = ?", (pid,)
            ).fetchone()
            return dict(row) if row else None

    def update_math_problem_status(self, pid: int, status: str) -> None:
        """Set the status of a math problem."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE math_problems SET status = ? WHERE id = ?",
                (status, pid),
            )

    def submit_math_solution(self, problem_id: int, method_collection_id: int,
                              user_address: str, steps: list[dict],
                              parent_id: int | None = None,
                              seed_combo_id: str = "",
                              seed_analysis: str = "") -> int:
        """Insert a new math solution. Returns id."""
        steps_json = json.dumps(steps, ensure_ascii=False)
        seed_analysis_json = seed_analysis
        max_step = self._calc_max_correct_step(steps)
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO math_solutions (problem_id, method_collection_id, user_address, "
                "parent_solution_id, steps_json, max_correct_step, seed_combo_id, "
                "seed_analysis_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (problem_id, method_collection_id, user_address, parent_id,
                 steps_json, max_step, seed_combo_id, seed_analysis_json, now, now),
            )
            return cur.lastrowid

    @staticmethod
    def _calc_max_correct_step(steps: list[dict]) -> int:
        """Count consecutive verified steps from step 1."""
        max_step = 0
        for s in sorted(steps, key=lambda x: x.get("step_num", 0)):
            if s.get("verified"):
                max_step = s["step_num"]
            else:
                break
        return max_step

    def get_math_solutions(self, problem_id: int, method_collection_id: int,
                            sort_by: str = "max_correct_step") -> list[dict]:
        """List solutions in a (problem, method) zone, sorted descending."""
        order = "max_correct_step DESC" if sort_by == "max_correct_step" else "created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM math_solutions WHERE problem_id = ? AND method_collection_id = ? "
                f"ORDER BY {order}",
                (problem_id, method_collection_id),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_math_solution(self, sid: int) -> dict | None:
        """Get a single math solution by id."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM math_solutions WHERE id = ?", (sid,)
            ).fetchone()
            return dict(row) if row else None

    def fork_math_solution(self, sid: int, user_address: str) -> int:
        """Copy an existing solution's steps as a new solution owned by user_address."""
        original = self.get_math_solution(sid)
        if not original:
            return 0
        try:
            steps = json.loads(original["steps_json"])
        except (json.JSONDecodeError, TypeError):
            steps = []
        return self.submit_math_solution(
            problem_id=original["problem_id"],
            method_collection_id=original["method_collection_id"],
            user_address=user_address,
            steps=steps,
            parent_id=sid,
            seed_combo_id=original.get("seed_combo_id", ""),
            seed_analysis=original.get("seed_analysis_json", ""),
        )

    def update_math_solution(self, sid: int, steps: list[dict],
                              max_correct_step: int | None = None) -> None:
        """Update steps and max_correct_step for an existing solution."""
        if max_correct_step is None:
            max_correct_step = self._calc_max_correct_step(steps)
        steps_json = json.dumps(steps, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "UPDATE math_solutions SET steps_json = ?, max_correct_step = ?, "
                "updated_at = ? WHERE id = ?",
                (steps_json, max_correct_step, time.time(), sid),
            )

    def check_math_access(self, problem_id: int, method_collection_id: int,
                           user_address: str) -> bool:
        """Returns True if user has unlocked this (problem, method) zone."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM math_access_log "
                "WHERE problem_id = ? AND method_collection_id = ? AND user_address = ?",
                (problem_id, method_collection_id, user_address),
            ).fetchone()
            return row[0] > 0 if row else False

    def grant_math_access(self, problem_id: int, method_collection_id: int,
                           user_address: str, combo_id: str,
                           analysis_json: str = "") -> None:
        """Record that a user has unlocked a (problem, method) zone."""
        now = time.time()
        with self._connect() as conn:
            # Upsert — replace if already exists
            conn.execute(
                "INSERT OR REPLACE INTO math_access_log "
                "(problem_id, method_collection_id, user_address, combo_id, "
                "analysis_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (problem_id, method_collection_id, user_address, combo_id,
                 analysis_json, now),
            )

    def get_math_access_log(self, problem_id: int, user_address: str) -> list[dict]:
        """List all access grants for a user on a problem (all methods)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM math_access_log WHERE problem_id = ? AND user_address = ? "
                "ORDER BY created_at DESC",
                (problem_id, user_address),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # MCTS Math Tree
    # ------------------------------------------------------------------

    def _migrate_math_to_tree(self, conn: sqlite3.Connection) -> None:
        """Migrate old math_solutions rows into tree nodes/edges (v0 -> v1)."""
        row = conn.execute(
            "SELECT version FROM _schema_version WHERE version >= 1"
        ).fetchone()
        if row:
            return  # already migrated

        rows = conn.execute("SELECT * FROM math_solutions ORDER BY id").fetchall()
        if not rows:
            conn.execute("UPDATE _schema_version SET version = 1")
            return

        for sol in rows:
            pid = sol["problem_id"]
            mid = sol["method_collection_id"]
            uaddr = sol["user_address"] or ""
            steps = json.loads(sol["steps_json"]) if sol["steps_json"] else []
            max_correct = sol["max_correct_step"] or 0
            now = sol["created_at"] or time.time()

            # Create root node from the problem title
            prob_row = conn.execute(
                "SELECT title FROM math_problems WHERE id = ?", (pid,)
            ).fetchone()
            root_content = prob_row["title"] if prob_row else f"Problem #{pid}"
            cur = conn.execute(
                "INSERT INTO math_tree_nodes (problem_id, method_collection_id, "
                "user_address, content, node_type, q_value, visit_count, is_root, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                (pid, mid, uaddr, root_content, "normal", 0.0, 0, now, now),
            )
            root_id = cur.lastrowid

            # Create nodes for each step, linked sequentially
            parent_id = root_id
            for i, step in enumerate(steps):
                step_num = step.get("step_num", i + 1)
                content = step.get("content", f"Step {step_num}")
                verified = step.get("verified", False)
                is_last = (i == len(steps) - 1)
                node_type = "terminal_success" if (is_last and verified and max_correct == len(steps)) else "normal"
                q_val = 1.0 if node_type == "terminal_success" else (max_correct / len(steps) if len(steps) > 0 else 0.0)
                visit = 1 if node_type == "terminal_success" else 0

                cur = conn.execute(
                    "INSERT INTO math_tree_nodes (problem_id, method_collection_id, "
                    "user_address, content, node_type, q_value, visit_count, reward, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (pid, mid, uaddr, content, node_type, q_val, visit,
                     1.0 if node_type == "terminal_success" else 0.0, now, now),
                )
                child_id = cur.lastrowid
                conn.execute(
                    "INSERT INTO math_tree_edges (parent_node_id, child_node_id, "
                    "action_label, created_at) VALUES (?, ?, ?, ?)",
                    (parent_id, child_id, f"step_{step_num}", now),
                )
                parent_id = child_id

        conn.execute("UPDATE _schema_version SET version = 1")
        conn.commit()

    # -- Node CRUD ----------------------------------------------------------------

    def create_tree_node(self, problem_id: int, method_collection_id: int,
                         user_address: str = "", content: str = "",
                         node_type: str = "normal", q_value: float = 0.0,
                         visit_count: int = 0, reward: float = 0.0,
                         is_root: int = 0, metadata_json: str = "{}") -> int:
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO math_tree_nodes (problem_id, method_collection_id, "
                "user_address, content, node_type, q_value, visit_count, reward, "
                "is_root, metadata_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (problem_id, method_collection_id, user_address, content,
                 node_type, q_value, visit_count, reward, is_root, metadata_json,
                 now, now),
            )
            return cur.lastrowid

    def get_tree_node(self, node_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM math_tree_nodes WHERE id = ?", (node_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_root_node(self, problem_id: int, method_collection_id: int) -> dict | None:
        """Get the root node for a zone, auto-creating one if missing."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM math_tree_nodes WHERE problem_id = ? "
                "AND method_collection_id = ? AND is_root = 1",
                (problem_id, method_collection_id),
            ).fetchone()
            if row:
                return dict(row)

            # Auto-create root from problem title
            prob = conn.execute(
                "SELECT title FROM math_problems WHERE id = ?", (problem_id,)
            ).fetchone()
            if not prob:
                return None
            now = time.time()
            cur = conn.execute(
                "INSERT INTO math_tree_nodes (problem_id, method_collection_id, "
                "content, node_type, is_root, created_at, updated_at) "
                "VALUES (?, ?, ?, 'normal', 1, ?, ?)",
                (problem_id, method_collection_id, prob["title"], now, now),
            )
            new_id = cur.lastrowid
        # re-fetch outside the with block so the INSERT is committed
        return self.get_tree_node(new_id)

    def get_tree_nodes_for_zone(self, problem_id: int,
                                method_collection_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM math_tree_nodes WHERE problem_id = ? "
                "AND method_collection_id = ? ORDER BY created_at",
                (problem_id, method_collection_id),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_tree_node(self, node_id: int, **kwargs) -> None:
        allowed = {"q_value", "visit_count", "node_type", "reward",
                   "metadata_json", "content"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return
        updates["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [node_id]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE math_tree_nodes SET {set_clause} WHERE id = ?", values,
            )

    def get_terminal_nodes(self, problem_id: int,
                           method_collection_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM math_tree_nodes WHERE problem_id = ? "
                "AND method_collection_id = ? AND node_type LIKE 'terminal_%'",
                (problem_id, method_collection_id),
            ).fetchall()
            return [dict(r) for r in rows]

    # -- Edge CRUD ---------------------------------------------------------------

    def create_tree_edge(self, parent_node_id: int, child_node_id: int,
                         action_label: str, action_description: str = "") -> int:
        now = time.time()
        with self._connect() as conn:
            # Prevent cycles: check parent is not a descendant of child
            if self._is_ancestor(parent_node_id, child_node_id):
                raise ValueError("Cannot create cycle in tree")
            cur = conn.execute(
                "INSERT INTO math_tree_edges (parent_node_id, child_node_id, "
                "action_label, action_description, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (parent_node_id, child_node_id, action_label, action_description, now),
            )
            return cur.lastrowid

    def _is_ancestor(self, node_id: int, candidate_ancestor_id: int) -> bool:
        """Check if candidate_ancestor_id is an ancestor of node_id."""
        with self._connect() as conn:
            current = node_id
            for _ in range(100):  # safety limit
                row = conn.execute(
                    "SELECT e.parent_node_id FROM math_tree_edges e "
                    "WHERE e.child_node_id = ?", (current,)
                ).fetchone()
                if not row:
                    return False
                if row["parent_node_id"] == candidate_ancestor_id:
                    return True
                current = row["parent_node_id"]
            return True  # too deep, assume cycle to be safe

    def get_children(self, node_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT e.id as edge_id, e.action_label, e.action_description, "
                "e.created_at as edge_created_at, "
                "n.id as child_id, n.content as child_content, "
                "n.node_type as child_node_type, n.q_value as child_q_value, "
                "n.visit_count as child_visit_count, n.reward as child_reward, "
                "n.user_address as child_user_address "
                "FROM math_tree_edges e JOIN math_tree_nodes n "
                "ON e.child_node_id = n.id "
                "WHERE e.parent_node_id = ? ORDER BY n.q_value DESC",
                (node_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def count_children(self, node_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM math_tree_edges "
                "WHERE parent_node_id = ?", (node_id,)
            ).fetchone()
            return row["cnt"] if row else 0

    def _get_parent_node(self, child_node_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT n.* FROM math_tree_nodes n JOIN math_tree_edges e "
                "ON n.id = e.parent_node_id WHERE e.child_node_id = ?",
                (child_node_id,),
            ).fetchone()
            return dict(row) if row else None

    def _get_path_to_root(self, node_id: int) -> list[int]:
        """Return list of node IDs from node_id up to (and including) root."""
        path = [node_id]
        with self._connect() as conn:
            current = node_id
            for _ in range(100):
                row = conn.execute(
                    "SELECT parent_node_id FROM math_tree_edges "
                    "WHERE child_node_id = ?", (current,)
                ).fetchone()
                if not row:
                    break
                path.append(row["parent_node_id"])
                current = row["parent_node_id"]
        return path

    # -- MCTS Operations ---------------------------------------------------------

    def backpropagate(self, node_id: int, reward: float) -> None:
        """Walk from node_id to root, updating Q and visit_count atomically."""
        path = self._get_path_to_root(node_id)
        with self._connect() as conn:
            for nid in path:
                conn.execute(
                    "UPDATE math_tree_nodes SET "
                    "q_value = (q_value * visit_count + ?) / (visit_count + 1), "
                    "visit_count = visit_count + 1, "
                    "updated_at = ? WHERE id = ?",
                    (reward, time.time(), nid),
                )
            # Also update the terminal node's reward
            conn.execute(
                "UPDATE math_tree_nodes SET reward = ?, "
                "node_type = CASE WHEN ? >= 0.5 THEN 'terminal_success' "
                "ELSE 'terminal_failure' END, "
                "updated_at = ? WHERE id = ?",
                (reward, reward, time.time(), node_id),
            )

    def get_uct_scores(self, node_id: int, exploration_constant: float = 1.414
                       ) -> list[dict]:
        """Compute UCT scores for all children of a node."""
        parent = self.get_tree_node(node_id)
        children = self.get_children(node_id)
        if not parent:
            return children
        parent_n = parent["visit_count"] or 1
        result = []
        for c in children:
            q = c["child_q_value"] or 0.0
            n = c["child_visit_count"] or 0
            if n == 0:
                uct = float('inf')  # unvisited nodes get priority
            else:
                import math
                uct = q + exploration_constant * math.sqrt(math.log(parent_n) / n)
            c["uct_score"] = uct
            result.append(c)
        result.sort(key=lambda x: x.get("uct_score", 0), reverse=True)
        return result

    def prune_node(self, node_id: int) -> None:
        """Mark a node as pruned and backpropagate neutral reward."""
        self.backpropagate(node_id, 0.0)
        with self._connect() as conn:
            conn.execute(
                "UPDATE math_tree_nodes SET node_type = 'pruned', "
                "updated_at = ? WHERE id = ?",
                (time.time(), node_id),
            )

    # -- Migration helper (public for testing) -----------------------------------

    def migrate_math_solutions_to_tree(self) -> int:
        """Public wrapper: run migration and return number of solutions migrated."""
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM math_solutions").fetchone()["c"]
            self._migrate_math_to_tree(conn)
            return count

    # ------------------------------------------------------------------
    # Blockchain Buffer Zone
    # ------------------------------------------------------------------

    def create_buffer_entry(self, sub_id: str, combo_id: str, method_id: str,
                            method_name: str, problem_id: str, problem_title: str,
                            submitter: str, analysis_json: str, analysis_text: str = "",
                            staked_amount: int = 0) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO buffer_submissions (id, combo_id, method_id, method_name, "
                "problem_id, problem_title, submitter, analysis_json, analysis_text, "
                "staked_amount, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sub_id, combo_id, method_id, method_name, problem_id, problem_title,
                 submitter, analysis_json, analysis_text, staked_amount, now),
            )

    def get_buffer_entry(self, sub_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM buffer_submissions WHERE id = ?", (sub_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_pending_buffer_entries(self, exclude_addr: str = "") -> list[dict]:
        with self._connect() as conn:
            if exclude_addr:
                rows = conn.execute(
                    "SELECT * FROM buffer_submissions WHERE status = 'pending' "
                    "AND submitter != ? ORDER BY created_at DESC", (exclude_addr,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM buffer_submissions WHERE status = 'pending' "
                    "ORDER BY created_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_buffer_entries_by_submitter(self, submitter: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM buffer_submissions WHERE submitter = ? "
                "ORDER BY created_at DESC", (submitter,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_buffer_entries_by_status(self, status: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM buffer_submissions WHERE status = ? "
                "ORDER BY created_at DESC", (status,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_buffer_entries(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM buffer_submissions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def update_buffer_status(self, sub_id: str, status: str, **kwargs) -> None:
        sets = ["status = ?"]
        params = [status]
        for key, val in kwargs.items():
            sets.append(f"{key} = ?")
            params.append(val)
        params.append(sub_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE buffer_submissions SET {', '.join(sets)} WHERE id = ?",
                params,
            )

    def count_buffer_by_status(self, status: str | None = None) -> int:
        with self._connect() as conn:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) FROM buffer_submissions WHERE status = ?", (status,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM buffer_submissions").fetchone()
            return row[0] if row else 0

    def classify_buffer_entry(self, submission_id: str, classifier_addr: str,
                              domain_label: str, is_nsfw: int, is_spam: int,
                              notes: str = "") -> int:
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO buffer_classifications (submission_id, classifier_addr, "
                "domain_label, is_nsfw, is_spam, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (submission_id, classifier_addr, domain_label, is_nsfw, is_spam, notes, now),
            )
            conn.execute(
                "UPDATE buffer_submissions SET classifier_count = classifier_count + 1 "
                "WHERE id = ?", (submission_id,)
            )
            return cur.lastrowid

    def get_classifications(self, submission_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM buffer_classifications WHERE submission_id = ? "
                "ORDER BY created_at", (submission_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_classifications_by_classifier(self, classifier_addr: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM buffer_classifications WHERE classifier_addr = ? "
                "ORDER BY created_at DESC", (classifier_addr,)
            ).fetchall()
            return [dict(r) for r in rows]

    def set_classification_consensus_match(self, class_id: int,
                                           matched: bool, reward: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE buffer_classifications SET matched_consensus = ?, reward_earned = ? "
                "WHERE id = ?", (1 if matched else 0, reward, class_id),
            )

    def get_or_create_account(self, address: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM token_accounts WHERE address = ?", (address,)
            ).fetchone()
            if row:
                return dict(row)
            conn.execute(
                "INSERT INTO token_accounts (address) VALUES (?)", (address,)
            )
            row2 = conn.execute(
                "SELECT * FROM token_accounts WHERE address = ?", (address,)
            ).fetchone()
            return dict(row2)

    def update_token_balance(self, address: str, delta: int) -> int:
        self.get_or_create_account(address)
        with self._connect() as conn:
            conn.execute(
                "UPDATE token_accounts SET balance = balance + ? WHERE address = ?",
                (delta, address),
            )
            row = conn.execute(
                "SELECT balance FROM token_accounts WHERE address = ?", (address,)
            ).fetchone()
            return row[0] if row else 0

    def update_token_staked(self, address: str, delta: int) -> int:
        self.get_or_create_account(address)
        with self._connect() as conn:
            conn.execute(
                "UPDATE token_accounts SET staked = staked + ? WHERE address = ?",
                (delta, address),
            )
            row = conn.execute(
                "SELECT staked FROM token_accounts WHERE address = ?", (address,)
            ).fetchone()
            return row[0] if row else 0

    def update_token_earned(self, address: str, delta: int) -> None:
        self.get_or_create_account(address)
        with self._connect() as conn:
            conn.execute(
                "UPDATE token_accounts SET total_earned = total_earned + ? WHERE address = ?",
                (delta, address),
            )

    def update_token_slashed(self, address: str, delta: int) -> None:
        self.get_or_create_account(address)
        with self._connect() as conn:
            conn.execute(
                "UPDATE token_accounts SET total_slashed = total_slashed + ? WHERE address = ?",
                (delta, address),
            )

    def update_classifier_stats(self, address: str, correct: bool) -> None:
        self.get_or_create_account(address)
        with self._connect() as conn:
            conn.execute(
                "UPDATE token_accounts SET total_classifications = total_classifications + 1 "
                "WHERE address = ?", (address,)
            )
            if correct:
                conn.execute(
                    "UPDATE token_accounts SET correct_classifications = correct_classifications + 1, "
                    "consecutive_correct = consecutive_correct + 1 WHERE address = ?", (address,)
                )
            else:
                conn.execute(
                    "UPDATE token_accounts SET consecutive_correct = 0 WHERE address = ?",
                    (address,)
                )

    def get_token_leaderboard(self, sort_by: str = "balance",
                               limit: int = 50) -> list[dict]:
        col = "balance" if sort_by == "balance" else "total_earned"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT address, balance, staked, total_earned, correct_classifications, "
                f"total_classifications, consecutive_correct FROM token_accounts "
                f"ORDER BY {col} DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def create_stake_record(self, address: str, amount: int,
                            submission_id: str = "") -> int:
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO stake_records (address, amount, submission_id, created_at) "
                "VALUES (?, ?, ?, ?)", (address, amount, submission_id, now),
            )
            return cur.lastrowid

    def get_active_stakes(self, address: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM stake_records WHERE address = ? AND status = 'active' "
                "ORDER BY created_at DESC", (address,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_stakes(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM stake_records ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def update_stake_status(self, stake_id: int, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE stake_records SET status = ?, released_at = ? WHERE id = ?",
                (status, time.time() if status != "active" else 0, stake_id),
            )

    def get_total_staked(self, address: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM stake_records "
                "WHERE address = ? AND status = 'active'", (address,)
            ).fetchone()
            return row[0] if row else 0
