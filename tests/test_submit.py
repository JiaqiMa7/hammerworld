"""Tests for community submissions: DB CRUD, web pages, API, CLI."""
from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hub.leaderboard import LeaderboardDB
from src.hub.web import (
    render_submit_home, render_submit_method, render_submit_problem,
    render_submissions,
)


class TestSubmissionDB(unittest.TestCase):
    """Tests for submissions CRUD in LeaderboardDB."""

    def setUp(self):
        self.db = LeaderboardDB(":memory:")

    def test_submit_method(self):
        sid = self.db.submit("method", {"name": "Test", "domain": "physics", "level": 2, "description": "Desc"})
        assert sid == 1
        pending = self.db.get_pending_submissions("method")
        assert len(pending) == 1
        assert pending[0]["type"] == "method"
        assert json.loads(pending[0]["data"])["name"] == "Test"

    def test_submit_problem(self):
        sid = self.db.submit("problem", {"title": "Prob", "domain": "energy", "description": "Hard"})
        assert sid == 1
        pending = self.db.get_pending_submissions("problem")
        assert len(pending) == 1
        assert pending[0]["type"] == "problem"

    def test_get_all_pending(self):
        self.db.submit("method", {"name": "M"}, "user1")
        self.db.submit("problem", {"title": "P"}, "user2")
        assert self.db.total_pending() == 2
        assert self.db.total_pending("method") == 1
        assert self.db.total_pending("problem") == 1

    def test_approve_submission(self):
        sid = self.db.submit("method", {"name": "ApproveMe", "domain": "bio"}, "alice")
        data = self.db.approve_submission(sid)
        assert data is not None
        assert data["name"] == "ApproveMe"
        assert self.db.total_pending() == 0
        approved = self.db.get_approved_methods()
        assert len(approved) == 1
        assert approved[0]["name"] == "ApproveMe"

    def test_approve_nonexistent(self):
        assert self.db.approve_submission(999) is None

    def test_reject_submission(self):
        sid = self.db.submit("problem", {"title": "RejectMe"}, "bob")
        assert self.db.reject_submission(sid) is True
        assert self.db.total_pending() == 0
        assert self.db.reject_submission(999) is False

    def test_approve_only_pending(self):
        sid = self.db.submit("method", {"name": "OnlyOnce"})
        self.db.approve_submission(sid)
        assert self.db.approve_submission(sid) is None  # already approved, not pending

    def test_submitter_stored(self):
        self.db.submit("method", {"name": "Signed"}, "0xALICE")
        pending = self.db.get_pending_submissions()
        assert pending[0]["submitter"] == "0xALICE"


class TestSubmissionWebPages(unittest.TestCase):
    """Tests for submission web page rendering."""

    def test_submit_home_renders(self):
        html = render_submit_home()
        assert "Community Submit" in html
        assert "Submit Method" in html
        assert "Submit Problem" in html
        assert "/web/submit/method" in html
        assert "/web/submit/problem" in html
        assert "<nav>" in html

    def test_submit_method_form_renders(self):
        html = render_submit_method()
        assert "Submit Method" in html
        assert 'name="name"' in html
        assert 'name="domain"' in html
        assert 'name="level"' in html
        assert 'name="description"' in html

    def test_submit_method_with_errors(self):
        html = render_submit_method(errors=["Name required", "Level must be 1-4"])
        assert "Name required" in html
        assert "Level must be 1-4" in html

    def test_submit_method_with_success(self):
        html = render_submit_method(success="Method submitted! ID: 5")
        assert "Method submitted! ID: 5" in html

    def test_submit_problem_form_renders(self):
        html = render_submit_problem()
        assert "Submit Problem" in html
        assert 'name="title"' in html
        assert 'name="domain"' in html
        assert 'name="description"' in html

    def test_submit_problem_with_errors(self):
        html = render_submit_problem(errors=["Title required"])
        assert "Title required" in html

    def test_submissions_page_empty(self):
        db = LeaderboardDB(":memory:")
        html = render_submissions(db)
        assert "No pending submissions" in html

    def test_submissions_page_with_items(self):
        db = LeaderboardDB(":memory:")
        db.submit("method", {"name": "M1"}, "user1")
        db.submit("problem", {"title": "P1"}, "user2")
        html = render_submissions(db)
        assert "2 pending" in html
        assert "M1" in html or "method" in html.lower()
        assert "user1" in html

    def test_submissions_page_has_action_links(self):
        db = LeaderboardDB(":memory:")
        db.submit("method", {"name": "Test"}, "tester")
        html = render_submissions(db)
        assert "Approve" in html
        assert "Reject" in html

    def test_nav_includes_submit(self):
        html = render_submit_home()
        assert 'href="/web/submit' in html
        assert "Submit" in html


