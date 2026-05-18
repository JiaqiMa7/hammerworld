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
    render_math_tree, render_math_tree_node,
    _render_tree_stats, _render_tree_recursive,
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
        self.assertIn('href="/web/math/new', html)

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
        self.assertIn('href="/web/math', html)
        self.assertIn("Math Zone", html)


class TestMathCLI(unittest.TestCase):
    """Tests for math zone CLI commands."""

    def setUp(self):
        os.environ["HAMMERWORLD_API_KEY"] = "sk-test-math-cli"
        from src.engine.config import HammerConfig
        HammerConfig.reload()
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
        os.environ.pop("HAMMERWORLD_API_KEY", None)

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


class TestMathTreeNodeCRUD(unittest.TestCase):
    """Tests for MCTS tree node and edge CRUD."""

    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.pid = self.db.create_math_problem("Tree Problem", "desc", "algebra", "alice")
        self.cid = self.db.create_collection(
            "method", "Tree Tools", "desc", "mathematics", "bob",
            [{"name": "M1", "domain": "mathematics", "level": 1, "description": "d"}])

    def test_create_and_get_node(self):
        nid = self.db.create_tree_node(self.pid, self.cid, "0xT", "State 1", "normal", 0.5, 10)
        self.assertGreater(nid, 0)
        node = self.db.get_tree_node(nid)
        self.assertEqual(node["content"], "State 1")
        self.assertEqual(node["q_value"], 0.5)
        self.assertEqual(node["visit_count"], 10)
        self.assertEqual(node["node_type"], "normal")

    def test_get_root_node_auto_create(self):
        root = self.db.get_root_node(self.pid, self.cid)
        self.assertIsNotNone(root)
        self.assertEqual(root["is_root"], 1)
        self.assertEqual(root["content"], "Tree Problem")
        # Second call returns same root
        root2 = self.db.get_root_node(self.pid, self.cid)
        self.assertEqual(root["id"], root2["id"])

    def test_create_edge(self):
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Parent")
        n2 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Child")
        eid = self.db.create_tree_edge(n1, n2, "因式分解", "Factor the expression")
        self.assertGreater(eid, 0)
        children = self.db.get_children(n1)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0]["action_label"], "因式分解")
        self.assertEqual(children[0]["child_content"], "Child")

    def test_edge_cycle_prevention(self):
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Parent")
        n2 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Child")
        self.db.create_tree_edge(n1, n2, "step")
        with self.assertRaises(ValueError):
            self.db.create_tree_edge(n2, n1, "back-edge")

    def test_update_tree_node(self):
        nid = self.db.create_tree_node(self.pid, self.cid, "0xT", "Test")
        self.db.update_tree_node(nid, q_value=0.75, visit_count=20, node_type="terminal_success", reward=1.0)
        node = self.db.get_tree_node(nid)
        self.assertEqual(node["q_value"], 0.75)
        self.assertEqual(node["visit_count"], 20)
        self.assertEqual(node["node_type"], "terminal_success")
        self.assertEqual(node["reward"], 1.0)

    def test_get_terminal_nodes(self):
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Normal")
        n2 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Success", "terminal_success", reward=1.0)
        n3 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Failure", "terminal_failure", reward=0.0)
        terms = self.db.get_terminal_nodes(self.pid, self.cid)
        self.assertEqual(len(terms), 2)

    def test_get_tree_nodes_for_zone(self):
        self.db.create_tree_node(self.pid, self.cid, "0xA", "N1")
        self.db.create_tree_node(self.pid, self.cid, "0xB", "N2")
        nodes = self.db.get_tree_nodes_for_zone(self.pid, self.cid)
        self.assertEqual(len(nodes), 2)

    def test_count_children(self):
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Parent")
        n2 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Child1")
        n3 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Child2")
        self.db.create_tree_edge(n1, n2, "a")
        self.db.create_tree_edge(n1, n3, "b")
        self.assertEqual(self.db.count_children(n1), 2)

    def test_get_parent_node(self):
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Parent")
        n2 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Child")
        self.db.create_tree_edge(n1, n2, "edge")
        parent = self.db._get_parent_node(n2)
        self.assertIsNotNone(parent)
        self.assertEqual(parent["id"], n1)

    def test_get_path_to_root(self):
        root = self.db.get_root_node(self.pid, self.cid)
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "N1")
        n2 = self.db.create_tree_node(self.pid, self.cid, "0xT", "N2")
        self.db.create_tree_edge(root["id"], n1, "a")
        self.db.create_tree_edge(n1, n2, "b")
        path = self.db._get_path_to_root(n2)
        self.assertEqual(path, [n2, n1, root["id"]])


