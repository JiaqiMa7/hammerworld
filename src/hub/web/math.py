"""Math Research Zone pages — problem list, method zones, solutions, MCTS tree."""
from __future__ import annotations

import json
import time

from ._translation import _t
from ._utils import _esc, _parse_query, _score_bar
from ._layout import _base_page
from src.hub.leaderboard import LeaderboardDB

_MATH_CATEGORIES = [
    "number_theory", "analysis", "algebra", "geometry",
    "topology", "combinatorics", "logic", "other",
]


# -- Helpers ------------------------------------------------------------------


def _math_problem_header(problem: dict) -> str:
    title = _esc(problem["title"])
    desc = _esc((problem.get("description") or "")[:300])
    cat = (problem.get("category") or "other").replace("_", " ").title()
    creator = _esc((problem.get("creator") or "unknown")[:16])
    return f"""
    <div class="card">
        <h3>{title}</h3>
        <p style="color:#777;font-size:13px;margin-bottom:4px;">
            <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
            &nbsp; by {creator}
        </p>
        <p style="font-size:14px;color:#555;margin-top:8px;">{desc}</p>
    </div>"""


def _math_zone_table_rows(db: LeaderboardDB, collections: list,
                          pid: int, user_addr: str) -> tuple[list[str], str]:
    rows = []
    for c in collections:
        mid = c["id"]
        mname = _esc(c["name"])
        mitems = len(json.loads(c.get("methods_json") or "[]"))
        accessed = db.check_math_access(pid, mid, user_addr) if user_addr else False

        with db._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*), MAX(max_correct_step) FROM math_solutions "
                "WHERE problem_id = ? AND method_collection_id = ?",
                (pid, mid),
            ).fetchone()
        sol_count = row[0] if row else 0
        top_step = row[1] or 0

        zone_url = f'/web/math/{pid}/{mid}'
        unlock_url = f'/web/math/{pid}/{mid}/unlock'
        if user_addr:
            zone_url += f'?user_address={_esc(user_addr)}'
            unlock_url += f'?user_address={_esc(user_addr)}'
        label = ('<span style="color:#22c55e;">&#x2713; Unlocked</span>'
                 if accessed
                 else f'<a href="{unlock_url}" style="color:#ef4444;">Locked &mdash; Unlock</a>')

        rows.append(f"""
        <tr>
            <td><a href="{zone_url}"><b>{mname}</b></a><br><span style="font-size:11px;color:#999;">{mitems} tools</span></td>
            <td>{label}</td>
            <td><b>{top_step}</b> steps</td>
            <td>{sol_count} solution(s)</td>
        </tr>""")

    form = f"""
    <form method="get" action="/web/math/{pid}" style="margin-bottom:12px;">
        <input type="text" name="user_address" value="{_esc(user_addr)}" placeholder="Your address (e.g. 0xALICE)" style="flex:1;min-width:260px;">
        <button type="submit">Check Access</button>
    </form>"""
    return rows, form


def _math_solution_rows(solutions: list, pid: int, mid: int,
                        user_addr: str, lang: str,
                        coll_name: str = "") -> list[str]:
    rows = []
    for i, s in enumerate(solutions):
        sid = s["id"]
        try:
            steps = json.loads(s["steps_json"])
        except Exception:
            steps = []
        step_count = len(steps)
        max_step = s["max_correct_step"]
        mname = _esc((s.get("method_name") or coll_name or "?")[:30])
        parent = s.get("parent_solution_id")
        fork_info = (f' <span style="font-size:11px;color:#999;">(forked from #{parent})</span>'
                     if parent else "")
        rows.append(f"""
        <tr>
            <td>{i + 1}</td>
            <td><a href="/web/math/{pid}/{mid}/{sid}">{mname}</a>{fork_info}</td>
            <td>{_score_bar(max_step, max(10, max_step + 5))}</td>
            <td>{step_count} steps</td>
            <td><a href="/web/math/{pid}/{mid}/{sid}?fork=1&user_address={_esc(user_addr)}" style="color:#2563eb;">Fork</a></td>
        </tr>""")
    return rows


def _math_step_rows(steps: list[dict], solution_id: int = 0,
                     db: LeaderboardDB | None = None,
                     p_user: str = "", pid: int = 0, mid: int = 0) -> list[str]:
    step_rows = []
    for s in sorted(steps, key=lambda x: x.get("step_num", 0)):
        sn = s.get("step_num", "?")
        verified = s.get("verified", False)
        content_text = _esc(s.get("content", ""))
        badge = '<span style="color:#22c55e;">&#x2713;</span>' if verified else '<span style="color:#ef4444;">&#x2717;</span>'
        star_info = ""
        if solution_id and db is not None:
            sc = db.get_step_star_count(solution_id, sn)
            star_display = f"★{sc}" if sc else "☆"
            user_q = _esc(p_user) if p_user else "anonymous"
            ref = _esc(f"/web/math/{pid}/{mid}/{solution_id}")
            star_info = f' <a href="/web/math/star-step/{solution_id}/{sn}?user_address={user_q}&ref={ref}" style="font-size:11px;color:#f59e0b;text-decoration:none;">{star_display}</a>'
        step_rows.append(f"""
        <tr>
            <td>{sn}</td>
            <td style="max-width:600px;">{content_text}</td>
            <td>{star_info}</td>
            <td>{badge}</td>
        </tr>""")
    return step_rows


