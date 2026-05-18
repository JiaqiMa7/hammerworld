"""Bounties listing page."""
from __future__ import annotations

import time

from ._translation import _t
from ._utils import _esc
from ._layout import _base_page
from src.hub.leaderboard import LeaderboardDB


def render_bounties(db: LeaderboardDB, lang: str = "en",
                    viewer_addr: str = "", filter_status: str = "",
                    token_gate=None) -> str:
    statuses = [
        ("", _t("bounties.all", lang)),
        ("open", _t("bounties.open", lang)),
        ("claimed", _t("bounties.claimed", lang)),
    ]
    filter_links = "".join(
        f'<a href="/web/bounties?lang={lang}{"&status=" + s if s else ""}" '
        f'class="{"active" if s == filter_status else ""}">{label}</a>'
        for s, label in statuses
    )

    status_filter = filter_status if filter_status else None
    bounties = db.get_bounties(status=status_filter)

    if not bounties:
        cards = f'<div class="empty">{_t("bounties.no_bounties", lang)}</div>'
    else:
        cards = ""
        for b in bounties:
            status_cls = b["status"]
            prize = b["prize_pool"]
            desc = _esc(b["problem_description"][:120])
            creator = _esc(b["creator_addr"][:12] + "...")
            created = f'{int((time.time() - (b["created_at"] or time.time())) / 3600)}h ago'
            status_label = {
                "open": _t("bounties.open", lang),
                "claimed": _t("bounties.claimed", lang),
                "expired": _t("bounties.expired", lang),
            }.get(b["status"], b["status"])

            claim_btn = ""
            if b["status"] == "open" and viewer_addr and b["creator_addr"] != viewer_addr:
                pass
            elif b["status"] == "open" and viewer_addr and token_gate:
                if b["creator_addr"] == viewer_addr and b.get("claimant_addr"):
                    claim_btn = f'''
                        <form method="post" action="/web/bounties/claim" style="display:inline;"
                              onsubmit="return confirm('{_t("bounties.claim_confirm", lang, prize=b["prize_pool"], addr=b["claimant_addr"][:12]+"...")}')">
                            <input type="hidden" name="bounty_id" value="{b["id"]}">
                            <input type="hidden" name="claimant_addr" value="{_esc(b["claimant_addr"])}">
                            <button type="submit">{_t("bounties.claim_btn", lang)}</button>
                        </form>'''

            cards += f"""
            <div class="bounty-card">
                <div class="meta">
                    <span class="status-badge {status_cls}">{status_label}</span>
                    <span class="prize">{prize} IDEA</span>
                    <span>{_t('bounties.creator', lang)}: {creator}</span>
                    <span>{created}</span>
                </div>
                <div class="desc">{desc}</div>
                {claim_btn}
            </div>"""

    not_logged = ""
    if not viewer_addr:
        not_logged = f'<p style="color:#999;font-size:13px;">{_t("bounties.not_logged_in", lang)}</p>'

    content = f"""
    <div class="bounty-filters">{filter_links}</div>
    {not_logged}
    {cards}
    """
    return _base_page(_t("bounties.title", lang), content, "bounties", lang=lang,
                      viewer_addr=viewer_addr)
