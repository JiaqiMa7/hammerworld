"""Server-side HTML rendering for the hub web interface."""
from __future__ import annotations

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
    background: #0f0f1a; color: #e0e0e0; line-height: 1.6;
    max-width: 1200px; margin: 0 auto; padding: 0 16px;
}
a { color: #7ec8e3; text-decoration: none; }
a:hover { text-decoration: underline; }
nav {
    display: flex; gap: 4px; padding: 16px 0; flex-wrap: wrap;
    border-bottom: 1px solid #2a2a4a; margin-bottom: 20px;
}
nav a {
    padding: 6px 14px; border-radius: 4px; background: #1a1a2e;
    color: #aaa; font-size: 14px;
}
nav a:hover, nav a.active { background: #0f3460; color: #fff; text-decoration: none; }
h1 { font-size: 22px; color: #fff; margin-bottom: 16px; }
h2 { font-size: 18px; color: #ccc; margin: 16px 0 8px; }
.stats { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.stat-card {
    background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 8px;
    padding: 16px 24px; text-align: center; min-width: 120px;
}
.stat-card .num { font-size: 28px; font-weight: bold; color: #7ec8e3; }
.stat-card .label { font-size: 13px; color: #888; margin-top: 4px; }
.quick-links { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
.quick-links a, .quick-links span {
    padding: 4px 12px; border-radius: 4px; font-size: 13px;
    background: #1a1a2e; border: 1px solid #2a2a4a; color: #aaa;
}
.quick-links a:hover { background: #0f3460; color: #fff; text-decoration: none; }
.quick-links .sep { border: none; background: none; color: #444; padding: 4px 2px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #2a2a4a; font-size: 13px; }
th { background: #1a1a2e; color: #888; font-weight: 600; position: sticky; top: 0; }
tr:hover { background: #1a1a2e; }
.bar-bg { width: 80px; height: 6px; background: #2a2a4a; border-radius: 3px; display: inline-block; vertical-align: middle; margin-right: 4px; }
.bar-fill { height: 100%; border-radius: 3px; }
.bar-high { background: #4caf50; } .bar-mid { background: #ff9800; } .bar-low { background: #f44336; }
form { margin-bottom: 20px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
input, select, button {
    background: #1a1a2e; border: 1px solid #2a2a4a; color: #e0e0e0;
    padding: 6px 12px; border-radius: 4px; font-size: 14px;
}
button { cursor: pointer; background: #0f3460; border-color: #0f3460; }
button:hover { background: #1a4a7a; }
.pagination { display: flex; gap: 8px; margin: 16px 0; }
.card {
    background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 8px;
    padding: 16px; margin-bottom: 12px;
}
.card h3 { font-size: 15px; color: #7ec8e3; margin-bottom: 8px; }
.card .scores { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.card .score-tag {
    font-size: 12px; padding: 2px 8px; border-radius: 3px;
    background: #0f3460; color: #ccc;
}
.empty { text-align: center; color: #666; padding: 40px; font-size: 15px; }
footer { text-align: center; padding: 20px; color: #555; font-size: 12px; border-top: 1px solid #2a2a4a; margin-top: 30px; }
.dim-label { font-size: 11px; color: #888; }
"""


def _base_page(title: str, content: str, active_nav: str = "") -> str:
    nav_items = [
        ("/", "Dashboard", "dashboard"),
        ("/web/leaderboard", "Leaderboard", "leaderboard"),
        ("/web/search", "Search", "search"),
        ("/web/random", "Random Draw", "random"),
        ("/web/peers", "Peers", "peers"),
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
    <p style="color:#888;margin-bottom:12px;">Showing: {filter_text} &mdash; {len(entries)} results (offset {offset})</p>

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
            result_html = f"<p style='color:#888;margin-bottom:12px;'>{len(entries)} results for '<b>{_esc(query)}</b>'</p>" + _entry_table(entries)
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
            <p style="color:#888;font-size:13px;">Best: <b>{e.best_dimension}</b> = {_score_bar(e.best_score)} | Domain: {e.problem_domain} | Level: {e.method_level}</p>
            <div class="scores">{scores_html}</div>
        </div>""")

    content = f"""
    <form method="get" action="/web/random">
        <select name="dim"><option value="">All Dimensions</option>{dim_opts}</select>
        <select name="domain"><option value="">All Domains</option>{domain_opts}</select>
        <input type="number" name="count" value="{count}" min="1" max="50" style="width:80px;" placeholder="Count">
        <button type="submit">Draw</button>
    </form>

    <p style="color:#888;margin:12px 0;">
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
            <tr><td style="color:#888;width:140px;">Combo ID</td><td>{entry.combo_id}</td></tr>
            <tr><td style="color:#888;">Method</td><td>{_esc(entry.method_name)}</td></tr>
            <tr><td style="color:#888;">Method Domain</td><td>{entry.method_domain}</td></tr>
            <tr><td style="color:#888;">Method Level</td><td>{entry.method_level}</td></tr>
            <tr><td style="color:#888;">Problem</td><td>{_esc(entry.problem_title)}</td></tr>
            <tr><td style="color:#888;">Problem Domain</td><td>{entry.problem_domain}</td></tr>
            <tr><td style="color:#888;">Best Dimension</td><td><b>{entry.best_dimension}</b></td></tr>
            <tr><td style="color:#888;">Best Score</td><td><b>{entry.best_score:.1f}</b></td></tr>
            <tr><td style="color:#888;">Miner</td><td>{entry.miner_address}</td></tr>
        </table>
    </div>

    <h2>Scores</h2>
    <table>{score_rows}</table>
    """
    return _base_page(f"{entry.method_name} × {entry.problem_title}", content)
