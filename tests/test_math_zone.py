"""Tests for Math Research Zone: DB CRUD, web pages, CLI."""
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
from src.hub.web import (
    render_math_home, render_math_new, render_math_problem,
    render_math_method_zone, render_math_solution, render_math_unlock,
)


class TestMathZoneDB(unittest.TestCase):
    """Tests for math zone CRUD in LeaderboardDB."""

    def setUp(self):
        self.db = LeaderboardDB(":memory:")

    def test_create_math_problem(self):
        pid = self.db.create_math_problem(
            "Riemann Hypothesis", "Prove all non-trivial zeros...",
            "number_theory", "alice")
        self.assertEqual(pid, 1)

        p = self.db.get_math_problem(1)
        self.assertEqual(p["title"], "Riemann Hypothesis")
        self.assertEqual(p["category"], "number_theory")
        self.assertEqual(p["creator"], "alice")
        self.assertEqual(p["status"], "active")

    def test_get_math_problems_filtered(self):
        self.db.create_math_problem("P1", "desc", "algebra", "u1")
        self.db.create_math_problem("P2", "desc", "geometry", "u2")
        self.db.create_math_problem("P3", "desc", "analysis", "u3")

        active = self.db.get_math_problems("active")
        self.assertEqual(len(active), 3)

        # Mark one as solved
        self.db.update_math_problem_status(2, "solved")
        active = self.db.get_math_problems("active")
        self.assertEqual(len(active), 2)

    def test_get_math_problem_not_found(self):
        self.assertIsNone(self.db.get_math_problem(999))

    def test_submit_math_solution(self):
        pid = self.db.create_math_problem("Test Problem", "desc")
        # Create a method collection for the solution
        cid = self.db.create_collection("method", "Math Tools", "desc",
                                        "mathematics", "alice",
                                        [{"name": "Tool1", "domain": "mathematics", "level": 1, "description": "d"}])
        steps = [
            {"step_num": 1, "content": "Define the problem", "verified": True},
            {"step_num": 2, "content": "Apply theorem A", "verified": True},
            {"step_num": 3, "content": "Attempt proof", "verified": False},
        ]
        sid = self.db.submit_math_solution(pid, cid, "0xSOLVER", steps)
        self.assertEqual(sid, 1)

        s = self.db.get_math_solution(1)
        self.assertEqual(s["problem_id"], 1)
        self.assertEqual(s["method_collection_id"], 1)
        self.assertEqual(s["user_address"], "0xSOLVER")
        self.assertEqual(s["max_correct_step"], 2)

    def test_calc_max_correct_step(self):
        # All verified
        self.assertEqual(self.db._calc_max_correct_step([
            {"step_num": 1, "verified": True},
            {"step_num": 2, "verified": True},
        ]), 2)

        # Break at step 2
        self.assertEqual(self.db._calc_max_correct_step([
            {"step_num": 1, "verified": True},
            {"step_num": 2, "verified": False},
            {"step_num": 3, "verified": True},
        ]), 1)

        # None verified
        self.assertEqual(self.db._calc_max_correct_step([
            {"step_num": 1, "verified": False},
        ]), 0)

        # Empty
        self.assertEqual(self.db._calc_max_correct_step([]), 0)

    def test_get_math_solutions_sorted(self):
        pid = self.db.create_math_problem("P", "desc")
        cid = self.db.create_collection("method", "Math Pack", "desc",
                                        "mathematics", "u",
                                        [{"name": "M", "domain": "mathematics", "level": 1, "description": "d"}])
        steps_a = [{"step_num": 1, "content": "a", "verified": True}]
        steps_b = [{"step_num": 1, "content": "b", "verified": True},
                   {"step_num": 2, "content": "b", "verified": True},
                   {"step_num": 3, "content": "b", "verified": True}]
        self.db.submit_math_solution(pid, cid, "u1", steps_a)
        self.db.submit_math_solution(pid, cid, "u2", steps_b)

        solutions = self.db.get_math_solutions(pid, cid)
        self.assertEqual(len(solutions), 2)
        # Highest max_correct_step first
        self.assertEqual(solutions[0]["max_correct_step"], 3)
        self.assertEqual(solutions[1]["max_correct_step"], 1)

    def test_fork_math_solution(self):
        pid = self.db.create_math_problem("P", "desc")
        cid = self.db.create_collection("method", "Math Pack", "desc",
                                        "mathematics", "u",
                                        [{"name": "M", "domain": "mathematics", "level": 1, "description": "d"}])
        steps = [{"step_num": 1, "content": "original", "verified": True}]
        original_sid = self.db.submit_math_solution(pid, cid, "alice", steps)

        new_sid = self.db.fork_math_solution(original_sid, "bob")
        self.assertGreater(new_sid, 0)
        self.assertNotEqual(new_sid, original_sid)

        forked = self.db.get_math_solution(new_sid)
        self.assertEqual(forked["user_address"], "bob")
        self.assertEqual(forked["parent_solution_id"], original_sid)
        self.assertEqual(forked["max_correct_step"], 1)

    def test_fork_nonexistent_returns_zero(self):
        result = self.db.fork_math_solution(999, "bob")
        self.assertEqual(result, 0)

    def test_update_math_solution(self):
        pid = self.db.create_math_problem("P", "desc")
        cid = self.db.create_collection("method", "Math Pack", "desc",
                                        "mathematics", "u",
                                        [{"name": "M", "domain": "mathematics", "level": 1, "description": "d"}])
        sid = self.db.submit_math_solution(pid, cid, "u1",
                                           [{"step_num": 1, "verified": True}])

        new_steps = [
            {"step_num": 1, "content": "v2", "verified": True},
            {"step_num": 2, "content": "v2", "verified": False},
        ]
        self.db.update_math_solution(sid, new_steps)

        updated = self.db.get_math_solution(sid)
        self.assertEqual(updated["max_correct_step"], 1)
        loaded = json.loads(updated["steps_json"])
        self.assertEqual(len(loaded), 2)

    def test_check_and_grant_math_access(self):
        pid = self.db.create_math_problem("P", "desc")
        cid = self.db.create_collection("method", "Math Pack", "desc",
                                        "mathematics", "u",
                                        [{"name": "M", "domain": "mathematics", "level": 1, "description": "d"}])

        self.assertFalse(self.db.check_math_access(pid, cid, "0xUSER"))

        self.db.grant_math_access(pid, cid, "0xUSER", "combo_abc", '{"score": 8.5}')
        self.assertTrue(self.db.check_math_access(pid, cid, "0xUSER"))

        # Check access log
        log = self.db.get_math_access_log(pid, "0xUSER")
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["combo_id"], "combo_abc")

    def test_update_math_problem_status(self):
        pid = self.db.create_math_problem("P", "desc")
        self.assertEqual(self.db.get_math_problem(pid)["status"], "active")
        self.db.update_math_problem_status(pid, "solved")
        self.assertEqual(self.db.get_math_problem(pid)["status"], "solved")