class TestMCTSBackpropagation(unittest.TestCase):
    """Tests for MCTS backpropagation and Q-value updates."""

    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.pid = self.db.create_math_problem("Backprop Test", "desc", "algebra", "me")
        self.cid = self.db.create_collection(
            "method", "BP Tools", "desc", "mathematics", "u",
            [{"name": "M", "domain": "mathematics", "level": 1, "description": "d"}])
        self.root = self.db.get_root_node(self.pid, self.cid)

    def test_single_path_backprop(self):
        # root -> n1 (terminal success)
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Success",
                                       "terminal_success", reward=1.0)
        self.db.create_tree_edge(self.root["id"], n1, "prove")
        self.db.backpropagate(n1, 1.0)

        n1_after = self.db.get_tree_node(n1)
        self.assertEqual(n1_after["q_value"], 1.0)
        self.assertEqual(n1_after["visit_count"], 1)

        root_after = self.db.get_tree_node(self.root["id"])
        self.assertEqual(root_after["q_value"], 1.0)
        self.assertEqual(root_after["visit_count"], 1)

    def test_two_paths_backprop(self):
        # root -> n1 (success, reward=1.0)
        # root -> n2 (failure, reward=0.0)
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Success",
                                       "terminal_success", reward=1.0)
        n2 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Failure",
                                       "terminal_failure", reward=0.0)
        self.db.create_tree_edge(self.root["id"], n1, "good path")
        self.db.create_tree_edge(self.root["id"], n2, "bad path")

        self.db.backpropagate(n1, 1.0)
        self.db.backpropagate(n2, 0.0)

        root_after = self.db.get_tree_node(self.root["id"])
        # Root should have Q = (1.0 + 0.0) / 2 = 0.5, N = 2
        self.assertAlmostEqual(root_after["q_value"], 0.5, places=3)
        self.assertEqual(root_after["visit_count"], 2)

    def test_deep_path_backprop(self):
        # root -> n1 -> n2 -> n3 (success)
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Step 1")
        n2 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Step 2")
        n3 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Proved",
                                       "terminal_success", reward=1.0)
        self.db.create_tree_edge(self.root["id"], n1, "expand")
        self.db.create_tree_edge(n1, n2, "factor")
        self.db.create_tree_edge(n2, n3, "conclude")

        self.db.backpropagate(n3, 1.0)

        # All ancestors should get Q=1.0, N=1
        for nid in [n3, n2, n1, self.root["id"]]:
            node = self.db.get_tree_node(nid)
            self.assertAlmostEqual(node["q_value"], 1.0, places=3)
            self.assertEqual(node["visit_count"], 1)

    def test_prune_node(self):
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "PruneMe")
        self.db.create_tree_edge(self.root["id"], n1, "dead end")
        self.db.prune_node(n1)

        pruned = self.db.get_tree_node(n1)
        self.assertEqual(pruned["node_type"], "pruned")
        # Root got backpropagated with 0.0 reward
        root_after = self.db.get_tree_node(self.root["id"])
        self.assertAlmostEqual(root_after["q_value"], 0.0, places=3)

    def test_uct_scores_unvisited_children(self):
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Visited",
                                       visit_count=10)
        n2 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Unvisited",
                                       visit_count=0)
        self.db.create_tree_edge(self.root["id"], n1, "explored")
        self.db.create_tree_edge(self.root["id"], n2, "unexplored")
        # Give root some visits so UCT is meaningful
        self.db.update_tree_node(self.root["id"], visit_count=15)

        uct = self.db.get_uct_scores(self.root["id"])
        # Unvisited node should have UCT=inf (highest priority)
        self.assertEqual(len(uct), 2)
        uct_values = {c["action_label"]: c.get("uct_score") for c in uct}
        self.assertEqual(uct_values["unexplored"], float('inf'))


