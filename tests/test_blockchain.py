"""Tests for blockchain buffer zone: contracts, buffer, web pages, CLI."""
from __future__ import annotations

import json
import os
import sys
import io
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hub.leaderboard import LeaderboardDB
from src.blockchain.contracts import SimulatedToken, StakingContract
from src.blockchain.buffer import BufferZone
from src.hub.web import (
    render_buffer_dashboard, render_buffer_pending,
    render_buffer_classify, render_buffer_submissions,
    render_buffer_submission_detail, render_buffer_tokens,
    render_buffer_leaderboard,
)


class TestSimulatedToken(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.token = SimulatedToken(self.db)

    def test_mint_and_balance(self):
        self.token.mint("0xALICE", 500)
        self.assertEqual(self.token.balance_of("0xALICE"), 500)

    def test_transfer_sufficient(self):
        self.token.mint("0xALICE", 500)
        ok = self.token.transfer("0xALICE", "0xBOB", 200)
        self.assertTrue(ok)
        self.assertEqual(self.token.balance_of("0xALICE"), 300)
        self.assertEqual(self.token.balance_of("0xBOB"), 200)

    def test_transfer_insufficient(self):
        self.token.mint("0xALICE", 100)
        ok = self.token.transfer("0xALICE", "0xBOB", 200)
        self.assertFalse(ok)
        self.assertEqual(self.token.balance_of("0xALICE"), 100)

    def test_faucet(self):
        self.token.faucet("0xNEWBIE", 1000)
        self.assertEqual(self.token.balance_of("0xNEWBIE"), 1000)

    def test_total_supply(self):
        self.token.mint("0xALICE", 500)
        self.token.mint("0xBOB", 300)
        self.assertEqual(self.token.total_supply(), 800)


class TestStakingContract(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.token = SimulatedToken(self.db)
        self.staking = StakingContract(self.db, self.token)

    def test_stake_success(self):
        self.token.faucet("0xALICE", 1000)
        sid = self.staking.stake("0xALICE", 200)
        self.assertGreater(sid, 0)
        self.assertEqual(self.token.balance_of("0xALICE"), 800)
        self.assertEqual(self.staking.get_active_stake("0xALICE"), 200)

    def test_stake_insufficient_balance(self):
        sid = self.staking.stake("0xALICE", 200)
        self.assertEqual(sid, -1)

    def test_release_stake(self):
        self.token.faucet("0xALICE", 1000)
        sid = self.staking.stake("0xALICE", 200)
        ok = self.staking.release_stake(sid)
        self.assertTrue(ok)
        self.assertEqual(self.staking.get_active_stake("0xALICE"), 0)
        self.assertEqual(self.token.balance_of("0xALICE"), 1000)

    def test_slash_full(self):
        self.token.faucet("0xALICE", 1000)
        sid = self.staking.stake("0xALICE", 200)
        ok = self.staking.slash_stake(sid, 200)
        self.assertTrue(ok)
        self.assertEqual(self.staking.get_active_stake("0xALICE"), 0)
        self.assertEqual(self.token.balance_of("0xALICE"), 800)

    def test_slash_partial(self):
        self.token.faucet("0xALICE", 1000)
        sid = self.staking.stake("0xALICE", 200)
        ok = self.staking.slash_stake(sid, 100)
        self.assertTrue(ok)
        self.assertEqual(self.token.balance_of("0xALICE"), 900)
        self.assertEqual(self.staking.get_active_stake("0xALICE"), 100)


class TestBufferSubmission(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.token = SimulatedToken(self.db)
        self.staking = StakingContract(self.db, self.token)
        self.buffer_zone = BufferZone(self.db, self.token, self.staking)

    def test_submit_analysis_returns_id(self):
        sub_id = self.buffer_zone.submit_analysis(
            combo_id="c1", method_id="m1", method_name="TestM",
            problem_id="p1", problem_title="TestP",
            submitter="0xALICE",
            analysis_json='{"scores":[{"dim":"elegance","score":8.5}]}',
        )
        self.assertIsNotNone(sub_id)
        self.assertEqual(len(sub_id), 12)

    def test_submit_creates_db_record(self):
        sub_id = self.buffer_zone.submit_analysis(
            combo_id="c2", method_id="m1", method_name="M",
            problem_id="p1", problem_title="P",
            submitter="0xALICE",
            analysis_json='{"scores":[]}',
        )
        entry = self.db.get_buffer_entry(sub_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["submitter"], "0xALICE")
        self.assertEqual(entry["combo_id"], "c2")

    def test_submit_auto_stakes_tokens(self):
        self.buffer_zone.submit_analysis(
            combo_id="c3", method_id="m1", method_name="M",
            problem_id="p1", problem_title="P",
            submitter="0xALICE",
            analysis_json="{}",
        )
        stats = self.buffer_zone.get_classifier_stats("0xALICE")
        self.assertGreaterEqual(stats["balance"], 900)
        self.assertGreaterEqual(stats["staked"], 50)

    def test_submit_auto_faucet_new_user(self):
        self.buffer_zone.submit_analysis(
            combo_id="c4", method_id="m1", method_name="M",
            problem_id="p1", problem_title="P",
            submitter="0xFRESH",
            analysis_json="{}",
        )
        self.assertGreaterEqual(self.token.balance_of("0xFRESH"), 900)


class TestBufferClassification(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.token = SimulatedToken(self.db)
        self.staking = StakingContract(self.db, self.token)
        self.buffer_zone = BufferZone(self.db, self.token, self.staking)
        self.sub_id = self.buffer_zone.submit_analysis(
            combo_id="c5", method_id="m1", method_name="M",
            problem_id="p1", problem_title="P",
            submitter="0xSUBMITTER",
            analysis_json='{"scores":[{"dim":"novelty","score":9.0}]}',
        )

    def test_classify_adds_vote(self):
        result = self.buffer_zone.classify(self.sub_id, "0xBOB", "medicine")
        self.assertTrue(result["ok"])
        classifications = self.db.get_classifications(self.sub_id)
        self.assertEqual(len(classifications), 1)
        self.assertEqual(classifications[0]["domain_label"], "medicine")

    def test_classify_requires_pending_status(self):
        # First manually set to classified
        self.db.update_buffer_status(self.sub_id, "classified")
        result = self.buffer_zone.classify(self.sub_id, "0xBOB", "medicine")
        self.assertFalse(result["ok"])
        self.assertIn("not pending", result["error"])

    def test_duplicate_classifier_rejected(self):
        self.buffer_zone.classify(self.sub_id, "0xBOB", "medicine")
        result = self.buffer_zone.classify(self.sub_id, "0xBOB", "energy")
        self.assertFalse(result["ok"])
        self.assertIn("Already classified", result["error"])

    def test_classify_auto_faucet_new_user(self):
        self.buffer_zone.classify(self.sub_id, "0xFRESH", "physics")
        self.assertGreaterEqual(self.token.balance_of("0xFRESH"), 900)


class TestConsensus(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.token = SimulatedToken(self.db)
        self.staking = StakingContract(self.db, self.token)
        self.buffer_zone = BufferZone(self.db, self.token, self.staking)
        self.sub_id = self.buffer_zone.submit_analysis(
            combo_id="c6", method_id="m1", method_name="M",
            problem_id="p1", problem_title="P",
            submitter="0xALICE",
            analysis_json='{"scores":[{"dim":"elegance","score":7.0}]}',
        )

    def test_consensus_not_reached_few_votes(self):
        self.buffer_zone.classify(self.sub_id, "0xBOB", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xCAROL", "medicine")
        status = self.buffer_zone.get_status(self.sub_id)
        self.assertEqual(status["status"], "pending")

    def test_consensus_reached_with_three_votes(self):
        for addr in ["0xBOB", "0xCAROL", "0xDAVE"]:
            self.buffer_zone.classify(self.sub_id, addr, "medicine")
        status = self.buffer_zone.get_status(self.sub_id)
        self.assertEqual(status["status"], "classified")
        self.assertEqual(status["consensus_domain"], "medicine")

    def test_consensus_majority_domain(self):
        self.buffer_zone.classify(self.sub_id, "0xBOB", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xCAROL", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xDAVE", "energy")
        self.buffer_zone.classify(self.sub_id, "0xEVE", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xFRANK", "medicine")
        status = self.buffer_zone.get_status(self.sub_id)
        self.assertEqual(status["status"], "classified")
        self.assertEqual(status["consensus_domain"], "medicine")

    def test_consensus_no_majority(self):
        self.buffer_zone.classify(self.sub_id, "0xBOB", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xCAROL", "energy")
        self.buffer_zone.classify(self.sub_id, "0xDAVE", "physics")
        status = self.buffer_zone.get_status(self.sub_id)
        # 3 votes, no domain > 60%, so no consensus
        self.assertEqual(status["status"], "pending")


class TestDisputeRouting(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.token = SimulatedToken(self.db)
        self.staking = StakingContract(self.db, self.token)
        self.buffer_zone = BufferZone(self.db, self.token, self.staking)
        self.sub_id = self.buffer_zone.submit_analysis(
            combo_id="c7", method_id="m1", method_name="M",
            problem_id="p1", problem_title="P",
            submitter="0xALICE",
            analysis_json="{}",
        )

    def test_disputed_after_max_classifications_no_consensus(self):
        addrs = ["0xA", "0xB", "0xC", "0xD", "0xE", "0xF", "0xG"]
        domains = ["medicine", "energy", "physics", "chemistry", "biology", "math", "other"]
        for addr, domain in zip(addrs, domains):
            self.buffer_zone.classify(self.sub_id, addr, domain)
        status = self.buffer_zone.get_status(self.sub_id)
        self.assertEqual(status["status"], "disputed")


class TestClassifierRewards(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.token = SimulatedToken(self.db)
        self.staking = StakingContract(self.db, self.token)
        self.buffer_zone = BufferZone(self.db, self.token, self.staking)
        self.sub_id = self.buffer_zone.submit_analysis(
            combo_id="c8", method_id="m1", method_name="M",
            problem_id="p1", problem_title="P",
            submitter="0xALICE",
            analysis_json="{}",
        )

    def test_correct_classifier_reward(self):
        self.buffer_zone.classify(self.sub_id, "0xBOB", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xCAROL", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xDAVE", "medicine")
        # BOB gets reward for matching consensus
        stats = self.buffer_zone.get_classifier_stats("0xBOB")
        self.assertGreater(stats["total_earned"], 1000)  # faucet + reward
        self.assertEqual(stats["correct_classifications"], 1)

    def test_wrong_classifier_penalty(self):
        self.buffer_zone.classify(self.sub_id, "0xBOB", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xCAROL", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xDAVE", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xEVE", "medicine")
        self.buffer_zone.classify(self.sub_id, "0xFRANK", "energy")
        # FRANK voted energy, consensus is medicine
        stats = self.buffer_zone.get_classifier_stats("0xFRANK")
        self.assertEqual(stats["correct_classifications"], 0)
        self.assertEqual(stats["consecutive_correct"], 0)

    def test_speed_bonus_streak(self):
        # First submission - all medicine consensus
        for addr in ["0xBOB", "0xCAROL", "0xDAVE"]:
            self.buffer_zone.classify(self.sub_id, addr, "medicine")
        stats = self.buffer_zone.get_classifier_stats("0xBOB")
        self.assertEqual(stats["consecutive_correct"], 1)
        self.assertGreater(stats["total_earned"], 1000 + BufferZone.REWARD_CORRECT - 1)

    def test_spam_detector_bonus(self):
        sub_id2 = self.buffer_zone.submit_analysis(
            combo_id="spam1", method_id="m2", method_name="SPAM",
            problem_id="p2", problem_title="SPAM",
            submitter="0xSPAMMER",
            analysis_json="{}",
        )
        self.buffer_zone.classify(sub_id2, "0xBOB", "medicine", is_spam=True)
        self.buffer_zone.classify(sub_id2, "0xCAROL", "medicine", is_spam=True)
        self.buffer_zone.classify(sub_id2, "0xDAVE", "medicine", is_spam=True)
        self.buffer_zone.classify(sub_id2, "0xEVE", "medicine", is_spam=True)
        # Spam consensus reached
        status = self.buffer_zone.get_status(sub_id2)
        self.assertEqual(status["status"], "classified")


class TestFullPipeline(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.token = SimulatedToken(self.db)
        self.staking = StakingContract(self.db, self.token)
        self.buffer_zone = BufferZone(self.db, self.token, self.staking)

    def test_submit_classify_publish_flow(self):
        sub_id = self.buffer_zone.submit_analysis(
            combo_id="flow1", method_id="m1", method_name="FlowM",
            problem_id="p1", problem_title="FlowP",
            submitter="0xALICE",
            analysis_json=json.dumps({"scores": [{"dim": "elegance", "score": 8.0}]}),
        )
        self.assertIsNotNone(sub_id)
        status = self.buffer_zone.get_status(sub_id)
        self.assertEqual(status["status"], "pending")

        for addr in ["0xBOB", "0xCAROL", "0xDAVE"]:
            result = self.buffer_zone.classify(sub_id, addr, "medicine")
            self.assertTrue(result["ok"])

        status = self.buffer_zone.get_status(sub_id)
        self.assertEqual(status["status"], "classified")
        self.assertEqual(status["consensus_domain"], "medicine")

        # Verify all 3 classifiers got rewards
        for addr in ["0xBOB", "0xCAROL", "0xDAVE"]:
            stats = self.buffer_zone.get_classifier_stats(addr)
            self.assertGreater(stats["total_earned"], 1000)

    def test_end_to_end_multiple_classifiers(self):
        sub_id = self.buffer_zone.submit_analysis(
            combo_id="multi1", method_id="m1", method_name="Multi",
            problem_id="p1", problem_title="Multi",
            submitter="0xALICE",
            analysis_json="{}",
        )
        results = []
        for i, addr in enumerate(["0xA", "0xB", "0xC", "0xD", "0xE"]):
            domain = "physics" if i < 3 else "medicine"  # 3 physics, 2 medicine
            result = self.buffer_zone.classify(sub_id, addr, domain)
            results.append(result)

        status = self.buffer_zone.get_status(sub_id)
        # 3/5 = 60% physics -> consensus reached
        self.assertEqual(status["status"], "classified")
        self.assertEqual(status["consensus_domain"], "physics")

        classifications = self.db.get_classifications(sub_id)
        # 3 matched consensus (physics), 2 didn't
        matched = sum(1 for c in classifications if c.get("matched_consensus"))
        self.assertEqual(matched, 3)


class TestWebPages(unittest.TestCase):
    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.token = SimulatedToken(self.db)
        self.staking = StakingContract(self.db, self.token)
        self.buffer_zone = BufferZone(self.db, self.token, self.staking)

    def test_buffer_dashboard_renders(self):
        html = render_buffer_dashboard(self.db)
        self.assertIn("Buffer Zone", html)
        self.assertIn("Pending", html)
        self.assertIn("Classified", html)

    def test_buffer_dashboard_with_submissions(self):
        self.buffer_zone.submit_analysis(
            combo_id="web1", method_id="m1", method_name="Web",
            problem_id="p1", problem_title="WebP",
            submitter="0xALICE",
            analysis_json="{}",
        )
        html = render_buffer_dashboard(self.db)
        self.assertIn("1", html)  # pending count

    def test_buffer_pending_renders(self):
        self.buffer_zone.submit_analysis(
            combo_id="web2", method_id="m1", method_name="Web2",
            problem_id="p1", problem_title="WebP2",
            submitter="0xALICE",
            analysis_json="{}",
        )
        html = render_buffer_pending(self.db, "/web/buffer/pending")
        self.assertIn("Web2", html)
        self.assertIn("Classify", html)

    def test_buffer_pending_empty(self):
        html = render_buffer_pending(self.db, "/web/buffer/pending")
        self.assertIn("No pending submissions", html)

    def test_buffer_classify_form(self):
        sub_id = self.buffer_zone.submit_analysis(
            combo_id="web3", method_id="m1", method_name="Web3",
            problem_id="p1", problem_title="WebP3",
            submitter="0xALICE",
            analysis_json='{"scores":[{"dim":"elegance","score":9.5}]}',
        )
        html = render_buffer_classify(self.db, sub_id, f"/web/buffer/classify/{sub_id}")
        self.assertIn("Web3", html)
        self.assertIn("WebP3", html)
        self.assertIn("domain", html)  # form field

    def test_buffer_submission_detail(self):
        sub_id = self.buffer_zone.submit_analysis(
            combo_id="web4", method_id="m1", method_name="Web4",
            problem_id="p1", problem_title="WebP4",
            submitter="0xALICE",
            analysis_json="{}",
        )
        self.buffer_zone.classify(sub_id, "0xBOB", "physics")
        html = render_buffer_submission_detail(self.db, sub_id)
        self.assertIn("Web4", html)
        self.assertIn("0xBOB", html)
        self.assertIn("physics", html)

    def test_buffer_submissions_by_user(self):
        self.buffer_zone.submit_analysis(
            combo_id="web5", method_id="m1", method_name="UWeb",
            problem_id="p1", problem_title="UWebP",
            submitter="0xUSER1",
            analysis_json="{}",
        )
        html = render_buffer_submissions(self.db, "0xUSER1")
        self.assertIn("UWeb", html)
        self.assertIn("pending", html)

    def test_buffer_tokens_page(self):
        self.buffer_zone.submit_analysis(
            combo_id="web6", method_id="m1", method_name="TWeb",
            problem_id="p1", problem_title="TWebP",
            submitter="0xRICH",
            analysis_json="{}",
        )
        html = render_buffer_tokens(self.db, "0xRICH")
        self.assertIn("Balance", html)
        self.assertIn("IDEA", html)
        self.assertIn("Staked", html)

    def test_buffer_leaderboard_page(self):
        self.buffer_zone.submit_analysis(
            combo_id="web7", method_id="m1", method_name="LWeb",
            problem_id="p1", problem_title="LWebP",
            submitter="0xALICE",
            analysis_json="{}",
        )
        for addr in ["0xBOB", "0xCAROL", "0xDAVE"]:
            self.buffer_zone.classify("web7", addr, "medicine")  # use correct sub_id format
        html = render_buffer_leaderboard(self.db)
        self.assertIn("Classifier Leaderboard", html)


class TestBufferCLI(unittest.TestCase):
    def setUp(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.db = LeaderboardDB(self.db_path)

    def tearDown(self):
        self.db = None
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_buffer_submit_cli(self):
        from src.cli.main import cmd_buffer_submit

        class Args:
            combo_id = "cli_test1"
            method_id = "m_cli"
            method_name = "CLI Method"
            problem_id = "p_cli"
            problem_title = "CLI Problem"
            analysis_json = '{"scores":[{"dim":"elegance","score":9.0}]}'
            analysis_file = None
            analysis_text = ""
            address = "0xCLI_SUB"
            db = self.db_path

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_buffer_submit(Args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertIn("Submission sent to buffer zone", output)
        self.assertIn("pending", output)

    def test_buffer_classify_cli(self):
        from src.cli.main import cmd_buffer_submit, cmd_buffer_classify

        # First submit
        class SubmitArgs:
            combo_id = "cli_test2"
            method_id = "m_cli"
            method_name = "CLI Method"
            problem_id = "p_cli"
            problem_title = "CLI Problem"
            analysis_json = "{}"
            analysis_file = None
            analysis_text = ""
            address = "0xCLI_SUB"
            db = self.db_path

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_buffer_submit(SubmitArgs)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        # Extract submission ID from output
        sub_id = None
        for line in output.split("\n"):
            if "Submission ID:" in line:
                sub_id = line.split("Submission ID:")[1].strip()
        self.assertIsNotNone(sub_id)

        # Now classify
        class ClassifyArgs:
            submission_id = sub_id
            domain = "physics"
            nsfw = False
            spam = False
            notes = "test note"
            address = "0xBOB"
            db = self.db_path

        sys.stdout = io.StringIO()
        try:
            cmd_buffer_classify(ClassifyArgs)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertIn("Classification submitted", output)

    def test_buffer_status_cli(self):
        from src.cli.main import cmd_buffer_status

        class Args:
            submission_id = None
            address = None
            db = self.db_path

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_buffer_status(Args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertIn("Buffer Zone Stats", output)
        self.assertIn("Pending", output)

    def test_buffer_tokens_cli(self):
        from src.cli.main import cmd_buffer_tokens

        class Args:
            address = "0xVIEWER"
            db = self.db_path

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_buffer_tokens(Args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertIn("Idea Token", output)
        self.assertIn("IDEA", output)


if __name__ == "__main__":
    unittest.main()
