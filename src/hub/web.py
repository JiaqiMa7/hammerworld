"""Server-side HTML rendering for the hub web interface."""
from __future__ import annotations

import json
import time
from typing import Optional

from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry
from src.hub.peer import PeerManager
from src.engine.models import EvalDimension, Domain, MethodLevel


# ------------------------------------------------------------------
# CSS (shared across all pages)
# ------------------------------------------------------------------

_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f4f6f9; color: #333; line-height: 1.6;
    max-width: 1200px; margin: 0 auto; padding: 0 16px;
}
a { color: #2563eb; text-decoration: none; }
a:hover { text-decoration: underline; }
nav {
    display: flex; gap: 4px; padding: 16px 0; flex-wrap: wrap;
    border-bottom: 1px solid #dde1e6; margin-bottom: 20px;
}
nav a {
    padding: 6px 14px; border-radius: 6px; background: #e8ecf0;
    color: #555; font-size: 14px; transition: background 0.15s, color 0.15s;
}
nav a:hover, nav a.active { background: #2563eb; color: #fff; text-decoration: none; }
h1 { font-size: 22px; color: #1a1a2e; margin-bottom: 16px; }
h2 { font-size: 18px; color: #555; margin: 16px 0 8px; }
.stats { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.stat-card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 16px 24px; text-align: center; min-width: 120px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stat-card .num { font-size: 28px; font-weight: bold; color: #2563eb; }
.stat-card .label { font-size: 13px; color: #777; margin-top: 4px; }
.quick-links { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
.quick-links a, .quick-links span {
    padding: 4px 12px; border-radius: 6px; font-size: 13px;
    background: #e8ecf0; border: 1px solid #dde1e6; color: #555;
    transition: background 0.15s, color 0.15s;
}
.quick-links a:hover { background: #2563eb; color: #fff; text-decoration: none; }
.quick-links .sep { border: none; background: none; color: #bbb; padding: 4px 2px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #eef0f4; font-size: 13px; }
th { background: #f0f3f7; color: #666; font-weight: 600; position: sticky; top: 0; }
tr:hover { background: #f0f4f8; }
.bar-bg { width: 80px; height: 6px; background: #e5e7eb; border-radius: 3px; display: inline-block; vertical-align: middle; margin-right: 4px; }
.bar-fill { height: 100%; border-radius: 3px; }
.bar-high { background: #22c55e; } .bar-mid { background: #f59e0b; } .bar-low { background: #ef4444; }
form { margin-bottom: 20px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
input, select, button {
    background: #fff; border: 1px solid #dde1e6; color: #333;
    padding: 6px 12px; border-radius: 6px; font-size: 14px;
}
input:focus, select:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
button { cursor: pointer; background: #2563eb; border-color: #2563eb; color: #fff; }
button:hover { background: #1d4ed8; }
.pagination { display: flex; gap: 8px; margin: 16px 0; }
.card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 16px; margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.card h3 { font-size: 15px; color: #2563eb; margin-bottom: 8px; }
.card .scores { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.card .score-tag {
    font-size: 12px; padding: 2px 8px; border-radius: 4px;
    background: #e8f0fe; color: #2563eb;
}
.empty { text-align: center; color: #999; padding: 40px; font-size: 15px; }
footer { text-align: center; padding: 20px; color: #999; font-size: 12px; border-top: 1px solid #e5e7eb; margin-top: 30px; }
.dim-label { font-size: 11px; color: #999; }
"""


def _base_page(title: str, content: str, active_nav: str = "") -> str:
    nav_items = [
        ("/", "Dashboard", "dashboard"),
        ("/web/leaderboard", "Leaderboard", "leaderboard"),
        ("/web/search", "Search", "search"),
        ("/web/random", "Random Draw", "random"),
        ("/web/peers", "Peers", "peers"),
        ("/web/math", "Math Zone", "math"),
        ("/web/collections", "Collections", "collections"),
        ("/web/buffer", "Buffer Zone", "buffer"),
        ("/web/submit", "Submit", "submit"),
    ]
    nav_html = "\n".join(
        f'<a href="{url}" class="{"active" if key == active_nav else ""}">{label}</a>'
        for url, label, key in nav_items
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)} — Idea Mining Network</title>
<style>{_CSS}</style>
</head>
<body>
<nav>{nav_html}</nav>
<h1>{_esc(title)}</h1>
{content}
<footer>Idea Mining Network &mdash; Phase 2 MVP</footer>
</body>
</html>"""


def _score_bar(score: float, max_score: float = 10.0) -> str:
    pct = min(score / max_score * 100, 100)
    if pct >= 70:
        cls = "bar-high"
    elif pct >= 40:
        cls = "bar-mid"
    else:
        cls = "bar-low"
    return f'<span class="bar-bg"><span class="bar-fill {cls}" style="width:{pct:.0f}%"></span></span>{score:.1f}'


def _entry_table(entries: list[LeaderboardEntry], start_rank: int = 1) -> str:
    if not entries:
        return '<div class="empty">No entries found.</div>'

    rows = []
    for i, e in enumerate(entries):
        row = (
            f"<tr>"
            f"<td>{start_rank + i}</td>"
            f"<td>{_score_bar(e.best_score)}</td>"
            f"<td>{e.best_dimension}</td>"
            f"<td><a href='/web/entry/{e.combo_id}'>{_esc(e.method_name[:30])}</a></td>"
            f"<td>{_esc(e.problem_title[:40])}</td>"
            f"<td><span class='dim-label'>{e.problem_domain}</span></td>"
            f"<td><span class='dim-label'>{_esc(e.miner_address[:12])}...</span></td>"
            f"</tr>"
        )
        rows.append(row)

    return f"""
    <table>
    <thead><tr>
        <th>#</th><th>Score</th><th>Dim</th><th>Method</th><th>Problem</th>
        <th>Domain</th><th>Miner</th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>"""


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _parse_query(path: str) -> dict[str, str]:
    params: dict[str, str] = {}
    if "?" in path:
        qs = path.split("?", 1)[1]
        for pair in qs.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = v
    return params


# ------------------------------------------------------------------
# Page renderers
# ------------------------------------------------------------------

def render_dashboard(db: LeaderboardDB, pm: PeerManager) -> str:
    total = db.total_entries()
    peers = len(pm.get_peers())
    uptime_m = int(pm.uptime / 60)
    uptime_str = f"{uptime_m // 60}h {uptime_m % 60}m" if uptime_m >= 60 else f"{uptime_m}m"

    # Top 10 entries
    top = db.get_top(limit=10)

    # Quick links
    dim_links = "".join(
        f'<a href="/web/leaderboard?dim={d.value}">{d.value.title()}</a>'
        for d in EvalDimension
    )
    domain_links = "".join(
        f'<a href="/web/leaderboard?domain={d.value}">{d.value.title()}</a>'
        for d in Domain
    )

    content = f"""
    <div class="stats">
        <div class="stat-card"><div class="num">{total}</div><div class="label">Entries</div></div>
        <div class="stat-card"><div class="num">{peers}</div><div class="label">Peers</div></div>
        <div class="stat-card"><div class="num">{uptime_str}</div><div class="label">Uptime</div></div>
    </div>

    <h2>By Dimension</h2>
    <div class="quick-links">{dim_links}</div>

    <h2>By Domain</h2>
    <div class="quick-links">{domain_links}</div>

    <h2>Top Entries</h2>
    {_entry_table(top)}
    """
    return _base_page("Dashboard", content, "dashboard")


def render_leaderboard(db: LeaderboardDB, path: str) -> str:
    params = _parse_query(path)
    dim = EvalDimension(params["dim"]) if params.get("dim") else None
    dom = Domain(params["domain"]) if params.get("domain") else None
    lvl = MethodLevel(int(params["level"])) if params.get("level") else None
    limit = min(int(params.get("limit", 50)), 200)
    offset = int(params.get("offset", 0))

    entries = db.get_top(dimension=dim, domain=dom, method_level=lvl, limit=limit, offset=offset)

    # Filter form
    dim_opts = "".join(
        f'<option value="{d.value}" {"selected" if dim and dim.value == d.value else ""}>{d.value.title()}</option>'
        for d in EvalDimension
    )
    domain_opts = "".join(
        f'<option value="{d.value}" {"selected" if dom and dom.value == d.value else ""}>{d.value.title()}</option>'
        for d in Domain
    )

    active_filters = []
    if dim:
        active_filters.append(f"Dimension: {dim.value}")
    if dom:
        active_filters.append(f"Domain: {dom.value}")
    if lvl:
        active_filters.append(f"Level: {lvl.value}")
    filter_text = " &mdash; ".join(active_filters) if active_filters else "All"

    # Build filter links (keep current params)
    def _filter_url(**overrides) -> str:
        p = {}
        if dim:
            p["dim"] = dim.value
        if dom:
            p["domain"] = dom.value
        if lvl:
            p["level"] = str(lvl.value)
        p.update(overrides)
        p["limit"] = str(limit)
        return "/web/leaderboard?" + "&".join(f"{k}={v}" for k, v in p.items())

    prev_link = ""
    if offset > 0:
        prev_offset = max(0, offset - limit)
        prev_link = f'<a href="{_filter_url(**{"offset": str(prev_offset)})}">&larr; Previous</a>'

    next_link = ""
    if len(entries) == limit:
        next_offset = offset + limit
        next_link = f'<a href="{_filter_url(**{"offset": str(next_offset)})}">Next &rarr;</a>'

    content = f"""
    <p style="color:#777;margin-bottom:12px;">Showing: {filter_text} &mdash; {len(entries)} results (offset {offset})</p>

    <form method="get" action="/web/leaderboard">
        <select name="dim"><option value="">All Dimensions</option>{dim_opts}</select>
        <select name="domain"><option value="">All Domains</option>{domain_opts}</select>
        <input type="number" name="limit" value="{limit}" min="10" max="200" style="width:80px;" placeholder="Limit">
        <button type="submit">Filter</button>
    </form>

    {_entry_table(entries, start_rank=offset + 1)}

    <div class="pagination">{prev_link}{next_link}</div>
    """
    return _base_page("Leaderboard", content, "leaderboard")


def render_search(db: LeaderboardDB, path: str) -> str:
    params = _parse_query(path)
    query = params.get("q", "")
    dim = EvalDimension(params["dim"]) if params.get("dim") else None
    limit = min(int(params.get("limit", 50)), 200)

    entries = db.search(query, dimension=dim, limit=limit) if query else []

    dim_opts = "".join(
        f'<option value="{d.value}" {"selected" if dim and dim.value == d.value else ""}>{d.value.title()}</option>'
        for d in EvalDimension
    )

    result_html = ""
    if query:
        if entries:
            result_html = f"<p style='color:#777;margin-bottom:12px;'>{len(entries)} results for '<b>{_esc(query)}</b>'</p>" + _entry_table(entries)
        else:
            result_html = f"<div class='empty'>No results for '<b>{_esc(query)}</b>'.</div>"
    else:
        result_html = "<div class='empty'>Enter a search term to find combinations.</div>"

    content = f"""
    <form method="get" action="/web/search">
        <input type="text" name="q" value="{_esc(query)}" placeholder="Search methods, problems, domains..." style="flex:1;min-width:300px;">
        <select name="dim"><option value="">All Dimensions</option>{dim_opts}</select>
        <button type="submit">Search</button>
    </form>
    {result_html}
    """
    return _base_page("Search", content, "search")


def render_random(db: LeaderboardDB, path: str) -> str:
    params = _parse_query(path)
    dim = EvalDimension(params["dim"]) if params.get("dim") else None
    dom = Domain(params["domain"]) if params.get("domain") else None
    count = min(int(params.get("count", 10)), 50)
    viewer = params.get("viewer", "web_viewer")

    draw = db.random_draw(dimension=dim, domain=dom, draw_count=count, viewer_addr=viewer)

    dim_opts = "".join(
        f'<option value="{d.value}" {"selected" if dim and dim.value == d.value else ""}>{d.value.title()}</option>'
        for d in EvalDimension
    )
    domain_opts = "".join(
        f'<option value="{d.value}" {"selected" if dom and dom.value == d.value else ""}>{d.value.title()}</option>'
        for d in Domain
    )

    cards = []
    for e in draw.entries:
        scores_html = "".join(
            f'<span class="score-tag">{name}: {score:.1f}</span>'
            for name, score in [
                ("Elegance", e.elegance), ("Weirdness", e.weirdness),
                ("Human Feas.", e.human_feasibility), ("AI Feas.", e.ai_feasibility),
                ("Novelty", e.novelty), ("Analogy Dist.", e.analogy_distance),
                ("Scale Pot.", e.scaling_potential), ("Side Effects", e.side_effects),
            ]
        )
        cards.append(f"""
        <div class="card">
            <h3><a href="/web/entry/{e.combo_id}">{_esc(e.method_name)} &times; {_esc(e.problem_title)}</a></h3>
            <p style="color:#777;font-size:13px;">Best: <b>{e.best_dimension}</b> = {_score_bar(e.best_score)} | Domain: {e.problem_domain} | Level: {e.method_level}</p>
            <div class="scores">{scores_html}</div>
        </div>""")

    content = f"""
    <form method="get" action="/web/random">
        <select name="dim"><option value="">All Dimensions</option>{dim_opts}</select>
        <select name="domain"><option value="">All Domains</option>{domain_opts}</select>
        <input type="number" name="count" value="{count}" min="1" max="50" style="width:80px;" placeholder="Count">
        <button type="submit">Draw</button>
    </form>

    <p style="color:#777;margin:12px 0;">
        Board: <b>{draw.board_name}</b> &mdash;
        Available: <b>{draw.total_in_board}</b> &mdash;
        Seed: <b>{draw.draw_seed}</b>
    </p>

    {"".join(cards) if cards else '<div class="empty">No entries available for this board.</div>'}
    """
    return _base_page("Random Draw", content, "random")


def render_peers(pm: PeerManager) -> str:
    peers = pm.get_peers()
    now = time.time()

    rows = []
    for i, p in enumerate(peers):
        ago = int(now - p.last_seen)
        ago_str = f"{ago}s ago" if ago < 60 else f"{ago // 60}m ago"
        rows.append(
            f"<tr><td>{i + 1}</td><td>{p.peer_id}</td>"
            f"<td>{p.address}:{p.port}</td><td>{ago_str}</td></tr>"
        )

    content = f"""
    <div class="stats">
        <div class="stat-card"><div class="num">{len(peers)}</div><div class="label">Connected Peers</div></div>
        <div class="stat-card"><div class="num">{pm.peer_id[:12]}...</div><div class="label">This Hub</div></div>
        <div class="stat-card"><div class="num">{pm.port}</div><div class="label">Port</div></div>
    </div>
    <table>
    <thead><tr><th>#</th><th>Peer ID</th><th>Address</th><th>Last Seen</th></tr></thead>
    <tbody>{"".join(rows) if rows else '<tr><td colspan="4" class="empty">No peers connected. Start another hub with --bootstrap to join.</td></tr>'}</tbody>
    </table>
    """
    return _base_page("Peers", content, "peers")


def render_entry(db: LeaderboardDB, combo_id: str) -> str:
    entry = db._get_by_id(combo_id)
    if not entry:
        content = '<div class="empty">Entry not found.</div>'
        return _base_page("Not Found", content)

    scores = [
        ("Elegance", entry.elegance),
        ("Weirdness", entry.weirdness),
        ("Human Feasibility", entry.human_feasibility),
        ("AI Feasibility", entry.ai_feasibility),
        ("Novelty", entry.novelty),
        ("Analogy Distance", entry.analogy_distance),
        ("Scaling Potential", entry.scaling_potential),
        ("Side Effects", entry.side_effects),
    ]

    score_rows = "".join(
        f"<tr><td>{name}</td><td>{_score_bar(score)}</td></tr>"
        for name, score in scores
    )

    content = f"""
    <div class="card">
        <h3>{_esc(entry.method_name)} &times; {_esc(entry.problem_title)}</h3>
        <table style="margin-top:12px;">
            <tr><td style="color:#777;width:140px;">Combo ID</td><td>{entry.combo_id}</td></tr>
            <tr><td style="color:#777;">Method</td><td>{_esc(entry.method_name)}</td></tr>
            <tr><td style="color:#777;">Method Domain</td><td>{entry.method_domain}</td></tr>
            <tr><td style="color:#777;">Method Level</td><td>{entry.method_level}</td></tr>
            <tr><td style="color:#777;">Problem</td><td>{_esc(entry.problem_title)}</td></tr>
            <tr><td style="color:#777;">Problem Domain</td><td>{entry.problem_domain}</td></tr>
            <tr><td style="color:#777;">Best Dimension</td><td><b>{entry.best_dimension}</b></td></tr>
            <tr><td style="color:#777;">Best Score</td><td><b>{entry.best_score:.1f}</b></td></tr>
            <tr><td style="color:#777;">Miner</td><td>{entry.miner_address}</td></tr>
        </table>
    </div>

    <h2>AI Analysis</h2>
    <div class="card" style="line-height:1.8;font-size:14px;">
        <p>{_esc(entry.analysis_text) if entry.analysis_text else '<span class="empty" style="padding:0;">No analysis text available.</span>'}</p>
    </div>

    <h2>Scores</h2>
    <table>{score_rows}</table>
    """
    return _base_page(f"{entry.method_name} × {entry.problem_title}", content)


# ------------------------------------------------------------------
# Matrix Marketplace — Collection pages
# ------------------------------------------------------------------

_COLLECTION_CATEGORIES_METHOD = [
    "triz", "biology", "physics", "chemistry", "mathematics",
    "economics", "machine_learning", "heuristic", "engineering",
    "design", "systems", "other",
]
_COLLECTION_CATEGORIES_PROBLEM = [
    "medicine", "energy", "environment", "information", "materials",
    "society", "transportation", "agriculture", "space", "other",
]


def render_collections(db: LeaderboardDB, path: str) -> str:
    """Browse method and problem collections with tab switching."""
    params = _parse_query(path)
    ctype = params.get("type", "method")
    sort_by = params.get("sort", "stars")
    category = params.get("category", None)
    mine = params.get("mine", None)

    if ctype not in ("method", "problem"):
        ctype = "method"

    collections = db.get_collections(ctype, sort_by=sort_by, category=category)

    if mine:
        collections = [c for c in collections if c.get("creator") == mine]

    # Tabs
    method_tab = f'<a href="/web/collections?type=method&sort=stars" class="{"active" if ctype == "method" else ""}">Methods</a>'
    problem_tab = f'<a href="/web/collections?type=problem&sort=imports" class="{"active" if ctype == "problem" else ""}">Problems</a>'

    # Sort links
    method_sorts = [
        ("stars", "Stars"),
        ("imports", "Imports"),
        ("newest", "Newest"),
    ]
    sort_links = " | ".join(
        f'<a href="/web/collections?type={ctype}&sort={s}&category={category or ""}&mine={mine or ""}" style="{"font-weight:bold;color:#2563eb;" if sort_by == s else "font-weight:normal;"}">{label}</a>'
        for s, label in method_sorts
    )

    # Category filter chips
    cats = _COLLECTION_CATEGORIES_METHOD if ctype == "method" else _COLLECTION_CATEGORIES_PROBLEM
    cat_links = "".join(
        f'<a href="/web/collections?type={ctype}&sort={sort_by}&category={c}" class="{"active" if category == c else ""}">{c.replace("_", " ").title()}</a>'
        for c in cats
    )

    # Cards
    cards = []
    for c in collections:
        cid = c["id"]
        items_json = c.get("methods_json") or c.get("problems_json") or "[]"
        try:
            items = json.loads(items_json)
        except Exception:
            items = []
        item_count = len(items)
        stars = c.get("stars", 0)
        imports = c.get("import_count", 0)
        name = _esc(c.get("name", "Unknown"))
        desc = _esc((c.get("description") or "")[:200])
        creator = _esc((c.get("creator") or "unknown")[:16])
        cat = c.get("category", "other").replace("_", " ").title()
        import_label = "import" if imports == 1 else "imports"

        cards.append(f"""
        <div class="card">
            <h3><a href="/web/collections/{ctype}/{cid}">{name}</a></h3>
            <p style="color:#777;font-size:13px;margin-bottom:4px;">
                <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
                &nbsp; {item_count} items &nbsp; &#x2605; {stars} &nbsp; {imports} {import_label} &nbsp; by {creator}
            </p>
            <p style="font-size:13px;color:#555;">{desc}</p>
        </div>""")

    if not cards:
        query_info = f" by <b>{_esc(mine)}</b>" if mine else ""
        cards_html = f'<div class="empty">No collections found{query_info}. <a href="/web/collections/new">Create the first one</a>.</div>'
    else:
        cards_html = "".join(cards)

    mine_link = f' | <a href="/web/collections?type={ctype}&mine=my">My Collections</a>' if not mine else f' | <a href="/web/collections?type={ctype}&sort={sort_by}">All Collections</a>'

    content = f"""
    <div class="quick-links" style="margin-bottom:12px;">
        {method_tab}{problem_tab}
        <span class="sep">|</span>
        <a href="/web/collections/new">+ New Collection</a>
        {mine_link}
    </div>
    <p style="color:#777;font-size:13px;margin-bottom:8px;">Sort: {sort_links}</p>
    <div class="quick-links" style="margin-bottom:16px;">{cat_links}</div>
    {cards_html}
    """
    return _base_page("Collections", content, "collections")


def render_collection_new(form: dict | None = None, errors: list[str] | None = None, success: str = "") -> str:
    """Render the collection creation form."""
    f = form or {}
    err_html = "".join(f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>' for e in (errors or []))
    ok_html = f'<p style="color:#22c55e;margin:8px 0;">{_esc(success)}</p>' if success else ""

    sel_method = 'selected' if f.get("ctype", "method") == "method" else ""
    sel_problem = 'selected' if f.get("ctype") == "problem" else ""

    method_cats = "".join(
        f'<option value="{c}" {"selected" if f.get("category") == c else ""}>{c.replace("_", " ").title()}</option>'
        for c in _COLLECTION_CATEGORIES_METHOD
    )
    problem_cats = "".join(
        f'<option value="{c}" {"selected" if f.get("category") == c else ""}>{c.title()}</option>'
        for c in _COLLECTION_CATEGORIES_PROBLEM
    )

    items_json = _esc(f.get("items_json", "[{\n  \n}]"))

    content = f"""
    {err_html}{ok_html}
    <form method="post" action="/web/collections/new">
        <table style="max-width:750px;">
            <tr><td style="color:#777;width:140px;padding:8px;">Type *</td>
                <td><select name="ctype" id="ctype-select" onchange="document.getElementById('cat-method').style.display=this.value==='problem'?'none':'block';document.getElementById('cat-problem').style.display=this.value==='method'?'none':'block';">
                    <option value="method" {sel_method}>Method Collection</option>
                    <option value="problem" {sel_problem}>Problem Collection</option>
                </select></td></tr>
            <tr><td style="color:#777;padding:8px;">Name *</td>
                <td><input type="text" name="name" value="{_esc(f.get('name', ''))}" required style="width:100%;" placeholder="e.g. Quantum Methods Pack"></td></tr>
            <tr><td style="color:#777;padding:8px;">Category *</td>
                <td>
                    <select name="category" id="cat-method" style="display:{'block' if f.get('ctype', 'method') == 'method' else 'none'};">{method_cats}</select>
                    <select name="category" id="cat-problem" style="display:{'block' if f.get('ctype') == 'problem' else 'none'};">{problem_cats}</select>
                </td></tr>
            <tr><td style="color:#777;padding:8px;">Description</td>
                <td><textarea name="description" rows="3" style="width:100%;" placeholder="Describe what this collection is about...">{_esc(f.get('description', ''))}</textarea></td></tr>
            <tr><td style="color:#777;padding:8px;">Items (JSON) *</td>
                <td><textarea name="items_json" rows="12" required style="width:100%;font-family:monospace;font-size:12px;" placeholder='[&#10;  {{"name": "...", "domain": "...", "level": 2, "description": "..."}}&#10;]'>{items_json}</textarea>
                <p style="font-size:11px;color:#999;margin-top:4px;">Paste a JSON array of method or problem objects.</p></td></tr>
            <tr><td style="color:#777;padding:8px;">Creator</td>
                <td><input type="text" name="creator" value="{_esc(f.get('creator', 'anonymous'))}" style="width:100%;"></td></tr>
        </table>
        <button type="submit" style="margin-top:12px;padding:10px 28px;">Create Collection</button>
    </form>
    """
    return _base_page("New Collection", content, "collections")


def render_collection_detail(db: LeaderboardDB, ctype: str, cid: int,
                             starrer: str = "", starred: bool = False) -> str:
    """Render a single collection's detail page with items and star button."""
    c = db.get_collection(ctype, cid)
    if not c:
        content = '<div class="empty">Collection not found.</div>'
        return _base_page("Not Found", content)

    items = json.loads(c.get("methods_json") or c.get("problems_json") or "[]")
    stars = c.get("stars", 0)
    imports = c.get("import_count", 0)
    name = _esc(c.get("name", "Unknown"))
    desc = _esc(c.get("description") or "")
    creator = _esc(c.get("creator", "unknown"))
    cat = (c.get("category") or "other").replace("_", " ").title()
    created = c.get("created_at", 0)

    star_verb = "Unstar" if starred else "Star"
    star_link = f"/web/collections/{ctype}/{cid}/star?starrer={_esc(starrer)}" if starrer else "#"
    star_disabled = "" if starrer else "disabled"

    item_rows = []
    for i, item in enumerate(items):
        if ctype == "method":
            label = f"{_esc(item.get('name', '?'))}"
            sub = f"Domain: {_esc(item.get('domain', '?'))} | Level: {item.get('level', '?')}"
        else:
            label = f"{_esc(item.get('title', '?'))}"
            sub = f"Domain: {_esc(item.get('domain', '?'))} | Maturity: {item.get('maturity', '?')}"
        desc_item = _esc((item.get("description") or "")[:150])
        item_rows.append(f"""
        <tr>
            <td>{i + 1}</td>
            <td><b>{label}</b><br><span style="font-size:11px;color:#999;">{sub}</span></td>
            <td style="font-size:12px;">{desc_item}</td>
        </tr>""")

    import_label = "import" if imports == 1 else "imports"

    content = f"""
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;">
            <div>
                <h3 style="margin-bottom:4px;">{name}</h3>
                <p style="color:#777;font-size:13px;">
                    <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
                    &nbsp; {len(items)} items &nbsp; &#x2605; {stars} &nbsp; {imports} {import_label} &nbsp; by {creator}
                </p>
            </div>
            <div style="text-align:center;">
                <a href="{star_link}" style="display:inline-block;padding:8px 16px;background:#2563eb;color:#fff;border-radius:6px;font-size:14px;text-decoration:none;{star_disabled}">{star_verb} &#x2605;</a>
                <p style="font-size:11px;color:#999;margin-top:4px;">{stars} stars</p>
            </div>
        </div>
        <p style="margin-top:12px;font-size:14px;color:#555;">{desc}</p>
    </div>

    <h2>Items ({len(items)})</h2>
    <table>
    <thead><tr><th>#</th><th>{"Method" if ctype == "method" else "Problem"}</th><th>Description</th></tr></thead>
    <tbody>{"".join(item_rows) if item_rows else '<tr><td colspan="3" class="empty">No items in this collection.</td></tr>'}</tbody>
    </table>

    <h2>Import</h2>
    <div class="card">
        <p style="font-size:13px;color:#555;">Use this command to mine with this collection:</p>
        <pre style="background:#f0f3f7;padding:12px;border-radius:6px;font-size:13px;overflow-x:auto;">python3 -m src.cli.main mine --{"methods" if ctype == "method" else "problems"}-collection "{name}" --batch 5</pre>
    </div>

    <p style="margin-top:16px;"><a href="/web/collections?type={ctype}">&larr; Back to Collections</a></p>
    """
    return _base_page(name, content, "collections")


def render_collections_mine(db: LeaderboardDB, creator: str) -> str:
    """Redirect to collections filtered by creator."""
    params = f"type=method&mine={_esc(creator)}"
    return f'<html><head><meta http-equiv="refresh" content="0;url=/web/collections?{params}"></head><body>Redirecting...</body></html>'


# ------------------------------------------------------------------
# Math Research Zone pages
# ------------------------------------------------------------------

_MATH_CATEGORIES = [
    "number_theory", "analysis", "algebra", "geometry",
    "topology", "combinatorics", "logic", "other",
]


def render_math_home(db: LeaderboardDB) -> str:
    """Math Zone home page — list all math problems."""
    problems = db.get_math_problems()
    cards = []
    for p in problems:
        pid = p["id"]
        title = _esc(p["title"])
        desc = _esc((p.get("description") or "")[:180])
        cat = (p.get("category") or "other").replace("_", " ").title()
        creator = _esc((p.get("creator") or "unknown")[:16])
        # Count solutions
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
    <div class="quick-links" style="margin-bottom:16px;">
        <a href="/web/math/new">+ New Problem</a>
    </div>
    {"".join(cards) if cards else '<div class="empty">No math problem zones yet. <a href="/web/math/new">Apply to create the first one</a>.</div>'}
    """
    return _base_page("Math Research Zone", content, "math")


def render_math_new(form: dict | None = None, errors: list[str] | None = None,
                    success: str = "") -> str:
    """Form to create a new math problem zone."""
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
    return _base_page("New Math Problem", content, "math")


def render_math_problem(db: LeaderboardDB, pid: int, path: str) -> str:
    """Problem area page — sub-divisions by method collection."""
    problem = db.get_math_problem(pid)
    if not problem:
        return _base_page("Not Found", '<div class="empty">Math problem not found.</div>')

    title = _esc(problem["title"])
    desc = _esc(problem.get("description") or "")
    cat = (problem.get("category") or "other").replace("_", " ").title()
    creator = _esc((problem.get("creator") or "unknown")[:16])

    params = _parse_query(path)
    user_addr = params.get("user_address", "")

    # Get math method collections (category=mathematics)
    method_colls = db.get_collections("method", sort_by="stars", category="mathematics")

    rows = []
    for c in method_colls:
        mid = c["id"]
        mname = _esc(c["name"])
        mitems = len(json.loads(c.get("methods_json") or "[]"))
        accessed = db.check_math_access(pid, mid, user_addr) if user_addr else False

        # Count solutions
        with db._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*), MAX(max_correct_step) FROM math_solutions "
                "WHERE problem_id = ? AND method_collection_id = ?",
                (pid, mid),
            ).fetchone()
        sol_count = row[0] if row else 0
        top_step = row[1] or 0

        access_label = '<span style="color:#22c55e;">&#x2713; Unlocked</span>' if accessed else '<a href="/web/math/{pid}/{mid}/unlock" style="color:#ef4444;">Locked — Unlock</a>'
        zone_link = f'/web/math/{pid}/{mid}' if accessed else f'/web/math/{pid}/{mid}/unlock'

        rows.append(f"""
        <tr>
            <td><a href="{zone_link}"><b>{mname}</b></a><br><span style="font-size:11px;color:#999;">{mitems} tools</span></td>
            <td>{access_label}</td>
            <td><b>{top_step}</b> steps</td>
            <td>{sol_count} solution(s)</td>
        </tr>""")

    content = f"""
    <div class="card">
        <h3>{title}</h3>
        <p style="color:#777;font-size:13px;margin-bottom:4px;">
            <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
            &nbsp; by {creator}
        </p>
        <p style="font-size:14px;color:#555;margin-top:8px;">{desc}</p>
    </div>

    <form method="get" action="/web/math/{pid}" style="margin-bottom:12px;">
        <input type="text" name="user_address" value="{_esc(user_addr)}" placeholder="Your address (e.g. 0xALICE)" style="flex:1;min-width:260px;">
        <button type="submit">Check Access</button>
    </form>

    <h2>Method Zones</h2>
    <table>
    <thead><tr><th>Method Collection</th><th>Access</th><th>Top Step</th><th>Solutions</th></tr></thead>
    <tbody>{"".join(rows) if rows else '<tr><td colspan="4" class="empty">No math method collections yet. <a href="/web/collections/new">Create one</a> with category "mathematics".</td></tr>'}</tbody>
    </table>

    <p style="margin-top:16px;"><a href="/web/math">&larr; Back to Math Zone</a></p>
    """
    return _base_page(title, content, "math")


def render_math_method_zone(db: LeaderboardDB, pid: int, mid: int, path: str) -> str:
    """All solutions for a (problem, method), ranked by max_correct_step."""
    problem = db.get_math_problem(pid)
    coll = db.get_collection("method", mid)
    if not problem or not coll:
        return _base_page("Not Found", '<div class="empty">Problem or method collection not found.</div>')

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
            <p style="margin-top:16px;"><a href="/web/math/{pid}">&larr; Back to Problem</a></p>
        </div>
        """, "math")

    solutions = db.get_math_solutions(pid, mid)

    sol_rows = []
    for i, s in enumerate(solutions):
        sid = s["id"]
        try:
            steps = json.loads(s["steps_json"])
        except Exception:
            steps = []
        step_count = len(steps)
        max_step = s["max_correct_step"]
        user = _esc((s.get("user_address") or "unknown")[:16])
        parent = s.get("parent_solution_id")
        fork_info = f' <span style="font-size:11px;color:#999;">(forked from #{parent})</span>' if parent else ""
        sol_rows.append(f"""
        <tr>
            <td>{i + 1}</td>
            <td><a href="/web/math/{pid}/{mid}/{sid}">{user}</a>{fork_info}</td>
            <td>{_score_bar(max_step, max(10, max_step + 5))}</td>
            <td>{step_count} steps</td>
            <td><a href="/web/math/{pid}/{mid}/{sid}?fork=1&user_address={_esc(user_addr)}" style="color:#2563eb;">Fork</a></td>
        </tr>""")

    content = f"""
    <div class="card">
        <h3>{_esc(problem['title'])} &mdash; {_esc(coll['name'])}</h3>
        <p style="color:#777;font-size:13px;">
            {json.loads(coll.get("methods_json") or "[]") if False else ''}
            Access: <span style="color:#22c55e;">&#x2713; Unlocked</span>
        </p>
    </div>

    <h2>Solutions ({len(solutions)})</h2>
    <table>
    <thead><tr><th>#</th><th>User</th><th>Max Correct Step</th><th>Steps</th><th>Action</th></tr></thead>
    <tbody>{"".join(sol_rows) if sol_rows else '<tr><td colspan="5" class="empty">No solutions yet. <a href="/web/math/{pid}/{mid}/unlock">Submit the first one</a>.</td></tr>'}</tbody>
    </table>

    <p style="margin-top:16px;"><a href="/web/math/{pid}">&larr; Back to Problem</a></p>
    """
    return _base_page(f"{problem['title']} — {coll['name']}", content, "math")


def render_math_solution(db: LeaderboardDB, pid: int, mid: int, sid: int, path: str) -> str:
    """Single solution detail — full steps, fork button, submit improvement."""
    solution = db.get_math_solution(sid)
    if not solution:
        return _base_page("Not Found", '<div class="empty">Solution not found.</div>')

    problem = db.get_math_problem(pid)
    coll = db.get_collection("method", mid)

    try:
        steps = json.loads(solution["steps_json"])
    except Exception:
        steps = []

    max_step = solution["max_correct_step"]
    user = _esc((solution.get("user_address") or "unknown")[:16])
    parent = solution.get("parent_solution_id")
    created = solution.get("created_at", 0)
    updated = solution.get("updated_at", 0)

    step_rows = []
    for s in sorted(steps, key=lambda x: x.get("step_num", 0)):
        sn = s.get("step_num", "?")
        verified = s.get("verified", False)
        content_text = _esc(s.get("content", ""))
        v_badge = '<span style="color:#22c55e;">&#x2713;</span>' if verified else '<span style="color:#ef4444;">&#x2717;</span>'
        step_rows.append(f"""
        <tr>
            <td>{sn}</td>
            <td style="max-width:600px;">{content_text}</td>
            <td>{v_badge}</td>
        </tr>""")

    params = _parse_query(path)
    fork = params.get("fork")

    fork_form = ""
    if fork:
        fork_form = f"""
        <div class="card" style="margin-top:16px;">
            <h3>Fork Solution #{sid}</h3>
            <form method="post" action="/web/math/{pid}/{mid}/{sid}/fork">
                <input type="hidden" name="user_address" value="{_esc(params.get('user_address', 'anonymous'))}">
                <p style="color:#777;font-size:13px;">This will create a copy of all {len(steps)} steps as your own solution.</p>
                <button type="submit" style="margin-top:8px;">Confirm Fork</button>
            </form>
        </div>"""

    submit_form = f"""
    <div class="card" style="margin-top:16px;">
        <h3>Submit Improvement</h3>
        <form method="post" action="/web/math/{pid}/{mid}/{sid}/submit">
            <input type="hidden" name="user_address" value="{_esc(params.get('user_address', 'anonymous'))}">
            <textarea name="steps_json" rows="8" style="width:100%;font-family:monospace;font-size:12px;">{_esc(json.dumps(steps, indent=2, ensure_ascii=False))}</textarea>
            <p style="font-size:11px;color:#999;margin-top:4px;">Edit the JSON above and submit. max_correct_step will be recalculated.</p>
            <button type="submit" style="margin-top:8px;">Submit Update</button>
        </form>
    </div>"""

    parent_info = f'<p style="color:#777;font-size:13px;">Forked from <a href="/web/math/{pid}/{mid}/{parent}">Solution #{parent}</a></p>' if parent else ""

    content = f"""
    <div class="card">
        <h3>Solution #{sid}</h3>
        <p style="color:#777;font-size:13px;">
            Problem: <b>{_esc(problem['title']) if problem else '?'}</b> &nbsp;
            Method: <b>{_esc(coll['name']) if coll else '?'}</b>
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
    <thead><tr><th>#</th><th>Content</th><th>Verified</th></tr></thead>
    <tbody>{"".join(step_rows) if step_rows else '<tr><td colspan="3" class="empty">No steps.</td></tr>'}</tbody>
    </table>

    <div class="quick-links" style="margin-top:16px;">
        <a href="/web/math/{pid}/{mid}/{sid}?fork=1&user_address={_esc(params.get('user_address', ''))}">Fork Solution</a>
    </div>
    {fork_form}
    {submit_form}

    <p style="margin-top:16px;"><a href="/web/math/{pid}/{mid}">&larr; Back to Method Zone</a></p>
    """
    return _base_page(f"Solution #{sid}", content, "math")


def render_math_unlock(db: LeaderboardDB, pid: int, mid: int, path: str) -> str:
    """Gate unlock page — shows CLI command or manual unlock."""
    problem = db.get_math_problem(pid)
    coll = db.get_collection("method", mid)
    if not problem or not coll:
        return _base_page("Not Found", '<div class="empty">Problem or method collection not found.</div>')

    params = _parse_query(path)
    user_addr = params.get("user_address", "")

    accessed = db.check_math_access(pid, mid, user_addr) if user_addr else False

    if accessed:
        return _base_page("Zone Unlocked", f"""
        <div class="card">
            <h3 style="color:#22c55e;">&#x2713; Zone Already Unlocked</h3>
            <p style="color:#777;margin:12px 0;">You have access to this zone.</p>
            <a href="/web/math/{pid}/{mid}?user_address={_esc(user_addr)}">Go to Method Zone</a>
        </div>
        """, "math")

    pname = _esc(problem["title"])
    cname = _esc(coll["name"])

    content = f"""
    <div class="card">
        <h3>Unlock: {cname} &rarr; {pname}</h3>
        <p style="color:#777;margin:12px 0;">
            To view solutions in this zone, you must first run a <b>math-mine</b> operation.
            This combines methods from the collection with the problem and generates an AI seed analysis.
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

    <p style="margin-top:16px;"><a href="/web/math/{pid}">&larr; Back to Problem</a></p>
    """
    return _base_page(f"Unlock: {cname}", content, "math")


# ------------------------------------------------------------------
# Community Submission pages
# ------------------------------------------------------------------

def render_submit_home() -> str:
    """Landing page for community submissions."""
    content = """
    <div class="stats">
        <div class="stat-card" style="flex:1;min-width:200px;">
            <div style="font-size:40px;margin-bottom:8px;">&#x1F9E0;</div>
            <div class="label">Submit a new thinking method to the matrix</div>
            <a href="/web/submit/method" style="display:inline-block;margin-top:12px;padding:8px 20px;background:#2563eb;color:#fff;border-radius:6px;">Submit Method</a>
        </div>
        <div class="stat-card" style="flex:1;min-width:200px;">
            <div style="font-size:40px;margin-bottom:8px;">&#x1F50D;</div>
            <div class="label">Submit an unsolved problem for the matrix</div>
            <a href="/web/submit/problem" style="display:inline-block;margin-top:12px;padding:8px 20px;background:#2563eb;color:#fff;border-radius:6px;">Submit Problem</a>
        </div>
    </div>
    <p style="color:#777;margin-top:16px;">All submissions are reviewed before joining the active matrix.</p>
    """
    return _base_page("Community Submit", content, "submit")


def render_submit_method(form: dict | None = None, errors: list[str] | None = None, success: str = "") -> str:
    """Render the method submission form."""
    f = form or {}
    err_html = "".join(f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>' for e in (errors or []))
    ok_html = f'<p style="color:#22c55e;margin:8px 0;">{_esc(success)}</p>' if success else ""

    domains = ["triz", "biology", "physics", "chemistry", "mathematics", "economics",
               "machine_learning", "heuristic", "engineering", "design", "systems", "other"]
    domain_opts = "".join(
        f'<option value="{d}" {"selected" if f.get("domain") == d else ""}>{d.replace("_", " ").title()}</option>'
        for d in domains
    )
    level_opts = "".join(
        f'<option value="{l}" {"selected" if str(f.get("level", "")) == str(l) else ""}>Level {l}</option>'
        for l in range(1, 5)
    )

    content = f"""
    {err_html}{ok_html}
    <form method="post" action="/submit/method">
        <table style="max-width:700px;">
            <tr><td style="color:#777;width:140px;padding:8px;">Name *</td>
                <td><input type="text" name="name" value="{_esc(f.get('name', ''))}" required style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Domain *</td>
                <td><select name="domain" required>{domain_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Level *</td>
                <td><select name="level" required>{level_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Description *</td>
                <td><textarea name="description" rows="4" required style="width:100%;">{_esc(f.get('description', ''))}</textarea></td></tr>
            <tr><td style="color:#777;padding:8px;">Examples</td>
                <td><input type="text" name="examples" value="{_esc(f.get('examples', ''))}" placeholder="comma-separated" style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Prerequisites</td>
                <td><input type="text" name="prerequisites" value="{_esc(f.get('prerequisites', ''))}" placeholder="comma-separated method IDs" style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Compatible With</td>
                <td><input type="text" name="compatible_with" value="{_esc(f.get('compatible_with', ''))}" placeholder="comma-separated method IDs" style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Submitter</td>
                <td><input type="text" name="submitter" value="{_esc(f.get('submitter', 'anonymous'))}" style="width:100%;"></td></tr>
        </table>
        <button type="submit" style="margin-top:12px;padding:10px 28px;">Submit Method</button>
    </form>
    """
    return _base_page("Submit Method", content, "submit")


def render_submit_problem(form: dict | None = None, errors: list[str] | None = None, success: str = "") -> str:
    """Render the problem submission form."""
    f = form or {}
    err_html = "".join(f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>' for e in (errors or []))
    ok_html = f'<p style="color:#22c55e;margin:8px 0;">{_esc(success)}</p>' if success else ""

    domains = ["medicine", "energy", "environment", "information", "materials", "society",
               "transportation", "agriculture", "space", "other"]
    domain_opts = "".join(
        f'<option value="{d}" {"selected" if f.get("domain") == d else ""}>{d.title()}</option>'
        for d in domains
    )
    mat_opts = "".join(
        f'<option value="{l}" {"selected" if str(f.get("maturity", "")) == str(l) else ""}>Level {l} — {["","Only problem description","Partial solutions, poor results","Solutions exist but too costly","Bottleneck clear, path unknown"][l]}</option>'
        for l in range(1, 5)
    )
    constraint_opts = ["physical_limit", "resource", "time", "complexity", "ethical"]
    constraint_html = "".join(
        f'<label style="margin-right:12px;"><input type="checkbox" name="constraints" value="{c}" {"checked" if c in f.get("constraints", []) else ""}> {c.replace("_", " ").title()}</label>'
        for c in constraint_opts
    )

    content = f"""
    {err_html}{ok_html}
    <form method="post" action="/submit/problem">
        <table style="max-width:700px;">
            <tr><td style="color:#777;width:140px;padding:8px;">Title *</td>
                <td><input type="text" name="title" value="{_esc(f.get('title', ''))}" required style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Domain *</td>
                <td><select name="domain" required>{domain_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Description *</td>
                <td><textarea name="description" rows="4" required style="width:100%;">{_esc(f.get('description', ''))}</textarea></td></tr>
            <tr><td style="color:#777;padding:8px;">Maturity</td>
                <td><select name="maturity">{mat_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Constraint Types</td>
                <td>{constraint_html}</td></tr>
            <tr><td style="color:#777;padding:8px;">Submitter</td>
                <td><input type="text" name="submitter" value="{_esc(f.get('submitter', 'anonymous'))}" style="width:100%;"></td></tr>
        </table>
        <button type="submit" style="margin-top:12px;padding:10px 28px;">Submit Problem</button>
    </form>
    """
    return _base_page("Submit Problem", content, "submit")


def render_submissions(db: LeaderboardDB) -> str:
    """Render the pending submissions list (operator review page)."""
    pending = db.get_pending_submissions()
    total = db.total_pending()

    if not pending:
        content = '<div class="empty">No pending submissions.</div>'
        return _base_page("Submissions", content, "submit")

    rows = []
    for sub in pending:
        data = json.loads(sub["data"])
        preview = _esc(str(data)[:120])
        sub_id = sub["id"]
        stype = sub["type"]
        submitter = _esc(sub.get("submitter", "")[:16])
        rows.append(f"""
        <tr>
            <td>{sub_id}</td>
            <td><span style="background:#e8f0fe;color:#2563eb;padding:2px 8px;border-radius:3px;font-size:12px;">{stype}</span></td>
            <td style="font-size:12px;max-width:300px;overflow:hidden;">{preview}</td>
            <td>{submitter}</td>
            <td>
                <a href="/web/submissions?approve={sub_id}" style="color:#22c55e;margin-right:8px;">Approve</a>
                <a href="/web/submissions?reject={sub_id}" style="color:#ef4444;">Reject</a>
            </td>
        </tr>""")

    content = f"""
    <p style="color:#777;margin-bottom:12px;">{total} pending submission(s)</p>
    <table>
    <thead><tr><th>ID</th><th>Type</th><th>Preview</th><th>Submitter</th><th>Action</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page("Submissions", content, "submit")


# ------------------------------------------------------------------
# Blockchain Buffer Zone Pages
# ------------------------------------------------------------------

def render_buffer_dashboard(db: LeaderboardDB) -> str:
    pending = db.count_buffer_by_status("pending")
    classified = db.count_buffer_by_status("classified")
    disputed = db.count_buffer_by_status("disputed")
    published = db.count_buffer_by_status("published")
    leaderboard = db.get_token_leaderboard(limit=5)

    content = f"""
    <h1>Blockchain Buffer Zone</h1>
    <p style="color:#777;margin-bottom:20px;">
        Submit AI analysis → Community classification → Consensus → Publish to leaderboard
    </p>
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#f59e0b;">{pending}</div>
            <div style="color:#777;">Pending</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#22c55e;">{classified}</div>
            <div style="color:#777;">Classified</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#ef4444;">{disputed}</div>
            <div style="color:#777;">Disputed</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#6366f1;">{published}</div>
            <div style="color:#777;">Published</div>
        </div>
    </div>
    <div style="display:flex;gap:16px;flex-wrap:wrap;">
        <a href="/web/buffer/pending" class="btn" style="padding:10px 20px;background:#2563eb;color:#fff;border-radius:6px;">Classify Pending</a>
        <a href="/web/buffer/tokens" class="btn" style="padding:10px 20px;background:#22c55e;color:#fff;border-radius:6px;">Token Dashboard</a>
        <a href="/web/buffer/leaderboard" class="btn" style="padding:10px 20px;background:#6366f1;color:#fff;border-radius:6px;">Classifier Leaderboard</a>
    </div>
    """
    if leaderboard:
        top_rows = []
        for i, r in enumerate(leaderboard, 1):
            top_rows.append(f"""<tr>
                <td>{i}</td>
                <td>{_esc(r['address'])[:14]}</td>
                <td>{r['balance']}</td>
                <td>{r['correct_classifications']}/{r['total_classifications']}</td>
                <td>{r['consecutive_correct']}</td>
            </tr>""")
        content += f"""
        <h2 style="margin-top:24px;">Top Classifiers</h2>
        <table>
        <thead><tr><th>#</th><th>Address</th><th>Balance</th><th>Accuracy</th><th>Streak</th></tr></thead>
        <tbody>{"".join(top_rows)}</tbody>
        </table>
        """
    return _base_page("Buffer Zone", content, "buffer")


def render_buffer_pending(db: LeaderboardDB, path: str) -> str:
    entries = db.get_pending_buffer_entries()
    if not entries:
        content = '<div class="empty">No pending submissions to classify.</div>'
        return _base_page("Pending Classifications", content, "buffer")

    rows = []
    for e in entries:
        analysis_preview = e.get("analysis_text", "")[:100]
        if not analysis_preview:
            try:
                data = json.loads(e["analysis_json"])
                scores = data.get("scores", [])
                if scores:
                    analysis_preview = f"{len(scores)} dimension(s) evaluated"
                else:
                    analysis_preview = "(no analysis text)"
            except (json.JSONDecodeError, KeyError):
                analysis_preview = "(parse error)"
        rows.append(f"""<tr>
            <td>{_esc(e['id'])}</td>
            <td>{_esc(e['method_name'])} × {_esc(e['problem_title'])}</td>
            <td>{_esc(analysis_preview)}</td>
            <td>{_esc(e['submitter'])[:12]}</td>
            <td>{e['classifier_count']}</td>
            <td><a href="/web/buffer/classify/{_esc(e['id'])}">Classify</a></td>
        </tr>""")

    content = f"""
    <h1>Pending Classifications</h1>
    <p style="color:#777;margin-bottom:12px;">{len(entries)} submission(s) awaiting classification</p>
    <table>
    <thead><tr><th>ID</th><th>Combo</th><th>Preview</th><th>Submitter</th><th>Votes</th><th>Action</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page("Pending Classifications", content, "buffer")


def render_buffer_classify(db: LeaderboardDB, sub_id: str, path: str) -> str:
    entry = db.get_buffer_entry(sub_id)
    if entry is None:
        return _base_page("Not Found", '<div class="empty">Submission not found.</div>', "buffer")

    classifications = db.get_classifications(sub_id)
    already = [c["classifier_addr"] for c in classifications]

    analysis_text = entry.get("analysis_text", "")
    if not analysis_text:
        try:
            data = json.loads(entry["analysis_json"])
            analysis_text = json.dumps(data, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, KeyError):
            analysis_text = entry["analysis_json"]

    existing_html = ""
    if classifications:
        cls_rows = []
        for c in classifications:
            cls_rows.append(f"""<tr>
                <td>{_esc(c['classifier_addr'])[:14]}</td>
                <td>{_esc(c['domain_label'])}</td>
                <td>{'Yes' if c['is_nsfw'] else 'No'}</td>
                <td>{'Yes' if c['is_spam'] else 'No'}</td>
                <td>{_esc(c.get('notes', ''))[:40]}</td>
            </tr>""")
        existing_html = f"""
        <h2>Existing Classifications ({len(classifications)})</h2>
        <table>
        <thead><tr><th>Classifier</th><th>Domain</th><th>NSFW</th><th>Spam</th><th>Notes</th></tr></thead>
        <tbody>{"".join(cls_rows)}</tbody>
        </table>
        """

    domains = ["medicine", "energy", "physics", "chemistry", "biology", "mathematics",
               "engineering", "computer_science", "agriculture", "environmental",
               "social_science", "business", "education", "art", "philosophy", "other"]
    domain_opts = "\n".join(f'<option value="{d}">{d}</option>' for d in domains)

    content = f"""
    <h1>Classify Submission</h1>
    <div style="background:#fff;padding:16px;border-radius:8px;margin-bottom:16px;">
        <h2>{_esc(entry['method_name'])} × {_esc(entry['problem_title'])}</h2>
        <p><strong>Submitter:</strong> {_esc(entry['submitter'])}</p>
        <p><strong>Status:</strong> {_esc(entry['status'])}</p>
        <p><strong>Votes:</strong> {entry['classifier_count']}</p>
        <details style="margin-top:8px;">
            <summary>Analysis Data</summary>
            <pre style="max-height:400px;overflow-y:auto;background:#f8f9fa;padding:12px;border-radius:4px;font-size:12px;">{_esc(analysis_text)}</pre>
        </details>
    </div>
    {existing_html}
    <form method="POST" action="/web/buffer/classify/{_esc(sub_id)}" style="background:#fff;padding:16px;border-radius:8px;">
        <h2>Submit Classification</h2>
        <p style="color:#777;margin-bottom:12px;">
            Classification requires a stake of 10 IDEA tokens (auto-faucet for new users).
        </p>
        <div style="margin-bottom:12px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">Domain Label:</label>
            <select name="domain" style="width:100%;padding:8px;border:1px solid #dde1e6;border-radius:4px;">
                {domain_opts}
            </select>
        </div>
        <div style="margin-bottom:8px;">
            <label><input type="checkbox" name="nsfw" value="1"> Mark as NSFW</label>
        </div>
        <div style="margin-bottom:8px;">
            <label><input type="checkbox" name="spam" value="1"> Mark as Spam / AI Hallucination</label>
        </div>
        <div style="margin-bottom:12px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">Notes:</label>
            <textarea name="notes" rows="3" style="width:100%;padding:8px;border:1px solid #dde1e6;border-radius:4px;" placeholder="Optional notes..."></textarea>
        </div>
        <div style="margin-bottom:12px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">Your Address:</label>
            <input type="text" name="address" value="0xCLASSIFIER" style="width:100%;padding:8px;border:1px solid #dde1e6;border-radius:4px;">
        </div>
        <input type="submit" value="Submit Classification" style="padding:10px 24px;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;">
    </form>
    """
    return _base_page(f"Classify {sub_id}", content, "buffer")


def render_buffer_submissions(db: LeaderboardDB, address: str) -> str:
    entries = db.get_buffer_entries_by_submitter(address)
    if not entries:
        content = f'<div class="empty">No submissions from {_esc(address)}.</div>'
        return _base_page("My Submissions", content, "buffer")

    rows = []
    status_colors = {"pending": "#f59e0b", "classified": "#22c55e",
                     "published": "#6366f1", "disputed": "#ef4444"}
    for e in entries:
        color = status_colors.get(e["status"], "#777")
        rows.append(f"""<tr>
            <td><a href="/web/buffer/detail/{_esc(e['id'])}">{_esc(e['id'])}</a></td>
            <td>{_esc(e['method_name'])} × {_esc(e['problem_title'])}</td>
            <td style="color:{color};font-weight:600;">{_esc(e['status'])}</td>
            <td>{e['classifier_count']}</td>
        </tr>""")

    content = f"""
    <h1>My Submissions</h1>
    <p style="color:#777;margin-bottom:12px;">Submitter: {_esc(address)}</p>
    <table>
    <thead><tr><th>ID</th><th>Combo</th><th>Status</th><th>Votes</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page("My Submissions", content, "buffer")


def render_buffer_submission_detail(db: LeaderboardDB, sub_id: str) -> str:
    entry = db.get_buffer_entry(sub_id)
    if entry is None:
        return _base_page("Not Found", '<div class="empty">Submission not found.</div>', "buffer")

    classifications = db.get_classifications(sub_id)
    cls_rows = []
    for c in classifications:
        match_icon = "✓" if c.get("matched_consensus") else "✗"
        reward = c.get("reward_earned", 0)
        cls_rows.append(f"""<tr>
            <td>{_esc(c['classifier_addr'])[:14]}</td>
            <td>{_esc(c['domain_label'])}</td>
            <td>{'Yes' if c['is_nsfw'] else 'No'}</td>
            <td>{'Yes' if c['is_spam'] else 'No'}</td>
            <td>{match_icon}</td>
            <td>{'+'+str(reward) if reward > 0 else str(reward)}</td>
        </tr>""")

    status_colors = {"pending": "#f59e0b", "classified": "#22c55e",
                     "published": "#6366f1", "disputed": "#ef4444"}
    color = status_colors.get(entry["status"], "#777")

    content = f"""
    <h1>Submission Detail</h1>
    <div style="background:#fff;padding:16px;border-radius:8px;margin-bottom:16px;">
        <table style="width:100%;border:none;">
            <tr><td style="width:150px;font-weight:600;">Submission ID</td><td>{_esc(entry['id'])}</td></tr>
            <tr><td style="font-weight:600;">Method</td><td>{_esc(entry['method_name'])} ({_esc(entry['method_id'])})</td></tr>
            <tr><td style="font-weight:600;">Problem</td><td>{_esc(entry['problem_title'])} ({_esc(entry['problem_id'])})</td></tr>
            <tr><td style="font-weight:600;">Submitter</td><td>{_esc(entry['submitter'])}</td></tr>
            <tr><td style="font-weight:600;">Status</td><td style="color:{color};font-weight:600;">{_esc(entry['status'])}</td></tr>
            <tr><td style="font-weight:600;">Staked</td><td>{entry['staked_amount']} IDEA</td></tr>
            <tr><td style="font-weight:600;">Classifiers</td><td>{entry['classifier_count']}</td></tr>
        </table>
        {f'<p style="margin-top:8px;"><strong>Consensus Domain:</strong> {_esc(entry["consensus_domain"])}</p>' if entry.get("consensus_domain") else ''}
    </div>
    """
    if cls_rows:
        content += f"""
        <h2>Classifications</h2>
        <table>
        <thead><tr><th>Classifier</th><th>Domain</th><th>NSFW</th><th>Spam</th><th>Match</th><th>Reward</th></tr></thead>
        <tbody>{"".join(cls_rows)}</tbody>
        </table>
        """
    return _base_page(f"Submission {sub_id}", content, "buffer")


def render_buffer_tokens(db: LeaderboardDB, address: str) -> str:
    acct = db.get_or_create_account(address)
    stakes = db.get_active_stakes(address)

    stake_rows = []
    for s in stakes:
        stake_rows.append(f"""<tr>
            <td>{s['id']}</td>
            <td>{s['amount']}</td>
            <td>{_esc(s['status'])}</td>
            <td>{_esc(s['submission_id'])[:16] if s.get('submission_id') else ''}</td>
        </tr>""")

    accuracy = 0
    if acct.get("total_classifications", 0) > 0:
        accuracy = acct["correct_classifications"] / acct["total_classifications"] * 100

    content = f"""
    <h1>Token Dashboard</h1>
    <p style="color:#777;margin-bottom:16px;">Address: {_esc(address)}</p>
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#2563eb;">{acct.get('balance', 0)}</div>
            <div style="color:#777;">Balance (IDEA)</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#f59e0b;">{acct.get('staked', 0)}</div>
            <div style="color:#777;">Staked</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#22c55e;">{acct.get('total_earned', 0)}</div>
            <div style="color:#777;">Total Earned</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#ef4444;">{acct.get('total_slashed', 0)}</div>
            <div style="color:#777;">Slashed</div>
        </div>
    </div>
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:24px;font-weight:bold;">{acct.get('correct_classifications', 0)}/{acct.get('total_classifications', 0)}</div>
            <div style="color:#777;">Accuracy ({accuracy:.1f}%)</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:24px;font-weight:bold;">{acct.get('consecutive_correct', 0)}</div>
            <div style="color:#777;">Consecutive Streak</div>
        </div>
    </div>
    """
    if stake_rows:
        content += f"""
        <h2>Active Stakes</h2>
        <table>
        <thead><tr><th>Stake ID</th><th>Amount</th><th>Status</th><th>Submission</th></tr></thead>
        <tbody>{"".join(stake_rows)}</tbody>
        </table>
        """
    return _base_page("Token Dashboard", content, "buffer")


def render_buffer_leaderboard(db: LeaderboardDB) -> str:
    entries = db.get_token_leaderboard(limit=50)
    if not entries:
        content = '<div class="empty">No classifiers yet.</div>'
        return _base_page("Classifier Leaderboard", content, "buffer")

    rows = []
    for i, r in enumerate(entries, 1):
        acc = 0
        if r.get("total_classifications", 0) > 0:
            acc = r["correct_classifications"] / r["total_classifications"] * 100
        rows.append(f"""<tr>
            <td>{i}</td>
            <td>{_esc(r['address'])[:14]}</td>
            <td>{r['balance']}</td>
            <td>{r.get('staked', 0)}</td>
            <td>{r['total_earned']}</td>
            <td>{r['correct_classifications']}/{r['total_classifications']} ({acc:.1f}%)</td>
            <td>{r.get('consecutive_correct', 0)}</td>
        </tr>""")

    content = f"""
    <h1>Classifier Leaderboard</h1>
    <p style="color:#777;margin-bottom:12px;">Top 50 classifiers by token balance</p>
    <table>
    <thead><tr><th>#</th><th>Address</th><th>Balance</th><th>Staked</th><th>Earned</th><th>Accuracy</th><th>Streak</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page("Classifier Leaderboard", content, "buffer")
