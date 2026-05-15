"""Token Gate: pay-to-view, leaderboard unlock, random draw payment, ratings."""
from __future__ import annotations

import time

from src.hub.leaderboard import LeaderboardDB

PROTOCOL_ADDR = "0xPROTOCOL"


class TokenGate:
    """Orchestrates payment flows between viewers and the token system."""

    VIEW_FEE_N = 10
    LEADERBOARD_FEE_P = 20
    DRAW_FEE_Q = 5
    FAUCET_AMOUNT = 100
    LEADERBOARD_DURATION = 86400  # 24h

    def __init__(self, db: LeaderboardDB, token):
        self.db = db
        self.token = token

    # ------------------------------------------------------------------
    # View Access
    # ------------------------------------------------------------------

    def pay_for_view(self, viewer_addr: str, run_id: str) -> dict:
        """Pay VIEW_FEE_N to unlock all analyses in a combo group. Returns result dict."""
        entry = self.db._get_by_id(run_id)
        if entry is None:
            return {"ok": False, "error": "Combo not found"}

        if entry.miner_address == viewer_addr:
            return {"ok": True, "status": "own", "message": "You own this analysis"}

        if self.db.has_paid(viewer_addr, entry.combo_group_id):
            return {"ok": True, "status": "already_paid", "message": "Already paid for this group"}

        self._ensure_balance(viewer_addr, self.VIEW_FEE_N)

        analyzer_addr = entry.miner_address

        self.token.transfer(viewer_addr, analyzer_addr, 8)       # 80% to analyzer
        self.token.transfer(viewer_addr, analyzer_addr, 1)       # 10% to discoverer (MVP: same)
        self.token.transfer(viewer_addr, PROTOCOL_ADDR, 1)       # 10% protocol fee

        self.db.record_payment(
            viewer_addr, entry.combo_group_id,
            paid_amount=self.VIEW_FEE_N,
            analyzer_addr=analyzer_addr,
            protocol_addr=PROTOCOL_ADDR,
        )
        return {"ok": True, "status": "paid", "message": "View unlocked"}

    def check_view_access(self, viewer_addr: str, run_id: str) -> str:
        """Return access level: 'own', 'paid', or 'no_access'."""
        if not viewer_addr:
            return "no_access"
        entry = self.db._get_by_id(run_id)
        if entry and entry.miner_address == viewer_addr:
            return "own"
        if entry and self.db.has_paid(viewer_addr, entry.combo_group_id):
            return "paid"
        return "no_access"

    # ------------------------------------------------------------------
    # Leaderboard Access
    # ------------------------------------------------------------------

    def pay_for_leaderboard(self, viewer_addr: str, board_name: str) -> dict:
        """Pay LEADERBOARD_FEE_P to unlock a leaderboard for 24h."""
        if self.db.has_leaderboard_access(viewer_addr, board_name):
            return {"ok": True, "status": "already_unlocked", "message": "Already unlocked"}

        self._ensure_balance(viewer_addr, self.LEADERBOARD_FEE_P)

        self.token.transfer(viewer_addr, PROTOCOL_ADDR, self.LEADERBOARD_FEE_P)
        self.db.grant_leaderboard_access(
            viewer_addr, board_name,
            paid_amount=self.LEADERBOARD_FEE_P,
            duration_seconds=self.LEADERBOARD_DURATION,
        )
        return {"ok": True, "status": "unlocked", "message": "Leaderboard unlocked for 24h"}

    def check_leaderboard_access(self, viewer_addr: str, board_name: str) -> bool:
        """Check if viewer has active leaderboard access."""
        if not viewer_addr:
            return False
        return self.db.has_leaderboard_access(viewer_addr, board_name)

    # ------------------------------------------------------------------
    # Random Draw
    # ------------------------------------------------------------------

    def pay_for_random_draw(self, viewer_addr: str) -> dict:
        """Pay DRAW_FEE_Q for a random draw."""
        self._ensure_balance(viewer_addr, self.DRAW_FEE_Q)
        ok = self.token.transfer(viewer_addr, PROTOCOL_ADDR, self.DRAW_FEE_Q)
        if not ok:
            return {"ok": False, "error": "Transfer failed"}
        self.db.record_draw_payment(viewer_addr)
        return {"ok": True, "status": "paid", "message": "Draw unlocked"}

    def has_draw_access(self, viewer_addr: str) -> bool:
        """Check if viewer has paid for random draw access."""
        if not viewer_addr:
            return False
        return self.db.has_draw_payment(viewer_addr)

    # ------------------------------------------------------------------
    # Ratings
    # ------------------------------------------------------------------

    def rate_analysis(self, viewer_addr: str, run_id: str,
                      rating: int, comment: str = "") -> dict:
        """Submit a rating for a run. Only paid viewers can rate."""
        access = self.check_view_access(viewer_addr, run_id)
        if access == "no_access":
            return {"ok": False, "error": "Must pay to rate"}

        if rating < 1 or rating > 5:
            return {"ok": False, "error": "Rating must be 1-5"}

        inserted = self.db.record_rating(viewer_addr, run_id, rating, comment)
        if not inserted:
            return {"ok": False, "error": "Already rated this run"}

        avg = self.db.get_avg_rating_for_run(run_id)
        return {"ok": True, "message": "Rating recorded", "avg_rating": avg}

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_viewer_summary(self, viewer_addr: str) -> dict:
        """Get a viewer's token dashboard summary."""
        acct = self.db.get_or_create_account(viewer_addr)
        payments = self.db.get_viewer_payments(viewer_addr)
        return {
            "address": viewer_addr,
            "balance": acct.get("balance", 0),
            "staked": acct.get("staked", 0),
            "total_earned": acct.get("total_earned", 0),
            "total_slashed": acct.get("total_slashed", 0),
            "total_payments": len(payments),
            "total_spent": sum(p.get("paid_amount", 0) for p in payments),
            "payments": payments[:20],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_balance(self, address: str, needed: int) -> bool:
        """Check balance and attempt faucet if needed. Returns True if balance is sufficient."""
        bal = self.token.balance_of(address)
        if bal >= needed:
            return True
        # Try faucet (may be rate-limited)
        self.token.faucet(address, self.FAUCET_AMOUNT)
        bal = self.token.balance_of(address)
        return bal >= needed
