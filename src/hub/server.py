"""HTTP API server for hub peer-to-peer sync."""
from __future__ import annotations

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Callable

from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry
from src.hub.peer import PeerManager, PeerConfig, _entry_to_json, _json_to_entry


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for concurrent peer connections."""
    daemon_threads = True


class _HubHandler(BaseHTTPRequestHandler):
    """Request handler that routes to HubAPI methods."""

    # Set by HubServer before starting
    api: Optional[HubAPI] = None
    db: Optional[LeaderboardDB] = None
    peer_manager: Optional[PeerManager] = None
    buffer_zone = None
    token_gate = None

    def log_message(self, format, *args):
        pass  # Suppress default logging

    @property
    def _remote_ip(self) -> str:
        return self.client_address[0]

    @property
    def _lang(self) -> str:
        """Extract language preference from query string."""
        from urllib.parse import parse_qs
        qs = self.path.split("?", 1)[1] if "?" in self.path else ""
        for pair in qs.split("&"):
            if pair.startswith("lang="):
                lang = pair.split("=", 1)[1]
                return lang if lang in ("en", "zh") else "en"
        return "en"

    def _cookie_addr(self) -> str:
        """Extract hammerworld_addr from Cookie header."""
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.replace(";", " ").split():
            if part.startswith("hammerworld_addr="):
                return part.split("=", 1)[1]
        return ""

    def _set_cookie(self, addr: str = "", clear: bool = False) -> None:
        """Set or clear the hammerworld_addr session cookie."""
        if clear or not addr:
            self.send_header("Set-Cookie",
                "hammerworld_addr=; Path=/; Max-Age=0; SameSite=Lax")
        else:
            self.send_header("Set-Cookie",
                f"hammerworld_addr={addr}; Path=/; SameSite=Lax")

    def _viewer_for_page(self, query_params: dict[str, str]) -> str:
        """Get viewer address: cookie > query param > empty."""
        return self._cookie_addr() or query_params.get("viewer", "")

    def _check_rate_limit(self) -> bool:
        """Check rate limit for discovery endpoints. Sends 429 if limited."""
        from src.hub.discovery import get_discovery_server
        ds = get_discovery_server()
        ip = self._remote_ip
        if ip and ds.is_rate_limited(ip):
            self._send_json(
                {"error": "rate_limited", "retry_after": 60}, 429
            )
            return False
        return True

    def _check_web_rate_limit(self) -> bool:
        """Check rate limit for web UI POST endpoints. Sends 429 if limited."""
        rl = getattr(_HubHandler, 'web_rate_limiter', None)
        if rl is None:
            return True
        ip = self._remote_ip
        if ip and not rl.is_allowed(ip):
            self._send_json(
                {"error": "rate_limited", "retry_after": 60}, 429
            )
            return False
        return True

    def _send_html(self, html: str, status: int = 200):
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict | list, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        if length > 1_048_576:  # 1MB limit
            return b""
        return self.rfile.read(length)

    def do_GET(self):
        assert self.api is not None
        path = self.path.split("?", 1)[0]

        # P2P API endpoints
        if self.path == "/health":
            self._send_json(self.api.handle_health())
        elif self.path == "/stats":
            self._send_json(self.api.handle_stats())
        elif self.path == "/peers":
            self._send_json(self.api.handle_get_peers())
        elif self.path == "/discovery/peers":
            if not self._check_rate_limit():
                return
            self._send_json(self.api.handle_discovery_peers())
        elif self.path.startswith("/combinations"):
            self._send_json(self.api.handle_get_combinations(self.path))
        # Web UI endpoints
        elif path == "/" or path == "/web":
            self._serve_web("dashboard")
        elif path == "/web/logout":
            self.send_response(302)
            self._set_cookie(clear=True)
            self.send_header("Location", "/")
            self.end_headers()
        elif path.startswith("/web/"):
            self._serve_web(path)
        else:
            self._send_json({"error": "not found"}, 404)

    def _serve_web(self, path: str):
        from src.hub.web import (
            render_dashboard, render_leaderboard, render_search,
            render_random, render_peers, render_entry,
            render_submit_home, render_submit_method, render_submit_problem,
            render_submissions,
            render_collections, render_collection_new, render_collection_detail,
            render_math_home, render_math_new, render_math_problem,
            render_math_method_zone, render_math_solution, render_math_unlock,
            render_math_tree, render_math_tree_node,
            render_buffer_dashboard, render_buffer_pending,
            render_buffer_classify, render_buffer_submissions,
            render_buffer_submission_detail, render_buffer_tokens,
            render_buffer_leaderboard, render_token_dashboard, _parse_query,
        )
        db = self.db
        pm = self.peer_manager
        tg = self.token_gate
        assert db is not None and pm is not None

        params = _parse_query(self.path)
        viewer = self._viewer_for_page(params)
        lang = params.get("lang", "en")

        if path in ("/", "/web", "dashboard"):
            html = render_dashboard(db, pm, lang=lang, viewer_addr=viewer)
        elif path.startswith("/web/leaderboard"):
            html = render_leaderboard(db, self.path, viewer_addr=viewer, token_gate=tg, lang=lang)
        elif path.startswith("/web/search"):
            html = render_search(db, self.path, lang=lang, viewer_addr=viewer)
        elif path.startswith("/web/random"):
            html = render_random(db, self.path, viewer_addr=viewer, token_gate=tg, lang=lang)
        elif path.startswith("/web/peers"):
            html = render_peers(pm, lang=lang, viewer_addr=viewer)
        elif path.startswith("/web/entry/"):
            combo_id = path.split("/web/entry/", 1)[1]
            html = render_entry(db, combo_id, viewer_addr=viewer, token_gate=tg, lang=lang)
        elif path == "/web/tokens":
            html = render_token_dashboard(db, token_gate=tg, viewer_addr=viewer, lang=lang)
        elif path == "/web/submit":
            html = render_submit_home(lang=lang, viewer_addr=viewer)
        elif path == "/web/submit/method":
            html = render_submit_method(lang=lang, viewer_addr=viewer)
        elif path == "/web/submit/problem":
            html = render_submit_problem(lang=lang, viewer_addr=viewer)
        elif path.startswith("/web/submissions"):
            self._handle_submissions(path)
            return
        # Matrix Marketplace — Collections
        elif _match_collection_star(path):
            self._handle_collection_star(path)
            return
        elif path == "/web/collections/new":
            html = render_collection_new(lang=lang)
        elif path.startswith("/web/collections/new"):
            # Nothing else matches this prefix besides the exact path above
            html = render_collection_new(lang=lang)
        elif _match_collection_detail(path):
            ctype, cid_str = _parse_collection_path(path)
            try:
                cid = int(cid_str)
            except ValueError:
                self._send_json({"error": "invalid collection id"}, 404)
                return
            html = render_collection_detail(db, ctype, cid, starrer="", lang=lang)
        elif path.startswith("/web/collections"):
            html = render_collections(db, self.path, lang=lang, viewer_addr=viewer)
        # Math Research Zone routes
        elif path == "/web/math":
            html = render_math_home(db, lang=lang, viewer_addr=viewer)
        elif path == "/web/math/new":
            html = render_math_new(lang=lang, viewer_addr=viewer)
        elif _match_math_tree_node(path):
            pid, mid, nid = _parse_math_tree_node(path)
            html = render_math_tree_node(db, pid, mid, nid, self.path, lang=lang)
        elif _match_math_tree(path):
            pid, mid = _parse_math_tree(path)
            html = render_math_tree(db, pid, mid, self.path, lang=lang)
        elif _match_math_solution(path):
            pid, mid, sid = _parse_math_solution(path)
            html = render_math_solution(db, pid, mid, sid, self.path, lang=lang)
        elif _match_math_method_zone(path):
            pid, mid = _parse_math_method_zone(path)
            html = render_math_method_zone(db, pid, mid, self.path, lang=lang)
        elif _match_math_problem(path):
            pid = _parse_math_problem_id(path)
            html = render_math_problem(db, pid, self.path, lang=lang)
        # Blockchain Buffer Zone routes
        elif path == "/web/buffer" or path == "/web/buffer/":
            html = render_buffer_dashboard(db, lang=lang, viewer_addr=viewer)
        elif path.startswith("/web/buffer/pending"):
            html = render_buffer_pending(db, self.path, lang=lang, viewer_addr=viewer)
        elif _match_buffer_classify(path):
            sub_id = _parse_buffer_classify(path)
            html = render_buffer_classify(db, sub_id, self.path, lang=lang, viewer_addr=viewer)
        elif _match_buffer_detail(path):
            sub_id = _parse_buffer_detail(path)
            html = render_buffer_submission_detail(db, sub_id, lang=lang, viewer_addr=viewer)
        elif path.startswith("/web/buffer/submissions"):
            params = _parse_query(self.path)
            addr = params.get("address", "0xVIEWER")
            html = render_buffer_submissions(db, addr, lang=lang, viewer_addr=viewer)
        elif path.startswith("/web/buffer/tokens"):
            params = _parse_query(self.path)
            addr = params.get("address", "0xVIEWER")
            html = render_buffer_tokens(db, addr, lang=lang, viewer_addr=viewer)
        elif path.startswith("/web/buffer/leaderboard"):
            html = render_buffer_leaderboard(db, lang=lang, viewer_addr=viewer)
        else:
            self._send_json({"error": "not found"}, 404)
            return
        self._send_html(html)

    def _respond_submit(self, form_path: str, result: dict, body: bytes):
        """Respond to a form submission — HTML for browser, JSON for API."""
        ct = self.headers.get("Content-Type", "")
        if "json" in ct:
            self._send_json(result)
            return

        from src.hub.web import render_submit_method, render_submit_problem
        if result.get("ok"):
            if "method" in form_path:
                html = render_submit_method(success=f"Method submitted! ID: {result['id']}", lang=self._lang)
            else:
                html = render_submit_problem(success=f"Problem submitted! ID: {result['id']}", lang=self._lang)
        else:
            # Re-render form with errors and submitted data
            from urllib.parse import parse_qs
            try:
                form_data = {k: v[0] for k, v in parse_qs(body.decode()).items()}
            except Exception:
                form_data = {}
            errors = result.get("errors", [])
            if "method" in form_path:
                html = render_submit_method(form=form_data, errors=errors, lang=self._lang)
            else:
                html = render_submit_problem(form=form_data, errors=errors, lang=self._lang)
        self._send_html(html)

    def _handle_submissions(self, path: str):
        from src.hub.web import render_submissions
        from urllib.parse import parse_qs
        db = self.db
        assert db is not None

        # Handle approve/reject actions via query params
        if "?" in self.path:
            qs = self.path.split("?", 1)[1]
            params = parse_qs(qs)
            if "approve" in params:
                sub_id = int(params["approve"][0])
                data = db.approve_submission(sub_id)
                if data:
                    self._send_html(render_submissions(db, lang=self._lang))
                    return
            elif "reject" in params:
                sub_id = int(params["reject"][0])
                db.reject_submission(sub_id)

        self._send_html(render_submissions(db, lang=self._lang))

    def _handle_collection_star(self, path: str):
        """Handle star toggle for a collection."""
        from src.hub.web import render_collection_detail
        db = self.db
        assert db is not None

        # Parse /web/collections/{type}/{id}/star?starrer=x
        rest = path.split("/web/collections/", 1)[1]
        parts = rest.split("/")
        ctype = parts[0]
        cid = int(parts[1])

        params: dict[str, str] = {}
        if "?" in self.path:
            qs = self.path.split("?", 1)[1]
            for pair in qs.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v
        starrer = params.get("starrer", "")

        try:
            db.toggle_star(ctype, cid, starrer)
        except Exception:
            pass

        # Redirect back to the detail page
        html = render_collection_detail(db, ctype, cid, starrer=starrer, starred=True, lang=self._lang)
        self._send_html(html)

    def _handle_create_collection(self, body: bytes):
        """Handle POST to create a new collection."""
        from urllib.parse import parse_qs
        from src.hub.web import render_collection_new

        db = self.db
        assert db is not None

        ct = self.headers.get("Content-Type", "")
        if "json" in ct:
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"ok": False, "errors": ["Invalid JSON"]})
                return
        else:
            decoded = parse_qs(body.decode())
            data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}

        ctype = data.get("ctype", "method").strip()
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        category = data.get("category", "other").strip()
        creator = data.get("creator", "anonymous").strip()
        items_json = data.get("items_json", "[]").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if ctype not in ("method", "problem"):
            errors.append("Type must be 'method' or 'problem'.")

        items = []
        if not errors:
            try:
                items = json.loads(items_json)
                if not isinstance(items, list):
                    errors.append("Items must be a JSON array.")
                elif len(items) == 0:
                    errors.append("At least one item is required.")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in items: {e}")

        if errors:
            if "json" in ct:
                self._send_json({"ok": False, "errors": errors})
            else:
                html = render_collection_new(form=data, errors=errors, lang=self._lang)
                self._send_html(html)
            return

        cid = db.create_collection(ctype, name, description, category, creator, items)

        if "json" in ct:
            self._send_json({"ok": True, "id": cid})
        else:
            # Redirect to the new collection detail
            from src.hub.web import render_collection_detail
            html = render_collection_detail(db, ctype, cid, starrer=creator, lang=self._lang)
            self._send_html(html)

    def _handle_create_math_problem(self, body: bytes):
        """Handle POST to create a new math problem."""
        from urllib.parse import parse_qs
        from src.hub.web import render_math_new

        db = self.db
        assert db is not None

        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}

        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        category = data.get("category", "number_theory").strip()
        creator = data.get("creator", "anonymous").strip()

        errors = []
        if not title:
            errors.append("Title is required.")

        if errors:
            html = render_math_new(form=data, errors=errors, lang=self._lang)
            self._send_html(html)
            return

        pid = db.create_math_problem(title, description, category, creator)
        # Redirect to the new problem page
        from src.hub.web import render_math_problem
        html = render_math_problem(db, pid, self.path, lang=self._lang)
        self._send_html(html)

    def _handle_fork_math_solution(self, pid: int, mid: int, sid: int, body: bytes):
        """Handle POST to fork a math solution."""
        from urllib.parse import parse_qs

        db = self.db
        assert db is not None

        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        user_address = data.get("user_address", "anonymous").strip()

        new_sid = db.fork_math_solution(sid, user_address)
        if new_sid:
            # Redirect to the new forked solution
            self.send_response(302)
            self.send_header("Location", f"/web/math/{pid}/{mid}/{new_sid}")
            self.end_headers()
        else:
            self._send_html("<div class='empty'>Failed to fork solution. Original not found.</div>", 404)

    def _handle_submit_math_solution(self, pid: int, mid: int, sid: int, body: bytes):
        """Handle POST to update math solution steps."""
        from urllib.parse import parse_qs

        db = self.db
        assert db is not None

        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}

        steps_json = data.get("steps_json", "[]")
        user_address = data.get("user_address", "anonymous").strip()

        errors = []
        try:
            steps = json.loads(steps_json)
            if not isinstance(steps, list):
                errors.append("Steps must be a JSON array.")
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")

        if errors:
            from src.hub.web import render_math_solution
            html = render_math_solution(db, pid, mid, sid, self.path, lang=lang)
            self._send_html(html)
            return

        db.update_math_solution(sid, steps)
        # Redirect back to solution page
        self.send_response(302)
        self.send_header("Location", f"/web/math/{pid}/{mid}/{sid}")
        self.end_headers()

    def _handle_math_unlock(self, pid: int, mid: int, body: bytes):
        """Handle POST to manually unlock a math zone."""
        from urllib.parse import parse_qs
        from src.hub.web import render_math_unlock

        db = self.db
        assert db is not None

        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        user_address = data.get("user_address", "").strip() or self._cookie_addr()
        combo_id = data.get("combo_id", "").strip()

        if not user_address or not combo_id:
            html = render_math_unlock(db, pid, mid, self.path, lang=self._lang)
            self._send_html(html)
            return

        db.grant_math_access(pid, mid, user_address, combo_id)
        self.send_response(302)
        self._set_cookie(user_address)
        self.send_header("Location", f"/web/math/{pid}/{mid}")
        self.end_headers()

    # -- Math tree POST handlers -------------------------------------------------

    def _handle_add_tree_child(self, pid: int, mid: int, nid: int, body: bytes):
        """Handle POST to add a child node to a tree node."""
        from urllib.parse import parse_qs

        db = self.db
        assert db is not None

        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        content = data.get("content", "").strip()
        action_label = data.get("action_label", "").strip()
        action_description = data.get("action_description", "").strip()
        user_address = data.get("user_address", "0xTREE").strip()
        node_type = data.get("node_type", "normal").strip()
        reward_str = data.get("reward", "0.0").strip()

        if not content:
            # re-render node page with error
            from src.hub.web import render_math_tree_node
            html = render_math_tree_node(db, pid, mid, nid, self.path,
                                         errors=["Content is required."],
                                         lang=self._lang)
            self._send_html(html)
            return

        try:
            reward = float(reward_str)
        except ValueError:
            reward = 0.0

        child_id = db.create_tree_node(
            pid, mid, user_address, content, node_type, reward=reward,
        )
        db.create_tree_edge(nid, child_id, action_label, action_description)

        if node_type in ("terminal_success", "terminal_failure"):
            db.backpropagate(child_id, reward)

        self.send_response(302)
        self.send_header("Location", f"/web/math/{pid}/{mid}/tree/node/{nid}")
        self.end_headers()

    def _handle_backpropagate(self, pid: int, mid: int, nid: int, body: bytes):
        """Handle POST to set terminal reward and backpropagate."""
        from urllib.parse import parse_qs

        db = self.db
        assert db is not None

        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        reward_str = data.get("reward", "1.0").strip()
        terminal_type = data.get("terminal_type", "terminal_success").strip()

        try:
            reward = float(reward_str)
        except ValueError:
            reward = 1.0
        reward = max(0.0, min(1.0, reward))

        db.update_tree_node(nid, node_type=terminal_type, reward=reward)
        db.backpropagate(nid, reward)

        self.send_response(302)
        self.send_header("Location", f"/web/math/{pid}/{mid}/tree/node/{nid}")
        self.end_headers()

    def _handle_prune_node(self, pid: int, mid: int, nid: int, body: bytes):
        """Handle POST to prune a tree node."""
        db = self.db
        assert db is not None

        db.prune_node(nid)

        self.send_response(302)
        self.send_header("Location", f"/web/math/{pid}/{mid}/tree")
        self.end_headers()

    def _handle_login(self, body: bytes):
        """Handle POST to set session cookie."""
        from urllib.parse import parse_qs
        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        addr = data.get("address", data.get("viewer_addr", "")).strip()
        redirect = data.get("redirect", "/")

        self.send_response(302)
        if addr:
            self._set_cookie(addr)
        self.send_header("Location", redirect)
        self.end_headers()

    def _handle_create_address(self, body: bytes):
        """Handle POST to create a new Ed25519 key-based address."""
        from src.hub.user_identity import ensure_user_identity, get_user_address
        from urllib.parse import parse_qs
        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        redirect = data.get("redirect", "/")

        identity = ensure_user_identity()
        addr = get_user_address(identity)

        self.send_response(302)
        self._set_cookie(addr)
        self.send_header("Location", redirect)
        self.end_headers()

    def _handle_pay_view(self, combo_id: str, body: bytes):
        """Handle POST to pay for viewing a combo."""
        from urllib.parse import parse_qs
        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        viewer_addr = data.get("viewer_addr_input", data.get("viewer_addr", "")).strip() or self._cookie_addr()
        redirect = data.get("redirect", f"/web/entry/{combo_id}")

        tg = self.token_gate
        if tg and viewer_addr:
            tg.pay_for_view(viewer_addr, combo_id)

        self.send_response(302)
        if viewer_addr:
            self._set_cookie(viewer_addr)
        self.send_header("Location", redirect)
        self.end_headers()

    def _handle_pay_leaderboard(self, board_name: str, body: bytes):
        """Handle POST to pay for leaderboard unlock."""
        from urllib.parse import parse_qs
        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        viewer_addr = data.get("viewer_addr_input", data.get("viewer_addr", "")).strip() or self._cookie_addr()
        redirect = data.get("redirect", "/web/leaderboard")

        tg = self.token_gate
        if tg and viewer_addr:
            tg.pay_for_leaderboard(viewer_addr, board_name)

        self.send_response(302)
        if viewer_addr:
            self._set_cookie(viewer_addr)
        self.send_header("Location", redirect)
        self.end_headers()

    def _handle_pay_draw(self, body: bytes):
        """Handle POST to pay for random draw."""
        from urllib.parse import parse_qs
        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        viewer_addr = data.get("viewer_addr_input", data.get("viewer_addr", "")).strip() or self._cookie_addr()
        redirect = data.get("redirect", "/web/random")

        tg = self.token_gate
        if tg and viewer_addr:
            tg.pay_for_random_draw(viewer_addr)

        self.send_response(302)
        if viewer_addr:
            self._set_cookie(viewer_addr)
        self.send_header("Location", redirect)
        self.end_headers()

    def _handle_rate(self, combo_id: str, body: bytes):
        """Handle POST to rate a combo."""
        from urllib.parse import parse_qs
        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        viewer_addr = data.get("viewer_addr", "").strip() or self._cookie_addr()
        redirect = data.get("redirect", f"/web/entry/{combo_id}")
        rating_str = data.get("rating", "")
        comment = data.get("comment", "").strip()

        tg = self.token_gate
        if tg and viewer_addr and rating_str:
            try:
                tg.rate_analysis(viewer_addr, combo_id, int(rating_str), comment)
            except (ValueError, TypeError):
                pass

        self.send_response(302)
        if viewer_addr:
            self._set_cookie(viewer_addr)
        self.send_header("Location", redirect)
        self.end_headers()

    def _handle_faucet(self, body: bytes):
        """Handle POST to trigger faucet."""
        from urllib.parse import parse_qs
        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        viewer_addr = data.get("viewer_addr", "").strip() or self._cookie_addr()
        redirect = data.get("redirect", "/web/tokens")

        tg = self.token_gate
        if tg and viewer_addr:
            tg.token.faucet(viewer_addr, tg.FAUCET_AMOUNT)

        self.send_response(302)
        if viewer_addr:
            self._set_cookie(viewer_addr)
        self.send_header("Location", redirect)
        self.end_headers()

    def _handle_buffer_classify(self, sub_id: str, body: bytes):
        """Handle POST to classify a buffer submission."""
        from urllib.parse import parse_qs
        from src.hub.web import render_buffer_classify

        buffer_zone = self.buffer_zone  # type: ignore[attr-defined]
        if buffer_zone is None:
            self._send_json({"ok": False, "error": "Buffer zone not available"}, 500)
            return

        db = self.db
        assert db is not None

        decoded = parse_qs(body.decode())
        data = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        classifier_addr = data.get("address", "0xCLASSIFIER").strip()
        domain = data.get("domain", "other").strip()
        is_nsfw = data.get("nsfw", "0") == "1"
        is_spam = data.get("spam", "0") == "1"
        notes = data.get("notes", "").strip()

        result = buffer_zone.classify(sub_id, classifier_addr, domain, is_nsfw, is_spam, notes)

        if not result.get("ok"):
            html = render_buffer_classify(db, sub_id, self.path, lang=lang)
            self._send_html(html)
            return

        # Redirect to detail page after successful classification
        self.send_response(302)
        self.send_header("Location", f"/web/buffer/detail/{sub_id}")
        self.end_headers()

    def do_POST(self):
        assert self.api is not None
        body = self._read_body()
        if self.path.startswith("/web/") and not self._check_web_rate_limit():
            return
        if self.path == "/combinations":
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, 400)
                return
            result = self.api.handle_post_combinations(data)
            self._send_json(result)
        elif self.path == "/peers/announce":
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, 400)
                return
            result = self.api.handle_announce(data)
            self._send_json(result)
        elif self.path == "/discovery/announce":
            if not self._check_rate_limit():
                return
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, 400)
                return
            result = self.api.handle_discovery_announce(data, remote_ip=self._remote_ip)
            self._send_json(result)
        elif self.path == "/discovery/heartbeat":
            if not self._check_rate_limit():
                return
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, 400)
                return
            result = self.api.handle_discovery_heartbeat(data, remote_ip=self._remote_ip)
            self._send_json(result)
        elif self.path == "/submit/method":
            result = self.api.handle_submit_method(body)
            self._respond_submit("/web/submit/method", result, body)
        elif self.path == "/submit/problem":
            result = self.api.handle_submit_problem(body)
            self._respond_submit("/web/submit/problem", result, body)
        elif self.path == "/web/collections/new":
            self._handle_create_collection(body)
        elif self.path == "/web/math/new":
            self._handle_create_math_problem(body)
        elif _match_add_tree_child(self.path):
            pid, mid, nid = _parse_tree_action_node(self.path)
            self._handle_add_tree_child(pid, mid, nid, body)
        elif _match_backpropagate(self.path):
            pid, mid, nid = _parse_tree_action_node(self.path)
            self._handle_backpropagate(pid, mid, nid, body)
        elif _match_prune_node(self.path):
            pid, mid, nid = _parse_tree_action_node(self.path)
            self._handle_prune_node(pid, mid, nid, body)
        elif _match_math_solution_fork(self.path):
            pid, mid, sid = _parse_math_solution_fork(self.path)
            self._handle_fork_math_solution(pid, mid, sid, body)
        elif _match_math_solution_submit(self.path):
            pid, mid, sid = _parse_math_solution_submit(self.path)
            self._handle_submit_math_solution(pid, mid, sid, body)
        elif _match_math_unlock_post(self.path):
            pid, mid = _parse_math_unlock_post(self.path)
            self._handle_math_unlock(pid, mid, body)
        elif _match_buffer_classify(self.path):
            sub_id = _parse_buffer_classify(self.path)
            self._handle_buffer_classify(sub_id, body)
        elif _match_pay_view(self.path):
            combo_id = _parse_pay_view(self.path)
            self._handle_pay_view(combo_id, body)
        elif _match_pay_leaderboard(self.path):
            board = _parse_pay_leaderboard(self.path)
            self._handle_pay_leaderboard(board, body)
        elif self.path == "/web/pay/draw":
            self._handle_pay_draw(body)
        elif _match_rate_post(self.path):
            combo_id = _parse_rate_post(self.path)
            self._handle_rate(combo_id, body)
        elif self.path == "/web/login":
            self._handle_login(body)
        elif self.path == "/web/create-address":
            self._handle_create_address(body)
        elif self.path == "/web/faucet":
            self._handle_faucet(body)
        else:
            self._send_json({"error": "not found"}, 404)


def _match_collection_star(path: str) -> bool:
    """Check if path matches /web/collections/{type}/{id}/star"""
    if not path.startswith("/web/collections/"):
        return False
    rest = path.split("/web/collections/", 1)[1]
    parts = rest.split("/")
    return len(parts) >= 3 and parts[2] == "star"


def _match_collection_detail(path: str) -> bool:
    """Check if path matches /web/collections/{type}/{id} (but NOT /star or /new)"""
    if not path.startswith("/web/collections/"):
        return False
    rest = path.split("/web/collections/", 1)[1]
    if rest in ("new", ""):
        return False
    parts = rest.split("/")
    if any(p in parts for p in ("star", "new")):
        return False
    return len(parts) == 2


def _parse_collection_path(path: str) -> tuple[str, str]:
    """Parse /web/collections/{type}/{id} -> (type, id_str)"""
    rest = path.split("/web/collections/", 1)[1]
    parts = rest.split("/")
    return parts[0], parts[1]


def _match_math_problem(path: str) -> bool:
    """Check if path matches /web/math/{id} (integer id, no further segments)."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    if rest in ("new", ""):
        return False
    parts = rest.split("/")
    return len(parts) == 1 and parts[0].isdigit()


