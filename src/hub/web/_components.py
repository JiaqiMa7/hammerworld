"""Shared HTML components used across multiple pages."""
from __future__ import annotations

import json

from ._translation import _t
from ._utils import _esc, _score_bar


def _entry_table(entries, start_rank: int = 1, lang: str = "en") -> str:
    """Render a table of leaderboard entries."""
    if not entries:
        return f'<div class="empty">{_t("common.no_entries", lang)}</div>'

    rows = []
    for i, e in enumerate(entries):
        row = (
            f"<tr>"
            f"<td>{start_rank + i}</td>"
            f"<td>{_score_bar(e.best_score)}</td>"
            f"<td>{e.best_dimension}</td>"
            f"<td><a href='/web/entry/{e.combo_id}?lang={lang}'>{_esc(e.method_name[:30])}</a></td>"
            f"<td>{_esc(e.problem_title[:40])}</td>"
            f"<td><span class='dim-label'>{e.problem_domain}</span></td>"
            f"<td><span class='dim-label'>{_esc(e.miner_address[:12])}...</span></td>"
            f"</tr>"
        )
        rows.append(row)

    return f"""
    <table>
    <thead><tr>
        <th>{_t("th.rank", lang)}</th><th>{_t("th.score", lang)}</th><th>{_t("th.dim", lang)}</th><th>{_t("th.method", lang)}</th><th>{_t("th.problem", lang)}</th>
        <th>{_t("th.domain", lang)}</th><th>{_t("th.miner", lang)}</th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>"""


def _render_triz_analysis(triz_data_str: str, lang: str = "en") -> str:
    """Render TRIZ analysis results as HTML sections (for entry detail page)."""
    if not triz_data_str or triz_data_str == "null":
        return f'<p style="color:#999;">{_t("entry.no_triz", lang)}</p>'
    try:
        data = json.loads(triz_data_str)
    except (json.JSONDecodeError, TypeError):
        return ""

    parts = []
    sf = data.get("su_field", data.get("standardized_problem", {}).get("su_field", {}))
    if sf and isinstance(sf, dict):
        parts.append(f'''
        <div class="triz-section">
            <h4>{_t("entry.triz_su_field", lang)}</h4>
            <table class="triz-table">
                <tr><td>S1</td><td>{sf.get("s1","?")}</td></tr>
                <tr><td>S2</td><td>{sf.get("s2","?")}</td></tr>
                <tr><td>Field</td><td>{sf.get("field","?")}</td></tr>
                <tr><td>Type</td><td>{sf.get("interaction_type","?")}</td></tr>
                <tr><td>Complete</td><td>{sf.get("is_complete","?")}</td></tr>
            </table>
        </div>''')

    ce = data.get("cause_effect", data.get("standardized_problem", {}).get("cause_effect", {}))
    if ce and isinstance(ce, dict):
        rc = ce.get("root_causes", []); fe = ce.get("final_effects", [])
        if rc or fe:
            parts.append(f'<div class="triz-section"><h4>{_t("entry.triz_cause_effect", lang)}</h4>')
            if rc:
                parts.append(f'<p><b>Root Causes:</b> {", ".join(str(c) for c in rc[:6])}</p>')
            if fe:
                parts.append(f'<p><b>Final Effects:</b> {", ".join(str(f) for f in fe[:6])}</p>')
            parts.append("</div>")

    res = data.get("resources", data.get("standardized_problem", {}).get("resources", {}))
    if res and isinstance(res, dict):
        subst = res.get("substances", []); fields = res.get("fields", [])
        if subst or fields:
            parts.append(f'<div class="triz-section"><h4>{_t("entry.triz_resources", lang)}</h4>')
            if subst:
                parts.append(f'<p><b>Substances:</b> {", ".join(subst[:6])}</p>')
            if fields:
                parts.append(f'<p><b>Fields:</b> {", ".join(fields[:6])}</p>')
            parts.append("</div>")

    nw = data.get("nine_windows", {})
    if nw and isinstance(nw, dict):
        parts.append(f'''
        <div class="triz-section">
            <h4>{_t("entry.triz_9windows", lang)}</h4>
            <table class="nine-windows-table">
                <tr><td class="nw-label">Super</td>
                    <td>{nw.get("supersystem_past","")}</td>
                    <td>{nw.get("supersystem_present","")}</td>
                    <td>{nw.get("supersystem_future","")}</td></tr>
                <tr><td class="nw-label">System</td>
                    <td>{nw.get("system_past","")}</td>
                    <td>{nw.get("system_present","")}</td>
                    <td>{nw.get("system_future","")}</td></tr>
                <tr><td class="nw-label">Sub</td>
                    <td>{nw.get("subsystem_past","")}</td>
                    <td>{nw.get("subsystem_present","")}</td>
                    <td>{nw.get("subsystem_future","")}</td></tr>
                <tr><td></td><td>Past</td><td>Present</td><td>Future</td></tr>
            </table>
        </div>''')

    ss = data.get("standard_solutions", {})
    if ss and isinstance(ss, dict):
        matched = ss.get("matched", []); rc = ss.get("recommended_class", "")
        if matched or rc:
            parts.append(f'<div class="triz-section"><h4>{_t("entry.triz_std_solutions", lang)}</h4>')
            if rc:
                parts.append(f'<p><b>Class:</b> {rc}</p>')
            for m in matched[:5]:
                parts.append(f'<p><b>{m.get("name","")}</b>: {m.get("description","")[:120]}</p>')
            parts.append("</div>")

    ariz = data.get("ariz", {})
    if ariz and isinstance(ariz, dict):
        mini = ariz.get("mini_problem", ""); ifr = ariz.get("ifr", "")
        parts.append(f'<div class="triz-section"><h4>{_t("entry.triz_ariz", lang)}</h4>')
        if mini:
            parts.append(f'<p><b>Mini-Problem:</b> {mini[:120]}</p>')
        if ifr:
            parts.append(f'<p><b>IFR:</b> {ifr[:120]}</p>')
        parts.append("</div>")

    return "\n".join(parts) if parts else ""


def _render_previously_drawn(draw, lang: str) -> str:
    """Render list of entries the viewer has previously drawn from a random-draw board."""
    prev = draw.previously_drawn
    if not prev:
        return ""
    rows = ""
    for e in prev:
        rows += (
            f'<div class="card" style="opacity:0.7;border-left:3px solid #9ca3af;">'
            f'<span style="font-size:12px;color:#6b7280;margin-right:8px;">&#10003; {_t("random.drawn_before", lang)}</span>'
            f'<a href="/web/entry/{e.combo_id}?lang={lang}">{_esc(e.method_name)} &times; {_esc(e.problem_title)}</a>'
            f'</div>'
        )
    return f"""
    <h3 style="margin-top:24px;color:#555;">{_t("random.drawn_before", lang)} ({len(prev)})</h3>
    {rows}
    """
