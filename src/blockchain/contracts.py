"""Simulated ERC-20 token and staking contract backed by LeaderboardDB tables."""
from __future__ import annotations

import time


class SimulatedToken:
    """Simulated ERC-20 token persistent in token_accounts table."""

    def __init__(self, db, name: str = "Idea Token", symbol: str = "IDEA"):
        self.db = db
        self.name = name
        self.symbol = symbol

    def balance_of(self, address: str) -> int:
        acct = self.db.get_or_create_account(address)
        return acct.get("balance", 0)

    def transfer(self, from_addr: str, to_addr: str, amount: int) -> bool:
        if amount <= 0:
            return False
        bal = self.balance_of(from_addr)
        if bal < amount:
            return False
        self.db.update_token_balance(from_addr, -amount)
        self.db.update_token_balance(to_addr, amount)
        return True

    def mint(self, to_addr: str, amount: int) -> None:
        self.db.update_token_balance(to_addr, amount)
        self.db.update_token_earned(to_addr, amount)

    def total_supply(self) -> int:
        from src.hub.leaderboard import LeaderboardDB
        with self.db._connect() as conn:
            row = conn.execute("SELECT COALESCE(SUM(balance), 0) FROM token_accounts").fetchone()
            return row[0]

    FAUCET_COOLDOWN = 3600  # seconds between faucet claims (1 hour)
    FAUCET_MAX = 10          # max faucet claims per address

    def faucet(self, address: str, amount: int = 1000) -> int:
        """Mint free tokens with cooldown and per-address limit.
        Returns the amount minted, or 0 if rate-limited."""
        acct = self.db.get_or_create_account(address)
        now = time.time()
        last_faucet = acct.get("last_faucet_at", 0)
        faucet_count = acct.get("faucet_count", 0)
        if now - last_faucet < self.FAUCET_COOLDOWN:
            return 0
        if faucet_count >= self.FAUCET_MAX:
            return 0
        self.mint(address, amount)
        with self.db._connect() as conn:
            conn.execute(
                "UPDATE token_accounts SET last_faucet_at = ?, faucet_count = faucet_count + 1 WHERE address = ?",
                (now, address),
            )
        return amount


class StakingContract:
    """Simulated staking contract backed by stake_records table."""

    def __init__(self, db, token: SimulatedToken):
        self.db = db
        self.token = token

    def stake(self, address: str, amount: int, submission_id: str = "") -> int:
        bal = self.token.balance_of(address)
        if amount <= 0 or bal < amount:
            return -1
        self.token.transfer(address, "", amount)  # burn from balance, track in staked
        self.db.update_token_staked(address, amount)
        sid = self.db.create_stake_record(address, amount, submission_id)
        return sid

    def release_stake(self, stake_id: int) -> bool:
        stakes = self.db.get_all_stakes()
        for s in stakes:
            if s["id"] == stake_id and s["status"] == "active":
                self.db.update_stake_status(stake_id, "released")
                self.db.update_token_staked(s["address"], -s["amount"])
                self.token.mint(s["address"], s["amount"])
                return True
        return False

    def slash_stake(self, stake_id: int, amount: int) -> bool:
        stakes = self.db.get_all_stakes()
        for s in stakes:
            if s["id"] == stake_id and s["status"] == "active":
                slash = min(amount, s["amount"])
                remaining = s["amount"] - slash
                self.db.update_stake_status(stake_id, "slashed")
                self.db.update_token_staked(s["address"], -s["amount"])
                self.db.update_token_slashed(s["address"], slash)
                if remaining > 0:
                    self.token.mint(s["address"], remaining)
                    self.db.create_stake_record(s["address"], remaining, s.get("submission_id", ""))
                    self.db.update_token_staked(s["address"], remaining)
                return True
        return False

    def get_active_stake(self, address: str) -> int:
        return self.db.get_total_staked(address)

    def get_total_at_stake(self, address: str) -> int:
        return self.db.get_total_staked(address)
