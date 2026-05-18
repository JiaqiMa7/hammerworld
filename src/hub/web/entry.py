"""Entry detail, combo group, and my-entries pages."""
from __future__ import annotations

from ._translation import _t
from ._utils import _esc, _score_bar
from ._layout import _base_page
from ._components import _render_triz_analysis
from src.hub.leaderboard import LeaderboardDB


def render_entry(db: LeaderboardDB, combo_id: str,
                 viewer_addr: str = "", token_gate=None, lang: str = "en") -> str:
    entry = db._get_by_id(combo_id)
    if not entry:
        runs = db.get_group_runs(combo_id)
        if runs:
            redirect = f"/web/combo/{combo_id}?viewer={_esc(viewer_addr)}&lang={lang}"
            return f'<html><head><meta http-equiv="refresh" content="0; url={redirect}"></head>' \
                   f'<body><p><a href="{redirect}">Redirecting to group page...</a></p></body></html>'
        content = f'<div class="empty">{_t("common.not_found", lang)}</div>'
        return _base_page(_t("entry.title", lang), content, lang=lang, viewer_addr=viewer_addr)

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

    run_id = entry.run_id
    combo_group_id = entry.combo_group_id

    access = token_gate.check_view_access(viewer_addr, run_id) if token_gate else "own"

    if access in ("own", "paid"):
        analysis_html = f"""
        <div class="card" style="line-height:1.8;font-size:14px;">
            <p>{_esc(entry.analysis_text) if entry.analysis_text else f'<span class="empty" style="padding:0;">{_t("entry.no_analysis", lang)}</span>'}</p>
        </div>"""
    else:
        fee = token_gate.VIEW_FEE_N if token_gate else 10
        analysis_html = f"""
        <div class="card" style="text-align:center;padding:32px;">
            <p style="font-size:16px;color:#555;margin-bottom:16px;">{_t("entry.paywalled", lang)}</p>
            <form method="post" action="/web/pay/view/{run_id}">
                <input type="hidden" name="viewer_addr" value="{_esc(viewer_addr)}">
                <input type="hidden" name="redirect" value="/web/entry/{run_id}?viewer={_esc(viewer_addr)}&lang={lang}">
                <input type="text" name="viewer_addr_input" value="{_esc(viewer_addr)}" placeholder="{_t("entry.your_address", lang)}" style="width:260px;margin-bottom:8px;display:block;margin-left:auto;margin-right:auto;">
                <button type="submit" style="font-size:15px;padding:10px 32px;">{_t("entry.pay_view", lang, fee=fee)}</button>
            </form>
        </div>"""

    ratings = db.get_ratings_for_run(run_id)
    avg_rating = db.get_avg_rating_for_run(run_id)
    ratings_html = ""
    if ratings:
        stars = "&#x2605;" * int(avg_rating) + "&#x2606;" * (5 - int(avg_rating))
        ratings_html = f'<p style="margin-bottom:8px;">{_t("entry.avg_rating", lang)}: <b>{stars}</b> ({avg_rating}/5 {_t("entry.from_n_viewers", lang, n=len(ratings))})</p>'
        for r in ratings[:10]:
            r_stars = "&#x2605;" * r["rating"] + "&#x2606;" * (5 - r["rating"])
            comment = _esc(r.get("comment", ""))
            ratings_html += f'<p style="font-size:13px;color:#555;">{r_stars} — {_esc(r["viewer_addr"][:14])}… {comment}</p>'

    rate_form = ""
    if access in ("own", "paid") and viewer_addr:
        rate_form = f"""
        <form method="post" action="/web/rate/{run_id}" style="margin-top:12px;">
            <input type="hidden" name="viewer_addr" value="{_esc(viewer_addr)}">
            <input type="hidden" name="redirect" value="/web/entry/{run_id}?viewer={_esc(viewer_addr)}&lang={lang}">
            <select name="rating" style="width:auto;">
                <option value="">{_t("entry.rate_placeholder", lang)}</option>
                <option value="5">5 — {_t("entry.excellent", lang)}</option>
                <option value="4">4 — {_t("entry.good", lang)}</option>
                <option value="3">3 — {_t("entry.average", lang)}</option>
                <option value="2">2 — {_t("entry.poor", lang)}</option>
                <option value="1">1 — {_t("entry.terrible", lang)}</option>
            </select>
            <input type="text" name="comment" placeholder="{_t("entry.optional_comment", lang)}" style="width:200px;">
            <button type="submit">{_t("entry.submit_rating", lang)}</button>
        </form>"""

    group_runs_count = len(db.get_group_runs(combo_group_id))
    group_link = ""
    if group_runs_count > 1:
        group_link = f"""<p style="margin-top:12px;">
            <a href="/web/combo/{_esc(combo_group_id)}?lang={lang}" class="btn" style="background:#6d28d9;color:white;">
                {_t("combo_group.view_all", lang, n=group_runs_count)}
            </a></p>"""

    content = f"""
    <div class="card">
        <h3>{_esc(entry.method_name)} &times; {_esc(entry.problem_title)}</h3>
        <table style="margin-top:12px;">
            <tr><td style="color:#777;width:140px;">{_t("entry.combo_id", lang)}</td><td>{run_id}</td></tr>
            <tr><td style="color:#777;">{_t("entry.method", lang)}</td><td>{_esc(entry.method_name)}</td></tr>
            <tr><td style="color:#777;">{_t("entry.method_domain", lang)}</td><td>{entry.method_domain}</td></tr>
            <tr><td style="color:#777;">{_t("entry.method_level", lang)}</td><td>{entry.method_level}</td></tr>
            <tr><td style="color:#777;">{_t("entry.problem_title", lang)}</td><td>{_esc(entry.problem_title)}</td></tr>
            <tr><td style="color:#777;">{_t("entry.problem_domain", lang)}</td><td>{entry.problem_domain}</td></tr>
            <tr><td style="color:#777;">{_t("entry.best_dimension", lang)}</td><td><b>{entry.best_dimension}</b></td></tr>
            <tr><td style="color:#777;">{_t("entry.best_score", lang)}</td><td><b>{entry.best_score:.1f}</b></td></tr>
            <tr><td style="color:#777;">{_t("entry.miner", lang)}</td><td>{entry.miner_address}</td></tr>
        </table>
        {group_link}
    </div>

    <h2>{_t("entry.ai_analysis", lang)}</h2>
    {analysis_html}

    <h2>{_t("entry.scores", lang)}</h2>
    <table>{score_rows}</table>

    {_render_triz_analysis(entry.triz_data, lang)}

    <h2>{_t("entry.ratings", lang)}</h2>
    <div class="card">
        {ratings_html if ratings_html else f'<p style="color:#999;">{_t("entry.no_ratings", lang)}</p>'}
        {rate_form}
    </div>
    """
    return _base_page(f"{entry.method_name} × {entry.problem_title}", content, lang=lang, viewer_addr=viewer_addr)


