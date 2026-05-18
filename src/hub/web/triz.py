"""Dedicated TRIZ Agent page — analysis, history, actions."""
from __future__ import annotations

import time

from ._translation import _t
from ._utils import _esc
from ._layout import _base_page
from src.hub.leaderboard import LeaderboardDB
from src.engine.models import Domain


def render_triz_agent(db: LeaderboardDB, lang: str = "en",
                      viewer_addr: str = "", analysis_result: str = "",
                      analysis_json: str = "") -> str:
    domain_opts = "".join(
        f'<option value="{d.value}">{d.value.title()}</option>'
        for d in Domain
    )

    history_items = _render_triz_history(db, viewer_addr, lang)

    show_actions = "style='display:none'" if not analysis_result else ""

    content = f"""
    <div class="triz-layout">
        <div class="triz-main">
            <div class="triz-input-area">
                <textarea id="triz-input" placeholder="{_t('triz.input_placeholder', lang)}" rows="4">{_esc(analysis_json)}</textarea>
                <div class="triz-controls">
                    <select id="triz-domain">{domain_opts}</select>
                    <button class="primary" onclick="runTrizAnalysis()" id="triz-btn">{_t('triz.analyze_btn', lang)}</button>
                </div>
            </div>
            <div id="triz-result">
                {analysis_result if analysis_result else '<div class="empty" style="margin-top:40px;">' + _t('triz.no_result_yet', lang) + '</div>'}
            </div>
        </div>
        <div class="triz-sidebar">
            <h4>{_t('triz.history', lang)}</h4>
            <div id="triz-history">{history_items}</div>
            <hr style="margin:12px 0;border:none;border-top:1px solid #eef0f4;">
            <h4>{_t('triz.quick_actions', lang)}</h4>
            <div id="triz-actions" {show_actions}>
                <div class="action-card" onclick="createMatrix()">{_t('triz.action_matrix', lang)}</div>
                <div class="action-card" onclick="showBountyForm()">{_t('triz.action_bounty', lang)}</div>
                <div class="action-card" onclick="exportMethod()">{_t('triz.action_export', lang)}</div>
                <div class="action-card" onclick="submitProblem()">{_t('triz.action_submit', lang)}</div>
                <div class="action-card" onclick="viewRelated()">{_t('triz.action_related', lang)}</div>
            </div>
            <div id="triz-bounty-form" class="triz-bounty-form" style="display:none;">
                <label style="font-size:12px;font-weight:600;">{_t('triz.bounty_amount', lang)}</label>
                <div style="display:flex;gap:6px;margin-top:4px;">
                    <input type="number" id="bounty-amount" value="50" min="10" style="width:100px;">
                    <button onclick="createBounty()" style="font-size:12px;">{_t('triz.confirm_bounty', lang)}</button>
                </div>
                <div style="font-size:11px;color:#999;margin-top:4px;">{_t('triz.bounty_hint', lang)}</div>
            </div>
        </div>
    </div>

    <script>
    var _lastAnalysis = null;
    var _toolLabels = {{
        standardize: 'Standardize',
        su_field: 'Su-Field',
        cause_effect: 'Cause-Effect',
        resources: 'Resources',
        nine_windows: '9-Windows',
        trimming: 'Trimming',
        function_ranking: 'Function Ranking',
        stc: 'STC Operator',
        slp: 'Smart People',
        standard_solutions: 'Standard Solutions',
        ariz: 'ARIZ',
        insights: 'Integration',
    }};

    function runTrizAnalysis() {{
        var input = document.getElementById('triz-input');
        var domain = document.getElementById('triz-domain');
        var btn = document.getElementById('triz-btn');
        var result = document.getElementById('triz-result');
        var desc = input.value.trim();
        if (!desc) {{ alert('Please enter a description'); return; }}

        btn.disabled = true;
        btn.textContent = 'Analyzing...';
        _lastAnalysis = null;

        var toolNames = ['standardize','su_field','cause_effect','resources','nine_windows',
                         'trimming','function_ranking','stc','slp','standard_solutions','ariz','insights'];
        var progressRows = toolNames.map(function(n) {{
            return '<div class="triz-pstep" data-tool="' + n + '">' +
                   '<span class="triz-picon">⏳</span>' +
                   '<span class="triz-pname">' + (_toolLabels[n] || n) + '</span>' +
                   '<span class="triz-ptime"></span></div>';
        }}).join('');
        result.innerHTML = '<div class="triz-progress" id="triz-progress">' +
            '<div class="triz-pbar"><div class="triz-pfill" id="triz-pfill" style="width:0%"></div></div>' +
            '<div class="triz-pcount" id="triz-pcount">0/12</div>' +
            '<div class="triz-plist">' + progressRows + '</div></div>' +
            '<div class="triz-pcurrent" id="triz-pcurrent" style="font-size:13px;color:#6d28d9;margin-top:8px;">Starting...</div>';

        var startTime = Date.now();

        fetch('/web/triz/analyze', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{description: desc, domain: domain.value}})
        }})
        .then(function(r) {{
            if (!r.ok) return r.json().then(function(d) {{ throw new Error(d.error || 'HTTP ' + r.status); }});
            var reader = r.body.getReader();
            var decoder = new TextDecoder();
            var buffer = '';

            function readChunk() {{
                reader.read().then(function(result) {{
                    if (result.done) {{
                        btn.disabled = false;
                        btn.textContent = 'Analyze';
                        return;
                    }}
                    buffer += decoder.decode(result.value, {{stream: true}});
                    var lines = buffer.split('\\n');
                    buffer = lines.pop() || '';
                    for (var i = 0; i < lines.length; i++) {{
                        var line = lines[i];
                        if (line.indexOf('data: ') === 0) {{
                            try {{
                                var data = JSON.parse(line.slice(6));
                                handleEvent(data);
                            }} catch(e) {{ /* skip malformed */ }}
                        }}
                    }}
                    readChunk();
                }}).catch(function(e) {{
                    btn.disabled = false;
                    btn.textContent = 'Analyze';
                    result.innerHTML = '<div class="empty" style="color:#991b1b;">Stream error: ' + e + '</div>';
                }});
            }}
            readChunk();
        }})
        .catch(function(e) {{
            btn.disabled = false;
            btn.textContent = 'Analyze';
            result.innerHTML = '<div class="empty" style="color:#991b1b;">' + e + '</div>';
        }});

        function handleEvent(data) {{
            if (data.error) {{
                btn.disabled = false;
                btn.textContent = 'Analyze';
                result.innerHTML = '<div class="empty" style="color:#991b1b;">' + data.error + '</div>';
                return;
            }}

            if (data.done) {{
                _lastAnalysis = data;
                result.innerHTML = data.html;
                document.getElementById('triz-actions').style.display = '';
                var hist = document.getElementById('triz-history');
                if (data.history_html) hist.innerHTML = data.history_html;
                btn.disabled = false;
                btn.textContent = 'Analyze';
                return;
            }}

            if (data.step) {{
                var elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                document.getElementById('triz-pcurrent').textContent =
                    'Running: ' + (_toolLabels[data.step] || data.step) + ' (' + data.current + '/' + data.total + ')';

                var pct = Math.round((data.current / data.total) * 100);
                var fill = document.getElementById('triz-pfill');
                if (fill) fill.style.width = pct + '%';
                var count = document.getElementById('triz-pcount');
                if (count) count.textContent = data.current + '/' + data.total;

                var row = document.querySelector('.triz-pstep[data-tool="' + data.step + '"]');
                if (row) {{
                    var icon = row.querySelector('.triz-picon');
                    var time = row.querySelector('.triz-ptime');
                    if (icon) icon.textContent = '✓';
                    if (time) time.textContent = elapsed + 's';
                    row.classList.add('done');
                }}

                var allRows = document.querySelectorAll('.triz-pstep');
                var found = false;
                for (var j = 0; j < allRows.length; j++) {{
                    var r = allRows[j];
                    if (!r.classList.contains('done')) {{
                        var rIcon = r.querySelector('.triz-picon');
                        if (rIcon) rIcon.textContent = found ? '⏳' : '⟳';
                        found = true;
                    }}
                }}
            }}
        }}
    }}

    function showTab(tabId) {{
        document.querySelectorAll('.triz-tab-content').forEach(function(el) {{ el.classList.remove('active'); }});
        document.querySelectorAll('.triz-tab').forEach(function(el) {{ el.classList.remove('active'); }});
        document.getElementById(tabId).classList.add('active');
        document.querySelector('[data-tab="' + tabId + '"]').classList.add('active');
    }}

    function createMatrix() {{
        if (!_lastAnalysis) return;
        fetch('/web/triz/create-matrix', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                analysis_id: _lastAnalysis.analysis_id || 0,
                problem_description: document.getElementById('triz-input').value.trim(),
                triz_data: JSON.stringify(_lastAnalysis)
            }})
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
            if (d.ok) window.location.href = d.redirect;
            else alert(d.error || 'Failed');
        }})
        .catch(function(e) {{ alert(e); }});
    }}

    function showBountyForm() {{
        var f = document.getElementById('triz-bounty-form');
        f.style.display = f.style.display === 'none' ? 'block' : 'none';
    }}

    function createBounty() {{
        if (!_lastAnalysis) return;
        var amount = document.getElementById('bounty-amount').value;
        fetch('/web/triz/bounty', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                problem_description: document.getElementById('triz-input').value.trim(),
                prize_pool: parseInt(amount) || 50,
                triz_data: JSON.stringify(_lastAnalysis)
            }})
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
            if (d.ok) window.location.href = '/web/bounties?lang={lang}';
            else alert(d.error || 'Failed');
        }})
        .catch(function(e) {{ alert(e); }});
    }}

    function exportMethod() {{
        if (!_lastAnalysis) return;
        fetch('/web/triz/export-method', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                description: document.getElementById('triz-input').value.trim(),
                analysis: _lastAnalysis
            }})
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
            if (d.ok && d.download_url) window.location.href = d.download_url;
            else alert(d.error || 'Failed');
        }})
        .catch(function(e) {{ alert(e); }});
    }}

    function submitProblem() {{
        if (!_lastAnalysis) return;
        fetch('/web/triz/submit-problem', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                description: document.getElementById('triz-input').value.trim(),
                analysis: _lastAnalysis
            }})
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
            if (d.ok) alert('Submitted! Submission ID: ' + d.submission_id);
            else alert(d.error || 'Failed');
        }})
        .catch(function(e) {{ alert(e); }});
    }}

    function viewRelated() {{
        if (!_lastAnalysis) return;
        fetch('/web/triz/related', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                description: document.getElementById('triz-input').value.trim(),
                analysis: _lastAnalysis
            }})
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
            if (d.ok) {{
                document.getElementById('triz-result').innerHTML += d.html;
            }}
        }})
        .catch(function(e) {{}});
    }}
    </script>
    """
    return _base_page(_t("triz.title", lang), content, "triz", lang=lang,
                      viewer_addr=viewer_addr)


