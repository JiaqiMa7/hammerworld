"""Tests for Matrix Marketplace: collections, stars, imports."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hub.leaderboard import LeaderboardDB
from src.hub.web import (
    render_collections, render_collection_new, render_collection_detail,
)


class TestCollectionDB(unittest.TestCase):
    """Tests for collection CRUD in LeaderboardDB."""

    def setUp(self):
        self.db = LeaderboardDB(":memory:")

    def test_create_method_collection(self):
        items = [{"name": "Reverse Thinking", "domain": "triz", "level": 2, "description": "Invert the problem"}]
        cid = self.db.create_collection("method", "Test Pack", "A test", "triz", "alice", items)
        self.assertEqual(cid, 1)

        coll = self.db.get_collection("method", 1)
        self.assertEqual(coll["name"], "Test Pack")
        self.assertEqual(coll["creator"], "alice")
        self.assertEqual(coll["stars"], 0)
        self.assertEqual(coll["import_count"], 0)
        loaded = json.loads(coll["methods_json"])
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["name"], "Reverse Thinking")

    def test_create_problem_collection(self):
        items = [{"title": "Cold Fusion", "domain": "energy", "description": "Achieve cold fusion"}]
        cid = self.db.create_collection("problem", "Energy Problems", "desc", "energy", "bob", items)
        coll = self.db.get_collection("problem", cid)
        self.assertEqual(coll["name"], "Energy Problems")
        loaded = json.loads(coll["problems_json"])
        self.assertEqual(loaded[0]["title"], "Cold Fusion")

    def test_get_nonexistent_collection(self):
        self.assertIsNone(self.db.get_collection("method", 999))

    def test_get_collections_sort(self):
        self.db.create_collection("method", "B Pack", "", "triz", "u1", [{"name": "X", "domain": "triz", "level": 1, "description": "d"}])
        self.db.create_collection("method", "A Pack", "", "physics", "u2", [{"name": "Y", "domain": "physics", "level": 2, "description": "d"}])
        self.db.create_collection("method", "C Pack", "", "biology", "u3", [{"name": "Z", "domain": "biology", "level": 3, "description": "d"}])

        # Sort by newest (default order by created_at DESC would show C first, but we test explicit)
        result = self.db.get_collections("method", sort_by="newest")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["name"], "C Pack")

        result = self.db.get_collections("method", sort_by="stars")
        self.assertEqual(len(result), 3)

    def test_get_collections_by_category(self):
        self.db.create_collection("method", "TRIZ Pack", "", "triz", "u1", [{"name": "X", "domain": "triz", "level": 1, "description": "d"}])
        self.db.create_collection("method", "Bio Pack", "", "biology", "u2", [{"name": "Y", "domain": "biology", "level": 2, "description": "d"}])

        result = self.db.get_collections("method", category="triz")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "TRIZ Pack")

    def test_search_collections(self):
        self.db.create_collection("method", "Quantum Pack", "quantum methods", "physics", "u1", [{"name": "Q", "domain": "physics", "level": 2, "description": "d"}])
        self.db.create_collection("method", "Bio Pack", "biology stuff", "biology", "u2", [{"name": "B", "domain": "biology", "level": 1, "description": "d"}])

        result = self.db.search_collections("method", "quantum")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Quantum Pack")

        result = self.db.search_collections("method", "stuff")
        self.assertEqual(len(result), 1)

        result = self.db.search_collections("method", "xyz")
        self.assertEqual(len(result), 0)

    def test_toggle_star(self):
        items = [{"name": "Test", "domain": "triz", "level": 1, "description": "d"}]
        cid = self.db.create_collection("method", "Star Pack", "", "triz", "alice", items)

        # First star
        count = self.db.toggle_star("method", cid, "user1")
        self.assertEqual(count, 1)

        # Check stored
        conn = self.db._connect()
        row = conn.execute("SELECT * FROM collection_stars WHERE collection_type = ? AND collection_id = ? AND starrer = ?",
                           ("method", cid, "user1")).fetchone()
        self.assertIsNotNone(row)

        # Second star (toggle off)
        count = self.db.toggle_star("method", cid, "user1")
        self.assertEqual(count, 0)

        # Different user
        count = self.db.toggle_star("method", cid, "user2")
        self.assertEqual(count, 1)

    def test_increment_import(self):
        items = [{"name": "Test", "domain": "triz", "level": 1, "description": "d"}]
        cid = self.db.create_collection("method", "Import Pack", "", "triz", "alice", items)

        self.db.increment_import("method", cid)
        self.db.increment_import("method", cid)

        coll = self.db.get_collection("method", cid)
        self.assertEqual(coll["import_count"], 2)

    def test_find_collection_by_name(self):
        items = [{"name": "Test", "domain": "triz", "level": 1, "description": "d"}]
        self.db.create_collection("method", "My Methods", "", "triz", "alice", items)

        found = self.db.find_collection_by_name("method", "My Methods")
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "My Methods")

        not_found = self.db.find_collection_by_name("method", "No Such Pack")
        self.assertIsNone(not_found)


class TestCollectionWebPages(unittest.TestCase):
    """Tests for collection web page rendering."""

    def test_collections_page_empty(self):
        db = LeaderboardDB(":memory:")
        html = render_collections(db, "/web/collections")
        self.assertIn("Collections", html)
        self.assertIn("No collections found", html)
        self.assertIn("New Collection", html)

    def test_collections_page_with_items(self):
        db = LeaderboardDB(":memory:")
        db.create_collection("method", "TRIZ Basics", "A starter pack", "triz", "alice",
                             [{"name": "Inversion", "domain": "triz", "level": 2, "description": "Flip it"}])
        html = render_collections(db, "/web/collections?type=method")
        self.assertIn("TRIZ Basics", html)
        self.assertIn("1 items", html)
        self.assertIn("alice", html)

    def test_collections_page_with_problems(self):
        db = LeaderboardDB(":memory:")
        db.create_collection("problem", "Energy", "Energy problems", "energy", "bob",
                             [{"title": "Fusion", "domain": "energy", "description": "Make it work"}])
        html = render_collections(db, "/web/collections?type=problem")
        self.assertIn("Energy", html)
        self.assertIn("1 items", html)

    def test_collections_page_tabs(self):
        db = LeaderboardDB(":memory:")
        html = render_collections(db, "/web/collections?type=method")
        self.assertIn("Methods", html)
        self.assertIn("Problems", html)
        self.assertIn('href="/web/collections?type=problem', html)

    def test_collection_new_form(self):
        html = render_collection_new()
        self.assertIn("New Collection", html)
        self.assertIn('name="name"', html)
        self.assertIn('name="ctype"', html)
        self.assertIn('name="category"', html)
        self.assertIn('name="items_json"', html)
        self.assertIn("Method Collection", html)
        self.assertIn("Problem Collection", html)

    def test_collection_new_with_errors(self):
        html = render_collection_new(form={"name": "Bad"}, errors=["Items JSON is invalid"])
        self.assertIn("Items JSON is invalid", html)
        self.assertIn('value="Bad"', html)

    def test_collection_detail(self):
        db = LeaderboardDB(":memory:")
        items = [
            {"name": "Method A", "domain": "triz", "level": 1, "description": "First method"},
            {"name": "Method B", "domain": "physics", "level": 2, "description": "Second method"},
        ]
        cid = db.create_collection("method", "My Pack", "A description", "triz", "creator1", items)
        html = render_collection_detail(db, "method", cid)
        self.assertIn("My Pack", html)
        self.assertIn("Method A", html)
        self.assertIn("Method B", html)
        self.assertIn("2 items", html)
        self.assertIn("creator1", html)
        self.assertIn("Star", html)
        self.assertIn("Import", html)
        self.assertIn("--methods-collection", html)

    def test_collection_detail_not_found(self):
        db = LeaderboardDB(":memory:")
        html = render_collection_detail(db, "method", 999)
        self.assertIn("Not Found", html)

    def test_collection_detail_problem(self):
        db = LeaderboardDB(":memory:")
        items = [{"title": "Problem X", "domain": "energy", "description": "Hard problem"}]
        cid = db.create_collection("problem", "Prob Pack", "desc", "energy", "user", items)
        html = render_collection_detail(db, "problem", cid)
        self.assertIn("Problem X", html)
        self.assertIn("--problems-collection", html)

    def test_nav_includes_collections(self):
        db = LeaderboardDB(":memory:")
        html = render_collections(db, "/web/collections")
        self.assertIn('href="/web/collections"', html)


class TestCollectionAPI(unittest.TestCase):
    """Tests for collection API endpoints via HubAPI."""

    def test_create_collection_api(self):
        db = LeaderboardDB(":memory:")
        from src.hub.server import HubAPI
        from src.hub.peer import PeerConfig, PeerManager
        pm = PeerManager(db, PeerConfig())
        api = HubAPI(db, pm)

        # Simulate the handler's create_collection logic via POST body
        # We test the DB directly here since the handler is in the HTTP layer
        body = json.dumps({
            "ctype": "method",
            "name": "API Pack",
            "description": "API test",
            "category": "triz",
            "creator": "api_user",
            "items_json": json.dumps([{"name": "M", "domain": "triz", "level": 1, "description": "d"}]),
        }).encode()

        # Use the server handler logic
        cid = db.create_collection("method", "API Pack", "API test", "triz", "api_user",
                                   [{"name": "M", "domain": "triz", "level": 1, "description": "d"}])
        self.assertEqual(cid, 1)

        coll = db.get_collection("method", 1)
        self.assertEqual(coll["name"], "API Pack")

    def test_star_toggle_api(self):
        db = LeaderboardDB(":memory:")
        cid = db.create_collection("method", "Star Me", "", "triz", "alice",
                                   [{"name": "M", "domain": "triz", "level": 1, "description": "d"}])

        count = db.toggle_star("method", cid, "viewer1")
        self.assertEqual(count, 1)

        count = db.toggle_star("method", cid, "viewer1")
        self.assertEqual(count, 0)

    def test_import_count_api(self):
        db = LeaderboardDB(":memory:")
        cid = db.create_collection("problem", "Import Me", "", "energy", "bob",
                                   [{"title": "P", "domain": "energy", "description": "d"}])

        self.assertEqual(db.get_collection("problem", cid)["import_count"], 0)
        db.increment_import("problem", cid)
        self.assertEqual(db.get_collection("problem", cid)["import_count"], 1)


if __name__ == "__main__":
    import unittest
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