def _math_fork_form(sid: int, pid: int, mid: int, steps: list[dict],
                    user_address: str) -> str:
    return f"""
    <div class="card" style="margin-top:16px;">
        <h3>Fork Solution #{sid}</h3>
        <form method="post" action="/web/math/{pid}/{mid}/{sid}/fork">
            <input type="hidden" name="user_address" value="{_esc(user_address)}">
            <p style="color:#777;font-size:13px;">This will create a copy of all {len(steps)} steps as your own solution.</p>
            <button type="submit" style="margin-top:8px;">Confirm Fork</button>
        </form>
    </div>"""


def _math_submit_form(pid: int, mid: int, sid: int, steps: list[dict],
                      user_address: str) -> str:
    return f"""
    <div class="card" style="margin-top:16px;">
        <h3>Submit Improvement</h3>
        <form method="post" action="/web/math/{pid}/{mid}/{sid}/submit">
            <input type="hidden" name="user_address" value="{_esc(user_address)}">
            <textarea name="steps_json" rows="8" style="width:100%;font-family:monospace;font-size:12px;">{_esc(json.dumps(steps, indent=2, ensure_ascii=False))}</textarea>
            <p style="font-size:11px;color:#999;margin-top:4px;">Edit the JSON above and submit. max_correct_step will be recalculated.</p>
            <button type="submit" style="margin-top:8px;">Submit Update</button>
        </form>
    </div>"""


def _math_unlock_content(pid: int, mid: int, problem: dict, coll: dict,
                         user_addr: str) -> str:
    pname = _esc(problem["title"])
    cname = _esc(coll["name"])
    return f"""
    <div class="card">
        <h3>Unlock: {cname} &rarr; {pname}</h3>
        <p style="color:#777;margin:12px 0;">
            To view solutions in this zone, you must first run a <b>math-mine</b> operation.
        </p>

        <h3 style="margin-top:16px;">Step 1: Run CLI command</h3>
        <pre style="background:#f0f3f7;padding:12px;border-radius:6px;font-size:13px;overflow-x:auto;">python3 -m src.cli.main math-mine \\
  --problem-id {pid} \\
  --methods-collection "{cname}" \\
  --address {"0xYOUR_ADDRESS" if not user_addr else _esc(user_addr)} \\
  --batch 3</pre>

        <h3 style="margin-top:16px;">Step 2: Manual unlock (if needed)</h3>
        <form method="post" action="/web/math/{pid}/{mid}/unlock">
            <input type="text" name="user_address" value="{_esc(user_addr)}" placeholder="Your address" required style="width:100%;margin-bottom:8px;">
            <input type="text" name="combo_id" placeholder="Combo ID from math-mine output" required style="width:100%;margin-bottom:8px;">
            <button type="submit">Unlock</button>
        </form>
    </div>

    <p style="margin-top:16px;"><a href="/web/math/{pid}">&larr; Back to Problem</a>"""


def _math_node_breadcrumb(db: LeaderboardDB, path_to_root: list[int],
                          pid: int, mid: int, lang: str) -> str:
    parts = []
    for pnid in reversed(path_to_root):
        pn = db.get_tree_node(pnid)
        if pn:
            parts.append(
                f'<a href="/web/math/{pid}/{mid}/tree/node/{pnid}?lang={lang}">'
                f'{_esc((pn["content"] or "Root")[:40])}</a>')
    return " → ".join(parts)


def _math_node_children_table(children: list[dict], uct_scores: list[dict],
                              pid: int, mid: int, lang: str) -> str:
    if not children:
        return '<p style="color:#999;margin-top:16px;">No children yet. Expand the tree!</p>'
    rows = ""
    for c in children:
        uct_str = ""
        for u in uct_scores:
            if u["child_id"] == c["child_id"]:
                if u.get("uct_score") == float('inf'):
                    uct_str = "∞"
                else:
                    uct_str = f'{u.get("uct_score", 0):.3f}'
                break
        rows += f"""<tr>
            <td><a href="/web/math/{pid}/{mid}/tree/node/{c['child_id']}?lang={lang}">{_esc(c['child_content'][:60])}</a></td>
            <td>{_esc(c['action_label'])}</td>
            <td>{c['child_q_value']:.3f}</td>
            <td>{c['child_visit_count']}</td>
            <td>{uct_str}</td>
            <td>{c['child_node_type']}</td>
        </tr>"""
    return f'<h2 style="margin-top:24px;">Children ({len(children)})</h2>\n<table><thead><tr><th>State</th><th>Action</th><th>Q</th><th>N</th><th>UCT</th><th>Type</th></tr></thead><tbody>{rows}</tbody></table>'


