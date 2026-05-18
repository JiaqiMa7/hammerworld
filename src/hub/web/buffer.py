"""Blockchain Buffer Zone pages — dashboard, classifications, tokens, leaderboard."""
from __future__ import annotations

import json

from ._translation import _t
from ._utils import _esc
from ._layout import _base_page
from src.hub.leaderboard import LeaderboardDB


def render_buffer_dashboard(db: LeaderboardDB, lang: str = "en", viewer_addr: str = "") -> str:
    pending = db.count_buffer_by_status("pending")
    classified = db.count_buffer_by_status("classified")
    disputed = db.count_buffer_by_status("disputed")
    published = db.count_buffer_by_status("published")
    leaderboard = db.get_token_leaderboard(limit=5)

    content = f"""
    <h1>Blockchain Buffer Zone</h1>
    <p style="color:#777;margin-bottom:20px;">
        Submit AI analysis → Community classification → Consensus → Publish to leaderboard
    </p>
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#f59e0b;">{pending}</div>
            <div style="color:#777;">Pending</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#22c55e;">{classified}</div>
            <div style="color:#777;">Classified</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#ef4444;">{disputed}</div>
            <div style="color:#777;">Disputed</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#6366f1;">{published}</div>
            <div style="color:#777;">Published</div>
        </div>
    </div>
    <div style="display:flex;gap:16px;flex-wrap:wrap;">
        <a href="/web/buffer/pending" class="btn" style="padding:10px 20px;background:#2563eb;color:#fff;border-radius:6px;">Classify Pending</a>
        <a href="/web/buffer/tokens" class="btn" style="padding:10px 20px;background:#22c55e;color:#fff;border-radius:6px;">Token Dashboard</a>
        <a href="/web/buffer/leaderboard" class="btn" style="padding:10px 20px;background:#6366f1;color:#fff;border-radius:6px;">Classifier Leaderboard</a>
    </div>
    """
    if leaderboard:
        top_rows = []
        for i, r in enumerate(leaderboard, 1):
            top_rows.append(f"""<tr>
                <td>{i}</td>
                <td>{_esc(r['address'])[:14]}</td>
                <td>{r['balance']}</td>
                <td>{r['correct_classifications']}/{r['total_classifications']}</td>
                <td>{r['consecutive_correct']}</td>
            </tr>""")
        content += f"""
        <h2 style="margin-top:24px;">Top Classifiers</h2>
        <table>
        <thead><tr><th>#</th><th>Address</th><th>Balance</th><th>Accuracy</th><th>Streak</th></tr></thead>
        <tbody>{"".join(top_rows)}</tbody>
        </table>
        """
    return _base_page("Buffer Zone", content, "buffer", lang=lang, viewer_addr=viewer_addr)


