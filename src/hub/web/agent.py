"""Agent Assistant Chat UI page."""
from __future__ import annotations

import json
from typing import Optional

from ._translation import _T, _t
from ._utils import _esc
from ._layout import _base_page
from src.hub.leaderboard import LeaderboardDB
from src.hub.peer import PeerManager


def _agent_category_sections(lang: str = "en") -> str:
    tip_field = f"tip_{lang}"

    categories = [
        ("agent.cat_explore", [
            ("🏆", "agent.card_lb", "show leaderboard"),
            ("🔍", "agent.card_search", "search AI"),
            ("🎲", "agent.card_draw", "draw 3 entries"),
            ("📄", "agent.card_detail", "view combo_xxx"),
        ]),
        ("agent.cat_tokens", [
            ("🎁", "agent.card_faucet", "get free tokens"),
            ("🔓", "agent.card_payview", "pay to view combo_xxx"),
            ("📊", "agent.card_paylb", "unlock leaderboard"),
            ("🎲", "agent.card_paydraw", "pay for draw"),
        ]),
        ("agent.cat_earn", [
            ("⛏️", "agent.card_mine", "start mining"),
            ("🗳️", "agent.card_bufclass", "classify buffer submissions"),
        ]),
        ("agent.cat_contribute", [
            ("📝", "agent.card_submit_m", "submit method"),
            ("❓", "agent.card_submit_p", "submit problem"),
            ("⭐", "agent.card_rate", "rate combo_xxx 5"),
            ("📚", "agent.card_collections", "collections"),
        ]),
        ("agent.cat_zones", [
            ("🧮", "agent.card_math", "math problems"),
            ("📋", "agent.card_buffer", "buffer status"),
            ("🔗", "agent.card_peers", "show peers"),
            ("⚙️", "agent.card_settings", "show settings"),
        ]),
    ]

    sections = []
    for title_key, cards in categories:
        card_html = ""
        for emoji, name_key, example in cards:
            tip = _t(name_key, lang)
            entry = _T.get(name_key, {})
            tooltip = entry.get(tip_field, "")
            escaped_example = example.replace("'", "&#39;")
            card_html += (
                f'<div class="cat-card" title="{_esc(tooltip)}" '
                f'onclick="document.getElementById(\'chat-input\').value=\'{escaped_example}\';'
                f'document.getElementById(\'chat-form\').requestSubmit();">'
                f'<span class="cat-icon">{emoji}</span>'
                f'<span class="cat-label">{_esc(_t(name_key, lang))}</span>'
                f'</div>'
            )
        sections.append(
            f'<details class="feature-details" open>'
            f'<summary class="cat-title">{_t(title_key, lang)}</summary>'
            f'<div class="cat-row">{card_html}</div>'
            f'</details>'
        )

    return f'<div class="cat-sections">{"".join(sections)}</div>'