def _render_triz_history(db: LeaderboardDB, viewer_addr: str, lang: str) -> str:
    items = []
    now = time.time()
    try:
        results = db.get_triz_analyses(viewer_addr, limit=10)
        for r in results:
            ts = r.get("created_at", now)
            date_str = f"{int((now - ts) / 3600)}h ago" if ts else ""
            desc = (r.get("description", "") or "")[:40]
            items.append(
                f'<div class="history-item" onclick="loadAnalysis({r["id"]})">'
                f'<div>{_esc(desc)}</div>'
                f'<div class="date">{date_str}</div>'
                f'</div>'
            )
    except AttributeError:
        pass
    if not items:
        return f'<div style="font-size:12px;color:#999;">{_t("triz.no_history", lang)}</div>'
    return "".join(items)


def render_triz_analysis_result_html(analysis: dict, lang: str) -> str:
    tabs = [
        ("contradiction", _t("triz.tab_contradiction", lang)),
        ("sufield", _t("triz.tab_sufield", lang)),
        ("cause_effect", _t("triz.tab_cause_effect", lang)),
        ("resources", _t("triz.tab_resources", lang)),
        ("nine_windows", _t("triz.tab_9windows", lang)),
        ("std_solutions", _t("triz.tab_std_solutions", lang)),
        ("ariz", _t("triz.tab_ariz", lang)),
    ]
    tab_headers = "".join(
        f'<span class="triz-tab {"active" if i == 0 else ""}" '
        f'data-tab="triz-panel-{tid}" onclick="showTab(\'triz-panel-{tid}\')">{label}</span>'
        for i, (tid, label) in enumerate(tabs)
    )

    a = analysis.get("analysis", analysis)

    contradiction = ""
    if isinstance(a.get("standardized_problem"), dict):
        sp = a["standardized_problem"]
        ctx = sp.get("triz_standardized") or {}
        c = ctx.get("contradiction", {})
        if c:
            contradiction += f'<p><strong>{_t("triz.contradiction", lang)}:</strong> {_esc(c.get("improving", "?"))} vs {_esc(c.get("worsening", "?"))}</p>'
        ifr = ctx.get("ifr", "")
        if ifr:
            contradiction += f'<p><strong>{_t("triz.ifr", lang)}:</strong> {_esc(ifr)}</p>'
        principles = ctx.get("triz_params", [])
        if principles:
            contradiction += f'<p><strong>{_t("triz.principles", lang)}:</strong> {", ".join(f"#{p}" for p in principles)}</p>'

    suf = a.get("su_field", {})
    if isinstance(suf, dict):
        suf = {k: v for k, v in suf.items() if not k.startswith("_")}
    sufield_tab = '<table class="triz-table">'
    for k, v in suf.items():
        if k == "transformation_suggestions" and isinstance(v, list):
            sufield_tab += f"<tr><td>Suggestions</td><td>{'; '.join(str(x) for x in v)}</td></tr>"
        else:
            sufield_tab += f"<tr><td>{k}</td><td>{_esc(str(v))}</td></tr>"
    sufield_tab += "</table>"

    ce = a.get("cause_effect", {})
    ce_tab = ""
    if isinstance(ce, dict):
        for k, v in ce.items():
            ce_tab += f"<p><strong>{k}:</strong> {_esc(str(v)[:200])}</p>"

    res = a.get("resources", {})
    res_tab = ""
    if isinstance(res, dict):
        for k, v in res.items():
            if isinstance(v, list):
                res_tab += f"<p><strong>{k}:</strong> {', '.join(str(x) for x in v)}</p>"

    nw = a.get("nine_windows", {})
    nw_tab = ""
    if isinstance(nw, dict):
        nw_tab += '<table class="nine-windows-table">'
        for row_label in ["supersystem", "system", "subsystem"]:
            nw_tab += f"<tr><td class='nw-label'>{row_label}</td>"
            for period in ["past", "present", "future"]:
                val = nw.get(f"{row_label}_{period}") or nw.get(f"{period}_{row_label}") or nw.get(period, {}).get(row_label, "")
                nw_tab += f"<td>{_esc(str(val)[:80])}</td>"
            nw_tab += "</tr>"
        nw_tab += f'<tr><td></td><td>Past</td><td>Present</td><td>Future</td></tr></table>'

    std = a.get("standard_solutions", {})
    std_tab = ""
    if isinstance(std, dict):
        matched = std.get("matched", [])
        if matched:
            cls = std.get("recommended_class", "")
            std_tab += f"<p><strong>Recommended Class:</strong> {cls}</p>"
            for s in matched[:10]:
                name = s.get("name", "")
                desc = s.get("description", "")[:100]
                std_tab += f"<p>• <strong>{_esc(name)}</strong>: {_esc(desc)}</p>"
        else:
            std_tab = '<p style="color:#999;">No standard solutions matched.</p>'

    ariz = a.get("ariz", {})
    ariz_tab = ""
    if isinstance(ariz, dict):
        steps = ariz.get("steps_completed", 0)
        phases = ariz.get("phases_completed", [])
        ariz_tab += f"<p><strong>Steps:</strong> {steps}</p>"
        if phases:
            ariz_tab += f"<p><strong>Phases:</strong> {', '.join(str(p) for p in phases)}</p>"

    tab_contents = {
        "contradiction": contradiction or '<p style="color:#999;">No contradiction data.</p>',
        "sufield": sufield_tab or '<p style="color:#999;">No Su-Field data.</p>',
        "cause_effect": ce_tab or '<p style="color:#999;">No cause-effect data.</p>',
        "resources": res_tab or '<p style="color:#999;">No resource data.</p>',
        "nine_windows": nw_tab or '<p style="color:#999;">No 9-Windows data.</p>',
        "std_solutions": std_tab or '<p style="color:#999;">No standard solutions data.</p>',
        "ariz": ariz_tab or '<p style="color:#999;">No ARIZ data.</p>',
    }

    panels = "".join(
        f'<div id="triz-panel-{tid}" class="triz-tab-content {"active" if i == 0 else ""}">'
        f'<div class="triz-section">{content}</div></div>'
        for i, (tid, _) in enumerate(tabs)
        for content in [tab_contents[tid]]
    )

    meta = analysis.get("_meta", {})
    cfg_info = meta.get("_config", {})
    config_banner = ""
    if cfg_info:
        mode_label = {"ai": "AI", "rule-based": "Rule-based"}.get(cfg_info.get("mode", ""), cfg_info.get("mode", "?"))
        cfg_path = cfg_info.get("config_path", "~/.hammerworld/config")
        api_icon = "✓" if cfg_info.get("api_key_set") else "✗"
        file_icon = "✓" if cfg_info.get("config_file_exists") else "✗"
        config_banner = '<div class="triz-config-banner" style="font-size:12px;color:#666;margin-bottom:12px;display:flex;gap:16px;">'
        config_banner += f'<span><strong>Config:</strong> <code>{cfg_path}</code> [{file_icon}]</span>'
        config_banner += f'<span><strong>API key:</strong> [{api_icon}]</span>'
        config_banner += f'<span><strong>Mode:</strong> {mode_label}</span>'
        config_banner += '</div>'

    return f"""
    <h3 style="margin-bottom:8px;">{_t('triz.analysis_result', lang)}</h3>
    {config_banner}
    <div class="triz-tabs">{tab_headers}</div>
    {panels}
    """