def render_buffer_pending(db: LeaderboardDB, path: str, lang: str = "en", viewer_addr: str = "") -> str:
    entries = db.get_pending_buffer_entries()
    if not entries:
        content = '<div class="empty">No pending submissions to classify.</div>'
        return _base_page("Pending Classifications", content, "buffer", lang=lang, viewer_addr=viewer_addr)

    rows = []
    for e in entries:
        analysis_preview = e.get("analysis_text", "")[:100]
        if not analysis_preview:
            try:
                data = json.loads(e["analysis_json"])
                scores = data.get("scores", [])
                if scores:
                    analysis_preview = f"{len(scores)} dimension(s) evaluated"
                else:
                    analysis_preview = "(no analysis text)"
            except (json.JSONDecodeError, KeyError):
                analysis_preview = "(parse error)"
        rows.append(f"""<tr>
            <td>{_esc(e['id'])}</td>
            <td>{_esc(e['method_name'])} × {_esc(e['problem_title'])}</td>
            <td>{_esc(analysis_preview)}</td>
            <td>{_esc(e['submitter'])[:12]}</td>
            <td>{e['classifier_count']}</td>
            <td><a href="/web/buffer/classify/{_esc(e['id'])}">Classify</a></td>
        </tr>""")

    content = f"""
    <h1>Pending Classifications</h1>
    <p style="color:#777;margin-bottom:12px;">{len(entries)} submission(s) awaiting classification</p>
    <table>
    <thead><tr><th>ID</th><th>Combo</th><th>Preview</th><th>Submitter</th><th>Votes</th><th>Action</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page("Pending Classifications", content, "buffer", lang=lang, viewer_addr=viewer_addr)


def render_buffer_classify(db: LeaderboardDB, sub_id: str, path: str, lang: str = "en", viewer_addr: str = "") -> str:
    entry = db.get_buffer_entry(sub_id)
    if entry is None:
        return _base_page("Not Found", '<div class="empty">Submission not found.</div>', "buffer", lang=lang, viewer_addr=viewer_addr)

    classifications = db.get_classifications(sub_id)
    already = [c["classifier_addr"] for c in classifications]

    analysis_text = entry.get("analysis_text", "")
    if not analysis_text:
        try:
            data = json.loads(entry["analysis_json"])
            analysis_text = json.dumps(data, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, KeyError):
            analysis_text = entry["analysis_json"]

    existing_html = ""
    if classifications:
        cls_rows = []
        for c in classifications:
            cls_rows.append(f"""<tr>
                <td>{_esc(c['classifier_addr'])[:14]}</td>
                <td>{_esc(c['domain_label'])}</td>
                <td>{'Yes' if c['is_nsfw'] else 'No'}</td>
                <td>{'Yes' if c['is_spam'] else 'No'}</td>
                <td>{_esc(c.get('notes', ''))[:40]}</td>
            </tr>""")
        existing_html = f"""
        <h2>Existing Classifications ({len(classifications)})</h2>
        <table>
        <thead><tr><th>Classifier</th><th>Domain</th><th>NSFW</th><th>Spam</th><th>Notes</th></tr></thead>
        <tbody>{"".join(cls_rows)}</tbody>
        </table>
        """

    domains = ["medicine", "energy", "physics", "chemistry", "biology", "mathematics",
               "engineering", "computer_science", "agriculture", "environmental",
               "social_science", "business", "education", "art", "philosophy", "other"]
    domain_opts = "\n".join(f'<option value="{d}">{d}</option>' for d in domains)

    content = f"""
    <h1>Classify Submission</h1>
    <div style="background:#fff;padding:16px;border-radius:8px;margin-bottom:16px;">
        <h2>{_esc(entry['method_name'])} × {_esc(entry['problem_title'])}</h2>
        <p><strong>Submitter:</strong> {_esc(entry['submitter'])}</p>
        <p><strong>Status:</strong> {_esc(entry['status'])}</p>
        <p><strong>Votes:</strong> {entry['classifier_count']}</p>
        <details style="margin-top:8px;">
            <summary>Analysis Data</summary>
            <pre style="max-height:400px;overflow-y:auto;background:#f8f9fa;padding:12px;border-radius:4px;font-size:12px;">{_esc(analysis_text)}</pre>
        </details>
    </div>
    {existing_html}
    <form method="POST" action="/web/buffer/classify/{_esc(sub_id)}" style="background:#fff;padding:16px;border-radius:8px;">
        <h2>Submit Classification</h2>
        <p style="color:#777;margin-bottom:12px;">
            Classification requires a stake of 10 IDEA tokens (auto-faucet for new users).
        </p>
        <div style="margin-bottom:12px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">Domain Label:</label>
            <select name="domain" style="width:100%;padding:8px;border:1px solid #dde1e6;border-radius:4px;">
                {domain_opts}
            </select>
        </div>
        <div style="margin-bottom:8px;">
            <label><input type="checkbox" name="nsfw" value="1"> Mark as NSFW</label>
        </div>
        <div style="margin-bottom:8px;">
            <label><input type="checkbox" name="spam" value="1"> Mark as Spam / AI Hallucination</label>
        </div>
        <div style="margin-bottom:12px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">Notes:</label>
            <textarea name="notes" rows="3" style="width:100%;padding:8px;border:1px solid #dde1e6;border-radius:4px;" placeholder="Optional notes..."></textarea>
        </div>
        <div style="margin-bottom:12px;">
            <label style="display:block;font-weight:600;margin-bottom:4px;">Your Address:</label>
            <input type="text" name="address" value="0xCLASSIFIER" style="width:100%;padding:8px;border:1px solid #dde1e6;border-radius:4px;">
        </div>
        <input type="submit" value="Submit Classification" style="padding:10px 24px;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;">
    </form>
    """
    return _base_page(f"Classify {sub_id}", content, "buffer", lang=lang, viewer_addr=viewer_addr)


def render_buffer_submissions(db: LeaderboardDB, address: str, lang: str = "en", viewer_addr: str = "") -> str:
    entries = db.get_buffer_entries_by_submitter(address)
    if not entries:
        content = f'<div class="empty">No submissions from {_esc(address)}.</div>'
        return _base_page("My Submissions", content, "buffer", lang=lang, viewer_addr=viewer_addr)

    rows = []
    status_colors = {"pending": "#f59e0b", "classified": "#22c55e",
                     "published": "#6366f1", "disputed": "#ef4444"}
    for e in entries:
        color = status_colors.get(e["status"], "#777")
        rows.append(f"""<tr>
            <td><a href="/web/buffer/detail/{_esc(e['id'])}">{_esc(e['id'])}</a></td>
            <td>{_esc(e['method_name'])} × {_esc(e['problem_title'])}</td>
            <td style="color:{color};font-weight:600;">{_esc(e['status'])}</td>
            <td>{e['classifier_count']}</td>
        </tr>""")

    content = f"""
    <h1>My Submissions</h1>
    <p style="color:#777;margin-bottom:12px;">Submitter: {_esc(address)}</p>
    <table>
    <thead><tr><th>ID</th><th>Combo</th><th>Status</th><th>Votes</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page("My Submissions", content, "buffer", lang=lang, viewer_addr=viewer_addr)


