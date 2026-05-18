"""Shared utility functions for HTML rendering."""
from __future__ import annotations


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _parse_query(path: str) -> dict[str, str]:
    params: dict[str, str] = {}
    if "?" in path:
        qs = path.split("?", 1)[1]
        for pair in qs.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = v
    return params


def _score_bar(score: float, max_score: float = 10.0) -> str:
    pct = min(score / max_score * 100, 100)
    if pct >= 70:
        cls = "bar-high"
    elif pct >= 40:
        cls = "bar-mid"
    else:
        cls = "bar-low"
    return f'<span class="bar-bg"><span class="bar-fill {cls}" style="width:{pct:.0f}%"></span></span>{score:.1f}'