def _math_node_add_form(nid: int, pid: int, mid: int, err_html: str) -> str:
    return f"""<div class="card" style="margin-top:24px;">
    <h3>Add Child Node</h3>
    {err_html}
    <form method="post" action="/web/math/{pid}/{mid}/tree/node/{nid}/add_child">
        <table style="width:100%;">
            <tr><td style="color:#777;width:120px;padding:4px;">Content *</td>
                <td><input type="text" name="content" required style="width:100%;" placeholder="Mathematical state description"></td></tr>
            <tr><td style="color:#777;padding:4px;">Action Label</td>
                <td><input type="text" name="action_label" style="width:100%;" placeholder="Method/theorem applied"></td></tr>
            <tr><td style="color:#777;padding:4px;">Action Detail</td>
                <td><input type="text" name="action_description" style="width:100%;" placeholder="Optional description"></td></tr>
            <tr><td style="color:#777;padding:4px;">Type</td>
                <td><select name="node_type">
                    <option value="normal">Normal</option>
                    <option value="terminal_success">Terminal Success</option>
                    <option value="terminal_failure">Terminal Failure</option>
                </select></td></tr>
            <tr><td style="color:#777;padding:4px;">Reward</td>
                <td><input type="number" name="reward" value="1.0" min="0" max="1" step="0.1" style="width:100px;"></td></tr>
            <tr><td style="color:#777;padding:4px;">Your Address</td>
                <td><input type="text" name="user_address" value="0xEXPLORER" style="width:200px;"></td></tr>
            <tr><td></td><td><button type="submit">Add Child</button></td></tr>
        </table>
    </form>
</div>"""


def _math_node_terminal_forms(nid: int, pid: int, mid: int,
                              node_type: str) -> str:
    if node_type in ("terminal_success", "terminal_failure", "pruned"):
        return ""
    return f"""
    <div class="card" style="margin-top:16px;">
        <h3>Mark Terminal & Backpropagate</h3>
        <form method="post" action="/web/math/{pid}/{mid}/tree/node/{nid}/backpropagate" style="display:flex;gap:8px;align-items:center;">
            <select name="terminal_type">
                <option value="terminal_success">Success (Proof Found)</option>
                <option value="terminal_failure">Failure (Dead End)</option>
            </select>
            <input type="number" name="reward" value="1.0" min="0" max="1" step="0.1" style="width:80px;">
            <button type="submit">Backprop</button>
        </form>
    </div>
    <div class="card" style="margin-top:8px;">
        <h3>Prune Node</h3>
        <form method="post" action="/web/math/{pid}/{mid}/tree/node/{nid}/prune">
            <p style="color:#777;font-size:13px;margin-bottom:8px;">Mark as pruned — backpropagates neutral reward.</p>
            <button type="submit" style="background:#9ca3af;border-color:#9ca3af;">Prune</button>
        </form>
    </div>"""


def _tree_node_html(node: dict, node_id: int, lang: str) -> str:
    node_type = node["node_type"]
    type_css = {"terminal_success": "terminal-success",
                "terminal_failure": "terminal-failure",
                "pruned": "pruned"}.get(node_type, "")
    type_badge = {"terminal_success": '<span class="node-type-badge success">TERMINAL: Proved</span>',
                  "terminal_failure": '<span class="node-type-badge failure">TERMINAL: Dead End</span>',
                  "pruned": '<span class="node-type-badge pruned">PRUNED</span>'}.get(node_type, "")
    return f"""<div class="tree-node {type_css}">
    <div class="tree-node-header">
        {type_badge}
        <strong>Q: {node['q_value']:.3f}</strong>
        <span style="color:#999;font-size:12px;">N={node['visit_count']}</span>
        <span style="color:#999;font-size:11px;margin-left:4px;">#{node_id}</span>
        <a href="/web/math/{node['problem_id']}/{node['method_collection_id']}/tree/node/{node_id}?lang={lang}" style="font-size:11px;margin-left:8px;">Details</a>
    </div>
    <div class="tree-node-content">{_esc(node['content'][:200])}{'...' if len(node['content']) > 200 else ''}</div>
    <div style="font-size:11px;color:#999;">by {_esc(node['user_address'][:16]) or 'anonymous'}</div>
</div>"""


def _render_tree_stats(db: LeaderboardDB, pid: int, mid: int) -> str:
    nodes = db.get_tree_nodes_for_zone(pid, mid)
    terms = db.get_terminal_nodes(pid, mid)
    success = [n for n in terms if n["node_type"] == "terminal_success"]
    root = db.get_root_node(pid, mid)

    max_depth = 0
    for n in nodes:
        path = db._get_path_to_root(n["id"])
        if len(path) > max_depth:
            max_depth = len(path)

    return f"""<div class="stats">
        <div class="stat-card"><div class="num">{len(nodes)}</div><div class="dim-label">States</div></div>
        <div class="stat-card"><div class="num">{len(success)}</div><div class="dim-label">Proofs</div></div>
        <div class="stat-card"><div class="num">{max_depth}</div><div class="dim-label">Max Depth</div></div>
        <div class="stat-card"><div class="num">{root['q_value']:.2f}</div><div class="dim-label">Root Q</div></div>
        <div class="stat-card"><div class="num">{root['visit_count']}</div><div class="dim-label">Root N</div></div>
    </div>"""