def render_combo_group(db: LeaderboardDB, combo_group_id: str,
                       viewer_addr: str = "", token_gate=None, lang: str = "en") -> str:
    runs = db.get_group_runs(combo_group_id)
    if not runs:
        content = f'<div class="empty">{_t("common.not_found", lang)}</div>'
        return _base_page(_t("combo_group.title", lang, combo=combo_group_id[:30]), content, lang=lang, viewer_addr=viewer_addr)

    first = runs[0]
    access = token_gate.check_view_access(viewer_addr, first.run_id) if token_gate else "own"

    header = f"""
    <div class="card">
        <h3>{_esc(first.method_name)} &times; {_esc(first.problem_title)}</h3>
        <p style="color:#777;margin-top:8px;">{_t("combo_group.n_runs", lang, n=len(runs))}</p>
        <table style="margin-top:12px;">
            <tr><td style="color:#777;width:140px;">Group ID</td><td>{combo_group_id}</td></tr>
            <tr><td style="color:#777;">Method Domain</td><td>{first.method_domain}</td></tr>
            <tr><td style="color:#777;">Method Level</td><td>{first.method_level}</td></tr>
            <tr><td style="color:#777;">Problem Domain</td><td>{first.problem_domain}</td></tr>
        </table>
    </div>"""

    paywall = ""
    if access not in ("own", "paid"):
        fee = token_gate.VIEW_FEE_N if token_gate else 10
        paywall = f"""
        <div class="card" style="text-align:center;padding:32px;margin-bottom:20px;">
            <p style="font-size:16px;color:#555;margin-bottom:16px;">{_t("combo_group.paywalled", lang)}</p>
            <form method="post" action="/web/pay/view/{first.run_id}">
                <input type="hidden" name="viewer_addr" value="{_esc(viewer_addr)}">
                <input type="hidden" name="redirect" value="/web/combo/{combo_group_id}?viewer={_esc(viewer_addr)}&lang={lang}">
                <input type="text" name="viewer_addr_input" value="{_esc(viewer_addr)}" placeholder="{_t("entry.your_address", lang)}" style="width:260px;margin-bottom:8px;display:block;margin-left:auto;margin-right:auto;">
                <button type="submit" style="font-size:15px;padding:10px 32px;">{_t("combo_group.pay_all", lang, fee=fee)}</button>
            </form>
        </div>"""

    import datetime as _dt_mod
    runs_html = ""
    for entry in runs:
        created = ""
        if entry.created_at:
            created = _dt_mod.datetime.fromtimestamp(entry.created_at).strftime("%Y-%m-%d %H:%M")

        analysis = ""
        if access in ("own", "paid") and entry.analysis_text:
            analysis = f'<div class="card" style="line-height:1.8;font-size:14px;margin-top:8px;"><p>{_esc(entry.analysis_text)}</p></div>'

        scores_list = [
            ("Elegance", entry.elegance),
            ("Weirdness", entry.weirdness),
            ("Human Feasibility", entry.human_feasibility),
            ("AI Feasibility", entry.ai_feasibility),
            ("Novelty", entry.novelty),
            ("Analogy Distance", entry.analogy_distance),
            ("Scaling Potential", entry.scaling_potential),
            ("Side Effects", entry.side_effects),
        ]
        score_bars = "".join(
            f'<span style="margin-right:12px;font-size:12px;color:#666;">{n}: {_score_bar(s)}</span>'
            for n, s in scores_list
        )

        ratings = db.get_ratings_for_run(entry.run_id)
        avg_rating = db.get_avg_rating_for_run(entry.run_id)
        ratings_html = ""
        if ratings:
            stars = "&#x2605;" * int(avg_rating) + "&#x2606;" * (5 - int(avg_rating))
            ratings_html = f'<p style="font-size:12px;color:#555;margin-top:4px;">Avg: <b>{stars}</b> ({avg_rating}/5)</p>'

        rate_form = ""
        if access in ("own", "paid") and viewer_addr:
            rate_form = f"""
            <form method="post" action="/web/rate/{entry.run_id}" style="margin-top:8px;">
                <input type="hidden" name="viewer_addr" value="{_esc(viewer_addr)}">
                <input type="hidden" name="redirect" value="/web/combo/{combo_group_id}?viewer={_esc(viewer_addr)}&lang={lang}">
                <select name="rating" style="width:auto;font-size:12px;">
                    <option value="">{_t("entry.rate_placeholder", lang)}</option>
                    <option value="5">5 — {_t("entry.excellent", lang)}</option>
                    <option value="4">4 — {_t("entry.good", lang)}</option>
                    <option value="3">3 — {_t("entry.average", lang)}</option>
                    <option value="2">2 — {_t("entry.poor", lang)}</option>
                    <option value="1">1 — {_t("entry.terrible", lang)}</option>
                </select>
                <input type="text" name="comment" placeholder="{_t("entry.optional_comment", lang)}" style="width:150px;font-size:12px;">
                <button type="submit" style="font-size:12px;padding:4px 8px;">{_t("entry.submit_rating", lang)}</button>
            </form>"""

        runs_html += f"""
        <div class="card" style="margin-bottom:12px;border-left:4px solid #2563eb;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                <div>
                    <span style="font-size:12px;color:#777;">{_t("combo_group.miner", lang)}:</span> {_esc(entry.miner_address[:16])}...
                    <span style="font-size:12px;color:#999;margin-left:8px;">{created}</span>
                </div>
                <div style="text-align:right;">
                    <span style="color:#2563eb;font-weight:bold;">{entry.best_dimension}</span> = {_score_bar(entry.best_score)}
                    <a href="/web/entry/{entry.run_id}?lang={lang}" class="btn" style="padding:4px 12px;font-size:12px;margin-left:8px;">{_t("combo_group.view_run", lang)}</a>
                </div>
            </div>
            <div style="margin-top:6px;display:flex;flex-wrap:wrap;">{score_bars}</div>
            {analysis}
            {ratings_html}
            {rate_form}
        </div>"""

    content = f"""
    {header}
    {paywall}
    <h2>{_t("combo_group.all_runs", lang)}</h2>
    {runs_html}
    """
    return _base_page(f"{first.method_name} x {first.problem_title}", content, lang=lang, viewer_addr=viewer_addr)


