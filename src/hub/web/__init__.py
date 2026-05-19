"""Server-side HTML rendering for the hub web interface.

Re-exports all public render_* functions from page-based sub-modules
for backwards-compatible imports from server.py.
"""
from __future__ import annotations

from .dashboard import render_dashboard
from .leaderboard import render_leaderboard, render_search, render_random
from .peers import render_peers
from .entry import render_entry, render_combo_group, render_my_entries
from .tokens import render_token_dashboard
from .collections import (
    render_collections,
    render_collection_new,
    render_collection_detail,
    render_collections_mine,
)
from .math import (
    render_math_home,
    render_math_new,
    render_math_problem,
    render_math_method_zone,
    render_math_solution,
    render_math_unlock,
    render_math_tree,
    render_math_tree_node,
    render_math_search,
)
from .submit import render_submit_home, render_submit_method, render_submit_problem, render_submissions
from .buffer import (
    render_buffer_dashboard,
    render_buffer_pending,
    render_buffer_classify,
    render_buffer_submissions,
    render_buffer_submission_detail,
    render_buffer_tokens,
    render_buffer_leaderboard,
)
from .settings import render_settings
from .agent import render_agent_chat
from .triz import render_triz_agent, render_triz_analysis_result_html
from .bounties import render_bounties
from ._components import _entry_table
from ._utils import _parse_query

__all__ = [
    "render_dashboard",
    "render_leaderboard",
    "render_search",
    "render_random",
    "render_peers",
    "render_entry",
    "render_combo_group",
    "render_my_entries",
    "render_token_dashboard",
    "render_collections",
    "render_collection_new",
    "render_collection_detail",
    "render_collections_mine",
    "render_math_home",
    "render_math_new",
    "render_math_problem",
    "render_math_method_zone",
    "render_math_solution",
    "render_math_unlock",
    "render_math_tree",
    "render_math_tree_node",
    "render_math_search",
    "render_submit_home",
    "render_submit_method",
    "render_submit_problem",
    "render_submissions",
    "render_buffer_dashboard",
    "render_buffer_pending",
    "render_buffer_classify",
    "render_buffer_submissions",
    "render_buffer_submission_detail",
    "render_buffer_tokens",
    "render_buffer_leaderboard",
    "render_settings",
    "render_agent_chat",
    "render_triz_agent",
    "render_triz_analysis_result_html",
    "render_bounties",
    "_entry_table",
    "_parse_query",
]
