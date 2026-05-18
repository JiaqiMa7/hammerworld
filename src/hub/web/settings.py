"""Settings page — system configuration."""
from __future__ import annotations

import os

from ._translation import _t
from ._utils import _esc
from ._layout import _base_page


def render_settings(path: str = "", lang: str = "en", viewer_addr: str = "",
                    saved: bool = False, error: str = "") -> str:
    from src.engine.config import HammerConfig
    cfg = HammerConfig.load()

    api_key = cfg.api_key or ""
    api_base = cfg.api_base or ""
    default_model = cfg.get_model("default") or ""
    agent_model = cfg.get_model("agent") or ""
    mining_model = cfg.get_model("mining") or ""
    triz_model = cfg.get_model("triz") or ""
    address = cfg.address or ""

    config_path = os.path.expanduser("~/.hammerworld/config")

    msg_html = ""
    if saved:
        msg_html = f'<div class="success" style="background:#dcfce7;color:#166534;padding:10px 16px;border-radius:6px;margin-bottom:16px;">{_t("settings.saved", lang)}</div>'
    if error:
        msg_html += f'<div class="error" style="background:#fee2e2;color:#991b1b;padding:10px 16px;border-radius:6px;margin-bottom:16px;">{_esc(error)}</div>'

    content = f"""
    <h1>{_t("settings.title", lang)}</h1>
    <p style="color:#777;margin-bottom:16px;">{_t("settings.description", lang)}</p>
    <p style="color:#999;font-size:12px;margin-bottom:20px;">{_t("settings.config_file", lang)}: <code>{_esc(config_path)}</code></p>
    {msg_html}
    <form method="POST" action="/web/settings/save" style="background:#fff;padding:20px;border-radius:10px;border:1px solid #e5e7eb;max-width:640px;">
        <div style="margin-bottom:14px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">{_t("settings.api_key", lang)}</label>
            <input type="text" name="api_key" value="{_esc(api_key)}" style="width:100%;padding:8px 12px;border:1px solid #dde1e6;border-radius:6px;font-family:monospace;font-size:13px;" placeholder="sk-...">
        </div>
        <div style="margin-bottom:14px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">{_t("settings.api_base", lang)}</label>
            <input type="text" name="api_base" value="{_esc(api_base)}" style="width:100%;padding:8px 12px;border:1px solid #dde1e6;border-radius:6px;font-family:monospace;font-size:13px;" placeholder="https://api.openai.com/v1">
        </div>
        <div style="margin-bottom:14px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">{_t("settings.default_model", lang)}</label>
            <input type="text" name="model" value="{_esc(default_model)}" style="width:100%;padding:8px 12px;border:1px solid #dde1e6;border-radius:6px;font-size:13px;" placeholder="gpt-4o">
        </div>
        <div style="margin-bottom:14px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">{_t("settings.agent_model", lang)}</label>
            <input type="text" name="agent_model" value="{_esc(agent_model)}" style="width:100%;padding:8px 12px;border:1px solid #dde1e6;border-radius:6px;font-size:13px;" placeholder="(uses default if empty)">
        </div>
        <div style="margin-bottom:14px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">{_t("settings.mining_model", lang)}</label>
            <input type="text" name="mining_model" value="{_esc(mining_model)}" style="width:100%;padding:8px 12px;border:1px solid #dde1e6;border-radius:6px;font-size:13px;" placeholder="(uses default if empty)">
        </div>
        <div style="margin-bottom:14px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">{_t("settings.triz_model", lang)}</label>
            <input type="text" name="triz_model" value="{_esc(triz_model)}" style="width:100%;padding:8px 12px;border:1px solid #dde1e6;border-radius:6px;font-size:13px;" placeholder="(uses default if empty)">
        </div>
        <div style="margin-bottom:20px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">{_t("settings.address", lang)}</label>
            <input type="text" name="address" value="{_esc(address)}" style="width:100%;padding:8px 12px;border:1px solid #dde1e6;border-radius:6px;font-family:monospace;font-size:13px;" placeholder="0x...">
        </div>
        <input type="submit" value="{_t("settings.save", lang)}" style="padding:10px 28px;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;font-weight:600;">
    </form>
    """
    return _base_page(_t("settings.title", lang), content, "settings", lang=lang, viewer_addr=viewer_addr)