def _parse_math_problem_id(path: str) -> int:
    """Extract math problem id from path."""
    rest = path.split("/web/math/", 1)[1]
    return int(rest.split("/")[0])


def _match_math_method_zone(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid} (two int segments, no further)."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()


def _parse_math_method_zone(path: str) -> tuple[int, int]:
    """Extract (pid, mid) from method zone path."""
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return int(parts[0]), int(parts[1])


def _match_math_solution(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid}/{sid} (three int segments)."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit()


def _parse_math_solution(path: str) -> tuple[int, int, int]:
    """Extract (pid, mid, sid) from solution path."""
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return int(parts[0]), int(parts[1]), int(parts[2])


def _match_math_unlock_post(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid}/unlock (POST)."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2] == "unlock"


def _parse_math_unlock_post(path: str) -> tuple[int, int]:
    """Extract (pid, mid) from unlock POST path."""
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return int(parts[0]), int(parts[1])


def _match_math_solution_fork(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid}/{sid}/fork."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return len(parts) >= 4 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit() and parts[3] == "fork"


def _parse_math_solution_fork(path: str) -> tuple[int, int, int]:
    """Extract (pid, mid, sid) from fork path."""
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return int(parts[0]), int(parts[1]), int(parts[2])


def _match_math_solution_submit(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid}/{sid}/submit."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return len(parts) >= 4 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit() and parts[3] == "submit"


