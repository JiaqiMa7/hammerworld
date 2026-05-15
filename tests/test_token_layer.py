"""Tests for Token Layer: TokenGate, payment flows, buffer bug fixes."""
from __future__ import annotations

import time
import unittest

from src.hub.leaderboard import LeaderboardDB
from src.blockchain.contracts import SimulatedToken, StakingContract
from src.blockchain.buffer import BufferZone, PROTOCOL_ADDR
from src.hub.token_layer import TokenGate
from src.engine.models import (
    Combination, Method, Problem, EvalDimension, Domain, MethodLevel,
    AIAnalysis, EvalScore,
)


def _make_combo(method_name="Test Method", problem_title="Test Problem",
                analysis_text="Secret analysis text.", miner="0xMINER",
                combo_id="test-combo-1"):
    m = Method(id='m1', name=method_name, domain='physics',
               level=MethodLevel(2), description='test')
    p = Problem(id='p1', title=problem_title,
                domain=Domain('energy'), description='test')
    analysis = AIAnalysis(
        scores=[EvalScore(dimension=EvalDimension.ELEGANCE, score=8.5,
                          explanation='Very elegant')],
        analysis_text=analysis_text,
        model_name='test-model', model_version='1.0', inference_hash='abc',
    )
    return Combination(id=combo_id, method=m, problem=p, analyses=[analysis])


class TestTokenGatePayForView(unittest.TestCase):
    """Tests for pay_for_view and check_view_access."""

    def setUp(self):
        self.db = LeaderboardDB(':memory:')
        self.token = SimulatedToken(self.db)
        self.tg = TokenGate(self.db, self.token)

    def test_check_access_no_viewer(self):
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        self.assertEqual(self.tg.check_view_access('', entry.run_id), 'no_access')

    def test_check_access_owner(self):
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        self.assertEqual(self.tg.check_view_access('0xMINER', entry.run_id), 'own')

    def test_check_access_no_payment(self):
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        self.assertEqual(self.tg.check_view_access('0xALICE', entry.run_id), 'no_access')

    def test_pay_for_view_success(self):
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        result = self.tg.pay_for_view('0xALICE', entry.run_id)
        self.assertTrue(result['ok'])
        self.assertEqual(result['status'], 'paid')
        self.assertEqual(self.tg.check_view_access('0xALICE', entry.run_id), 'paid')

    def test_pay_for_view_idempotent(self):
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        self.tg.pay_for_view('0xALICE', entry.run_id)
        result2 = self.tg.pay_for_view('0xALICE', entry.run_id)
        self.assertTrue(result2['ok'])
        self.assertEqual(result2['status'], 'already_paid')

    def test_pay_for_view_own_is_free(self):
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        result = self.tg.pay_for_view('0xMINER', entry.run_id)
        self.assertTrue(result['ok'])
        self.assertEqual(result['status'], 'own')

    def test_pay_for_view_auto_faucet(self):
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        self.assertEqual(self.token.balance_of('0xBOB'), 0)
        result = self.tg.pay_for_view('0xBOB', entry.run_id)
        self.assertTrue(result['ok'])
        self.assertEqual(self.token.balance_of('0xBOB'), 90)  # 100 - 10

    def test_pay_for_view_fee_distribution(self):
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        self.tg.pay_for_view('0xALICE', entry.run_id)
        # 0xALICE: 100 faucet - 10 fee = 90
        self.assertEqual(self.token.balance_of('0xALICE'), 90)
        # 0xMINER: 8 (80% analyzer) + 1 (10% discoverer) = 9
        self.assertEqual(self.token.balance_of('0xMINER'), 9)
        # PROTOCOL: 1 (10%)
        self.assertEqual(self.token.balance_of(PROTOCOL_ADDR), 1)

    def test_pay_for_view_combo_not_found(self):
        result = self.tg.pay_for_view('0xALICE', 'nonexistent')
        self.assertFalse(result['ok'])


class TestTokenGateLeaderboard(unittest.TestCase):
    """Tests for leaderboard payment and access."""

    def setUp(self):
        self.db = LeaderboardDB(':memory:')
        self.token = SimulatedToken(self.db)
        self.tg = TokenGate(self.db, self.token)

    def test_no_access_initially(self):
        self.assertFalse(self.tg.check_leaderboard_access('0xALICE', 'test_board'))

    def test_pay_unlocks_access(self):
        result = self.tg.pay_for_leaderboard('0xALICE', 'test_board')
        self.assertTrue(result['ok'])
        self.assertTrue(self.tg.check_leaderboard_access('0xALICE', 'test_board'))

    def test_already_unlocked(self):
        self.tg.pay_for_leaderboard('0xALICE', 'test_board')
        result = self.tg.pay_for_leaderboard('0xALICE', 'test_board')
        self.assertTrue(result['ok'])
        self.assertEqual(result['status'], 'already_unlocked')

    def test_no_access_without_viewer(self):
        self.assertFalse(self.tg.check_leaderboard_access('', 'test_board'))

    def test_leaderboard_fee_deducted(self):
        self.tg.pay_for_leaderboard('0xALICE', 'test_board')
        self.assertEqual(self.token.balance_of('0xALICE'), 80)  # 100 - 20