def render_agent_chat(
    db: LeaderboardDB,
    path: str,
    viewer_addr: str = "",
    token_gate=None,
    peer_manager: Optional[PeerManager] = None,
    lang: str = "en",
    conversation: list[dict] | None = None,
) -> str:
    from src.hub.agent_assistant import AgentAssistant

    conversation = conversation or []

    if not conversation:
        agent = AgentAssistant(db, token_gate, peer_manager)
        welcome = agent._t("agent.welcome", lang)
        conversation = [{"role": "agent", "text": welcome}]

    bubbles = ""
    for m in conversation:
        role = m.get("role", "agent")
        text = _esc(m.get("text", ""))
        if role == "user":
            bubbles += f'<div class="chat-bubble user">{text}</div>'
        else:
            formatted = text.replace("**", "<strong>", 1)
            if "**" in text:
                formatted = formatted.replace("**", "</strong>", 1)
            bubbles += f'<div class="chat-bubble agent">{formatted}</div>'

    conv_json = json.dumps(conversation, ensure_ascii=False)

    sending_text = _t("agent.sending", lang)

    has_addr = bool(viewer_addr and len(viewer_addr) > 10)
    sidebar_html = ""
    if has_addr:
        short_addr = viewer_addr[:10] + "..." + viewer_addr[-4:]
        bal = 0; staked = 0
        if token_gate:
            try:
                s = token_gate.get_viewer_summary(viewer_addr)
                bal = s.get("balance", 0)
                staked = s.get("staked", 0)
            except Exception:
                pass
        sidebar_html = f"""
        <div class="agent-sidebar" id="agent-sidebar">
            <h4>{_esc(_t('agent.sb_address', lang))}</h4>
            <div class="sb-addr" title="{_esc(viewer_addr)}">{_esc(short_addr)}</div>
            <h4>{_esc(_t('agent.sb_balance', lang))}</h4>
            <div class="sb-bal" id="sb-balance">{bal}</div>
            <div class="sb-stake" id="sb-staked">{_esc(_t('agent.sb_staked', lang))}: {staked}</div>
        </div>"""
    elif viewer_addr:
        sidebar_html = f"""
        <div class="agent-sidebar" id="agent-sidebar">
            <h4>{_esc(_t('agent.sb_address', lang))}</h4>
            <div class="sb-addr">{_esc(viewer_addr)}</div>
            <div class="sb-bal" id="sb-balance">-</div>
        </div>"""
    else:
        sidebar_html = f"""
        <div class="agent-sidebar" id="agent-sidebar">
            <div class="sb-addr" style="color:#999;">{_esc(_t('agent.sb_not_logged', lang))}</div>
        </div>"""

    content = f"""
    <div class="agent-layout">
    <div class="agent-main">
    <div style="margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:14px;color:#777;">{_t("agent.intro_desc", lang)}</span>
    </div>
    <details class="feature-guide" open>
        <summary class="guide-title">{_t("agent.intro_title", lang)}</summary>
        {_agent_category_sections(lang)}
    </details>

    <div class="chat-container">
        <div class="chat-messages" id="chat-messages">
            {bubbles}
        </div>
        <form class="chat-input" id="chat-form">
            <input type="hidden" name="conversation" id="conv-field" value=\'{conv_json}\'>
            <input type="hidden" name="lang" value="{lang}">
            <input type="text" id="chat-input" name="message"
                   placeholder="{_t("agent.placeholder", lang)}" autofocus autocomplete="off">
            <button type="submit" id="send-btn">{_t("agent.send", lang)}</button>
        </form>
    </div>
    </div>
    {sidebar_html}
    </div>
    <script>
    (function() {{
        var form = document.getElementById('chat-form');
        var input = document.getElementById('chat-input');
        var convField = document.getElementById('conv-field');
        var msgs = document.getElementById('chat-messages');
        var btn = document.getElementById('send-btn');
        var sidebar = document.getElementById('agent-sidebar');
        var sending = '{sending_text}';

        function scrollBottom() {{
            if (msgs) msgs.scrollTop = msgs.scrollHeight;
        }}

        function addBubble(role, text, formHtml) {{
            var div = document.createElement('div');
            div.className = 'chat-bubble ' + role;
            div.textContent = text;
            if (formHtml) {{
                var formContainer = document.createElement('div');
                formContainer.className = 'chat-form-container';
                formContainer.innerHTML = formHtml;
                div.appendChild(formContainer);
            }}
            msgs.appendChild(div);
            scrollBottom();
        }}

        function sendMessage(msg) {{
            var conv = convField.value;
            addBubble('user', msg);
            input.value = '';
            btn.disabled = true;
            btn.textContent = sending;

            fetch('/web/agent/chat/json', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: 'message=' + encodeURIComponent(msg) + '&lang={lang}&conversation=' + encodeURIComponent(conv)
            }})
            .then(function(r) {{ return r.json(); }})
            .then(function(data) {{
                if (data.reply) addBubble('agent', data.reply, data.form);
                convField.value = JSON.stringify(data.conversation || []);
                btn.disabled = false;
                btn.textContent = '{_t("agent.send", lang)}';
                input.focus();
                updateSidebar();
            }})
            .catch(function(err) {{
                addBubble('agent', 'Error: ' + err.message);
                btn.disabled = false;
                btn.textContent = '{_t("agent.send", lang)}';
                input.focus();
                updateSidebar();
            }});
        }}

        form.addEventListener('submit', function(e) {{
            e.preventDefault();
            var msg = input.value.trim();
            if (!msg) return;
            sendMessage(msg);
        }});

        window.submitMineForm = function(event) {{
            event.preventDefault();
            var f = document.getElementById('mine-custom-form');
            var params = new URLSearchParams();
            params.append('domain', f.elements['domain'].value);
            params.append('level', f.elements['level'].value);
            params.append('batch_size', f.elements['batch_size'].value);
            params.append('model', f.elements['model'].value);
            params.append('lang', '{lang}');
            params.append('message', 'start mining (custom config)');

            var conv = convField.value;
            btn.disabled = true;
            btn.textContent = sending;

            fetch('/web/agent/mine/run', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: params.toString()
            }})
            .then(function(r) {{ return r.json(); }})
            .then(function(data) {{
                if (data.reply) addBubble('agent', data.reply);
                convField.value = JSON.stringify(data.conversation || []);
                btn.disabled = false;
                btn.textContent = '{_t("agent.send", lang)}';
                input.focus();
                updateSidebar();
            }})
            .catch(function(err) {{
                addBubble('agent', 'Error: ' + err.message);
                btn.disabled = false;
                btn.textContent = '{_t("agent.send", lang)}';
                updateSidebar();
            }});
            return false;
        }};

        function updateSidebar() {{
            if (!sidebar) return;
            fetch('/web/agent/balance/json', {{method: 'POST'}})
            .then(function(r) {{ return r.json(); }})
            .then(function(d) {{
                var balEl = document.getElementById('sb-balance');
                var stkEl = document.getElementById('sb-staked');
                if (balEl && d.balance !== undefined) balEl.textContent = d.balance;
                if (stkEl && d.staked !== undefined) stkEl.textContent = '{_t("agent.sb_staked", lang)}: ' + d.staked;
            }})
            .catch(function() {{}});
        }}

        scrollBottom();
        updateSidebar();
    }})();
    </script>
    """
    return _base_page(_t("agent.title", lang), content, "agent", lang=lang,
                      viewer_addr=viewer_addr)