def _parse_math_solution_submit(path: str) -> tuple[int, int, int]:
    """Extract (pid, mid, sid) from submit path."""
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return int(parts[0]), int(parts[1]), int(parts[2])


# -- Math tree matchers (must match before _match_math_method_zone) ---------------

def _match_math_tree_node(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid}/tree/node/{nid}."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return (len(parts) == 5 and parts[0].isdigit() and parts[1].isdigit()
            and parts[2] == "tree" and parts[3] == "node" and parts[4].isdigit())


def _parse_math_tree_node(path: str) -> tuple[int, int, int]:
    """Extract (pid, mid, nid) from tree node path."""
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return int(parts[0]), int(parts[1]), int(parts[4])


def _match_math_tree(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid}/tree."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return (len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit()
            and parts[2] == "tree")


def _parse_math_tree(path: str) -> tuple[int, int]:
    """Extract (pid, mid) from tree path."""
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return int(parts[0]), int(parts[1])


def _match_add_tree_child(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid}/tree/node/{nid}/add_child."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return (len(parts) == 6 and parts[0].isdigit() and parts[1].isdigit()
            and parts[2] == "tree" and parts[3] == "node"
            and parts[4].isdigit() and parts[5] == "add_child")


def _match_backpropagate(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid}/tree/node/{nid}/backpropagate."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return (len(parts) == 6 and parts[0].isdigit() and parts[1].isdigit()
            and parts[2] == "tree" and parts[3] == "node"
            and parts[4].isdigit() and parts[5] == "backpropagate")