class TestMathWebPages(unittest.TestCase):
    """Tests for math zone web page rendering."""

    def _setup_test_data(self):
        """Create a math problem and a math method collection."""
        db = LeaderboardDB(":memory:")
        pid = db.create_math_problem(
            "Riemann Hypothesis",
            "Prove that all non-trivial zeros of the zeta function lie on the critical line.",
            "number_theory", "alice")
        cid = db.create_collection("method", "Complex Analysis Tools",
                                   "Tools for complex analysis",
                                   "mathematics", "bob",
                                   [{"name": "Contour Integration", "domain": "mathematics", "level": 3, "description": "..."},
                                    {"name": "Residue Theorem", "domain": "mathematics", "level": 3, "description": "..."}])
        return db, pid, cid

    def test_math_home_empty(self):
        db = LeaderboardDB(":memory:")
        html = render_math_home(db)
        self.assertIn("Math Research Zone", html)
        self.assertIn("No math problem zones yet", html)
        self.assertIn('href="/web/math/new"', html)

    def test_math_home_with_problems(self):
        db = LeaderboardDB(":memory:")
        db.create_math_problem("Riemann Hypothesis", "desc", "number_theory", "alice")
        db.create_math_problem("P vs NP", "desc", "combinatorics", "bob")
        html = render_math_home(db)
        self.assertIn("Riemann Hypothesis", html)
        self.assertIn("P vs NP", html)
        self.assertIn("0 solution(s)", html)

    def test_math_new_form(self):
        html = render_math_new()
        self.assertIn("New Math Problem", html)
        self.assertIn('name="title"', html)
        self.assertIn('name="category"', html)
        self.assertIn('name="description"', html)
        self.assertIn('name="creator"', html)
        self.assertIn("Create Problem Zone", html)

    def test_math_new_with_errors(self):
        html = render_math_new(form={"title": "Test"}, errors=["Title is required"])
        self.assertIn("Title is required", html)
        self.assertIn('value="Test"', html)

    def test_math_problem_renders(self):
        db, pid, cid = self._setup_test_data()
        html = render_math_problem(db, pid, "/web/math/1")
        self.assertIn("Riemann Hypothesis", html)
        self.assertIn("Complex Analysis Tools", html)
        self.assertIn("Method Zones", html)
        self.assertIn("Locked", html)  # No access yet

    def test_math_problem_with_access(self):
        db, pid, cid = self._setup_test_data()
        db.grant_math_access(pid, cid, "0xALICE", "combo_1", "{}")
        html = render_math_problem(db, pid, "/web/math/1?user_address=0xALICE")
        self.assertIn("Unlocked", html)

    def test_math_unlock_page(self):
        db, pid, cid = self._setup_test_data()
        html = render_math_unlock(db, pid, cid, "/web/math/1/1/unlock")
        self.assertIn("Unlock", html)
        self.assertIn("math-mine", html)
        self.assertIn('name="combo_id"', html)
        self.assertIn('name="user_address"', html)

    def test_math_unlock_when_already_unlocked(self):
        db, pid, cid = self._setup_test_data()
        db.grant_math_access(pid, cid, "0xALICE", "combo_1", "{}")
        html = render_math_unlock(db, pid, cid, "/web/math/1/1/unlock?user_address=0xALICE")
        self.assertIn("Already Unlocked", html)

    def test_math_method_zone_locked(self):
        db, pid, cid = self._setup_test_data()
        html = render_math_method_zone(db, pid, cid, "/web/math/1/1")
        self.assertIn("Access Required", html)

    def test_math_method_zone_unlocked(self):
        db, pid, cid = self._setup_test_data()
        db.grant_math_access(pid, cid, "0xALICE", "combo_1", "{}")
        # Add a solution
        steps = [{"step_num": 1, "content": "Step 1", "verified": True}]
        db.submit_math_solution(pid, cid, "0xBOB", steps)
        html = render_math_method_zone(db, pid, cid, "/web/math/1/1?user_address=0xALICE")
        self.assertIn("Solutions", html)
        self.assertIn("0xBOB", html)

    def test_math_solution_detail(self):
        db, pid, cid = self._setup_test_data()
        steps = [
            {"step_num": 1, "content": "Define zeta function", "verified": True},
            {"step_num": 2, "content": "Apply contour integral", "verified": False},
        ]
        sid = db.submit_math_solution(pid, cid, "0xEULER", steps,
                                      seed_combo_id="combo_1",
                                      seed_analysis="test analysis")
        html = render_math_solution(db, pid, cid, sid, f"/web/math/{pid}/{cid}/{sid}")
        self.assertIn("Solution #" + str(sid), html)
        self.assertIn("Define zeta function", html)
        self.assertIn("0xEULER", html)
        self.assertIn("Fork", html)
        self.assertIn("Submit Improvement", html)

    def test_math_solution_fork_form(self):
        db, pid, cid = self._setup_test_data()
        sid = db.submit_math_solution(pid, cid, "0xEULER",
                                      [{"step_num": 1, "content": "s1", "verified": True}])
        html = render_math_solution(db, pid, cid, sid, f"/web/math/{pid}/{cid}/{sid}?fork=1&user_address=0xGAUSS")
        self.assertIn("Confirm Fork", html)

    def test_nav_includes_math_zone(self):
        db = LeaderboardDB(":memory:")
        html = render_math_home(db)
        self.assertIn('href="/web/math"', html)
        self.assertIn("Math Zone", html)


