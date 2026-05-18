"""Dashboard page — stats, mining panel, quick links."""
from __future__ import annotations

from ._translation import _t
from ._utils import _esc
from ._layout import _base_page
from ._components import _entry_table
from src.hub.leaderboard import LeaderboardDB
from src.hub.peer import PeerManager
from src.engine.models import EvalDimension, Domain


def render_dashboard(db: LeaderboardDB, pm: PeerManager, lang: str = "en", viewer_addr: str = "") -> str:
    total = db.total_entries()
    peers = len(pm.get_peers())
    uptime_m = int(pm.uptime / 60)
    uptime_str = f"{uptime_m // 60}h {uptime_m % 60}m" if uptime_m >= 60 else f"{uptime_m}m"

    top = db.get_top(limit=10)

    dim_links = "".join(
        f'<a href="/web/leaderboard?dim={d.value}&lang={lang}">{d.value.title()}</a>'
        for d in EvalDimension
    )
    domain_links = "".join(
        f'<a href="/web/leaderboard?domain={d.value}&lang={lang}">{d.value.title()}</a>'
        for d in Domain
    )

    method_colls = db.get_collections("method", sort_by="newest")
    problem_colls = db.get_collections("problem", sort_by="newest")

    method_opts = '<option value="">-- Select --</option>' + "".join(
        f'<option value="{_esc(c["name"])}">{_esc(c["name"])}</option>'
        for c in method_colls
    )
    problem_opts = '<option value="">-- Select --</option>' + "".join(
        f'<option value="{_esc(c["name"])}">{_esc(c["name"])}</option>'
        for c in problem_colls
    )

    mine_panel = f"""
    <div class="mine-panel">
        <h2>{_t("dash.mine_title", lang)}</h2>
        <p style="font-size:13px;color:#777;margin-bottom:12px;">{_t("dash.mine_desc", lang)}</p>
        <div class="mine-form">
            <div class="mine-field">
                <label>{_t("dash.mine_method_col", lang)}</label>
                <select id="mine-method-col">{method_opts}</select>
            </div>
            <div class="mine-field">
                <label>{_t("dash.mine_problem_col", lang)}</label>
                <select id="mine-problem-col">{problem_opts}</select>
            </div>
            <div class="mine-field">
                <label>{_t("dash.mine_batch", lang)}</label>
                <input type="number" id="mine-batch" value="5" min="1" max="50">
            </div>
            <div class="mine-field">
                <label>{_t("dash.mine_model", lang)}</label>
                <input type="text" id="mine-model" value="" placeholder="default">
            </div>
            <button onclick="startMining()" id="mine-btn">{_t("dash.mine_start", lang)}</button>
        </div>
        <div id="mine-result" style="display:none;"></div>
    </div>
    <script>
    function startMining() {{
        var btn = document.getElementById('mine-btn');
        var result = document.getElementById('mine-result');
        var methodCol = document.getElementById('mine-method-col').value;
        var problemCol = document.getElementById('mine-problem-col').value;
        var batch = document.getElementById('mine-batch').value || 5;
        var model = document.getElementById('mine-model').value;

        if (!methodCol || !problemCol) {{ alert('Please select both collections'); return; }}

        btn.disabled = true;
        btn.textContent = '{_t("dash.mine_running", lang)}';
        result.style.display = 'block';
        result.innerHTML = '<div class="mine-progress">{_t("dash.mine_running", lang)}</div>';

        fetch('/web/dashboard/mine', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                method_collection: methodCol,
                problem_collection: problemCol,
                batch_size: parseInt(batch),
                model: model
            }})
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
            if (d.ok) {{
                result.innerHTML = '<div class="mine-result"><div class="ok">'
                    + d.message + '</div>'
                    + (d.leaderboard_link ? '<br><a href="' + d.leaderboard_link + '?lang={lang}">'
                    + '{_t("dash.mine_result_link", lang)}</a>' : '')
                    + '</div>';
            }} else {{
                result.innerHTML = '<div class="mine-result"><div class="err">' + d.error + '</div></div>';
            }}
            btn.disabled = false;
            btn.textContent = '{_t("dash.mine_start", lang)}';
        }})
        .catch(function(e) {{
            result.innerHTML = '<div class="mine-result"><div class="err">' + e + '</div></div>';
            btn.disabled = false;
            btn.textContent = '{_t("dash.mine_start", lang)}';
        }});
    }}
    </script>
    """

    if not method_colls or not problem_colls:
        mine_panel = f"""
        <div class="mine-panel">
            <h2>{_t("dash.mine_title", lang)}</h2>
            <p style="font-size:13px;color:#999;">{_t("dash.mine_no_collections", lang)}</p>
        </div>"""

    content = f"""
    <div class="stats">
        <div class="stat-card"><div class="num">{total}</div><div class="label">{_t("dash.entries", lang)}</div></div>
        <div class="stat-card"><div class="num">{peers}</div><div class="label">{_t("dash.peers", lang)}</div></div>
        <div class="stat-card"><div class="num">{uptime_str}</div><div class="label">{_t("dash.uptime", lang)}</div></div>
    </div>

    {mine_panel}

    <h2>{_t("dash.by_dimension", lang)}</h2>
    <div class="quick-links">{dim_links}</div>

    <h2>{_t("dash.by_domain", lang)}</h2>
    <div class="quick-links">{domain_links}</div>

    <h2>{_t("dash.top_entries", lang)}</h2>
    {_entry_table(top, lang=lang)}
    """
    return _base_page(_t("dash.title", lang), content, "dashboard", lang=lang, viewer_addr=viewer_addr)