def _render_tree_recursive(db: LeaderboardDB, node_id: int, depth: int = 0,
                           max_depth: int = 12, lang: str = "en") -> str:
    node = db.get_tree_node(node_id)
    if not node or depth > max_depth:
        return ""

    collapsed = depth >= 3
    checkbox_id = f"tc_{node_id}"
    children = db.get_children(node_id)
    has_children = len(children) > 0

    node_html = _tree_node_html(node, node_id, lang)

    if not has_children:
        return node_html

    children_html = ""
    for c in children:
        uct_str = ""
        if c.get("uct_score") is not None and c["uct_score"] != float('inf'):
            uct_str = f' UCT:{c["uct_score"]:.3f}'
        elif c.get("uct_score") == float('inf'):
            uct_str = ' UCT:∞'
        edge_tag = f'<span class="edge-label">→ {_esc(c["action_label"])}{uct_str}</span>'
        child_tree = _render_tree_recursive(db, c["child_id"], depth + 1, max_depth, lang)
        children_html += f'<div class="tree-child-wrapper">{edge_tag}{child_tree}</div>'

    if collapsed:
        return f"""{node_html}
<label class="tree-toggle collapsed" for="{checkbox_id}">{len(children)} branches</label>
<input type="checkbox" id="{checkbox_id}" style="display:none;">
<div class="tree-child-list tree-collapsible">{children_html}</div>"""
    else:
        return f"""{node_html}
<div class="tree-child-list">{children_html}</div>"""


def _render_method_pool(db: LeaderboardDB, pid: int, lang: str = "en") -> str:
    """Render the method pool section for a problem page."""
    pool = db.get_method_pool(pid)
    if not pool:
        return ""

    rows = []
    for e in pool:
        mname = _esc(e["method_name"][:60])
        star = f"★{e.get('stars', 0)}" if e.get("stars", 0) > 0 else "☆"
        bdim = _esc(e.get("best_dimension", ""))
        bscore = e.get("best_score", 0)
        miner = _esc((e.get("miner_address") or "?")[:16])
        # Decode analysis for a short insight
        insight = ""
        try:
            analysis = json.loads(e.get("analysis_json", "{}"))
            scores = analysis.get("scores", [])
            if scores:
                top = max(scores, key=lambda s: s.get("score", 0))
                insight = _esc(f"{top.get('dimension', '')}={top.get('score', 0):.1f}")
        except Exception:
            pass
        rows.append(f"""<tr>
    <td>#{e['id']}</td>
    <td><b>{mname}</b></td>
    <td>{star}</td>
    <td>{bscore:.1f} {bdim}</td>
    <td style="color:#777;font-size:12px;">{insight}</td>
    <td style="font-size:12px;">{miner}</td>
</tr>""")

    return f"""
<h2 style="margin-top:24px;">Method Pool ({len(pool)})</h2>
<p style="color:#777;font-size:13px;">Methods discovered via math-mining. Star a method to signal quality.</p>
<table>
<thead><tr><th>#</th><th>Method</th><th>Stars</th><th>Best Score</th><th>Insight</th><th>Miner</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
<p style="font-size:12px;color:#999;">
  <a href="/web/math/{pid}/pool?lang={lang}">View pool details</a>
</p>"""

def _render_method_pool_section(db: LeaderboardDB, pid: int, mid: int, coll_name: str, lang: str = "en") -> str:
    """Render method pool entries relevant to a specific (problem, method) zone."""
    pool = db.get_method_pool(pid, method_collection_id=mid)
    if not pool:
        return ""
    rows = []
    for e in pool:
        mname = _esc(e["method_name"][:60])
        star = f"★{e.get('stars', 0)}" if e.get("stars", 0) > 0 else "☆"
        bdim = _esc(e.get("best_dimension", ""))
        bscore = e.get("best_score", 0)
        miner = _esc((e.get("miner_address") or "?")[:16])
        rows.append(f"""<tr>
    <td>#{e['id']}</td>
    <td><b>{mname}</b></td>
    <td>{star}</td>
    <td>{bscore:.1f} {bdim}</td>
    <td style="font-size:12px;">{miner}</td>
</tr>""")
    return f"""
<h3 style="margin-top:20px;">Pooled Methods ({len(pool)})</h3>
<p style="color:#777;font-size:12px;">Mined methods in this zone. <a href="/web/math/{pid}">View full pool</a></p>
<table>
<thead><tr><th>#</th><th>Method</th><th>Stars</th><th>Best Score</th><th>Miner</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>"""


# -- Rendered page functions --------------------------------------------------


def render_math_home(db: LeaderboardDB, lang: str = "en", viewer_addr: str = "") -> str:
    problems = db.get_math_problems()
    cards = []
    for p in problems:
        pid = p["id"]
        title = _esc(p["title"])
        desc = _esc((p.get("description") or "")[:180])
        cat = (p.get("category") or "other").replace("_", " ").title()
        creator = _esc((p.get("creator") or "unknown")[:16])
        with db._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM math_solutions WHERE problem_id = ?", (pid,)
            ).fetchone()
        solution_count = row[0] if row else 0
        cards.append(f"""
        <div class="card">
            <h3><a href="/web/math/{pid}">{title}</a></h3>
            <p style="color:#777;font-size:13px;margin-bottom:4px;">
                <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
                &nbsp; {solution_count} solution(s) &nbsp; by {creator}
            </p>
            <p style="font-size:13px;color:#555;">{desc}</p>
        </div>""")

    content = f"""
    <div class="quick-links" style="margin-bottom:16px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <a href="/web/math/new">+ New Problem</a>
        <form action="/web/math/search" method="get" style="display:inline-flex;gap:4px;margin-left:auto;">
            <input type="text" name="q" placeholder="Search problems, methods..."
                   style="padding:4px 8px;border:1px solid #ccc;border-radius:4px;font-size:13px;">
            <button type="submit" style="padding:4px 12px;">Search</button>
        </form>
    </div>
    {"".join(cards) if cards else '<div class="empty">No math problem zones yet. <a href="/web/math/new">Apply to create the first one</a>.</div>'}
    """
    return _base_page("Math Research Zone", content, "math", lang=lang, viewer_addr=viewer_addr)


