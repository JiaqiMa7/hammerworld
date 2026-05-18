"""Leaderboard, search, and random draw pages."""
from __future__ import annotations

from ._translation import _t
from ._utils import _esc, _parse_query, _score_bar
from ._layout import _base_page
from ._components import _entry_table, _render_previously_drawn
from src.hub.leaderboard import LeaderboardDB
from src.engine.models import EvalDimension, Domain, MethodLevel


def render_leaderboard(db: LeaderboardDB, path: str,
                       viewer_addr: str = "", token_gate=None, lang: str = "en") -> str:
    params = _parse_query(path)
    dim = EvalDimension(params["dim"]) if params.get("dim") else None
    dom = Domain(params["domain"]) if params.get("domain") else None
    lvl = MethodLevel(int(params["level"])) if params.get("level") else None
    limit = min(int(params.get("limit", 50)), 200)
    offset = int(params.get("offset", 0))

    board_name = f"{(dim.value if dim else 'best')}_{(dom.value if dom else 'all')}"
    has_access = True
    if token_gate and viewer_addr:
        has_access = token_gate.check_leaderboard_access(viewer_addr, board_name)

    entries = db.get_top(dimension=dim, domain=dom, method_level=lvl, limit=limit, offset=offset)

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
        active_filters.append(f"{_t('lb.dimension', lang)}: {dim.value}")
    if dom:
        active_filters.append(f"{_t('lb.domain', lang)}: {dom.value}")
    if lvl:
        active_filters.append(f"{_t('lb.level', lang)}: {lvl.value}")
    filter_text = " &mdash; ".join(active_filters) if active_filters else "All"

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
        p["lang"] = lang
        return "/web/leaderboard?" + "&".join(f"{k}={v}" for k, v in p.items())

    prev_link = ""
    if offset > 0:
        prev_offset = max(0, offset - limit)
        prev_link = f'<a href="{_filter_url(**{"offset": str(prev_offset)})}">&larr; {_t("lb.previous", lang)}</a>'

    next_link = ""
    if len(entries) == limit:
        next_offset = offset + limit
        next_link = f'<a href="{_filter_url(**{"offset": str(next_offset)})}">{_t("lb.next", lang)} &rarr;</a>'

    base_params = f"dim={dim.value if dim else ''}&domain={dom.value if dom else ''}&limit={limit}&offset={offset}&viewer={_esc(viewer_addr)}&lang={lang}"

    unlock_html = ""
    if not has_access:
        fee = token_gate.LEADERBOARD_FEE_P if token_gate else 20
        unlock_html = f"""
        <div class="card" style="text-align:center;padding:32px;margin-bottom:20px;">
            <p style="font-size:16px;color:#555;margin-bottom:16px;">{_t("lb.locked", lang)}</p>
            <form method="post" action="/web/pay/leaderboard/{board_name}">
                <input type="hidden" name="viewer_addr" value="{_esc(viewer_addr)}">
                <input type="hidden" name="redirect" value="/web/leaderboard?{base_params}">
                <input type="text" name="viewer_addr_input" value="{_esc(viewer_addr)}" placeholder="{_t("entry.your_address", lang)}" style="width:260px;margin-bottom:8px;display:block;margin-left:auto;margin-right:auto;">
                <button type="submit" style="font-size:15px;padding:10px 32px;">{_t("lb.pay_unlock", lang, fee=fee)}</button>
            </form>
        </div>"""

    content = f"""
    <p style="color:#777;margin-bottom:12px;">{_t("lb.showing", lang)}: {filter_text} &mdash; {len(entries) if has_access else 0} {_t("lb.results", lang)} ({_t("lb.offset", lang)} {offset})</p>

    <form method="get" action="/web/leaderboard">
        <select name="dim"><option value="">{_t("lb.all_dimensions", lang)}</option>{dim_opts}</select>
        <select name="domain"><option value="">{_t("lb.all_domains", lang)}</option>{domain_opts}</select>
        <input type="number" name="limit" value="{limit}" min="10" max="200" style="width:80px;" placeholder="Limit">
        <input type="hidden" name="viewer" value="{_esc(viewer_addr)}">
        <input type="hidden" name="lang" value="{lang}">
        <button type="submit">{_t("lb.filter", lang)}</button>
    </form>

    {unlock_html}

    {_entry_table(entries, start_rank=offset + 1, lang=lang) if has_access else ''}

    <div class="pagination">{prev_link if has_access else ''}{next_link if has_access else ''}</div>
    """
    return _base_page(_t("lb.title", lang), content, "leaderboard", lang=lang, viewer_addr=viewer_addr)


