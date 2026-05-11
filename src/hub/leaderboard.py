"""Local leaderboard with SQLite storage, ranking, search, and random draw."""
from __future__ import annotations

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
                    created_at REAL DEFAULT 0
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
            """)
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
        )

        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO combinations
                (combo_id, method_name, method_domain, method_level,
                 problem_title, problem_domain, best_dim, best_score,
                 elegance, weirdness, human_feasibility, ai_feasibility,
                 novelty, analogy_distance, scaling_potential, side_effects,
                 miner_addr, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.combo_id, entry.method_name, entry.method_domain,
                entry.method_level, entry.problem_title, entry.problem_domain,
                entry.best_dimension, entry.best_score,
                entry.elegance, entry.weirdness, entry.human_feasibility,
                entry.ai_feasibility, entry.novelty, entry.analogy_distance,
                entry.scaling_potential, entry.side_effects,
                entry.miner_address, entry.created_at,
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
                 miner_addr, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.combo_id, entry.method_name, entry.method_domain,
                entry.method_level, entry.problem_title, entry.problem_domain,
                entry.best_dimension, entry.best_score,
                entry.elegance, entry.weirdness, entry.human_feasibility,
                entry.ai_feasibility, entry.novelty, entry.analogy_distance,
                entry.scaling_potential, entry.side_effects,
                entry.miner_address, entry.created_at,
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

    def record_payment(self, viewer_addr: str, combo_id: str):
        """Record that a viewer paid to view an analysis."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO paid_views (viewer_addr, combo_id, paid_at) VALUES (?, ?, ?)",
                (viewer_addr, combo_id, time.time()),
            )

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
        )