def render_buffer_submission_detail(db: LeaderboardDB, sub_id: str, lang: str = "en", viewer_addr: str = "") -> str:
    entry = db.get_buffer_entry(sub_id)
    if entry is None:
        return _base_page("Not Found", '<div class="empty">Submission not found.</div>', "buffer", lang=lang, viewer_addr=viewer_addr)

    classifications = db.get_classifications(sub_id)
    cls_rows = []
    for c in classifications:
        match_icon = "✓" if c.get("matched_consensus") else "✗"
        reward = c.get("reward_earned", 0)
        cls_rows.append(f"""<tr>
            <td>{_esc(c['classifier_addr'])[:14]}</td>
            <td>{_esc(c['domain_label'])}</td>
            <td>{'Yes' if c['is_nsfw'] else 'No'}</td>
            <td>{'Yes' if c['is_spam'] else 'No'}</td>
            <td>{match_icon}</td>
            <td>{'+'+str(reward) if reward > 0 else str(reward)}</td>
        </tr>""")

    status_colors = {"pending": "#f59e0b", "classified": "#22c55e",
                     "published": "#6366f1", "disputed": "#ef4444"}
    color = status_colors.get(entry["status"], "#777")

    content = f"""
    <h1>Submission Detail</h1>
    <div style="background:#fff;padding:16px;border-radius:8px;margin-bottom:16px;">
        <table style="width:100%;border:none;">
            <tr><td style="width:150px;font-weight:600;">Submission ID</td><td>{_esc(entry['id'])}</td></tr>
            <tr><td style="font-weight:600;">Method</td><td>{_esc(entry['method_name'])} ({_esc(entry['method_id'])})</td></tr>
            <tr><td style="font-weight:600;">Problem</td><td>{_esc(entry['problem_title'])} ({_esc(entry['problem_id'])})</td></tr>
            <tr><td style="font-weight:600;">Submitter</td><td>{_esc(entry['submitter'])}</td></tr>
            <tr><td style="font-weight:600;">Status</td><td style="color:{color};font-weight:600;">{_esc(entry['status'])}</td></tr>
            <tr><td style="font-weight:600;">Staked</td><td>{entry['staked_amount']} IDEA</td></tr>
            <tr><td style="font-weight:600;">Classifiers</td><td>{entry['classifier_count']}</td></tr>
        </table>
        {f'<p style="margin-top:8px;"><strong>Consensus Domain:</strong> {_esc(entry["consensus_domain"])}</p>' if entry.get("consensus_domain") else ''}
    </div>
    """
    if cls_rows:
        content += f"""
        <h2>Classifications</h2>
        <table>
        <thead><tr><th>Classifier</th><th>Domain</th><th>NSFW</th><th>Spam</th><th>Match</th><th>Reward</th></tr></thead>
        <tbody>{"".join(cls_rows)}</tbody>
        </table>
        """
    return _base_page(f"Submission {sub_id}", content, "buffer", lang=lang, viewer_addr=viewer_addr)