def _match_prune_node(path: str) -> bool:
    """Check if path matches /web/math/{pid}/{mid}/tree/node/{nid}/prune."""
    if not path.startswith("/web/math/"):
        return False
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return (len(parts) == 6 and parts[0].isdigit() and parts[1].isdigit()
            and parts[2] == "tree" and parts[3] == "node"
            and parts[4].isdigit() and parts[5] == "prune")


def _parse_tree_action_node(path: str) -> tuple[int, int, int]:
    """Extract (pid, mid, nid) from tree action path."""
    rest = path.split("/web/math/", 1)[1]
    parts = rest.split("/")
    return int(parts[0]), int(parts[1]), int(parts[4])


def _match_buffer_classify(path: str) -> bool:
    """Check if path matches /web/buffer/classify/{sub_id}."""
    if not path.startswith("/web/buffer/classify/"):
        return False
    rest = path.split("/web/buffer/classify/", 1)[1]
    if "?" in rest:
        rest = rest.split("?")[0]
    return len(rest) > 0 and "/" not in rest


def _parse_buffer_classify(path: str) -> str:
    """Extract submission ID from buffer classify path."""
    rest = path.split("/web/buffer/classify/", 1)[1]
    if "?" in rest:
        rest = rest.split("?")[0]
    return rest


