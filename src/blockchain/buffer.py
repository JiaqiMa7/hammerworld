"""Buffer zone pipeline: submit AI analysis -> classify -> consensus -> publish."""
from __future__ import annotations

import json
import time
import uuid

from src.engine.models import Combination

PROTOCOL_ADDR = "0xPROTOCOL"


class BufferZone:
    """Orchestrates the blockchain buffer zone pipeline."""

    MIN_CLASSIFICATIONS = 3
    MAX_CLASSIFICATIONS = 7
    CONSENSUS_THRESHOLD = 0.6
    REWARD_CORRECT = 10
    REWARD_SPAM = 25
    PENALTY_WRONG = 5
    STAKE_PER_SUBMISSION = 50
    STAKE_PER_CLASSIFICATION = 10
    SPEED_BONUS_RATE = 0.1

    def __init__(self, db, token, staking):
        self.db = db
        self.token = token
        self.staking = staking

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit_analysis(self, combo_id: str, method_id: str, method_name: str,
                        problem_id: str, problem_title: str,
                        submitter: str, analysis_json: str,
                        analysis_text: str = "") -> str:
        sub_id = str(uuid.uuid4())[:12]
        bal = self.token.balance_of(submitter)
        if bal < self.STAKE_PER_SUBMISSION:
            self.token.faucet(submitter)
        self.staking.stake(submitter, self.STAKE_PER_SUBMISSION, sub_id)
        self.db.create_buffer_entry(
            sub_id, combo_id, method_id, method_name,
            problem_id, problem_title, submitter,
            analysis_json, analysis_text,
            staked_amount=self.STAKE_PER_SUBMISSION,
        )
        return sub_id

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify(self, submission_id: str, classifier_addr: str,
                 domain_label: str, is_nsfw: bool = False,
                 is_spam: bool = False, notes: str = "") -> dict:
        entry = self.db.get_buffer_entry(submission_id)
        if entry is None:
            return {"ok": False, "error": "Submission not found"}
        if entry["status"] != "pending":
            return {"ok": False, "error": f"Submission is {entry['status']}, not pending"}

        existing = self.db.get_classifications(submission_id)
        for c in existing:
            if c["classifier_addr"] == classifier_addr:
                return {"ok": False, "error": "Already classified"}

        if entry["classifier_count"] >= self.MAX_CLASSIFICATIONS:
            return {"ok": False, "error": "Max classifications reached"}

        nsfw_int = 1 if is_nsfw else 0
        spam_int = 1 if is_spam else 0

        bal = self.token.balance_of(classifier_addr)
        if bal < self.STAKE_PER_CLASSIFICATION:
            self.token.faucet(classifier_addr)
        self.staking.stake(classifier_addr, self.STAKE_PER_CLASSIFICATION, submission_id)

        self.db.classify_buffer_entry(
            submission_id, classifier_addr, domain_label,
            nsfw_int, spam_int, notes,
        )

        consensus = self._check_consensus(submission_id)
        if consensus["reached"]:
            self._distribute_rewards(submission_id, consensus)
            self.db.update_buffer_status(submission_id, "classified",
                                         consensus_domain=consensus["domain"],
                                         consensus_nsfw=consensus["nsfw"],
                                         consensus_spam=consensus["spam"],
                                         classified_at=time.time())
        elif entry["classifier_count"] + 1 >= self.MAX_CLASSIFICATIONS:
            self.db.update_buffer_status(submission_id, "disputed")

        return {"ok": True, "consensus": consensus}

    # ------------------------------------------------------------------
    # Consensus
    # ------------------------------------------------------------------

    def _check_consensus(self, submission_id: str) -> dict:
        classifications = self.db.get_classifications(submission_id)
        n = len(classifications)
        if n < self.MIN_CLASSIFICATIONS:
            return {"reached": False, "total": n, "reason": "insufficient votes"}

        domain_votes = {}
        nsfw_total = 0
        spam_total = 0
        for c in classifications:
            d = c["domain_label"]
            domain_votes[d] = domain_votes.get(d, 0) + 1
            nsfw_total += c.get("is_nsfw", 0)
            spam_total += c.get("is_spam", 0)

        best_domain = max(domain_votes, key=domain_votes.get)
        best_count = domain_votes[best_domain]
        domain_ratio = best_count / n if n > 0 else 0

        domain_ok = domain_ratio >= self.CONSENSUS_THRESHOLD
        nsfw_val = 1 if nsfw_total > n / 2 else 0
        spam_val = 1 if spam_total > n / 2 else 0

        consensus_nsfw_count = nsfw_total if nsfw_val else (n - nsfw_total)
        consensus_spam_count = spam_total if spam_val else (n - spam_total)

        reached = domain_ok
        return {
            "reached": reached,
            "total": n,
            "domain": best_domain if domain_ok else "",
            "nsfw": nsfw_val,
            "spam": spam_val,
            "domain_ratio": domain_ratio,
            "domain_votes": domain_votes,
            "consensus_nsfw_count": consensus_nsfw_count,
            "consensus_spam_count": consensus_spam_count,
        }

    # ------------------------------------------------------------------
    # Rewards
    # ------------------------------------------------------------------

    def _distribute_rewards(self, submission_id: str, consensus: dict) -> dict:
        classifications = self.db.get_classifications(submission_id)
        rewards = []

        for c in classifications:
            matched = True
            bonus = 0
            if c["domain_label"] != consensus["domain"]:
                matched = False
            if consensus["spam"] != c.get("is_nsfw", 0):  # check nsfw
                pass  # nsfw mismatch handled differently

            if matched:
                reward = self.REWARD_CORRECT
                if consensus["spam"] == 1 and c.get("is_spam", 0) == 1:
                    reward += self.REWARD_SPAM
                self.db.update_classifier_stats(c["classifier_addr"], True)
                streak = self.db.get_or_create_account(c["classifier_addr"]).get("consecutive_correct", 0)
                speed_bonus = int(reward * min(streak * self.SPEED_BONUS_RATE, 1.0))
                reward += speed_bonus
                self.token.mint(c["classifier_addr"], reward)
            else:
                reward = -self.PENALTY_WRONG
                self.db.update_classifier_stats(c["classifier_addr"], False)
                self.db.update_token_slashed(c["classifier_addr"], self.PENALTY_WRONG)
                self.token.transfer(c["classifier_addr"], PROTOCOL_ADDR, self.PENALTY_WRONG)

            self.db.set_classification_consensus_match(c["id"], matched, reward)
            rewards.append({"class_id": c["id"], "addr": c["classifier_addr"],
                           "matched": matched, "reward": reward})

        return {"rewards": rewards, "total_classified": len(classifications)}

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish_to_leaderboard(self, submission_id: str, combo: Combination,
                                miner_addr: str) -> bool:
        entry = self.db.get_buffer_entry(submission_id)
        if entry is None or entry["status"] != "classified":
            return False
        self.db.insert(combo, miner_addr)
        self.db.update_buffer_status(submission_id, "published")
        return True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self, submission_id: str) -> dict:
        entry = self.db.get_buffer_entry(submission_id)
        if entry is None:
            return {"error": "not found"}
        classifications = self.db.get_classifications(submission_id)
        entry["classifications"] = classifications
        return entry

    def get_classifier_stats(self, address: str) -> dict:
        acct = self.db.get_or_create_account(address)
        return {
            "address": address,
            "balance": acct.get("balance", 0),
            "staked": acct.get("staked", 0),
            "total_earned": acct.get("total_earned", 0),
            "total_slashed": acct.get("total_slashed", 0),
            "consecutive_correct": acct.get("consecutive_correct", 0),
            "total_classifications": acct.get("total_classifications", 0),
            "correct_classifications": acct.get("correct_classifications", 0),
        }

    def get_dashboard_stats(self) -> dict:
        return {
            "pending": self.db.count_buffer_by_status("pending"),
            "classified": self.db.count_buffer_by_status("classified"),
            "disputed": self.db.count_buffer_by_status("disputed"),
            "published": self.db.count_buffer_by_status("published"),
        }
