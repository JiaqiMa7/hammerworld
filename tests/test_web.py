"""Tests for web UI rendering: src/hub/web.py"""
from __future__ import annotations

import threading
import time
import unittest

from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry
from src.hub.peer import PeerManager, PeerConfig
from src.hub.web import (
    render_dashboard, render_leaderboard, render_search,
    render_random, render_peers, render_entry,
)


class TestWebUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = LeaderboardDB(":memory:")
        cls.pm = PeerManager(cls.db, PeerConfig(port=9999))
        cls._seed_data()

    @classmethod
    def _seed_data(cls):
        import time as _time
        t = _time.time()
        for i in range(5):
            entry = LeaderboardEntry(
                rank=0, run_id=f"web_{i}", combo_group_id=f"web_g_{i}",
                method_name=f"TestMethod{i}",
                method_domain=f"Domain{i % 2}", method_level=(i % 4) + 1,
                problem_title=f"TestProblem{i}", problem_domain="medicine",
                best_dimension="weirdness" if i % 2 == 0 else "novelty",
                best_score=9.0 - i * 0.5,
                elegance=5.0, weirdness=8.5, human_feasibility=5.0,
                ai_feasibility=5.0, novelty=7.0, analogy_distance=5.0,
                scaling_potential=5.0, side_effects=5.0,
                miner_address=f"0xMINER_{i}", created_at=t + i,
            )
            cls.db.insert_from_sync(entry)

    def test_dashboard_renders(self):
        html = render_dashboard(self.db, self.pm)
        self.assertIn("Dashboard", html)
        self.assertIn("Idea Mining Network", html)

    def test_dashboard_contains_stats(self):
        html = render_dashboard(self.db, self.pm)
        self.assertIn("Entries", html)
        self.assertIn("Peers", html)

    def test_dashboard_contains_top_table(self):
        html = render_dashboard(self.db, self.pm)
        self.assertIn("TestMethod0", html)
        self.assertIn("TestProblem0", html)

    def test_leaderboard_renders(self):
        html = render_leaderboard(self.db, "/web/leaderboard")
        self.assertIn("Leaderboard", html)
        self.assertIn("TestMethod", html)

    def test_leaderboard_with_dimension_filter(self):
        html = render_leaderboard(self.db, "/web/leaderboard?dim=weirdness")
        self.assertIn("weirdness", html.lower())

    def test_leaderboard_pagination(self):
        html = render_leaderboard(self.db, "/web/leaderboard?limit=2&offset=2")
        self.assertIn("Previous", html)

    def test_search_page_renders(self):
        html = render_search(self.db, "/web/search")
        self.assertIn("Search", html)

    def test_search_with_query(self):
        html = render_search(self.db, "/web/search?q=TestMethod1")
        self.assertIn("TestMethod1", html)

    def test_search_no_results(self):
        html = render_search(self.db, "/web/search?q=nonexistent_xyz")
        self.assertIn("No results", html)

    def test_random_page_renders(self):
        html = render_random(self.db, "/web/random")
        self.assertIn("Random Draw", html)

    def test_random_shows_board_name(self):
        html = render_random(self.db, "/web/random?dim=weirdness&count=3")
        self.assertIn("weirdness_all", html)

    def test_peers_page_renders(self):
        html = render_peers(self.pm)
        self.assertIn("Peers", html)
        self.assertIn("Connected", html)

    def test_peers_shows_peer(self):
        self.pm.add_peer("10.0.0.1", 8765)
        html = render_peers(self.pm)
        self.assertIn("10.0.0.1", html)
        self.pm.remove_peer(self.pm.get_peer_ids()[0])

    def test_entry_detail_renders(self):
        html = render_entry(self.db, "web_0")
        self.assertIn("TestMethod0", html)
        self.assertIn("TestProblem0", html)
        self.assertIn("Elegance", html)

    def test_entry_not_found(self):
        html = render_entry(self.db, "nonexistent")
        self.assertIn("not found", html.lower())

    def test_html_escapes_script_tags(self):
        db = LeaderboardDB(":memory:")
        entry = LeaderboardEntry(
            rank=0, run_id="xss_test", combo_group_id="xss_test_g",
            method_name="<script>alert(1)</script>",
            method_domain="D", method_level=1,
            problem_title="<b>Bad</b>", problem_domain="medicine",
            best_dimension="elegance", best_score=5.0,
            elegance=5.0, weirdness=5.0, human_feasibility=5.0,
            ai_feasibility=5.0, novelty=5.0, analogy_distance=5.0,
            scaling_potential=5.0, side_effects=5.0,
            miner_address="0xM", created_at=time.time(),
        )
        db.insert_from_sync(entry)
        html = render_entry(db, "xss_test")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestLoginWidget(unittest.TestCase):
    """Tests for the login/logout widget and cookie-based session."""

    def test_login_widget_logged_out(self):
        from src.hub.web import _login_widget
        html = _login_widget("", "en")
        self.assertIn('action="/web/login"', html)
        self.assertIn('name="address"', html)

    def test_login_widget_logged_in(self):
        from src.hub.web import _login_widget
        html = _login_widget("0xABCDEF1234567890", "en")
        self.assertIn("0xABCDEF", html)
        self.assertIn('href="/web/logout"', html)

    def test_login_widget_chinese(self):
        from src.hub.web import _login_widget
        html = _login_widget("", "zh")
        self.assertIn('action="/web/login"', html)

    def test_login_widget_short_address(self):
        from src.hub.web import _login_widget
        html = _login_widget("0xAB", "en")
        self.assertIn("0xAB", html)

    def test_login_widget_create_button(self):
        """Logged-out widget should show 'Create new address' button."""
        from src.hub.web import _login_widget
        html = _login_widget("", "en")
        self.assertIn('action="/web/create-address"', html)
        self.assertIn("Create new address", html)

    def test_login_widget_create_button_chinese(self):
        """Chinese locale should show the create button in Chinese."""
        from src.hub.web import _login_widget
        html = _login_widget("", "zh")
        self.assertIn("创建新地址", html)

    def test_login_widget_no_create_button_when_logged_in(self):
        """Logged-in widget should NOT show the create button."""
        from src.hub.web import _login_widget
        html = _login_widget("0xABCDEF1234567890", "en")
        self.assertNotIn("create-address", html)

    def test_base_page_includes_login_widget(self):
        from src.hub.web import _base_page
        html = _base_page("Test", "<p>content</p>", lang="en", viewer_addr="0xUSER")
        self.assertIn("login-widget", html)
        self.assertIn("0xUSER", html)

    def test_base_page_no_viewer(self):
        from src.hub.web import _base_page
        html = _base_page("Test", "<p>content</p>", lang="en")
        self.assertIn("login-widget", html)
        self.assertIn('action="/web/login"', html)

    def test_dashboard_passes_viewer(self):
        from src.hub.peer import PeerManager, PeerConfig
        db = LeaderboardDB(":memory:")
        pm = PeerManager(PeerConfig(port=9999))
        html = render_dashboard(db, pm, lang="en", viewer_addr="0xDASH")
        self.assertIn("0xDASH", html)

    def test_leaderboard_includes_viewer(self):
        db = LeaderboardDB(":memory:")
        html = render_leaderboard(db, "/web/leaderboard", viewer_addr="0xLB", lang="en")
        self.assertIn("login-widget", html)

    def test_entry_includes_viewer(self):
        db = LeaderboardDB(":memory:")
        entry = LeaderboardEntry(
            rank=0, run_id="test_login_entry", combo_group_id="test_login_entry_g",
            method_name="M",
            method_domain="D", method_level=1,
            problem_title="P", problem_domain="medicine",
            best_dimension="elegance", best_score=5.0,
            elegance=5.0, weirdness=5.0, human_feasibility=5.0,
            ai_feasibility=5.0, novelty=5.0, analogy_distance=5.0,
            scaling_potential=5.0, side_effects=5.0,
            miner_address="0xM", created_at=time.time(),
        )
        db.insert_from_sync(entry)
        html = render_entry(db, "test_login_entry", viewer_addr="0xENTRY")
        self.assertIn("0xENTRY", html)


if __name__ == "__main__":
    unittest.main()