def _match_buffer_detail(path: str) -> bool:
    """Check if path matches /web/buffer/detail/{sub_id}."""
    if not path.startswith("/web/buffer/detail/"):
        return False
    rest = path.split("/web/buffer/detail/", 1)[1]
    if "?" in rest:
        rest = rest.split("?")[0]
    return len(rest) > 0 and "/" not in rest


def _parse_buffer_detail(path: str) -> str:
    """Extract submission ID from buffer detail path."""
    rest = path.split("/web/buffer/detail/", 1)[1]
    if "?" in rest:
        rest = rest.split("?")[0]
    return rest


def _match_pay_view(path: str) -> bool:
    """Check if path matches /web/pay/view/{combo_id}."""
    return path.startswith("/web/pay/view/")


def _parse_pay_view(path: str) -> str:
    """Extract combo_id from pay view path."""
    return path.split("/web/pay/view/", 1)[1]


def _match_pay_leaderboard(path: str) -> bool:
    """Check if path matches /web/pay/leaderboard/{board_name}."""
    return path.startswith("/web/pay/leaderboard/")


def _parse_pay_leaderboard(path: str) -> str:
    """Extract board_name from pay leaderboard path."""
    return path.split("/web/pay/leaderboard/", 1)[1]


def _match_rate_post(path: str) -> bool:
    """Check if path matches /web/rate/{combo_id}."""
    return path.startswith("/web/rate/")