def render_my_entries(db: LeaderboardDB, viewer_addr: str = "", lang: str = "en") -> str:
    if not viewer_addr:
        content = f'<div class="empty">{_t("agent.sb_not_logged", lang)}</div>'
        return _base_page(_t("my_entries.title", lang), content, "my-entries", lang=lang, viewer_addr=viewer_addr)

    entries = db.get_entries_by_miner(viewer_addr, limit=50)

    if not entries:
        content = f'<div class="empty">{_t("my_entries.empty", lang)}</div>'
        return _base_page(_t("my_entries.title", lang), content, "my-entries", lang=lang, viewer_addr=viewer_addr)

    import datetime as _dt_mod
    rows = []
    for e in entries:
        created = ""
        if e.created_at:
            created = _dt_mod.datetime.fromtimestamp(e.created_at).strftime("%Y-%m-%d %H:%M")
        rows.append(f"""<tr>
            <td>{e.rank}</td>
            <td><a href="/web/entry/{_esc(e.combo_id)}?lang={lang}">{_esc(e.method_name)} × {_esc(e.problem_title)}</a></td>
            <td>{_esc(e.best_dimension)}</td>
            <td>{e.best_score:.1f}</td>
            <td style="font-size:12px;color:#999;">{created}</td>
            <td><a href="/web/entry/{_esc(e.combo_id)}?lang={lang}" class="btn" style="padding:4px 12px;font-size:12px;">{_t("my_entries.view", lang)}</a></td>
        </tr>""")

    content = f"""
    <h1>{_t("my_entries.title", lang)}</h1>
    <p style="color:#777;margin-bottom:16px;">{_t("my_entries.count", lang, n=len(entries))}</p>
    <table>
    <thead><tr>
        <th>#</th>
        <th>{_t("th.combo", lang)}</th>
        <th>{_t("th.best_dim", lang)}</th>
        <th>{_t("th.score", lang)}</th>
        <th>{_t("th.created", lang)}</th>
        <th></th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page(_t("my_entries.title", lang), content, "my-entries", lang=lang, viewer_addr=viewer_addr)