def render_buffer_tokens(db: LeaderboardDB, address: str, lang: str = "en", viewer_addr: str = "") -> str:
    acct = db.get_or_create_account(address)
    stakes = db.get_active_stakes(address)

    stake_rows = []
    for s in stakes:
        stake_rows.append(f"""<tr>
            <td>{s['id']}</td>
            <td>{s['amount']}</td>
            <td>{_esc(s['status'])}</td>
            <td>{_esc(s['submission_id'])[:16] if s.get('submission_id') else ''}</td>
        </tr>""")

    accuracy = 0
    if acct.get("total_classifications", 0) > 0:
        accuracy = acct["correct_classifications"] / acct["total_classifications"] * 100

    content = f"""
    <h1>Token Dashboard</h1>
    <p style="color:#777;margin-bottom:16px;">Address: {_esc(address)}</p>
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#2563eb;">{acct.get('balance', 0)}</div>
            <div style="color:#777;">Balance (IDEA)</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#f59e0b;">{acct.get('staked', 0)}</div>
            <div style="color:#777;">Staked</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#22c55e;">{acct.get('total_earned', 0)}</div>
            <div style="color:#777;">Total Earned</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:32px;font-weight:bold;color:#ef4444;">{acct.get('total_slashed', 0)}</div>
            <div style="color:#777;">Slashed</div>
        </div>
    </div>
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:24px;font-weight:bold;">{acct.get('correct_classifications', 0)}/{acct.get('total_classifications', 0)}</div>
            <div style="color:#777;">Accuracy ({accuracy:.1f}%)</div>
        </div>
        <div class="stat-card" style="flex:1;min-width:120px;background:#fff;padding:16px;border-radius:8px;text-align:center;">
            <div style="font-size:24px;font-weight:bold;">{acct.get('consecutive_correct', 0)}</div>
            <div style="color:#777;">Consecutive Streak</div>
        </div>
    </div>
    """
    if stake_rows:
        content += f"""
        <h2>Active Stakes</h2>
        <table>
        <thead><tr><th>Stake ID</th><th>Amount</th><th>Status</th><th>Submission</th></tr></thead>
        <tbody>{"".join(stake_rows)}</tbody>
        </table>
        """
    return _base_page("Token Dashboard", content, "buffer", lang=lang, viewer_addr=viewer_addr)


def render_buffer_leaderboard(db: LeaderboardDB, lang: str = "en", viewer_addr: str = "") -> str:
    entries = db.get_token_leaderboard(limit=50)
    if not entries:
        content = '<div class="empty">No classifiers yet.</div>'
        return _base_page("Classifier Leaderboard", content, "buffer", lang=lang, viewer_addr=viewer_addr)

    rows = []
    for i, r in enumerate(entries, 1):
        acc = 0
        if r.get("total_classifications", 0) > 0:
            acc = r["correct_classifications"] / r["total_classifications"] * 100
        rows.append(f"""<tr>
            <td>{i}</td>
            <td>{_esc(r['address'])[:14]}</td>
            <td>{r['balance']}</td>
            <td>{r.get('staked', 0)}</td>
            <td>{r['total_earned']}</td>
            <td>{r['correct_classifications']}/{r['total_classifications']} ({acc:.1f}%)</td>
            <td>{r.get('consecutive_correct', 0)}</td>
        </tr>""")

    content = f"""
    <h1>Classifier Leaderboard</h1>
    <p style="color:#777;margin-bottom:12px;">Top 50 classifiers by token balance</p>
    <table>
    <thead><tr><th>#</th><th>Address</th><th>Balance</th><th>Staked</th><th>Earned</th><th>Accuracy</th><th>Streak</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page("Classifier Leaderboard", content, "buffer", lang=lang, viewer_addr=viewer_addr)