def _parse_rate_post(path: str) -> str:
    """Extract combo_id from rate path."""
    return path.split("/web/rate/", 1)[1]


class HubAPI:
    """REST API logic — separated from HTTP transport for testability."""

    def __init__(self, db: LeaderboardDB, peer_manager: PeerManager):
        self.db = db
        self.peer_manager = peer_manager

    def handle_health(self) -> dict:
        return {
            "status": "ok",
            "peer_id": self.peer_manager.peer_id,
            "entries": self.db.total_entries(),
        }

    def handle_stats(self) -> dict:
        return {
            "peer_id": self.peer_manager.peer_id,
            "entries": self.db.total_entries(),
            "peers": len(self.peer_manager.get_peers()),
            "uptime": self.peer_manager.uptime,
        }

    def handle_get_peers(self) -> dict:
        peers = self.peer_manager.get_peers()
        return {
            "peer_id": self.peer_manager.peer_id,
            "peers": [
                {"peer_id": p.peer_id, "address": p.address, "port": p.port}
                for p in peers
            ],
        }

    def handle_get_combinations(self, path: str) -> dict:
        # Parse query string from path
        params: dict[str, str] = {}
        if "?" in path:
            qs = path.split("?", 1)[1]
            for pair in qs.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v

        since = float(params.get("since", 0))
        limit = min(int(params.get("limit", 100)), 500)
        entries = self.db.get_since(since, limit)
        return {
            "entries": [_entry_to_json(e) for e in entries],
            "ttl": [3] * len(entries),
        }

    def handle_post_combinations(self, data: dict) -> dict:
        entries_data = data.get("entries", [])
        ttl_list = data.get("ttl", [])
        accepted = 0
        for i, entry_data in enumerate(entries_data):
            entry = _json_to_entry(entry_data)
            if entry is None:
                continue
            try:
                is_new = self.db.insert_from_sync(entry)
                if is_new:
                    accepted += 1
                    # Re-broadcast to other peers
                    ttl = ttl_list[i] if i < len(ttl_list) else 0
                    if ttl > 0:
                        self.peer_manager.broadcast(entry, ttl)
            except Exception:
                pass
        return {"accepted": accepted}

    def handle_announce(self, data: dict) -> dict:
        peer_id = data.get("peer_id", "")
        address = data.get("address", "127.0.0.1")
        port = data.get("port", 8765)
        self.peer_manager.add_peer(address, port, peer_id)
        return {
            "peer_id": self.peer_manager.peer_id,
            "peers": [
                {"peer_id": p.peer_id, "address": p.address, "port": p.port}
                for p in self.peer_manager.get_peers()
            ],
        }

    # ------------------------------------------------------------------
    # Discovery Server endpoints (lightweight tracker)
    # ------------------------------------------------------------------

    def handle_discovery_announce(self, data: dict, remote_ip: str = "") -> dict:
        from src.hub.discovery import get_discovery_server
        ds = get_discovery_server()

        peer_id = data.get("peer_id", "")
        address = data.get("address", "127.0.0.1")
        port = int(data.get("port", 8765))
        timestamp = float(data.get("timestamp", 0))
        public_key_b64 = data.get("public_key", "")
        signature_b64 = data.get("signature", "")

        # Signature verification (when present)
        verified = False
        if public_key_b64 and signature_b64:
            from src.hub.identity import verify_announce_payload
            ok, reason = verify_announce_payload(
                peer_id, address, port, timestamp,
                public_key_b64, signature_b64,
            )
            if not ok:
                # Signature present but invalid → reject
                return {"ok": False, "error": f"verification_failed: {reason}"}

        result = ds.announce(
            peer_id=peer_id,
            address=address,
            port=port,
            detected_ip=remote_ip,
            public_key_b64=public_key_b64,
            signature_b64=signature_b64,
            timestamp=timestamp,
        )
        if verified:
            result["verified"] = True
        return result

    def handle_discovery_peers(self) -> dict:
        from src.hub.discovery import get_discovery_server
        ds = get_discovery_server()
        return {"peers": ds.get_peers()}

    def handle_discovery_heartbeat(self, data: dict, remote_ip: str = "") -> dict:
        from src.hub.discovery import get_discovery_server
        ds = get_discovery_server()
        ok = ds.heartbeat(data.get("peer_id", ""))
        return {"ok": ok}

    def handle_submit_method(self, body: bytes) -> dict:
        """Handle method submission (form-urlencoded or JSON)."""
        from urllib.parse import parse_qs
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {k: v[0] for k, v in parse_qs(body.decode()).items()}

        errors = []
        name = data.get("name", "").strip()
        domain = data.get("domain", "").strip()
        level = data.get("level", "")
        description = data.get("description", "").strip()

        if not name:
            errors.append("Name is required.")
        if not domain:
            errors.append("Domain is required.")
        if not description:
            errors.append("Description is required.")
        try:
            level = int(level)
            if level < 1 or level > 4:
                errors.append("Level must be 1-4.")
        except (ValueError, TypeError):
            errors.append("Level must be a number 1-4.")

        if errors:
            return {"ok": False, "errors": errors}

        sub_data = {
            "name": name,
            "domain": domain,
            "level": level,
            "description": description,
            "examples": [e.strip() for e in data.get("examples", "").split(",") if e.strip()],
            "prerequisites": [p.strip() for p in data.get("prerequisites", "").split(",") if p.strip()],
            "compatible_with": [c.strip() for c in data.get("compatible_with", "").split(",") if c.strip()],
        }
        submitter = data.get("submitter", "anonymous").strip()
        sub_id = self.db.submit("method", sub_data, submitter)
        return {"ok": True, "id": sub_id}

    def handle_submit_problem(self, body: bytes) -> dict:
        """Handle problem submission (form-urlencoded or JSON)."""
        from urllib.parse import parse_qs
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            decoded = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(body.decode()).items()}
            data = decoded

        errors = []
        title = data.get("title", "").strip()
        domain = data.get("domain", "").strip()
        description = data.get("description", "").strip()

        if not title:
            errors.append("Title is required.")
        if not domain:
            errors.append("Domain is required.")
        if not description:
            errors.append("Description is required.")

        if errors:
            return {"ok": False, "errors": errors}

        constraints = data.get("constraints", data.get("constraint_types", []))
        if isinstance(constraints, str):
            constraints = [constraints] if constraints else []
        maturity = data.get("maturity", 1)
        try:
            maturity = int(maturity)
        except (ValueError, TypeError):
            maturity = 1

        sub_data = {
            "title": title,
            "domain": domain,
            "description": description,
            "constraint_types": constraints,
            "maturity": maturity,
        }

        # TRIZ standardization
        try:
            from src.triz.agent import TRIZAgent
            from src.evaluation.providers import get_api_key, get_api_base, get_model
            api_key = get_api_key()
            agent = TRIZAgent()
            if api_key:
                from src.evaluation.providers import OpenAIProvider
                agent = TRIZAgent(ai_provider=OpenAIProvider(
                    api_key=api_key, api_base=get_api_base(), model=get_model()))
            problem = agent.standardize(description, domain)
            if problem.triz_standardized:
                sub_data["triz_standardized"] = problem.triz_standardized
        except Exception:
            pass  # TRIZ is best-effort, never block submission

        submitter = data.get("submitter", "anonymous").strip()
        sub_id = self.db.submit("problem", sub_data, submitter)
        return {"ok": True, "id": sub_id}


