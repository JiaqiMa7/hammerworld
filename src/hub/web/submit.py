"""Community submission pages — methods, problems, and submissions list."""
from __future__ import annotations

import json

from ._translation import _t
from ._utils import _esc
from ._layout import _base_page
from src.hub.leaderboard import LeaderboardDB


def render_submit_home(lang: str = "en", viewer_addr: str = "") -> str:
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
    return _base_page("Community Submit", content, "submit", lang=lang, viewer_addr=viewer_addr)


def render_submit_method(form: dict | None = None, errors: list[str] | None = None, success: str = "", lang: str = "en", viewer_addr: str = "") -> str:
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
    return _base_page("Submit Method", content, "submit", lang=lang, viewer_addr=viewer_addr)


def render_submit_problem(form: dict | None = None, errors: list[str] | None = None, success: str = "", lang: str = "en", viewer_addr: str = "") -> str:
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
    return _base_page("Submit Problem", content, "submit", lang=lang, viewer_addr=viewer_addr)


def render_submissions(db: LeaderboardDB, lang: str = "en", viewer_addr: str = "") -> str:
    pending = db.get_pending_submissions()
    total = db.total_pending()

    if not pending:
        content = '<div class="empty">No pending submissions.</div>'
        return _base_page("Submissions", content, "submit", lang=lang, viewer_addr=viewer_addr)

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
    return _base_page("Submissions", content, "submit", lang=lang, viewer_addr=viewer_addr)