class TestMathCLI(unittest.TestCase):
    """Tests for math zone CLI commands."""

    @classmethod
    def setUpClass(cls):
        os.environ["HAMMERWORLD_API_KEY"] = "sk-test-math-cli"

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("HAMMERWORLD_API_KEY", None)

    def setUp(self):
        import src.evaluation.providers as p
        self._orig_provider = p.OpenAIProvider

        class _FakeProvider:
            def __init__(self, api_key=None, api_base=None, model=None):
                pass

            def generate(self, system_prompt, user_prompt):
                return '```json\n{"scores": [{"dimension": "elegance", "score": 8.5, "explanation": "test"}], "analysis_text": "Fake math analysis."}\n```'

        p.OpenAIProvider = _FakeProvider

    def tearDown(self):
        import src.evaluation.providers as p
        p.OpenAIProvider = self._orig_provider

    class _Args:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def test_math_submit_creates_solution(self):
        from src.cli.main import cmd_math_submit

        db_path = tempfile.mktemp(suffix=".db")
        db = LeaderboardDB(db_path)
        pid = db.create_math_problem("Test Problem", "desc")
        cid = db.create_collection("method", "Test Tools", "desc",
                                   "mathematics", "u",
                                   [{"name": "T", "domain": "mathematics", "level": 1, "description": "d"}])
        steps = json.dumps([{"step_num": 1, "content": "s1", "verified": True}])

        args = self._Args(
            problem_id=pid, method_collection_id=cid,
            steps_json=steps, parent_id=None,
            address="0xCLI", db=db_path,
        )

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_math_submit(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertIn("Solution submitted", output)
        self.assertIn("Max correct step: 1", output)
        # Verify in DB (re-open to read back)
        db2 = LeaderboardDB(db_path)
        solutions = db2.get_math_solutions(pid, cid)
        self.assertEqual(len(solutions), 1)
        os.unlink(db_path)

    def test_math_submit_fork(self):
        from src.cli.main import cmd_math_submit

        db_path = tempfile.mktemp(suffix=".db")
        db = LeaderboardDB(db_path)
        pid = db.create_math_problem("Fork Problem", "desc")
        cid = db.create_collection("method", "Fork Tools", "desc",
                                   "mathematics", "u",
                                   [{"name": "F", "domain": "mathematics", "level": 1, "description": "d"}])
        orig_sid = db.submit_math_solution(pid, cid, "alice",
                                           [{"step_num": 1, "content": "original", "verified": True}])
        steps = json.dumps([{"step_num": 1, "content": "improved", "verified": True}])

        args = self._Args(
            problem_id=pid, method_collection_id=cid,
            steps_json=steps, parent_id=orig_sid,
            address="0xBOB", db=db_path,
        )

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_math_submit(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertIn("Forked from solution #" + str(orig_sid), output)
        os.unlink(db_path)

    def test_math_mine_grants_access(self):
        from src.cli.main import cmd_math_mine

        db_path = tempfile.mktemp(suffix=".db")
        db = LeaderboardDB(db_path)
        pid = db.create_math_problem("Mine Problem", "desc")
        cid = db.create_collection("method", "Mine Tools", "desc",
                                   "mathematics", "u",
                                   [{"name": "M1", "domain": "mathematics", "level": 1, "description": "d"},
                                    {"name": "M2", "domain": "mathematics", "level": 2, "description": "d"}])

        args = self._Args(
            problem_id=pid, methods_collection="Mine Tools",
            address="0xMINER", block_height=100, nonce=0,
            batch=2, db=db_path, threshold=8.0,
            model=None, api_base=None, parallel=1,
            method_step=0, max_attempts=0,
        )

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cmd_math_mine(args)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        self.assertIn("Access granted", output)
        # Verify access was actually granted
        db2 = LeaderboardDB(db_path)
        self.assertTrue(db2.check_math_access(pid, cid, "0xMINER"))
        os.unlink(db_path)

    def test_math_mine_missing_problem(self):
        from src.cli.main import cmd_math_mine

        db = LeaderboardDB(":memory:")

        args = self._Args(
            problem_id=999, methods_collection="NoSuch",
            address="0xMINER", block_height=1, nonce=0,
            batch=1, db=":memory:", threshold=8.0,
            model=None, api_base=None, parallel=1,
            method_step=0, max_attempts=0,
        )

        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            with self.assertRaises(SystemExit) as ctx:
                cmd_math_mine(args)
        finally:
            sys.stderr = old_stderr
        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