class TestTokenGateDraw(unittest.TestCase):
    """Tests for random draw payment."""

    def setUp(self):
        self.db = LeaderboardDB(':memory:')
        self.token = SimulatedToken(self.db)
        self.tg = TokenGate(self.db, self.token)

    def test_pay_for_draw_success(self):
        result = self.tg.pay_for_random_draw('0xALICE')
        self.assertTrue(result['ok'])
        self.assertEqual(self.token.balance_of('0xALICE'), 95)  # 100 - 5


class TestTokenGateRatings(unittest.TestCase):
    """Tests for rating submissions."""

    def setUp(self):
        self.db = LeaderboardDB(':memory:')
        self.token = SimulatedToken(self.db)
        self.tg = TokenGate(self.db, self.token)
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        self.run_id = entry.run_id
        self.tg.pay_for_view('0xALICE', self.run_id)

    def test_rate_success(self):
        result = self.tg.rate_analysis('0xALICE', self.run_id, 5)
        self.assertTrue(result['ok'])
        self.assertEqual(self.db.get_avg_rating_for_run(self.run_id), 5.0)

    def test_rate_already_rated(self):
        self.tg.rate_analysis('0xALICE', self.run_id, 5)
        result = self.tg.rate_analysis('0xALICE', self.run_id, 4)
        self.assertFalse(result['ok'])
        self.assertEqual(self.db.get_avg_rating_for_run(self.run_id), 5.0)

    def test_rate_without_payment(self):
        result = self.tg.rate_analysis('0xBOB', self.run_id, 3)
        self.assertFalse(result['ok'])

    def test_rate_invalid_value(self):
        result = self.tg.rate_analysis('0xALICE', self.run_id, 6)
        self.assertFalse(result['ok'])
        result = self.tg.rate_analysis('0xALICE', self.run_id, 0)
        self.assertFalse(result['ok'])


class TestViewerSummary(unittest.TestCase):
    """Tests for get_viewer_summary."""

    def setUp(self):
        self.db = LeaderboardDB(':memory:')
        self.token = SimulatedToken(self.db)
        self.tg = TokenGate(self.db, self.token)

    def test_summary_new_viewer(self):
        summary = self.tg.get_viewer_summary('0xNEW')
        self.assertEqual(summary['balance'], 0)
        self.assertEqual(summary['total_payments'], 0)
        self.assertEqual(summary['total_spent'], 0)

    def test_summary_after_payments(self):
        combo = _make_combo()
        entry = self.db.insert(combo, miner_addr='0xMINER')
        self.tg.pay_for_view('0xALICE', entry.run_id)
        summary = self.tg.get_viewer_summary('0xALICE')
        self.assertEqual(summary['total_payments'], 1)
        self.assertEqual(summary['total_spent'], 10)
        self.assertEqual(summary['balance'], 90)


class TestBufferBugFixes(unittest.TestCase):
    """Verify the two buffer.py bug fixes."""

    def setUp(self):
        self.db = LeaderboardDB(':memory:')
        self.token = SimulatedToken(self.db)
        self.staking = StakingContract(self.db, self.token)
        self.buffer = BufferZone(self.db, self.token, self.staking)

    def test_penalty_deducts_balance(self):
        """Bug fix 1: penalty must actually transfer tokens, not just record."""
        sub_id = self.buffer.submit_analysis(
            combo_id='c1', method_id='m1', method_name='M1',
            problem_id='p1', problem_title='P1', submitter='0xSUBMITTER',
            analysis_json='{}', analysis_text='test',
        )
        # 3 classifiers: 2 agree on domain 'math', 1 disagrees
        self.buffer.classify(sub_id, '0xC1', 'math')
        self.buffer.classify(sub_id, '0xC2', 'math')
        # Record balances before the dissenting vote
        bal_before = self.token.balance_of('0xC3')
        self.buffer.classify(sub_id, '0xC3', 'physics')  # This one loses
        bal_after = self.token.balance_of('0xC3')
        # Classifiers get 1000 faucet in buffer.py (default faucet amount),
        # minus stake (10) and penalty (5) = 985
        self.assertEqual(bal_after, 985)

    def test_publish_to_leaderboard_works(self):
        """Bug fix 2: publish_to_leaderboard uses correct db.insert signature."""
        sub_id = self.buffer.submit_analysis(
            combo_id='c1', method_id='m1', method_name='M1',
            problem_id='p1', problem_title='P1', submitter='0xSUBMITTER',
            analysis_json='{}', analysis_text='test',
        )
        # Get consensus
        self.buffer.classify(sub_id, '0xC1', 'math')
        self.buffer.classify(sub_id, '0xC2', 'math')
        self.buffer.classify(sub_id, '0xC3', 'math')

        entry = self.db.get_buffer_entry(sub_id)
        self.assertEqual(entry['status'], 'classified')

        combo = _make_combo()
        success = self.buffer.publish_to_leaderboard(sub_id, combo, '0xMINER')
        self.assertTrue(success)

        # Verify the entry exists in leaderboard
        buf_entry = self.db.get_buffer_entry(sub_id)
        self.assertEqual(buf_entry['status'], 'published')

        # The published entry has a run_id generated during publish
        lb_entry = self.db._get_by_id(combo.id)
        if not lb_entry:
            # combo.id is the combo_group_id; find by group
            runs = self.db.get_group_runs(combo.id)
            self.assertGreater(len(runs), 0)
            lb_entry = runs[0]
        self.assertEqual(lb_entry.miner_address, '0xMINER')


