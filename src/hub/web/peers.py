"""Peers page — connected hubs."""
from __future__ import annotations

import time

from ._translation import _t
from ._utils import _esc
from ._layout import _base_page
from src.hub.peer import PeerManager


def render_peers(pm: PeerManager, lang: str = "en", viewer_addr: str = "") -> str:
    peers = pm.get_peers()
    now = time.time()

    rows = []
    for i, p in enumerate(peers):
        ago = int(now - p.last_seen)
        ago_str = _t("peers.s_ago", lang, n=ago) if ago < 60 else _t("peers.m_ago", lang, n=ago // 60)
        rows.append(
            f"<tr><td>{i + 1}</td><td>{p.peer_id}</td>"
            f"<td>{p.address}:{p.port}</td><td>{ago_str}</td></tr>"
        )

    content = f"""
    <div class="stats">
        <div class="stat-card"><div class="num">{len(peers)}</div><div class="label">{_t("peers.connected", lang)}</div></div>
        <div class="stat-card"><div class="num">{pm.peer_id[:12]}...</div><div class="label">{_t("peers.this_hub", lang)}</div></div>
        <div class="stat-card"><div class="num">{pm.port}</div><div class="label">{_t("peers.port", lang)}</div></div>
    </div>
    <table>
    <thead><tr><th>{_t("th.rank", lang)}</th><th>{_t("th.peer_id", lang)}</th><th>{_t("th.address", lang)}</th><th>{_t("th.last_seen", lang)}</th></tr></thead>
    <tbody>{"".join(rows) if rows else f'<tr><td colspan="4" class="empty">{_t("peers.no_peers", lang)}</td></tr>'}</tbody>
    </table>
    """
    return _base_page(_t("peers.title", lang), content, "peers", lang=lang, viewer_addr=viewer_addr)
