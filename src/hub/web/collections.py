"""Collection marketplace pages — browse, create, detail."""
from __future__ import annotations

import json

from ._translation import _t
from ._utils import _esc, _parse_query
from ._layout import _base_page
from src.hub.leaderboard import LeaderboardDB

_COLLECTION_CATEGORIES_METHOD = [
    "triz", "biology", "physics", "chemistry", "mathematics",
    "economics", "machine_learning", "heuristic", "engineering",
    "design", "systems", "other",
]
_COLLECTION_CATEGORIES_PROBLEM = [
    "medicine", "energy", "environment", "information", "materials",
    "society", "transportation", "agriculture", "space", "other",
]


def render_collections(db: LeaderboardDB, path: str, lang: str = "en", viewer_addr: str = "") -> str:
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

    method_tab = f'<a href="/web/collections?type=method&sort=stars" class="{"active" if ctype == "method" else ""}">Methods</a>'
    problem_tab = f'<a href="/web/collections?type=problem&sort=imports" class="{"active" if ctype == "problem" else ""}">Problems</a>'

    method_sorts = [
        ("stars", "Stars"),
        ("imports", "Imports"),
        ("newest", "Newest"),
    ]
    sort_links = " | ".join(
        f'<a href="/web/collections?type={ctype}&sort={s}&category={category or ""}&mine={mine or ""}" style="{"font-weight:bold;color:#2563eb;" if sort_by == s else "font-weight:normal;"}">{label}</a>'
        for s, label in method_sorts
    )

    cats = _COLLECTION_CATEGORIES_METHOD if ctype == "method" else _COLLECTION_CATEGORIES_PROBLEM
    cat_links = "".join(
        f'<a href="/web/collections?type={ctype}&sort={sort_by}&category={c}" class="{"active" if category == c else ""}">{c.replace("_", " ").title()}</a>'
        for c in cats
    )

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
    return _base_page("Collections", content, "collections", lang=lang, viewer_addr=viewer_addr)


def render_collection_new(form: dict | None = None, errors: list[str] | None = None, success: str = "", lang: str = "en") -> str:
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
    return _base_page("New Collection", content, "collections", lang=lang)


def render_collection_detail(db: LeaderboardDB, ctype: str, cid: int, starrer: str = "", starred: bool = False, lang: str = "en") -> str:
    c = db.get_collection(ctype, cid)
    if not c:
        content = '<div class="empty">Collection not found.</div>'
        return _base_page("Not Found", content, lang=lang)

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
    return _base_page(name, content, "collections", lang=lang)


def render_collections_mine(db: LeaderboardDB, creator: str) -> str:
    params = f"type=method&mine={_esc(creator)}"
    return f'<html><head><meta http-equiv="refresh" content="0;url=/web/collections?{params}"></head><body>Redirecting...</body></html>'