def render_math_search(db: LeaderboardDB, path: str, lang: str = "en",
                       viewer_addr: str = "") -> str:
    """Render search results across problems and method pool."""
    params = _parse_query(path)
    query = params.get("q", "").strip()
    if not query:
        return render_math_home(db, lang=lang, viewer_addr=viewer_addr)

    like = f"%{query}%"
    results = []

    # Search problems
    with db._connect() as conn:
        for row in conn.execute(
            "SELECT id, title, description, category, creator FROM math_problems "
            "WHERE title LIKE ? OR description LIKE ? LIMIT 10",
            (like, like),
        ):
            r = dict(row)
            r["_type"] = "problem"
            results.append(r)

    # Search method pool
    for e in db.search_math_pool(query, limit=10):
        e["_type"] = "pool"
        results.append(e)

    cards = []
    for r in results:
        if r["_type"] == "problem":
            pid = r["id"]
            title = _esc(r["title"])
            desc = _esc((r.get("description") or "")[:180])
            cat = (r.get("category") or "other").replace("_", " ").title()
            cards.append(f"""<div class="card">
    <h3><a href="/web/math/{pid}">{title}</a></h3>
    <p style="color:#777;font-size:13px;">
        <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
        &nbsp; Problem
    </p>
    <p style="font-size:13px;color:#555;">{desc}</p>
</div>""")
        elif r["_type"] == "pool":
            mname = _esc(r["method_name"][:60])
            bscore = r.get("best_score", 0)
            bdim = _esc(r.get("best_dimension", ""))
            miner = _esc((r.get("miner_address") or "?")[:16])
            star = f"★{r.get('stars', 0)}" if r.get("stars", 0) > 0 else "☆"
            cards.append(f"""<div class="card">
    <h3><a href="/web/math/{r['problem_id']}">{mname}</a></h3>
    <p style="color:#777;font-size:13px;">
        <span style="background:#fef3c7;color:#92400e;padding:1px 8px;border-radius:3px;font-size:11px;">Pool Method</span>
        &nbsp; {star} &nbsp; best={bscore:.1f} {bdim} &nbsp; by {miner}
    </p>
    <p style="font-size:13px;color:#555;">Problem #{r['problem_id']} &middot; {_esc(r.get('method_name', '')[:80])}</p>
</div>""")

    content = f"""
    <div class="quick-links" style="margin-bottom:16px;">
        <a href="/web/math">&larr; Back to Math Zone</a>
    </div>
    <h2>Search: {_esc(query)}</h2>
    <p style="color:#777;margin-bottom:16px;">{len(results)} result(s)</p>
    {''.join(cards) if cards else '<div class="empty">No results found.</div>'}
    """
    return _base_page(f"Search: {query}", content, "math", lang=lang, viewer_addr=viewer_addr)


