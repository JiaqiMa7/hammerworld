"""Page layout: CSS, nav, login widget, base page wrapper."""
from __future__ import annotations

from ._translation import _t
from ._utils import _esc

_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f4f6f9; color: #333; line-height: 1.6;
    max-width: 1200px; margin: 0 auto; padding: 0 16px;
}
a { color: #2563eb; text-decoration: none; }
a:hover { text-decoration: underline; }
nav {
    display: flex; gap: 4px; padding: 16px 0; flex-wrap: wrap;
    border-bottom: 1px solid #dde1e6; margin-bottom: 20px;
}
nav a {
    padding: 6px 14px; border-radius: 6px; background: #e8ecf0;
    color: #555; font-size: 14px; transition: background 0.15s, color 0.15s;
}
nav a:hover, nav a.active { background: #2563eb; color: #fff; text-decoration: none; }
h1 { font-size: 22px; color: #1a1a2e; margin-bottom: 16px; }
h2 { font-size: 18px; color: #555; margin: 16px 0 8px; }
.stats { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.stat-card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 16px 24px; text-align: center; min-width: 120px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stat-card .num { font-size: 28px; font-weight: bold; color: #2563eb; }
.stat-card .label { font-size: 13px; color: #777; margin-top: 4px; }
.quick-links { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
.quick-links a, .quick-links span {
    padding: 4px 12px; border-radius: 6px; font-size: 13px;
    background: #e8ecf0; border: 1px solid #dde1e6; color: #555;
    transition: background 0.15s, color 0.15s;
}
.quick-links a:hover { background: #2563eb; color: #fff; text-decoration: none; }
.quick-links .sep { border: none; background: none; color: #bbb; padding: 4px 2px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #eef0f4; font-size: 13px; }
th { background: #f0f3f7; color: #666; font-weight: 600; position: sticky; top: 0; }
tr:hover { background: #f0f4f8; }
.bar-bg { width: 80px; height: 6px; background: #e5e7eb; border-radius: 3px; display: inline-block; vertical-align: middle; margin-right: 4px; }
.bar-fill { height: 100%; border-radius: 3px; }
.bar-high { background: #22c55e; } .bar-mid { background: #f59e0b; } .bar-low { background: #ef4444; }
form { margin-bottom: 20px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
input, select, button {
    background: #fff; border: 1px solid #dde1e6; color: #333;
    padding: 6px 12px; border-radius: 6px; font-size: 14px;
}
input:focus, select:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
button { cursor: pointer; background: #2563eb; border-color: #2563eb; color: #fff; }
button:hover { background: #1d4ed8; }
.pagination { display: flex; gap: 8px; margin: 16px 0; }
.card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 16px; margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.card h3 { font-size: 15px; color: #2563eb; margin-bottom: 8px; }
.card .scores { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.card .score-tag {
    font-size: 12px; padding: 2px 8px; border-radius: 4px;
    background: #e8f0fe; color: #2563eb;
}
.empty { text-align: center; color: #999; padding: 40px; font-size: 15px; }
footer { text-align: center; padding: 20px; color: #999; font-size: 12px; border-top: 1px solid #e5e7eb; margin-top: 30px; }
.dim-label { font-size: 11px; color: #999; }
.lang-toggle {
    margin-left: auto; padding: 6px 16px; border-radius: 6px;
    background: #2563eb; color: #fff; font-size: 13px; font-weight: 500;
    border: 1px solid #2563eb; transition: background 0.15s, opacity 0.15s;
}
.lang-toggle:hover { background: #1d4ed8; border-color: #1d4ed8; color: #fff; text-decoration: none; }
.login-widget { display: inline-flex; align-items: center; gap: 6px; }
.login-input { padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; width: 180px; background: #fff; color: #1f2937; }
.login-btn { padding: 4px 10px; border: 1px solid #6b7280; border-radius: 4px; font-size: 12px; cursor: pointer; background: #f9fafb; color: #374151; text-decoration: none; white-space: nowrap; }
.login-btn:hover { background: #e5e7eb; }
.create-addr-btn { padding: 4px 10px; border: 1px solid #059669; border-radius: 4px; font-size: 12px; cursor: pointer; background: #d1fae5; color: #065f46; text-decoration: none; white-space: nowrap; }
.create-addr-btn:hover { background: #a7f3d0; }
.logout-btn { color: #dc2626; border-color: #dc2626; }
.login-addr { font-size: 12px; color: #2563eb; font-weight: 500; }
.tree-container { margin: 16px 0; }
.tree-node { border-left: 3px solid #2563eb; padding: 8px 12px; margin: 6px 0; background: #f8faff; border-radius: 4px; }
.tree-node.terminal-success { border-left-color: #22c55e; background: #f0fdf4; }
.tree-node.terminal-failure { border-left-color: #ef4444; background: #fef2f2; }
.tree-node.pruned { border-left-color: #9ca3af; background: #f9fafb; }
.node-type-badge { display: inline-block; padding: 1px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }
.node-type-badge.success { background: #dcfce7; color: #166534; }
.node-type-badge.failure { background: #fee2e2; color: #991b1b; }
.node-type-badge.pruned { background: #f3f4f6; color: #4b5563; }
.node-type-badge.normal { background: #e8f0fe; color: #2563eb; }
.tree-child-list { margin-left: 24px; padding-left: 12px; border-left: 1px dashed #d1d5db; }
.tree-child-wrapper { margin: 4px 0; }
.edge-label { display: inline-block; font-size: 11px; color: #6b7280; background: #f3f4f6; padding: 1px 8px; border-radius: 3px; margin: 2px 0; }
.tree-toggle { cursor: pointer; user-select: none; font-size: 12px; color: #6b7280; display: block; margin: 4px 0; }
.tree-toggle::before { content: "[-] "; }
.tree-toggle.collapsed::before { content: "[+] "; }
.tree-collapsible { display: block; }
.tree-toggle.collapsed + input[type=checkbox] + .tree-collapsible { display: none; }
input[type=checkbox]:checked + .tree-collapsible { display: block; }
input[type=checkbox]:not(:checked) + .tree-collapsible { display: none; }

/* --- Agent Chat UI --- */
.chat-container { display: flex; flex-direction: column; gap: 0; height: calc(100vh - 300px); min-height: 400px; margin-bottom: 20px; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; background: #fff; }
.chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; background: #f8fafb; }
.chat-bubble { max-width: 85%; padding: 10px 16px; border-radius: 12px; font-size: 14px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
.chat-bubble.user { align-self: flex-end; background: #2563eb; color: #fff; border-bottom-right-radius: 4px; }
.chat-bubble.agent { align-self: flex-start; background: #f0f4f8; color: #333; border: 1px solid #e5e7eb; border-bottom-left-radius: 4px; }
.chat-bubble.agent pre { background: #e8ecf0; padding: 6px 10px; border-radius: 6px; font-size: 13px; overflow-x: auto; margin: 4px 0; }
.chat-input { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid #e5e7eb; background: #fff; }
.chat-input input { flex: 1; padding: 10px 14px; border: 1px solid #dde1e6; border-radius: 8px; font-size: 14px; }
.chat-input button { padding: 10px 24px; border-radius: 8px; font-size: 14px; }
/* --- Agent page grid: chat + sidebar --- */
.agent-layout { display: grid; grid-template-columns: 1fr 200px; gap: 20px; align-items: start; }
@media (max-width: 768px) { .agent-layout { grid-template-columns: 1fr; } }
.agent-sidebar {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 16px; position: sticky; top: 16px;
}
.agent-sidebar h4 { font-size: 12px; text-transform: uppercase; letter-spacing: .05em; color: #888; margin: 0 0 10px; border-bottom: 1px solid #eef0f4; padding-bottom: 8px; }
.agent-sidebar .sb-addr { font-family: monospace; font-size: 12px; color: #555; word-break: break-all; margin-bottom: 12px; background: #f8fafb; padding: 6px 8px; border-radius: 4px; }
.agent-sidebar .sb-bal { font-size: 24px; font-weight: 700; color: #2563eb; }
.agent-sidebar .sb-stake { font-size: 12px; color: #888; margin-top: 2px; }
.agent-sidebar .sb-label { font-size: 12px; color: #999; margin-bottom: 2px; }

/* --- Category sections --- */
.cat-sections { margin: 4px 0 12px; }
details.feature-guide { margin-bottom: 8px; }
details.feature-guide > summary {
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-weight: 800; font-size: 17px; color: #7c3aed;
    cursor: pointer; padding: 10px 0 10px 14px; user-select: none;
    border-left: 4px solid #7c3aed; margin-bottom: 6px;
    letter-spacing: .02em;
}
details.feature-guide > summary:hover { color: #6d28d9; border-left-color: #6d28d9; }
details.feature-details { margin-bottom: 2px; }
details.feature-details > summary {
    font-weight: 700; font-size: 14px; color: #374151;
    border-left: 3px solid #2563eb; padding-left: 12px;
}
details.feature-details > summary:hover { border-left-color: #1d4ed8; color: #1f2937; }
.cat-row { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 8px 12px; }
.cat-card {
    display: flex; align-items: center; gap: 6px;
    background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 7px 12px; cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
    user-select: none; position: relative;
}
.cat-card:hover {
    transform: translateY(-2px); box-shadow: 0 4px 14px rgba(37,99,235,0.15);
    border-color: #2563eb;
}
.cat-card .cat-icon { font-size: 16px; line-height: 1; }
.cat-card .cat-label { font-size: 13px; color: #444; white-space: nowrap; font-weight: 500; }

/* Inline form inside chat bubbles */
.chat-form-container { margin-top: 12px; padding-top: 12px; border-top: 1px solid #e5e7eb; }
.chat-form-container .inline-form { display: flex; flex-direction: column; gap: 10px; }
.chat-form-container .inline-field label { display: block; font-weight: 600; font-size: 12px; margin-bottom: 3px; color: #555; }
.chat-form-container .inline-field .field-desc { font-weight: 400; color: #999; font-size: 11px; margin-left: 6px; }
.chat-form-container .inline-field select,
.chat-form-container .inline-field input { padding: 6px 10px; border: 1px solid #dde1e6; border-radius: 5px; font-size: 13px; }
.chat-form-container .inline-actions { display: flex; gap: 8px; margin-top: 4px; }
.chat-form-container .inline-actions button { padding: 7px 18px; border-radius: 6px; font-size: 13px; cursor: pointer; border: 1px solid #dde1e6; background: #fff; }
.chat-form-container .inline-actions .btn-primary { background: #2563eb; color: #fff; border-color: #2563eb; font-weight: 600; }

/* Chat container */
.chat-container { flex: 1; }
.chat-messages { min-height: 200px; }
.chat-input button:disabled { opacity: 0.6; cursor: not-allowed; }

/* TRIZ analysis display */
.triz-section {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 12px 16px; margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.triz-section h4 { font-size: 14px; color: #6d28d9; margin-bottom: 8px; }
.triz-config-banner { font-size: 12px; color: #666; margin-bottom: 12px; display: flex; gap: 16px; flex-wrap: wrap; }
.triz-progress { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.triz-pbar { height: 6px; background: #e5e7eb; border-radius: 3px; margin-bottom: 12px; overflow: hidden; }
.triz-pfill { height: 100%; background: #6d28d9; border-radius: 3px; transition: width 0.3s ease; }
.triz-pcount { font-size: 12px; color: #888; margin-bottom: 8px; }
.triz-plist { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 24px; font-size: 13px; }
.triz-pstep { display: flex; align-items: center; padding: 3px 6px; border-radius: 4px; }
.triz-pstep.done { color: #888; }
.triz-picon { width: 20px; text-align: center; margin-right: 6px; }
.triz-pname { flex: 1; }
.triz-ptime { font-size: 11px; color: #aaa; margin-left: 8px; min-width: 40px; text-align: right; }
.triz-table { width: auto; border-collapse: collapse; }
.triz-table td { padding: 3px 12px 3px 0; font-size: 13px; }
.triz-table td:first-child { font-weight: 600; color: #555; width: 60px; }
.nine-windows-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.nine-windows-table td {
    border: 1px solid #dde1e6; padding: 6px 8px; text-align: center;
    min-width: 80px; vertical-align: top;
}
.nine-windows-table tr:last-child td { font-weight: 600; color: #888; font-size: 11px; }
.nine-windows-table .nw-label { font-weight: 600; color: #555; width: 50px; font-size: 11px; }

/* --- Dashboard Mining Panel --- */
.mine-panel {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 16px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.mine-panel h2 { margin-top: 0; font-size: 18px; color: #1a1a2e; }
.mine-form { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
.mine-field { display: flex; flex-direction: column; gap: 4px; }
.mine-field label { font-size: 12px; font-weight: 600; color: #555; }
.mine-field select, .mine-field input { padding: 6px 10px; border: 1px solid #dde1e6; border-radius: 5px; font-size: 13px; min-width: 160px; }
.mine-result { margin-top: 12px; padding: 12px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; }
.mine-result .ok { color: #166534; }
.mine-result .err { color: #991b1b; }
.mine-progress { margin-top: 12px; padding: 12px; background: #f8fafb; border: 1px solid #e5e7eb; border-radius: 6px; color: #555; }

/* --- Bounties Page --- */
.bounty-filters { display: flex; gap: 8px; margin-bottom: 16px; }
.bounty-filters a {
    padding: 4px 14px; border-radius: 6px; font-size: 13px;
    background: #e8ecf0; border: 1px solid #dde1e6; color: #555;
    transition: background 0.15s, color 0.15s;
}
.bounty-filters a:hover, .bounty-filters a.active { background: #2563eb; color: #fff; text-decoration: none; }
.bounty-card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.bounty-card h3 { font-size: 15px; color: #2563eb; margin-bottom: 6px; }
.bounty-card .meta { display: flex; gap: 16px; font-size: 12px; color: #888; margin-bottom: 8px; }
.bounty-card .meta span { display: inline-flex; align-items: center; gap: 4px; }
.bounty-card .desc { font-size: 13px; color: #555; margin-bottom: 8px; }
.bounty-card .status-badge {
    display: inline-block; padding: 2px 10px; border-radius: 4px;
    font-size: 11px; font-weight: 600;
}
.bounty-card .status-badge.open { background: #dcfce7; color: #166534; }
.bounty-card .status-badge.claimed { background: #e8f0fe; color: #2563eb; }
.bounty-card .status-badge.expired { background: #f3f4f6; color: #6b7280; }
.bounty-card .prize { font-size: 18px; font-weight: bold; color: #f59e0b; }

/* --- TRIZ Agent page --- */
.triz-layout { display: grid; grid-template-columns: 1fr 240px; gap: 20px; align-items: start; }
@media (max-width: 768px) { .triz-layout { grid-template-columns: 1fr; } }
.triz-input-area { margin-bottom: 16px; }
.triz-input-area textarea {
    width: 100%; padding: 12px; border: 1px solid #dde1e6; border-radius: 8px;
    font-size: 14px; font-family: inherit; resize: vertical; min-height: 80px;
}
.triz-input-area textarea:focus { outline: none; border-color: #6d28d9; box-shadow: 0 0 0 3px rgba(109,40,217,0.1); }
.triz-controls { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; align-items: center; }
.triz-controls select { padding: 6px 10px; border: 1px solid #dde1e6; border-radius: 5px; font-size: 13px; }
.triz-controls button { padding: 6px 18px; border-radius: 6px; font-size: 13px; font-weight: 600; }
.triz-controls button.primary { background: #6d28d9; border-color: #6d28d9; }
.triz-controls button.primary:hover { background: #5b21b6; }
.triz-sidebar {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 16px; position: sticky; top: 16px;
}
.triz-sidebar h4 { font-size: 12px; text-transform: uppercase; letter-spacing: .05em; color: #888; margin: 0 0 10px; border-bottom: 1px solid #eef0f4; padding-bottom: 8px; }
.triz-sidebar .history-item {
    padding: 8px; border-radius: 6px; font-size: 12px; color: #555;
    cursor: pointer; margin-bottom: 4px; background: #f8fafb; transition: background 0.15s;
}
.triz-sidebar .history-item:hover { background: #e8f0fe; }
.triz-sidebar .history-item .date { font-size: 11px; color: #999; }
.triz-sidebar .action-card {
    padding: 10px; border-radius: 6px; font-size: 12px; color: #555;
    cursor: pointer; margin-bottom: 6px; background: #f8fafb; border: 1px solid #e5e7eb;
    transition: all 0.15s; text-align: center;
}
.triz-sidebar .action-card:hover { background: #eef2ff; border-color: #6d28d9; color: #6d28d9; }
.triz-tabs { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
.triz-tab {
    padding: 5px 14px; border-radius: 6px; font-size: 13px; background: #e8ecf0;
    border: 1px solid transparent; color: #555; cursor: pointer; transition: all 0.15s;
}
.triz-tab.active { background: #6d28d9; color: #fff; border-color: #6d28d9; }
.triz-tab:hover:not(.active) { background: #ddd; }
.triz-tab-content { display: none; }
.triz-tab-content.active { display: block; }
.triz-bounty-form { margin-top: 8px; padding: 12px; background: #f8fafb; border-radius: 8px; border: 1px solid #e5e7eb; }
.triz-bounty-form input { width: 120px; }
"""


def _lang_toggle(lang: str) -> str:
    """Return the HTML link that toggles between English and Chinese."""
    next_lang = "zh" if lang == "en" else "en"
    label = _t("common.lang_toggle", lang)
    return f'<a href="?lang={next_lang}" class="lang-toggle" title="Switch language">{label}</a>'


def _login_widget(viewer_addr: str, lang: str) -> str:
    """Render the login/logout widget for the nav bar."""
    if viewer_addr:
        short = viewer_addr[:8] + "..." + viewer_addr[-4:] if len(viewer_addr) > 14 else viewer_addr
        return (
            f'<span class="login-widget">'
            f'<span class="login-addr" title="{viewer_addr}">{_t("login.logged_in", lang)} {short}</span>'
            f'<a href="/web/logout" class="login-btn logout-btn">{_t("login.logout", lang)}</a>'
            f'</span>'
        )
    else:
        return (
            f'<span class="login-widget">'
            f'<form action="/web/login" method="post" style="display:inline;">'
            f'<input type="hidden" name="redirect" value="">'
            f'<input type="text" name="address" placeholder="{_t("login.placeholder", lang)}" class="login-input">'
            f'<button type="submit" class="login-btn">{_t("login.login", lang)}</button>'
            f'</form>'
            f'<form action="/web/create-address" method="post" style="display:inline;">'
            f'<input type="hidden" name="redirect" value="">'
            f'<button type="submit" class="create-addr-btn">{_t("login.create_address", lang)}</button>'
            f'</form>'
            f'</span>'
        )


def _base_page(title: str, content: str, active_nav: str = "", lang: str = "en",
               viewer_addr: str = "") -> str:
    nav_items = [
        ("/", _t("nav.dashboard", lang), "dashboard"),
        ("/web/leaderboard", _t("nav.leaderboard", lang), "leaderboard"),
        ("/web/search", _t("nav.search", lang), "search"),
        ("/web/random", _t("nav.random_draw", lang), "random"),
        ("/web/agent", _t("agent.title", lang), "agent"),
        ("/web/triz", _t("triz.title", lang), "triz"),
        ("/web/bounties", _t("bounties.title", lang), "bounties"),
        ("/web/my-entries", _t("nav.my_entries", lang), "my-entries"),
        ("/web/peers", _t("nav.peers", lang), "peers"),
        ("/web/tokens", _t("nav.tokens", lang), "tokens"),
        ("/web/math", _t("nav.math_zone", lang), "math"),
        ("/web/collections", _t("nav.collections", lang), "collections"),
        ("/web/buffer", _t("nav.buffer_zone", lang), "buffer"),
        ("/web/submit", _t("nav.submit", lang), "submit"),
    ]
    nav_html = "\n".join(
        f'<a href="{url}?lang={lang}" class="{"active" if key == active_nav else ""}">{label}</a>'
        for url, label, key in nav_items
    )
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)} — {_t("common.home", lang)}</title>
<style>{_CSS}</style>
</head>
<body>
<nav>{nav_html}{_login_widget(viewer_addr, lang)}{_lang_toggle(lang)}</nav>
<h1>{_esc(title)}</h1>
{content}
<footer>{_t("common.footer", lang)}</footer>
</body>
</html>"""