class TestTreeWebPages(unittest.TestCase):
    """Tests for tree web page rendering."""

    def setUp(self):
        self.db = LeaderboardDB(":memory:")
        self.pid = self.db.create_math_problem("Riemann Hypothesis",
            "Prove all non-trivial zeros...", "number_theory", "alice")
        self.cid = self.db.create_collection(
            "method", "Complex Analysis", "Tools for complex analysis",
            "mathematics", "bob",
            [{"name": "Contour Integration", "domain": "mathematics", "level": 3, "description": "..."}])

    def test_tree_page_renders(self):
        self.db.get_root_node(self.pid, self.cid)  # ensure root exists
        html = render_math_tree(self.db, self.pid, self.cid, "/web/math/1/1/tree")
        self.assertIn("tree-node", html)
        self.assertIn("Riemann Hypothesis", html)
        self.assertIn("Complex Analysis", html)

    def test_tree_page_empty(self):
        """Tree page without a problem shows not found."""
        html = render_math_tree(self.db, 999, 999, "/web/math/999/999/tree")
        self.assertIn("Not Found", html)

    def test_tree_node_page_renders(self):
        root = self.db.get_root_node(self.pid, self.cid)
        html = render_math_tree_node(self.db, self.pid, self.cid, root["id"],
                                      f"/web/math/{self.pid}/{self.cid}/tree/node/{root['id']}")
        self.assertIn("tree-node", html)
        self.assertIn("Riemann Hypothesis", html)
        self.assertIn("Add Child Node", html)
        self.assertIn("backpropagate", html)

    def test_tree_node_page_with_errors(self):
        root = self.db.get_root_node(self.pid, self.cid)
        html = render_math_tree_node(self.db, self.pid, self.cid, root["id"],
                                      "/web/math/1/1/tree/node/1",
                                      errors=["Content is required."])
        self.assertIn("Content is required.", html)

    def test_tree_node_page_not_found(self):
        html = render_math_tree_node(self.db, 999, 999, 999, "/web/math/999/999/tree/node/999")
        self.assertIn("Not Found", html)

    def test_tree_stats(self):
        root = self.db.get_root_node(self.pid, self.cid)
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Success",
                                       "terminal_success", reward=1.0)
        self.db.create_tree_edge(root["id"], n1, "prove")
        stats = _render_tree_stats(self.db, self.pid, self.cid)
        self.assertIn("States", stats)
        self.assertIn("Proofs", stats)

    def test_tree_recursive_empty(self):
        root = self.db.get_root_node(self.pid, self.cid)
        rec = _render_tree_recursive(self.db, root["id"])
        self.assertIn("tree-node", rec)
        self.assertIn("Riemann Hypothesis", rec)

    def test_tree_recursive_with_children(self):
        root = self.db.get_root_node(self.pid, self.cid)
        n1 = self.db.create_tree_node(self.pid, self.cid, "0xT", "Step 1")
        self.db.create_tree_edge(root["id"], n1, "因式分解")
        rec = _render_tree_recursive(self.db, root["id"])
        self.assertIn("因式分解", rec)
        self.assertIn("Step 1", rec)

    def test_method_zone_has_tree_link(self):
        html = render_math_method_zone(self.db, self.pid, self.cid, "/web/math/1/1")
        self.assertIn("Tree View", html)

    def test_solution_page_has_deprecation_banner(self):
        steps = [{"step_num": 1, "content": "s1", "verified": True}]
        sid = self.db.submit_math_solution(self.pid, self.cid, "0xSOLVER", steps)
        html = render_math_solution(self.db, self.pid, self.cid, sid, f"/web/math/1/1/{sid}")
        self.assertIn("deprecated", html.lower())
        self.assertIn("Tree View", html)