def render_math_new(form: dict | None = None, errors: list[str] | None = None, success: str = "", lang: str = "en", viewer_addr: str = "") -> str:
    f = form or {}
    err_html = "".join(f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>' for e in (errors or []))
    ok_html = f'<p style="color:#22c55e;margin:8px 0;">{_esc(success)}</p>' if success else ""

    cat_opts = "".join(
        f'<option value="{c}" {"selected" if f.get("category") == c else ""}>{c.replace("_", " ").title()}</option>'
        for c in _MATH_CATEGORIES
    )

    content = f"""
    {err_html}{ok_html}
    <form method="post" action="/web/math/new">
        <table style="max-width:700px;">
            <tr><td style="color:#777;width:140px;padding:8px;">Title *</td>
                <td><input type="text" name="title" value="{_esc(f.get('title', ''))}" required style="width:100%;" placeholder="e.g. Riemann Hypothesis"></td></tr>
            <tr><td style="color:#777;padding:8px;">Category *</td>
                <td><select name="category">{cat_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Description</td>
                <td><textarea name="description" rows="4" style="width:100%;" placeholder="Describe the problem...">{_esc(f.get('description', ''))}</textarea></td></tr>
            <tr><td style="color:#777;padding:8px;">Creator</td>
                <td><input type="text" name="creator" value="{_esc(f.get('creator', 'anonymous'))}" style="width:100%;"></td></tr>
        </table>
        <button type="submit" style="margin-top:12px;padding:10px 28px;">Create Problem Zone</button>
    </form>
    """
    return _base_page("New Math Problem", content, "math", lang=lang, viewer_addr=viewer_addr)


def render_math_problem(db: LeaderboardDB, pid: int, path: str, lang: str = "en",
                         viewer_addr: str = "") -> str:
    problem = db.get_math_problem(pid)
    if not problem:
        return _base_page("Not Found", '<div class="empty">Math problem not found.</div>', lang=lang, viewer_addr=viewer_addr)

    params = _parse_query(path)
    user_addr = params.get("user_address", "")

    header_card = _math_problem_header(problem)
    method_colls = db.get_collections("method", sort_by="stars", category="mathematics")
    rows, addr_form = _math_zone_table_rows(db, method_colls, pid, user_addr)

    pool_html = _render_method_pool(db, pid, lang)

    content = f"""
    {header_card}
    {addr_form}
    <h2>Method Zones</h2>
    <table>
    <thead><tr><th>Method Collection</th><th>Access</th><th>Top Step</th><th>Solutions</th></tr></thead>
    <tbody>{"".join(rows) if rows else '<tr><td colspan="4" class="empty">No math method collections yet. <a href="/web/collections/new">Create one</a> with category "mathematics".</td></tr>'}</tbody>
    </table>
    {pool_html}
    <p style="margin-top:16px;"><a href="/web/math">&larr; Back to Math Zone</a></p>
    """
    return _base_page(_esc(problem["title"]), content, "math", lang=lang, viewer_addr=viewer_addr)


def render_math_method_zone(db: LeaderboardDB, pid: int, mid: int, path: str,
                             lang: str = "en", viewer_addr: str = "") -> str:
    problem = db.get_math_problem(pid)
    coll = db.get_collection("method", mid)
    if not problem or not coll:
        return _base_page("Not Found", '<div class="empty">Problem or method collection not found.</div>', lang=lang, viewer_addr=viewer_addr)

    params = _parse_query(path)
    user_addr = params.get("user_address", "")

    accessed = db.check_math_access(pid, mid, user_addr) if user_addr else False
    if not accessed:
        return _base_page("Access Required", f"""
        <div class="card">
            <h3>Access Required</h3>
            <p style="color:#777;margin:12px 0;">You must unlock this zone before viewing solutions.</p>
            <pre style="background:#f0f3f7;padding:12px;border-radius:6px;font-size:13px;">python3 -m src.cli.main math-mine --problem-id {pid} --methods-collection "{_esc(coll['name'])}" --address {"0xYOUR_ADDRESS" if not user_addr else _esc(user_addr)} --batch 3</pre>
            <p style="margin-top:8px;"><a href="/web/math/{pid}/{mid}/unlock?user_address={_esc(user_addr)}">Manual Unlock</a></p>
            <p style="margin-top:8px;"><a href="/web/math/{pid}/{mid}/tree?lang={lang}">Tree View</a></p>
            <p style="margin-top:16px;"><a href="/web/math/{pid}{'?user_address=' + _esc(user_addr) if user_addr else ''}">&larr; Back to Problem</a></p>
        </div>
        """, "math", viewer_addr=viewer_addr)

    solutions = db.get_math_solutions(pid, mid)
    sol_rows = _math_solution_rows(solutions, pid, mid, user_addr, lang,
                                   coll_name=coll['name'])

    # Method pool section for this zone
    pool_entries = db.get_method_pool(pid, method_collection_id=mid)
    pool_html = _render_method_pool_section(db, pid, mid, coll['name'], lang) if pool_entries else ""

    content = f"""
    <div class="card">
        <h3>{_esc(problem['title'])} &mdash; {_esc(coll['name'])}</h3>
        <p style="color:#777;font-size:13px;">
            Access: <span style="color:#22c55e;">&#x2713; Unlocked</span>
        </p>
    </div>

    <h2>Solutions ({len(solutions)})</h2>
    <table>
    <thead><tr><th>#</th><th>Method</th><th>Max Correct Step</th><th>Steps</th><th>Action</th></tr></thead>
    <tbody>{"".join(sol_rows) if sol_rows else '<tr><td colspan="5" class="empty">No solutions yet. <a href="/web/math/{pid}/{mid}/unlock">Submit the first one</a>.</td></tr>'}</tbody>
    </table>

    {pool_html}

    <p style="margin-top:16px;">
        <a href="/web/math/{pid}{'?user_address=' + _esc(user_addr) if user_addr else ''}">&larr; Back to Problem</a>
        &nbsp;|&nbsp; <a href="/web/math/{pid}/{mid}/tree?lang={lang}">Tree View</a>
    </p>
    """
    return _base_page(f"{problem['title']} — {coll['name']}", content, "math", lang=lang, viewer_addr=viewer_addr)


def _math_solution_content(solution: dict, problem: dict | None, coll: dict | None,
                           sid: int, pid: int, mid: int, lang: str,
                           user: str, max_step: int, steps: list, step_rows: list,
                           fork_form: str, submit_form: str, parent_info: str,
                           p_user: str) -> str:
    ptitle = _esc(problem['title']) if problem else '?'
    cname = _esc(coll['name']) if coll else '?'
    mname = _esc((solution.get("method_name") or cname)[:40])
    step_tbody = ("".join(step_rows) if step_rows
                  else '<tr><td colspan="4" class="empty">No steps.</td></tr>')
    return f"""
    <div style="background:#fefce8;border:1px solid #facc15;border-radius:6px;padding:8px 12px;margin-bottom:16px;font-size:13px;color:#92400e;">
        This flat solution view is deprecated. See the <a href="/web/math/{pid}/{mid}/tree?lang={lang}">Tree View</a> for the new MCTS exploration interface.
    </div>
    <div class="card">
        <h3>Solution #{sid}</h3>
        <p style="color:#777;font-size:13px;">
            Problem: <b>{ptitle}</b> &nbsp;
            Method: <b>{mname}</b> <span style="font-size:11px;color:#999;">(collection: {cname})</span>
        </p>
        <p style="color:#777;font-size:13px;">
            By: <b>{user}</b> &nbsp;
            Max Correct Step: <b>{max_step}</b> &nbsp;
            Steps: <b>{len(steps)}</b>
        </p>
        {parent_info}
    </div>

    <h2>Steps</h2>
    <table>
    <thead><tr><th>#</th><th>Content</th><th>Stars</th><th>Verified</th></tr></thead>
    <tbody>{step_tbody}</tbody>
    </table>

    <div class="quick-links" style="margin-top:16px;">
        <a href="/web/math/{pid}/{mid}/{sid}?fork=1&user_address={_esc(p_user)}">Fork Solution</a>
    </div>
    {fork_form}
    {submit_form}

    <p style="margin-top:16px;"><a href="/web/math/{pid}/{mid}{'?user_address=' + _esc(p_user) if p_user else ''}">&larr; Back to Method Zone</a>"""


def render_math_solution(db: LeaderboardDB, pid: int, mid: int, sid: int, path: str,
                          lang: str = "en", viewer_addr: str = "") -> str:
    solution = db.get_math_solution(sid)
    if not solution:
        return _base_page("Not Found", '<div class="empty">Solution not found.</div>', lang=lang, viewer_addr=viewer_addr)

    problem = db.get_math_problem(pid)
    coll = db.get_collection("method", mid)

    try:
        steps = json.loads(solution["steps_json"])
    except Exception:
        steps = []

    max_step = solution["max_correct_step"]
    user = _esc((solution.get("user_address") or "unknown")[:16])
    parent = solution.get("parent_solution_id")

    params = _parse_query(path)
    p_user = params.get("user_address", "anonymous")
    step_rows = _math_step_rows(steps, solution_id=sid, db=db, p_user=p_user, pid=pid, mid=mid)
    fork = params.get("fork")

    fork_form = _math_fork_form(sid, pid, mid, steps, p_user) if fork else ""
    submit_form = _math_submit_form(pid, mid, sid, steps, p_user)
    parent_info = (f'<p style="color:#777;font-size:13px;">Forked from <a href="/web/math/{pid}/{mid}/{parent}">Solution #{parent}</a></p>'
                   if parent else "")

    content = _math_solution_content(solution, problem, coll, sid, pid, mid, lang,
                                     user, max_step, steps, step_rows,
                                     fork_form, submit_form, parent_info, p_user)
    return _base_page(f"Solution #{sid}", content, "math", lang=lang, viewer_addr=viewer_addr)


def render_math_unlock(db: LeaderboardDB, pid: int, mid: int, path: str,
                        lang: str = "en", viewer_addr: str = "") -> str:
    problem = db.get_math_problem(pid)
    coll = db.get_collection("method", mid)
    if not problem or not coll:
        return _base_page("Not Found", '<div class="empty">Problem or method collection not found.</div>', lang=lang, viewer_addr=viewer_addr)

    params = _parse_query(path)
    user_addr = params.get("user_address", "") or viewer_addr

    accessed = db.check_math_access(pid, mid, user_addr) if user_addr else False

    if accessed:
        return _base_page("Zone Unlocked", f"""
        <div class="card">
            <h3 style="color:#22c55e;">&#x2713; Zone Already Unlocked</h3>
            <p style="color:#777;margin:12px 0;">You have access to this zone.</p>
            <a href="/web/math/{pid}/{mid}?user_address={_esc(user_addr)}">Go to Method Zone</a>
        </div>
        """, "math", viewer_addr=viewer_addr)

    cname = _esc(coll["name"])
    content = _math_unlock_content(pid, mid, problem, coll, user_addr)
    return _base_page(f"Unlock: {cname}", content, "math", lang=lang, viewer_addr=viewer_addr)


def render_math_tree(db: LeaderboardDB, pid: int, mid: int, path: str,
                     lang: str = "en", viewer_addr: str = "") -> str:
    problem = db.get_math_problem(pid)
    if not problem:
        return _base_page("Not Found", "<p>Problem not found.</p>", "math", lang=lang, viewer_addr=viewer_addr)

    coll = db.get_collection("method", mid)
    if not coll:
        return _base_page("Not Found", "<p>Method collection not found.</p>", "math", lang=lang, viewer_addr=viewer_addr)

    root = db.get_root_node(pid, mid)
    if not root:
        return _base_page("Empty Tree", "<p>No tree root. Run math-mine first.</p>", "math", lang=lang, viewer_addr=viewer_addr)

    stats_html = _render_tree_stats(db, pid, mid)
    tree_html = _render_tree_recursive(db, root["id"], lang=lang)

    content = f"""
    <div class="quick-links">
        <a href="/web/math/{pid}?lang={lang}">Problem</a>
        <a href="/web/math/{pid}/{mid}?lang={lang}">Solutions</a>
        <span class="sep">Tree View</span>
    </div>

    {stats_html}

    <h2>{_esc(coll['name'])} — {_t('math.tree.title', lang)}</h2>

    <div style="margin:12px 0;">
        <a href="/web/math/{pid}/{mid}/tree/node/{root['id']}?lang={lang}" class="tree-toggle">Root Node Detail</a>
    </div>

    <div class="tree-container">
        {tree_html}
    </div>
    """
    title = f"{_esc(problem['title'])} — Tree"
    return _base_page(title, content, "math", lang=lang, viewer_addr=viewer_addr)


def _math_node_detail_content(node: dict, parent_node: dict | None, nid: int,
                               pid: int, mid: int, lang: str, breadcrumb: str,
                               type_css: str, type_badge_html: str,
                               children: list, children_table: str,
                               terminal_form: str, add_form: str) -> str:
    author_stat = (f'<div class="stat-card"><div class="num">{node["user_address"][:12]}</div><div class="dim-label">Author</div></div>'
                   if node['user_address'] else "")
    created = (time.strftime('%Y-%m-%d %H:%M', time.localtime(node['created_at']))
               if node['created_at'] else 'N/A')
    parent_link = (f' | Parent: <a href="/web/math/{pid}/{mid}/tree/node/{parent_node["id"]}?lang={lang}">#{parent_node["id"]}</a>'
                   if parent_node else ' | Root Node')
    return f"""
    <div class="quick-links">
        <a href="/web/math/{pid}?lang={lang}">Problem</a>
        <a href="/web/math/{pid}/{mid}?lang={lang}">Method Zone</a>
        <a href="/web/math/{pid}/{mid}/tree?lang={lang}">Tree View</a>
        <span class="sep">Node #{nid}</span>
    </div>

    <div style="font-size:13px;color:#999;margin-bottom:16px;">{breadcrumb}</div>

    <div class="card tree-node {type_css}">
        <div style="margin-bottom:8px;">{type_badge_html}</div>
        <h3>{_esc(node['content'])}</h3>
        <div class="stats" style="margin-top:12px;">
            <div class="stat-card"><div class="num">{node['q_value']:.3f}</div><div class="dim-label">Q-Value</div></div>
            <div class="stat-card"><div class="num">{node['visit_count']}</div><div class="dim-label">Visits (N)</div></div>
            <div class="stat-card"><div class="num">{node['reward']:.2f}</div><div class="dim-label">Reward</div></div>
            <div class="stat-card"><div class="num">{len(children)}</div><div class="dim-label">Children</div></div>
            {author_stat}
        </div>
        <p style="color:#777;font-size:12px;margin-top:8px;">
            Created: {created}
            {parent_link}
        </p>
    </div>

    {children_table}
    {terminal_form}
    {add_form}"""


def render_math_tree_node(db: LeaderboardDB, pid: int, mid: int, nid: int,
                          path: str, lang: str = "en",
                          errors: list[str] | None = None,
                          viewer_addr: str = "") -> str:
    problem = db.get_math_problem(pid)
    if not problem:
        return _base_page("Not Found", "<p>Problem not found.</p>", "math", lang=lang, viewer_addr=viewer_addr)

    node = db.get_tree_node(nid)
    if not node:
        return _base_page("Not Found", "<p>Node not found.</p>", "math", lang=lang, viewer_addr=viewer_addr)

    children = db.get_children(nid)
    uct_scores = db.get_uct_scores(nid)
    path_to_root = db._get_path_to_root(nid)
    parent = db._get_parent_node(nid)
    parent_node = parent if parent else None

    err_html = ("".join(f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>' for e in errors)
                if errors else "")
    breadcrumb = _math_node_breadcrumb(db, path_to_root, pid, mid, lang)

    node_type = node["node_type"]
    type_css = {"terminal_success": "terminal-success",
                "terminal_failure": "terminal-failure",
                "pruned": "pruned"}.get(node_type, "")
    type_badge_html = {"terminal_success": '<span class="node-type-badge success">TERMINAL: Proved</span>',
                       "terminal_failure": '<span class="node-type-badge failure">TERMINAL: Dead End</span>',
                       "pruned": '<span class="node-type-badge pruned">PRUNED</span>',
                       "normal": '<span class="node-type-badge normal">Normal</span>'}.get(node_type, "")

    children_table = _math_node_children_table(children, uct_scores, pid, mid, lang)
    add_form = _math_node_add_form(nid, pid, mid, err_html)
    terminal_form = _math_node_terminal_forms(nid, pid, mid, node_type)

    content = _math_node_detail_content(node, parent_node, nid, pid, mid, lang,
                                        breadcrumb, type_css, type_badge_html,
                                        children, children_table, terminal_form, add_form)
    title = f"Node #{nid} — {_esc(problem['title'])}"
    return _base_page(title, content, "math", lang=lang, viewer_addr=viewer_addr)