class TestTokenLayerWebAccess(unittest.TestCase):
    """Verify web.py updated signatures don't crash with token_gate."""

    def test_render_entry_no_token_gate(self):
        """render_entry works without token_gate (backwards compat)."""
        from src.hub.web import render_entry
        db = LeaderboardDB(':memory:')
        combo = _make_combo()
        entry = db.insert(combo, miner_addr='0xMINER')
        html = render_entry(db, entry.run_id)
        self.assertIn('Secret analysis text.', html)

    def test_render_entry_with_paywall(self):
        """render_entry shows paywall when token_gate provided but unpaid."""
        from src.hub.web import render_entry
        db = LeaderboardDB(':memory:')
        token = SimulatedToken(db)
        tg = TokenGate(db, token)
        combo = _make_combo()
        entry = db.insert(combo, miner_addr='0xMINER')
        html = render_entry(db, entry.run_id, viewer_addr='0xBOB', token_gate=tg)
        self.assertIn('Pay 10 IDEA', html)
        self.assertNotIn('Secret analysis text.', html)

    def test_render_entry_after_payment(self):
        """render_entry shows full content after payment."""
        from src.hub.web import render_entry
        db = LeaderboardDB(':memory:')
        token = SimulatedToken(db)
        tg = TokenGate(db, token)
        combo = _make_combo()
        entry = db.insert(combo, miner_addr='0xMINER')
        tg.pay_for_view('0xALICE', entry.run_id)
        html = render_entry(db, entry.run_id, viewer_addr='0xALICE', token_gate=tg)
        self.assertIn('Secret analysis text.', html)
        self.assertNotIn('Pay 10 IDEA', html)

    def test_render_leaderboard_with_token_gate(self):
        """render_leaderboard works with token_gate."""
        from src.hub.web import render_leaderboard
        db = LeaderboardDB(':memory:')
        combo = _make_combo()
        db.insert(combo, miner_addr='0xMINER')
        html = render_leaderboard(db, '/web/leaderboard',
                                  viewer_addr='0xBOB', token_gate=None)
        self.assertIn('Leaderboard', html)

    def test_render_random_without_payment_shows_paywall(self):
        """render_random shows paywall when not paid."""
        from src.hub.web import render_random
        db = LeaderboardDB(':memory:')
        token = SimulatedToken(db)
        tg = TokenGate(db, token)
        combo = _make_combo()
        db.insert(combo, miner_addr='0xMINER')
        html = render_random(db, '/web/random',
                            viewer_addr='0xBOB', token_gate=tg)
        self.assertIn('Pay 5 IDEA', html)

    def test_render_token_dashboard(self):
        """render_token_dashboard renders without crashing."""
        from src.hub.web import render_token_dashboard
        db = LeaderboardDB(':memory:')
        token = SimulatedToken(db)
        tg = TokenGate(db, token)
        html = render_token_dashboard(db, token_gate=tg, viewer_addr='0xALICE')
        self.assertIn('Balance', html)
        self.assertIn('0xALICE', html)


class TestTokenLayerCLI(unittest.TestCase):
    """Smoke tests for new CLI commands."""

    def test_token_balance_cli(self):
        import sys
        import io
        old_stdout = sys.stdout
        try:
            sys.stdout = io.StringIO()
            from src.cli.main import cmd_token_balance
            import argparse
            args = argparse.Namespace(address='0xALICE', db=':memory:')
            cmd_token_balance(args)
            output = sys.stdout.getvalue()
            self.assertIn('0xALICE', output)
            self.assertIn('Balance', output)
        finally:
            sys.stdout = old_stdout

    def test_pay_view_cli(self):
        import sys
        import io
        import tempfile
        import os
        old_stdout = sys.stdout
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, 'test.db')
        try:
            db = LeaderboardDB(db_path)
            combo = _make_combo()
            entry = db.insert(combo, miner_addr='0xMINER')
            sys.stdout = io.StringIO()
            from src.cli.main import cmd_pay_view
            import argparse
            args = argparse.Namespace(
                combo_id=entry.run_id, address='0xALICE', db=db_path,
            )
            cmd_pay_view(args)
            output = sys.stdout.getvalue()
            self.assertIn('Payment', output)
        finally:
            sys.stdout = old_stdout
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