class HubServer:
    """HTTP server wrapping HubAPI + PeerManager for P2P hub operation."""

    def __init__(
        self,
        db: LeaderboardDB,
        config: PeerConfig | None = None,
    ):
        self.config = config or PeerConfig()
        self.db = db
        self.peer_manager = PeerManager(db, self.config)
        self.api = HubAPI(db, self.peer_manager)
        from src.blockchain.contracts import SimulatedToken, StakingContract
        from src.blockchain.buffer import BufferZone
        self.token = SimulatedToken(db)
        self.staking = StakingContract(db, self.token)
        self.buffer_zone = BufferZone(db, self.token, self.staking)
        from src.hub.token_layer import TokenGate
        self.token_gate = TokenGate(db, self.token)

    def start(self):
        self.peer_manager.start()
        print(f"Hub started on port {self.config.port} "
              f"(peer_id: {self.peer_manager.peer_id})")
        print("WARNING: Serving over HTTP. For production, use a reverse "
              "proxy with HTTPS (e.g., nginx + certbot).")
        _HubHandler.api = self.api
        _HubHandler.db = self.db
        _HubHandler.peer_manager = self.peer_manager
        _HubHandler.buffer_zone = self.buffer_zone
        _HubHandler.token_gate = self.token_gate
        from src.hub.discovery import RateLimiter
        _HubHandler.web_rate_limiter = RateLimiter(max_requests=30, window_seconds=60)
        self._http = _ThreadingHTTPServer(("0.0.0.0", self.config.port), _HubHandler)
        # Run server in daemon thread so shutdown() works from signal handler
        import threading
        self._server_thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._server_thread.start()
        self._server_thread.join()

    def stop(self):
        self.peer_manager.stop()
        self._http.shutdown()
        self._http.server_close()
