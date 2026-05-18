"""Token dashboard page."""
from __future__ import annotations

from ._translation import _t
from ._utils import _esc, _parse_query
from ._layout import _base_page
from src.hub.leaderboard import LeaderboardDB


def render_token_dashboard(db: LeaderboardDB, token_gate=None,
                           viewer_addr: str = "", lang: str = "en",
                           path: str = "") -> str:
    params = _parse_query(path) if path else {}
    msg = params.get("msg", "")
    summary = token_gate.get_viewer_summary(viewer_addr) if token_gate else {
        "address": viewer_addr, "balance": 0, "staked": 0,
        "total_earned": 0, "total_slashed": 0,
        "total_payments": 0, "total_spent": 0, "payments": [],
    }

    payment_rows = ""
    for p in summary.get("payments", []):
        p_combo = _esc(p.get("combo_group_id", "")[:12])
        p_amount = p.get("paid_amount", 0)
        p_time = p.get("paid_at", 0)
        p_analyzer = _esc(p.get("analyzer_addr", "")[:12])
        payment_rows += f"""<tr>
            <td>{p_combo}…</td>
            <td>{p_amount}</td>
            <td>{p_analyzer}…</td>
            <td>{p_time}</td>
        </tr>"""

    content = f"""
    <p style="color:#777;margin-bottom:16px;">{_t("tokens.address_label", lang)}: {_esc(summary['address'])}</p>

    <div class="stats">
        <div class="stat-card"><div class="num">{summary['balance']}</div><div class="label">{_t("tokens.balance_idea", lang)}</div></div>
        <div class="stat-card"><div class="num">{summary['staked']}</div><div class="label">{_t("tokens.staked", lang)}</div></div>
        <div class="stat-card"><div class="num">{summary['total_earned']}</div><div class="label">{_t("tokens.total_earned", lang)}</div></div>
        <div class="stat-card"><div class="num">{summary['total_slashed']}</div><div class="label">{_t("tokens.slashed", lang)}</div></div>
        <div class="stat-card"><div class="num">{summary['total_spent']}</div><div class="label">{_t("tokens.total_spent", lang)}</div></div>
        <div class="stat-card"><div class="num">{summary['total_payments']}</div><div class="label">{_t("tokens.payments", lang)}</div></div>
    </div>

    <form method="post" action="/web/faucet" style="margin-bottom:20px;">
        <input type="hidden" name="viewer_addr" value="{_esc(viewer_addr)}">
        <input type="hidden" name="redirect" value="/web/tokens?viewer={_esc(viewer_addr)}&lang={lang}">
        <button type="submit" style="background:#22c55e;">{_t("tokens.faucet", lang)}</button>
        <span style="font-size:12px;color:#999;margin-left:8px;">{_t("tokens.faucet_hint", lang)}</span>
        {f'<p style="color:#22c55e;font-size:13px;margin:4px 0;">{_t("tokens.faucet_got", lang)}</p>' if msg == "faucet_ok" else ''}
        {f'<p style="color:#ef4444;font-size:13px;margin:4px 0;">{_t("tokens.faucet_limited", lang)}</p>' if msg == "faucet_limited" else ''}
    </form>
    """
    if payment_rows:
        content += f"""
        <h2>{_t("tokens.payment_history", lang)}</h2>
        <table>
        <thead><tr><th>{_t("th.combo", lang)}</th><th>{_t("th.amount", lang)}</th><th>{_t("th.analyzer", lang)}</th><th>{_t("th.paid_at", lang)}</th></tr></thead>
        <tbody>{payment_rows}</tbody>
        </table>
        """
    else:
        content += f'<p style="color:#999;margin:16px 0;">{_t("tokens.no_payments", lang)}</p>'

    return _base_page(_t("tokens.title", lang), content, "tokens", lang=lang, viewer_addr=viewer_addr)