class TestNewMathCLI(unittest.TestCase):
    """Tests for the new math zone CLI view and action commands."""

    class _Args:
        """Simple argparse.Namespace stand-in."""
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def setUp(self):
        self.db_path = tempfile.mktemp(suffix=".db")
        self.db = LeaderboardDB(self.db_path)
        # Seed: problem + method collection + solution + tree
        self.pid = self.db.create_math_problem(
            "Goldbach Conjecture", "Every even integer > 2 is sum of two primes",
            "number_theory", "alice")
        self.cid = self.db.create_collection(
            "method", "Number Theory", "desc", "mathematics", "bob",
            [{"name": "Modular Arithmetic", "domain": "mathematics", "level": 2, "description": "d"}])
        self.steps = [
            {"step_num": 1, "content": "Let 2n be even", "verified": True},
            {"step_num": 2, "content": "Apply theorem", "verified": True},
            {"step_num": 3, "content": "Attempt", "verified": False},
        ]
        self.sid = self.db.submit_math_solution(self.pid, self.cid, "0xALICE", self.steps)
        # Grant access + seed tree
        self.db.grant_math_access(self.pid, self.cid, "0xALICE", "combo_001", "{}")
        self.root = self.db.get_root_node(self.pid, self.cid)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _run(self, cmd_func, **kwargs):
        """Run a CLI command with kwargs as args, return stdout string."""
        merged = dict(db=self.db_path)
        merged.update(kwargs)
        args = self._Args(**merged)
        old = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            cmd_func(args)
            return buf.getvalue()
        finally:
            sys.stdout = old

    # -- View commands --

    def test_math_collection_list(self):
        from src.cli.main import cmd_math_collection_list
        out = self._run(cmd_math_collection_list)
        self.assertIn("Number Theory", out)
        self.assertIn("1 tools", out)

    def test_math_collection_list_json(self):
        from src.cli.main import cmd_math_collection_list
        out = self._run(cmd_math_collection_list, json=True)
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]["name"], "Number Theory")

    def test_math_collection_list_empty(self):
        from src.cli.main import cmd_math_collection_list
        db_path2 = tempfile.mktemp(suffix=".db")
        LeaderboardDB(db_path2)  # fresh DB, no collections
        out = self._run(cmd_math_collection_list, db=db_path2)
        self.assertIn("No method collections", out)
        os.unlink(db_path2)

    def test_math_problem_list(self):
        from src.cli.main import cmd_math_problem_list
        out = self._run(cmd_math_problem_list)
        self.assertIn("Goldbach Conjecture", out)
        self.assertIn("solution(s)", out)

    def test_math_problem_list_json(self):
        from src.cli.main import cmd_math_problem_list
        out = self._run(cmd_math_problem_list, json=True)
        data = json.loads(out)
        self.assertEqual(data[0]["title"], "Goldbach Conjecture")
        self.assertIn("solution_count", data[0])

    def test_math_problem_list_search(self):
        from src.cli.main import cmd_math_problem_list
        out = self._run(cmd_math_problem_list, search="Goldbach")
        self.assertIn("Goldbach Conjecture", out)
        out2 = self._run(cmd_math_problem_list, search="Nonexistent")
        self.assertIn("No math problems", out2)

    def test_math_problem_show(self):
        from src.cli.main import cmd_math_problem_show
        out = self._run(cmd_math_problem_show, problem_id=self.pid, address="0xALICE")
        self.assertIn("Goldbach Conjecture", out)
        self.assertIn("Number Theory", out)
        self.assertIn("Unlocked", out)

    def test_math_problem_show_not_found(self):
        from src.cli.main import cmd_math_problem_show
        with self.assertRaises(SystemExit):
            self._run(cmd_math_problem_show, problem_id=999)

    def test_math_problem_show_json(self):
        from src.cli.main import cmd_math_problem_show
        out = self._run(cmd_math_problem_show, problem_id=self.pid, json=True)
        data = json.loads(out)
        self.assertEqual(data["problem"]["title"], "Goldbach Conjecture")
        self.assertGreater(len(data["method_zones"]), 0)

    def test_math_zone(self):
        from src.cli.main import cmd_math_zone
        out = self._run(cmd_math_zone, problem_id=self.pid,
                        method_collection_id=self.cid, address="0xALICE")
        self.assertIn("Goldbach Conjecture", out)
        self.assertIn("Number Theory", out)
        self.assertIn("Unlocked", out)
        self.assertIn("0xALICE", out)

    def test_math_zone_locked(self):
        from src.cli.main import cmd_math_zone
        out = self._run(cmd_math_zone, problem_id=self.pid,
                        method_collection_id=self.cid)
        self.assertIn("Locked", out)

    def test_math_zone_json(self):
        from src.cli.main import cmd_math_zone
        out = self._run(cmd_math_zone, problem_id=self.pid,
                        method_collection_id=self.cid, json=True)
        data = json.loads(out)
        self.assertEqual(data["problem"]["id"], self.pid)
        self.assertGreater(len(data["solutions"]), 0)

    def test_math_solution_show(self):
        from src.cli.main import cmd_math_solution_show
        out = self._run(cmd_math_solution_show, solution_id=self.sid)
        self.assertIn("Goldbach Conjecture", out)
        self.assertIn("Max Correct", out)
        self.assertIn("✓", out)

    def test_math_solution_show_json(self):
        from src.cli.main import cmd_math_solution_show
        out = self._run(cmd_math_solution_show, solution_id=self.sid, json=True)
        data = json.loads(out)
        self.assertEqual(len(data["steps"]), 3)
        self.assertEqual(data["max_correct_step"], 2)

    def test_math_solution_show_not_found(self):
        from src.cli.main import cmd_math_solution_show
        with self.assertRaises(SystemExit):
            self._run(cmd_math_solution_show, solution_id=999)

    def test_math_tree_show(self):
        from src.cli.main import cmd_math_tree_show
        out = self._run(cmd_math_tree_show, problem_id=self.pid,
                        method_collection_id=self.cid)
        self.assertIn("Stats", out)
        self.assertIn("Goldbach Conjecture", out)

    def test_math_tree_show_no_root(self):
        from src.cli.main import cmd_math_tree_show
        # The root is auto-created in setUp; test by trying a non-existent zone
        with self.assertRaises(SystemExit):
            self._run(cmd_math_tree_show, problem_id=999,
                      method_collection_id=999)

    def test_math_tree_show_json(self):
        from src.cli.main import cmd_math_tree_show
        out = self._run(cmd_math_tree_show, problem_id=self.pid,
                        method_collection_id=self.cid, json=True)
        data = json.loads(out)
        self.assertIn("stats", data)
        self.assertIn("tree", data)

    def test_math_tree_node(self):
        from src.cli.main import cmd_math_tree_node
        out = self._run(cmd_math_tree_node, node_id=self.root["id"])
        self.assertIn("Goldbach Conjecture", out)
        self.assertIn("Root", out)

    def test_math_tree_node_json(self):
        from src.cli.main import cmd_math_tree_node
        out = self._run(cmd_math_tree_node, node_id=self.root["id"], json=True)
        data = json.loads(out)
        self.assertEqual(data["node"]["id"], self.root["id"])

    def test_math_tree_node_not_found(self):
        from src.cli.main import cmd_math_tree_node
        with self.assertRaises(SystemExit):
            self._run(cmd_math_tree_node, node_id=999)

    # -- Action commands --

    def test_math_problem_create(self):
        from src.cli.main import cmd_math_problem_create
        out = self._run(cmd_math_problem_create, title="P vs NP",
                        description="Is P = NP?", category="logic",
                        creator="bob")
        self.assertIn("Math problem created", out)
        self.assertIn("P vs NP", out)
        # Verify in DB
        # PID=1 created by setUp, so new problem is PID=2
        p = self.db.get_math_problem(2)
        self.assertEqual(p["title"], "P vs NP")

    def test_math_problem_create_empty_title(self):
        from src.cli.main import cmd_math_problem_create
        with self.assertRaises(SystemExit):
            self._run(cmd_math_problem_create, title="   ")

    def test_math_unlock(self):
        from src.cli.main import cmd_math_unlock
        # Create another method collection for the same problem
        cid2 = self.db.create_collection(
            "method", "Analysis Tools", "desc", "mathematics", "bob",
            [{"name": "Real Analysis", "domain": "mathematics", "level": 2, "description": "d"}])
        out = self._run(cmd_math_unlock, problem_id=self.pid,
                        method_collection_id=cid2, combo_id="combo_xyz",
                        address="0xNEWUSER")
        self.assertIn("Access granted", out)
        self.assertTrue(self.db.check_math_access(self.pid, cid2, "0xNEWUSER"))

    def test_math_unlock_not_found(self):
        from src.cli.main import cmd_math_unlock
        with self.assertRaises(SystemExit):
            self._run(cmd_math_unlock, problem_id=999,
                      method_collection_id=1, combo_id="c1")

    def test_math_tree_backpropagate(self):
        from src.cli.main import cmd_math_tree_backpropagate
        # Create a child node first
        nid = self.db.create_tree_node(self.pid, self.cid, "0xT", "Test step")
        self.db.create_tree_edge(self.root["id"], nid, "test")
        out = self._run(cmd_math_tree_backpropagate, node_id=nid,
                        type="terminal_success")
        self.assertIn("Backpropagated", out)
        # Verify node type changed
        node = self.db.get_tree_node(nid)
        self.assertEqual(node["node_type"], "terminal_success")
        # Root Q should be updated
        root = self.db.get_tree_node(self.root["id"])
        self.assertGreater(root["visit_count"], 0)

    def test_math_tree_backpropagate_not_found(self):
        from src.cli.main import cmd_math_tree_backpropagate
        with self.assertRaises(SystemExit):
            self._run(cmd_math_tree_backpropagate, node_id=999, type="terminal_success")

    def test_math_tree_prune(self):
        from src.cli.main import cmd_math_tree_prune
        nid = self.db.create_tree_node(self.pid, self.cid, "0xT", "Dead end")
        self.db.create_tree_edge(self.root["id"], nid, "bad")
        out = self._run(cmd_math_tree_prune, node_id=nid)
        self.assertIn("Pruned", out)
        node = self.db.get_tree_node(nid)
        self.assertEqual(node["node_type"], "pruned")

    def test_math_tree_prune_not_found(self):
        from src.cli.main import cmd_math_tree_prune
        with self.assertRaises(SystemExit):
            self._run(cmd_math_tree_prune, node_id=999)

    def test_math_pull(self):
        from src.cli.main import cmd_math_pull
        out_path = tempfile.mktemp(suffix=".json")
        out = self._run(cmd_math_pull, problem_id=self.pid,
                        method_collection_id=self.cid, output=out_path)
        self.assertIn("Pulled", out)
        self.assertTrue(os.path.exists(out_path))
        data = json.loads(Path(out_path).read_text())
        self.assertEqual(data["problem"]["title"], "Goldbach Conjecture")
        self.assertGreater(len(data["solutions"]), 0)
        self.assertIn("steps", data["solutions"][0])
        os.unlink(out_path)

    def test_math_pull_no_solutions(self):
        from src.cli.main import cmd_math_pull
        out_path = tempfile.mktemp(suffix=".json")
        # This problem has no solutions
        pid2 = self.db.create_math_problem("New Problem", "...")
        out = self._run(cmd_math_pull, problem_id=pid2,
                        method_collection_id=self.cid, output=out_path,
                        best_only=True)
        self.assertIn("Pulled 0", out)
        os.unlink(out_path)

    def test_math_search(self):
        from src.cli.main import cmd_math_search
        out = self._run(cmd_math_search, query="Goldbach")
        self.assertIn("Goldbach Conjecture", out)
        self.assertIn("Problems (1)", out)

    def test_math_search_all_scopes(self):
        from src.cli.main import cmd_math_search
        out = self._run(cmd_math_search, query="even", scope="all")
        self.assertIn("Math Search Results", out)

    def test_math_search_json(self):
        from src.cli.main import cmd_math_search
        out = self._run(cmd_math_search, query="theorem", json=True)
        data = json.loads(out)
        self.assertIn("solutions", data)

    def test_math_search_empty(self):
        from src.cli.main import cmd_math_search
        out = self._run(cmd_math_search, query="zzz_nonexistent_zzz")
        self.assertIn("0 matches", out)

    def test_math_search_no_query(self):
        from src.cli.main import cmd_math_search
        with self.assertRaises(SystemExit):
            self._run(cmd_math_search, query="")

    # -- JSON output consistency --

    def test_all_view_commands_json(self):
        """Verify all view commands produce valid JSON."""
        from src.cli.main import (
            cmd_math_collection_list, cmd_math_problem_list,
            cmd_math_problem_show, cmd_math_zone,
            cmd_math_solution_show, cmd_math_tree_show, cmd_math_tree_node,
        )
        for cmd, kwargs in [
            (cmd_math_collection_list, {}),
            (cmd_math_problem_list, {}),
            (cmd_math_problem_show, {"problem_id": self.pid}),
            (cmd_math_zone, {"problem_id": self.pid,
                             "method_collection_id": self.cid}),
            (cmd_math_solution_show, {"solution_id": self.sid}),
            (cmd_math_tree_show, {"problem_id": self.pid,
                                  "method_collection_id": self.cid}),
            (cmd_math_tree_node, {"node_id": self.root["id"]}),
        ]:
            out = self._run(cmd, json=True, **kwargs)
            data = json.loads(out)  # will raise if invalid JSON
            self.assertIsNotNone(data)


if __name__ == "__main__":
    unittest.main()