def render_search(db: LeaderboardDB, path: str, lang: str = "en", viewer_addr: str = "") -> str:
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
            result_html = f"<p style='color:#777;margin-bottom:12px;'>{len(entries)} {_t('search.title', lang).lower()} {_t('lb.results', lang)} '<b>{_esc(query)}</b>'</p>" + _entry_table(entries, lang=lang)
        else:
            result_html = f"<div class='empty'>{_t('common.no_results', lang)} '<b>{_esc(query)}</b>'.</div>"
    else:
        result_html = f"<div class='empty'>{_t('common.enter_search', lang)}</div>"

    content = f"""
    <form method="get" action="/web/search">
        <input type="text" name="q" value="{_esc(query)}" placeholder="{_t('search.placeholder', lang)}" style="flex:1;min-width:300px;">
        <select name="dim"><option value="">{_t('lb.all_dimensions', lang)}</option>{dim_opts}</select>
        <input type="hidden" name="lang" value="{lang}">
        <button type="submit">{_t('search.button', lang)}</button>
    </form>
    {result_html}
    """
    return _base_page(_t("search.title", lang), content, "search", lang=lang, viewer_addr=viewer_addr)


def render_random(db: LeaderboardDB, path: str,
                   viewer_addr: str = "", token_gate=None, lang: str = "en") -> str:
    params = _parse_query(path)
    dim = EvalDimension(params["dim"]) if params.get("dim") else None
    dom = Domain(params["domain"]) if params.get("domain") else None
    count = min(int(params.get("count", 10)), 50)
    viewer = params.get("viewer", viewer_addr) if viewer_addr else ""

    dim_opts = "".join(
        f'<option value="{d.value}" {"selected" if dim and dim.value == d.value else ""}>{d.value.title()}</option>'
        for d in EvalDimension
    )
    domain_opts = "".join(
        f'<option value="{d.value}" {"selected" if dom and dom.value == d.value else ""}>{d.value.title()}</option>'
        for d in Domain
    )

    viewer_qs = f"&viewer={_esc(viewer)}" if viewer else ""
    base_params = f"dim={dim.value if dim else ''}&domain={dom.value if dom else ''}&count={count}{viewer_qs}&lang={lang}"

    cards = ""
    draw_info = ""
    unpaid_html = ""

    draw = db.random_draw(dimension=dim, domain=dom, draw_count=0, viewer_addr=viewer)

    if token_gate and viewer_addr and not token_gate.has_draw_access(viewer_addr):
        fee = token_gate.DRAW_FEE_Q
        unpaid_html = f"""
        <div class="card" style="text-align:center;padding:32px;margin-bottom:20px;">
            <p style="font-size:16px;color:#555;margin-bottom:16px;">{_t("random.cost", lang, fee=fee)}</p>
            <form method="post" action="/web/pay/draw">
                <input type="hidden" name="viewer_addr" value="{_esc(viewer_addr)}">
                <input type="hidden" name="redirect" value="/web/random?{base_params}">
                <input type="text" name="viewer_addr_input" value="{_esc(viewer_addr)}" placeholder="{_t("entry.your_address", lang)}" style="width:260px;margin-bottom:8px;display:block;margin-left:auto;margin-right:auto;">
                <button type="submit" style="font-size:15px;padding:10px 32px;">{_t("random.pay_draw", lang, fee=fee)}</button>
            </form>
        </div>"""
    else:
        draw = db.random_draw(dimension=dim, domain=dom, draw_count=count, viewer_addr=viewer)

    drawn_total = draw.total_drawn + len(draw.entries)
    draw_info = f"""
    <p style="color:#777;margin:12px 0;">
        {_t("random.board", lang)}: <b>{draw.board_name}</b> &mdash;
        {_t("random.drawn_count", lang, drawn=drawn_total, total=draw.total_in_board)} &mdash;
        {_t("random.seed", lang)}: <b>{draw.draw_seed}</b>
    </p>"""

    if draw.entries:
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
            cards += f"""
            <div class="card">
                <h3><a href="/web/entry/{e.combo_id}?lang={lang}">{_esc(e.method_name)} &times; {_esc(e.problem_title)}</a></h3>
                <p style="color:#777;font-size:13px;">Best: <b>{e.best_dimension}</b> = {_score_bar(e.best_score)} | {_t("th.domain", lang)}: {e.problem_domain} | {_t("lb.level", lang)}: {e.method_level}</p>
                <div class="scores">{scores_html}</div>
            </div>"""

    content = f"""
    <form method="get" action="/web/random">
        <select name="dim"><option value="">{_t("lb.all_dimensions", lang)}</option>{dim_opts}</select>
        <select name="domain"><option value="">{_t("lb.all_domains", lang)}</option>{domain_opts}</select>
        <input type="number" name="count" value="{count}" min="1" max="50" style="width:80px;" placeholder="{_t("random.count", lang)}">
        <input type="hidden" name="viewer" value="{_esc(viewer)}">
        <input type="hidden" name="lang" value="{lang}">
        <button type="submit">{_t("random.draw", lang)}</button>
    </form>

    {unpaid_html}
    {draw_info}
    {cards if cards else (f'<div class="empty">{_t("random.no_entries", lang)}</div>' if not unpaid_html else '')}
    {_render_previously_drawn(draw, lang)}
    """
    return _base_page(_t("random.title", lang), content, "random", lang=lang, viewer_addr=viewer_addr)