class TestSubmissionAPI(unittest.TestCase):
    """Tests for the HubAPI submission handlers."""

    def test_handle_submit_method_valid(self):
        from src.hub.server import HubAPI
        from src.hub.peer import PeerConfig, PeerManager
        db = LeaderboardDB(":memory:")
        pm = PeerManager(db, PeerConfig())
        api = HubAPI(db, pm)
        result = api.handle_submit_method(json.dumps({
            "name": "API Method", "domain": "math", "level": 3,
            "description": "API submitted method",
        }).encode())
        assert result["ok"] is True
        assert result["id"] == 1

    def test_handle_submit_method_missing_name(self):
        from src.hub.server import HubAPI
        from src.hub.peer import PeerConfig, PeerManager
        db = LeaderboardDB(":memory:")
        pm = PeerManager(db, PeerConfig())
        api = HubAPI(db, pm)
        result = api.handle_submit_method(json.dumps({
            "domain": "math", "level": 3, "description": "No name",
        }).encode())
        assert result["ok"] is False
        assert any("Name" in e for e in result["errors"])

    def test_handle_submit_method_bad_level(self):
        from src.hub.server import HubAPI
        from src.hub.peer import PeerConfig, PeerManager
        db = LeaderboardDB(":memory:")
        pm = PeerManager(db, PeerConfig())
        api = HubAPI(db, pm)
        result = api.handle_submit_method(json.dumps({
            "name": "Bad Level", "domain": "math", "level": 99,
            "description": "Bad level value",
        }).encode())
        assert result["ok"] is False

    def test_handle_submit_problem_valid(self):
        from src.hub.server import HubAPI
        from src.hub.peer import PeerConfig, PeerManager
        db = LeaderboardDB(":memory:")
        pm = PeerManager(db, PeerConfig())
        api = HubAPI(db, pm)
        result = api.handle_submit_problem(json.dumps({
            "title": "API Problem", "domain": "energy",
            "description": "API submitted problem",
        }).encode())
        assert result["ok"] is True

    def test_handle_submit_problem_missing_title(self):
        from src.hub.server import HubAPI
        from src.hub.peer import PeerConfig, PeerManager
        db = LeaderboardDB(":memory:")
        pm = PeerManager(db, PeerConfig())
        api = HubAPI(db, pm)
        result = api.handle_submit_problem(json.dumps({
            "domain": "energy", "description": "No title",
        }).encode())
        assert result["ok"] is False

    def test_handle_submit_method_form_urlencoded(self):
        """Simulate HTML form POST."""
        from src.hub.server import HubAPI
        from src.hub.peer import PeerConfig, PeerManager
        db = LeaderboardDB(":memory:")
        pm = PeerManager(db, PeerConfig())
        api = HubAPI(db, pm)
        body = b"name=Form+Method&domain=bio&level=2&description=From+web+form"
        result = api.handle_submit_method(body)
        assert result["ok"] is True
        pending = db.get_pending_submissions("method")
        assert json.loads(pending[0]["data"])["name"] == "Form Method"


class TestSubmissionEndToEnd(unittest.TestCase):
    """End-to-end submission → approve flow."""

    def test_full_flow(self):
        db = LeaderboardDB(":memory:")
        # Submit
        sid = db.submit("method", {"name": "E2E", "domain": "triz", "level": 1, "description": "Full flow test"}, "e2e_user")
        assert db.total_pending() == 1
        # Approve
        data = db.approve_submission(sid)
        assert data is not None
        assert data["name"] == "E2E"
        # Verify approved
        assert db.total_pending() == 0
        approved = db.get_approved_methods()
        assert len(approved) == 1
        assert approved[0]["submitter"] == "e2e_user"
        # Reject another
        sid2 = db.submit("problem", {"title": "ToReject"}, "bad_actor")
        assert db.total_pending() == 1
        db.reject_submission(sid2)
        assert db.total_pending() == 0


if __name__ == "__main__":
    import unittest
    # Simple test runner without pytest
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
