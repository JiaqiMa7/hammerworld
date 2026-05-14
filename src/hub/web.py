"""Server-side HTML rendering for the hub web interface."""
from __future__ import annotations

import json
import os
import time
from typing import Optional

from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry
from src.hub.peer import PeerManager
from src.engine.models import EvalDimension, Domain, MethodLevel


# ------------------------------------------------------------------
# Translation System (EN / ZH)
# ------------------------------------------------------------------

_T = {
    # Nav
    "nav.dashboard":         {"en": "Dashboard",          "zh": "仪表板"},
    "nav.leaderboard":       {"en": "Leaderboard",        "zh": "排行榜"},
    "nav.search":            {"en": "Search",             "zh": "搜索"},
    "nav.random_draw":       {"en": "Random Draw",        "zh": "随机抽取"},
    "nav.peers":             {"en": "Peers",              "zh": "节点"},
    "nav.tokens":            {"en": "Tokens",             "zh": "代币"},
    "nav.math_zone":         {"en": "Math Zone",          "zh": "数学区"},
    "nav.collections":       {"en": "Collections",        "zh": "合集"},
    "nav.buffer_zone":       {"en": "Buffer Zone",        "zh": "缓冲区"},
    "nav.submit":            {"en": "Submit",             "zh": "提交"},
    "nav.my_entries":        {"en": "My Entries",         "zh": "我的挖掘"},
    "my_entries.title":      {"en": "My Mined Entries",   "zh": "我的挖掘记录"},
    "my_entries.empty":      {"en": "No mined entries yet. Try asking the agent to \"start mining\"!", "zh": "暂无挖掘记录。试试让 AI 助手「开始挖矿」！"},
    "my_entries.count":      {"en": "{n} entries",        "zh": "共 {n} 条"},
    "my_entries.view":       {"en": "View",               "zh": "查看"},
    # Common
    "common.home":           {"en": "Idea Mining Network", "zh": "创意挖矿网络"},
    "common.footer":         {"en": "Idea Mining Network — Phase 2 MVP", "zh": "创意挖矿网络 — 第二阶段 MVP"},
    "common.lang_toggle":    {"en": "中文",                "zh": "EN"},
    "common.no_entries":     {"en": "No entries found.",   "zh": "暂无条目。"},
    "common.not_found":      {"en": "Entry not found.",    "zh": "条目未找到。"},
    "common.no_results":     {"en": "No results for",      "zh": "未找到结果："},
    "common.enter_search":   {"en": "Enter a search term to find combinations.", "zh": "输入关键词搜索组合。"},
    "common.unknown":        {"en": "Unknown",             "zh": "未知"},
    "common.anonymous":      {"en": "anonymous",           "zh": "匿名"},
    "common.back":            {"en": "Back",                "zh": "返回"},
    "common.none":           {"en": "None",                "zh": "无"},
    # Dashboard
    "dash.title":            {"en": "Dashboard",           "zh": "仪表板"},
    "dash.entries":          {"en": "Entries",             "zh": "条目"},
    "dash.peers":            {"en": "Peers",               "zh": "节点"},
    "dash.uptime":           {"en": "Uptime",              "zh": "运行时间"},
    "dash.by_dimension":     {"en": "By Dimension",        "zh": "按维度"},
    "dash.by_domain":        {"en": "By Domain",           "zh": "按领域"},
    "dash.top_entries":      {"en": "Top Entries",         "zh": "热门条目"},
    # Leaderboard
    "lb.title":              {"en": "Leaderboard",         "zh": "排行榜"},
    "lb.showing":            {"en": "Showing",             "zh": "筛选"},
    "lb.results":            {"en": "results",             "zh": "条结果"},
    "lb.offset":             {"en": "offset",              "zh": "偏移"},
    "lb.all_dimensions":     {"en": "All Dimensions",      "zh": "全部维度"},
    "lb.all_domains":        {"en": "All Domains",         "zh": "全部领域"},
    "lb.filter":             {"en": "Filter",              "zh": "筛选"},
    "lb.previous":           {"en": "Previous",            "zh": "上一页"},
    "lb.next":               {"en": "Next",                "zh": "下一页"},
    "lb.dimension":          {"en": "Dimension",           "zh": "维度"},
    "lb.domain":             {"en": "Domain",              "zh": "领域"},
    "lb.level":              {"en": "Level",               "zh": "等级"},
    "lb.locked":             {"en": "This leaderboard is locked.", "zh": "此排行榜已锁定。"},
    "lb.pay_unlock":         {"en": "Pay {fee} IDEA to Unlock (24h)", "zh": "支付 {fee} IDEA 解锁 (24小时)"},
    "lb.unlock":             {"en": "Unlock",              "zh": "解锁"},
    # Table headers
    "th.rank":               {"en": "#",                   "zh": "#"},
    "th.score":              {"en": "Score",               "zh": "评分"},
    "th.dim":                {"en": "Dim",                 "zh": "维度"},
    "th.best_dim":           {"en": "Best Dim",            "zh": "最佳维度"},
    "th.created":            {"en": "Created",             "zh": "创建时间"},
    "th.method":             {"en": "Method",              "zh": "方法"},
    "th.problem":            {"en": "Problem",             "zh": "问题"},
    "th.domain":             {"en": "Domain",              "zh": "领域"},
    "th.miner":              {"en": "Miner",               "zh": "矿工"},
    "th.peer_id":            {"en": "Peer ID",             "zh": "节点 ID"},
    "th.address":            {"en": "Address",             "zh": "地址"},
    "th.last_seen":          {"en": "Last Seen",           "zh": "最后在线"},
    "th.action":             {"en": "Action",              "zh": "操作"},
    "th.status":             {"en": "Status",              "zh": "状态"},
    "th.type":               {"en": "Type",                "zh": "类型"},
    "th.preview":            {"en": "Preview",             "zh": "预览"},
    "th.submitter":          {"en": "Submitter",           "zh": "提交者"},
    "th.user":               {"en": "User",                "zh": "用户"},
    "th.steps":              {"en": "Steps",               "zh": "步骤"},
    "th.content":            {"en": "Content",             "zh": "内容"},
    "th.verified":           {"en": "Verified",            "zh": "已验证"},
    "th.notes":              {"en": "Notes",               "zh": "备注"},
    "th.accuracy":           {"en": "Accuracy",            "zh": "准确率"},
    "th.streak":             {"en": "Streak",              "zh": "连击"},
    "th.amount":             {"en": "Amount",              "zh": "金额"},
    "th.votes":              {"en": "Votes",               "zh": "票数"},
    "th.classifier":         {"en": "Classifier",          "zh": "分类员"},
    "th.nsfw":               {"en": "NSFW",                "zh": "违规"},
    "th.spam":               {"en": "Spam",                "zh": "垃圾"},
    "th.match":              {"en": "Match",               "zh": "匹配"},
    "th.reward":             {"en": "Reward",              "zh": "奖励"},
    "th.balance":            {"en": "Balance",             "zh": "余额"},
    "th.staked":             {"en": "Staked",              "zh": "质押"},
    "th.earned":             {"en": "Earned",              "zh": "已赚"},
    "th.combo":              {"en": "Combo",               "zh": "组合"},
    "th.paid_at":            {"en": "Paid At",             "zh": "支付时间"},
    "th.analyzer":           {"en": "Analyzer",            "zh": "分析者"},
    "th.description":        {"en": "Description",         "zh": "描述"},
    "th.access":             {"en": "Access",              "zh": "访问"},
    "th.top_step":           {"en": "Top Step",            "zh": "最高步骤"},
    "th.solutions":          {"en": "Solutions",           "zh": "解法"},
    "th.max_correct_step":   {"en": "Max Correct Step",    "zh": "最大正确步骤"},
    # Search
    "search.title":          {"en": "Search",              "zh": "搜索"},
    "search.placeholder":    {"en": "Search methods, problems, domains...", "zh": "搜索方法、问题、领域..."},
    "search.button":         {"en": "Search",              "zh": "搜索"},
    # Random Draw
    "random.title":          {"en": "Random Draw",         "zh": "随机抽取"},
    "random.draw":           {"en": "Draw",                "zh": "抽取"},
    "random.count":          {"en": "Count",               "zh": "数量"},
    "random.board":          {"en": "Board",               "zh": "面板"},
    "random.available":      {"en": "Available",           "zh": "可用"},
    "random.seed":           {"en": "Seed",                "zh": "种子"},
    "random.no_entries":     {"en": "No entries available for this board.", "zh": "此面板暂无条目。"},
    "random.drawn_count":    {"en": "Drawn: {drawn}/{total}", "zh": "已抽取: {drawn}/{total}"},
    "random.drawn_before":   {"en": "Previously Drawn", "zh": "已抽取过的 Idea"},
    "random.no_drawn_yet":   {"en": "You haven't drawn any entries from this board yet.", "zh": "你尚未从此面板抽取过条目。"},
    "random.cost":           {"en": "Random draw costs {fee} IDEA per use.", "zh": "随机抽取每次消耗 {fee} IDEA。"},
    "random.pay_draw":       {"en": "Pay {fee} IDEA to Draw", "zh": "支付 {fee} IDEA 抽取"},
    # Peers
    "peers.title":           {"en": "Peers",               "zh": "节点"},
    "peers.connected":       {"en": "Connected Peers",     "zh": "已连接节点"},
    "peers.this_hub":        {"en": "This Hub",            "zh": "本 Hub"},
    "peers.port":            {"en": "Port",                "zh": "端口"},
    "peers.no_peers":        {"en": "No peers connected. Start another hub with --bootstrap to join.", "zh": "暂无节点连接。用 --bootstrap 启动另一个 hub 加入。"},
    "peers.s_ago":            {"en": "{n}s ago",            "zh": "{n}秒前"},
    "peers.m_ago":            {"en": "{n}m ago",            "zh": "{n}分钟前"},
    # Entry detail
    "entry.title":           {"en": "Entry Detail",        "zh": "条目详情"},
    "entry.combo_id":        {"en": "Combo ID",            "zh": "组合 ID"},
    "entry.method":          {"en": "Method",              "zh": "方法"},
    "entry.method_domain":   {"en": "Method Domain",       "zh": "方法领域"},
    "entry.method_level":    {"en": "Method Level",        "zh": "方法等级"},
    "entry.problem_title":   {"en": "Problem",             "zh": "问题"},
    "entry.problem_domain":  {"en": "Problem Domain",      "zh": "问题领域"},
    "entry.best_dimension":  {"en": "Best Dimension",      "zh": "最佳维度"},
    "entry.best_score":      {"en": "Best Score",          "zh": "最佳评分"},
    "entry.miner":           {"en": "Miner",               "zh": "矿工"},
    "entry.ai_analysis":     {"en": "AI Analysis",         "zh": "AI 分析"},
    "entry.scores":          {"en": "Scores",              "zh": "评分"},
    "entry.ratings":         {"en": "Ratings",             "zh": "评价"},
    "entry.no_analysis":     {"en": "No analysis text available.", "zh": "暂无分析文本。"},
    "entry.paywalled":       {"en": "AI analysis is paywalled.", "zh": "AI 分析需付费查看。"},
    "entry.pay_view":        {"en": "Pay {fee} IDEA to View Analysis", "zh": "支付 {fee} IDEA 查看分析"},
    "entry.no_ratings":      {"en": "No ratings yet.",     "zh": "暂无评价。"},
    "entry.avg_rating":      {"en": "Avg Rating",          "zh": "平均评分"},
    "entry.from_n_viewers":  {"en": "from {n} viewer(s)",  "zh": "来自 {n} 位观众"},
    "entry.rate_placeholder": {"en": "Rate...",            "zh": "评分..."},
    "entry.excellent":       {"en": "Excellent",           "zh": "优秀"},
    "entry.good":            {"en": "Good",                "zh": "好"},
    "entry.average":         {"en": "Average",             "zh": "一般"},
    "entry.poor":            {"en": "Poor",                "zh": "差"},
    "entry.terrible":        {"en": "Terrible",            "zh": "很差"},
    "entry.optional_comment": {"en": "Optional comment",   "zh": "评论（可选）"},
    "entry.submit_rating":   {"en": "Submit Rating",       "zh": "提交评价"},
    "entry.your_address":    {"en": "Your address (0x...)", "zh": "你的地址 (0x...)"},
    # Tokens
    "tokens.title":          {"en": "Tokens",              "zh": "代币"},
    "tokens.address_label":  {"en": "Address",             "zh": "地址"},
    "tokens.balance_idea":   {"en": "Balance (IDEA)",      "zh": "余额 (IDEA)"},
    "tokens.staked":         {"en": "Staked",              "zh": "已质押"},
    "tokens.total_earned":   {"en": "Total Earned",        "zh": "累计赚取"},
    "tokens.slashed":        {"en": "Slashed",             "zh": "被罚没"},
    "tokens.total_spent":    {"en": "Total Spent",         "zh": "累计花费"},
    "tokens.payments":       {"en": "Payments",            "zh": "支付次数"},
    "tokens.faucet":         {"en": "Get Free Tokens (Faucet)", "zh": "领取免费代币"},
    "tokens.faucet_hint":    {"en": "+100 IDEA for new users", "zh": "新用户 +100 IDEA"},
    "tokens.faucet_limited": {"en": "Faucet rate-limited: 1 hour cooldown or max 10 claims.", "zh": "已限流：每小时只能领取 1 次，最多 10 次。"},
    "tokens.faucet_got":     {"en": "Faucet: +100 IDEA received.", "zh": "已领取 100 IDEA。"},
    "tokens.payment_history": {"en": "Payment History",    "zh": "支付历史"},
    "tokens.no_payments":    {"en": "No payments yet.",    "zh": "暂无支付记录。"},
    # Submissions
    "submit.title":          {"en": "Community Submit",    "zh": "社区提交"},
    "submit.home_title":     {"en": "Community Submit",    "zh": "社区提交"},
    "submit.home_desc":      {"en": "All submissions are reviewed before joining the active matrix.", "zh": "所有提交在加入活跃矩阵前需经过审核。"},
    "submit.method.card":    {"en": "Submit a new thinking method to the matrix", "zh": "提交一个新的思维方法到矩阵"},
    "submit.problem.card":   {"en": "Submit an unsolved problem for the matrix", "zh": "提交一个未解决的问题到矩阵"},
    "submit.method_btn":     {"en": "Submit Method",       "zh": "提交方法"},
    "submit.problem_btn":    {"en": "Submit Problem",      "zh": "提交问题"},
    "submit.method_title":   {"en": "Submit Method",       "zh": "提交方法"},
    "submit.problem_title":  {"en": "Submit Problem",      "zh": "提交问题"},
    "submit.name":           {"en": "Name",                "zh": "名称"},
    "submit.domain":         {"en": "Domain",              "zh": "领域"},
    "submit.level":          {"en": "Level",               "zh": "等级"},
    "submit.description":    {"en": "Description",         "zh": "描述"},
    "submit.examples":       {"en": "Examples",            "zh": "示例"},
    "submit.prerequisites":  {"en": "Prerequisites",       "zh": "前置条件"},
    "submit.compatible_with": {"en": "Compatible With",    "zh": "兼容方法"},
    "submit.submitter":      {"en": "Submitter",           "zh": "提交者"},
    "submit.title_label":    {"en": "Title",               "zh": "标题"},
    "submit.maturity":       {"en": "Maturity",            "zh": "成熟度"},
    "submit.constraints":    {"en": "Constraint Types",    "zh": "约束类型"},
    "submit.create_btn":     {"en": "Submit Method",       "zh": "提交方法"},
    "submit.problem_btn2":   {"en": "Submit Problem",      "zh": "提交问题"},
    "submit.pending_title":  {"en": "Submissions",         "zh": "待审核提交"},
    "submit.pending_count":  {"en": "{n} pending submission(s)", "zh": "{n} 条待审核"},
    "submit.approve":        {"en": "Approve",             "zh": "通过"},
    "submit.reject":         {"en": "Reject",              "zh": "拒绝"},
    "submit.no_pending":     {"en": "No pending submissions.", "zh": "暂无待审核提交。"},
    "submit.placeholder":    {"en": "comma-separated",     "zh": "逗号分隔"},
    "submit.placeholder_ids": {"en": "comma-separated method IDs", "zh": "逗号分隔方法 ID"},
    "submit.placeholder_examples": {"en": "comma-separated", "zh": "逗号分隔"},
    # Collections
    "collections.title":     {"en": "Collections",          "zh": "合集"},
    "collections.methods":   {"en": "Methods",              "zh": "方法"},
    "collections.problems":  {"en": "Problems",             "zh": "问题"},
    "collections.stars":     {"en": "Stars",                "zh": "收藏"},
    "collections.imports":   {"en": "Imports",              "zh": "导入"},
    "collections.newest":    {"en": "Newest",               "zh": "最新"},
    "collections.import":    {"en": "import",               "zh": "次导入"},
    "collections.imports_label": {"en": "imports",          "zh": "次导入"},
    "collections.items":     {"en": "items",                "zh": "项"},
    "collections.by":        {"en": "by",                   "zh": "作者"},
    "collections.my":        {"en": "My Collections",       "zh": "我的合集"},
    "collections.all":       {"en": "All Collections",      "zh": "全部合集"},
    "collections.new":       {"en": "New Collection",       "zh": "新建合集"},
    "collections.create":    {"en": "Create Collection",    "zh": "创建合集"},
    "collections.no_collections": {"en": "No collections found.", "zh": "暂无合集。"},
    "collections.create_first": {"en": "Create the first one", "zh": "创建第一个合集"},
    "collections.sort":      {"en": "Sort",                 "zh": "排序"},
    "collections.type":      {"en": "Type",                 "zh": "类型"},
    "collections.category":  {"en": "Category",             "zh": "分类"},
    "collections.creator":   {"en": "Creator",              "zh": "创建者"},
    "collections.items_json": {"en": "Items (JSON)",        "zh": "项目 (JSON)"},
    "collections.json_hint": {"en": "Paste a JSON array of method or problem objects.", "zh": "粘贴方法或问题对象的 JSON 数组。"},
    "collections.json_placeholder": {"en": "Describe what this collection is about...", "zh": "描述这个合集的内容..."},
    "collections.star":      {"en": "Star",                 "zh": "收藏"},
    "collections.unstar":    {"en": "Unstar",               "zh": "取消收藏"},
    "collections.back":      {"en": "Back to Collections",  "zh": "返回合集列表"},
    "collections.import_hint": {"en": "Use this command to mine with this collection:", "zh": "使用此命令用本合集进行挖掘："},
    "collections.no_items":  {"en": "No items in this collection.", "zh": "此合集暂无项目。"},
    "collections.quantity":  {"en": "items",                "zh": "项"},
    "collections.method_col": {"en": "Method Collection",   "zh": "方法合集"},
    "collections.problem_col": {"en": "Problem Collection", "zh": "问题合集"},
    "collections.name_placeholder": {"en": "e.g. Quantum Methods Pack", "zh": "例如：量子方法包"},
    "collections.required":  {"en": "required",             "zh": "必填"},
    # Math Zone
    "math.title":            {"en": "Math Research Zone",   "zh": "数学研究区"},
    "math.new_problem":      {"en": "New Problem",          "zh": "新建问题"},
    "math.no_problems":      {"en": "No math problem zones yet.", "zh": "暂无数学问题区。"},
    "math.apply_first":      {"en": "Apply to create the first one", "zh": "申请创建第一个"},
    "math.solutions_count":  {"en": "{n} solution(s)",      "zh": "{n} 个解法"},
    "math.method_zones":     {"en": "Method Zones",         "zh": "方法区"},
    "math.check_access":     {"en": "Check Access",         "zh": "检查权限"},
    "math.unlocked":         {"en": "Unlocked",             "zh": "已解锁"},
    "math.locked_status":    {"en": "Locked — Unlock",      "zh": "已锁定 — 解锁"},
    "math.tools":            {"en": "tools",                "zh": "工具"},
    "math.no_method_zones":  {"en": "No math method collections yet.", "zh": "暂无数学方法合集。"},
    "math.create_one":       {"en": "Create one",           "zh": "创建一个"},
    "math.with_category":    {"en": "with category \"mathematics\".", "zh": "分类选 \"mathematics\"。"},
    "math.access_required":  {"en": "Access Required",      "zh": "需要权限"},
    "math.must_unlock":      {"en": "You must unlock this zone before viewing solutions.", "zh": "你必须解锁此区域才能查看解法。"},
    "math.manual_unlock":    {"en": "Manual Unlock",        "zh": "手动解锁"},
    "math.unlock_title":     {"en": "Unlock Zone",          "zh": "解锁区域"},
    "math.unlock_desc":      {"en": "To view solutions in this zone, you must first run a <b>math-mine</b> operation.", "zh": "要查看此区域的解法，你需要先运行 <b>math-mine</b> 操作。"},
    "math.step1":            {"en": "Step 1: Run CLI command", "zh": "步骤 1：运行 CLI 命令"},
    "math.step2":            {"en": "Step 2: Manual unlock (if needed)", "zh": "步骤 2：手动解锁（如需）"},
    "math.unlock_btn":       {"en": "Unlock",               "zh": "解锁"},
    "math.already_unlocked": {"en": "Zone Already Unlocked", "zh": "区域已解锁"},
    "math.has_access":       {"en": "You have access to this zone.", "zh": "你已有此区域的访问权限。"},
    "math.go_zone":          {"en": "Go to Method Zone",    "zh": "前往方法区"},
    "math.back_problem":     {"en": "Back to Problem",      "zh": "返回问题"},
    "math.back_zone":        {"en": "Back to Math Zone",    "zh": "返回数学区"},
    "math.back_method_zone": {"en": "Back to Method Zone",  "zh": "返回方法区"},
    "math.no_solutions":     {"en": "No solutions yet.",    "zh": "暂无解法。"},
    "math.submit_first":     {"en": "Submit the first one", "zh": "提交第一个解法"},
    "math.fork":             {"en": "Fork",                 "zh": "派生"},
    "math.fork_solution":    {"en": "Fork Solution",        "zh": "派生解法"},
    "math.fork_desc":        {"en": "This will create a copy of all {n} steps as your own solution.", "zh": "这将复制全部 {n} 个步骤作为你的解法。"},
    "math.confirm_fork":     {"en": "Confirm Fork",         "zh": "确认派生"},
    "math.submit_improvement": {"en": "Submit Improvement", "zh": "提交改进"},
    "math.submit_update":    {"en": "Submit Update",        "zh": "提交更新"},
    "math.edit_hint":        {"en": "Edit the JSON above and submit. max_correct_step will be recalculated.", "zh": "编辑上方 JSON 提交，max_correct_step 将重新计算。"},
    "math.forked_from":      {"en": "Forked from",          "zh": "派生自"},
    "math.new_math_problem": {"en": "New Math Problem",     "zh": "新建数学问题"},
    "math.create_zone":      {"en": "Create Problem Zone",  "zh": "创建问题区"},
    "math.title_placeholder": {"en": "e.g. Riemann Hypothesis", "zh": "例如：黎曼猜想"},
    "math.desc_placeholder": {"en": "Describe the problem...", "zh": "描述问题..."},
    "math.problem_not_found": {"en": "Math problem not found.", "zh": "数学问题未找到。"},
    "math.collection_not_found": {"en": "Problem or method collection not found.", "zh": "问题或方法合集未找到。"},
    "math.solution_not_found": {"en": "Solution not found.", "zh": "解法未找到。"},
    "math.solution_label":   {"en": "Solution",             "zh": "解法"},
    "math.tree.title":       {"en": "Exploration Tree",     "zh": "探索树"},
    "math.tree.root_detail": {"en": "Root Node Detail",     "zh": "根节点详情"},
    "math.tree.add_child":   {"en": "Add Child Node",       "zh": "添加子节点"},
    "math.tree.backprop":    {"en": "Mark Terminal & Backpropagate", "zh": "标记终点并反向传播"},
    "math.tree.prune":       {"en": "Prune Node",           "zh": "剪枝"},
    "math.tree.prune_desc":  {"en": "Mark as pruned (complexity explosion, contradiction, etc.) — backpropagates neutral reward.", "zh": "标记为剪枝（复杂度爆炸、矛盾等）— 反向传播中性奖励。"},
    "math.tree.state":       {"en": "State",                "zh": "状态"},
    "math.tree.action":      {"en": "Action",               "zh": "动作"},
    # Buffer Zone
    "buffer.title":          {"en": "Buffer Zone",          "zh": "区块链缓冲区"},
    "buffer.desc":           {"en": "Submit AI analysis → Community classification → Consensus → Publish to leaderboard", "zh": "提交 AI 分析 → 社区分类 → 共识达成 → 发布至排行榜"},
    "buffer.pending":        {"en": "Pending",              "zh": "待分类"},
    "buffer.classified":     {"en": "Classified",           "zh": "已分类"},
    "buffer.disputed":       {"en": "Disputed",             "zh": "争议中"},
    "buffer.published":      {"en": "Published",            "zh": "已发布"},
    "buffer.classify_pending": {"en": "Classify Pending",   "zh": "分类待处理"},
    "buffer.token_dashboard": {"en": "Token Dashboard",     "zh": "代币面板"},
    "buffer.classifier_lb":  {"en": "Classifier Leaderboard", "zh": "分类员排行榜"},
    "buffer.top_classifiers": {"en": "Top Classifiers",     "zh": "顶级分类员"},
    "buffer.no_pending":     {"en": "No pending submissions to classify.", "zh": "暂无待分类提交。"},
    "buffer.no_classifiers": {"en": "No classifiers yet.",  "zh": "暂无分类员。"},
    "buffer.classify_title": {"en": "Classify Submission",  "zh": "分类提交"},
    "buffer.classify_submit": {"en": "Submit Classification", "zh": "提交分类"},
    "buffer.classify_hint":  {"en": "Classification requires a stake of 10 IDEA tokens (auto-faucet for new users).", "zh": "分类需要质押 10 IDEA 代币（新用户自动领取）。"},
    "buffer.domain_label":   {"en": "Domain Label",         "zh": "领域标签"},
    "buffer.mark_nsfw":      {"en": "Mark as NSFW",         "zh": "标记为违规"},
    "buffer.mark_spam":      {"en": "Mark as Spam / AI Hallucination", "zh": "标记为垃圾 / AI 幻觉"},
    "buffer.your_address":   {"en": "Your Address",         "zh": "你的地址"},
    "buffer.analysis_data":  {"en": "Analysis Data",        "zh": "分析数据"},
    "buffer.existing_classifications": {"en": "Existing Classifications ({n})", "zh": "已有分类 ({n})"},
    "buffer.submission_detail": {"en": "Submission Detail", "zh": "提交详情"},
    "buffer.submission_id":  {"en": "Submission ID",        "zh": "提交 ID"},
    "buffer.my_submissions": {"en": "My Submissions",       "zh": "我的提交"},
    "buffer.no_submissions": {"en": "No submissions from {addr}.", "zh": "{addr} 暂无提交。"},
    "buffer.no_entry":       {"en": "Submission not found.", "zh": "提交未找到。"},
    "buffer.classifier_leaderboard": {"en": "Classifier Leaderboard", "zh": "分类员排行榜"},
    "buffer.top_50":         {"en": "Top 50 classifiers by token balance", "zh": "按代币余额排名前 50 分类员"},
    "buffer.classifications": {"en": "Classifications",     "zh": "分类记录"},
    "buffer.consensus_domain": {"en": "Consensus Domain",   "zh": "共识领域"},
    "buffer.active_stakes":  {"en": "Active Stakes",        "zh": "活跃质押"},
    "buffer.stake_id":       {"en": "Stake ID",             "zh": "质押 ID"},
    "buffer.submission":     {"en": "Submission",           "zh": "提交"},
    "buffer.consecutive_streak": {"en": "Consecutive Streak", "zh": "连续正确"},
    "buffer.pending_classifications": {"en": "Pending Classifications", "zh": "待分类项目"},
    "buffer.awaiting":       {"en": "{n} submission(s) awaiting classification", "zh": "{n} 条提交等待分类"},
    # Token Dashboard (buffer)
    "tokendash.title":       {"en": "Token Dashboard",      "zh": "代币面板"},
    "tokendash.balance_idea": {"en": "Balance (IDEA)",      "zh": "余额 (IDEA)"},
    "tokendash.staked":      {"en": "Staked",               "zh": "已质押"},
    "tokendash.total_earned": {"en": "Total Earned",        "zh": "累计赚取"},
    "tokendash.slashed":     {"en": "Slashed",              "zh": "被罚没"},
    # Error messages
    "error.form.name_required":      {"en": "Name is required.", "zh": "名称为必填。"},
    "error.form.domain_required":    {"en": "Domain is required.", "zh": "领域为必填。"},
    "error.form.level_required":     {"en": "Level must be 1-4.", "zh": "等级必须为 1-4。"},
    "error.form.level_number":       {"en": "Level must be a number 1-4.", "zh": "等级必须是 1-4 的数字。"},
    "error.form.description_required": {"en": "Description is required.", "zh": "描述为必填。"},
    "error.form.title_required":     {"en": "Title is required.", "zh": "标题为必填。"},
    "error.form.items_array":        {"en": "Items must be a JSON array.", "zh": "项目必须是 JSON 数组。"},
    "error.form.items_one":          {"en": "At least one item is required.", "zh": "至少需要一个项目。"},
    "error.form.invalid_json":       {"en": "Invalid JSON.", "zh": "JSON 格式无效。"},
    "error.form.type_required":      {"en": "Type must be 'method' or 'problem'.", "zh": "类型必须是 'method' 或 'problem'。"},
    "error.form.steps_array":        {"en": "Steps must be a JSON array.", "zh": "步骤必须是 JSON 数组。"},
    "error.form.invalid_json_item":  {"en": "Invalid JSON in items: {e}", "zh": "项目 JSON 无效：{e}"},
    "error.form.invalid_json_generic": {"en": "Invalid JSON", "zh": "JSON 格式无效"},
    # Misc
    "form.required_hint":    {"en": "Required fields are marked with *", "zh": "带 * 的为必填项"},
    # Login
    "login.login":           {"en": "Login",                   "zh": "登录"},
    "login.logout":          {"en": "Logout",                  "zh": "退出"},
    "login.logged_in":       {"en": "",                        "zh": ""},
    "login.placeholder":     {"en": "Your address (0x...)",    "zh": "你的地址 (0x...)"},
    "login.create_address":  {"en": "Create new address",      "zh": "创建新地址"},
    # Agent Assistant
    "agent.title":           {"en": "AI Assistant",             "zh": "AI 助手"},
    "agent.placeholder":     {"en": "Ask me anything...",       "zh": "输入你的问题..."},
    "agent.send":            {"en": "Send",                     "zh": "发送"},
    "agent.intro_title":     {"en": "Feature Guide",        "zh": "功能导览"},
    "agent.intro_desc":      {"en": "Click any card to try it, or type your request naturally!",
                               "zh": "点击卡片快速体验，或直接输入你的需求！"},
    "agent.cat_explore":     {"en": "Explore & Discover",     "zh": "探索与发现"},
    "agent.cat_tokens":      {"en": "Token Economy",           "zh": "代币经济"},
    "agent.cat_earn":        {"en": "Earn Rewards",            "zh": "获取收益"},
    "agent.cat_contribute":  {"en": "Create & Contribute",     "zh": "创作与贡献"},
    "agent.cat_zones":       {"en": "Research Zones",          "zh": "研究专区"},
    "agent.card_lb":   {"en": "Leaderboard",   "zh": "排行榜",     "tip_en": "Browse top-rated method×problem combinations", "tip_zh": "浏览评分最高的方法×问题组合"},
    "agent.card_search": {"en": "Search",    "zh": "搜索",       "tip_en": "Search across methods, problems, and domains", "tip_zh": "跨方法、问题、领域搜索"},
    "agent.card_draw": {"en": "Random Draw",  "zh": "随机抽取",   "tip_en": "Randomly pick entries — pay 5 IDEA to draw", "tip_zh": "随机抽取条目 — 需支付 5 IDEA"},
    "agent.card_detail": {"en": "Entry Detail","zh": "条目详情",  "tip_en": "View full scores and analysis of a combo", "tip_zh": "查看组合的完整评分与分析"},
    "agent.card_faucet":   {"en": "Get Tokens","zh": "领取代币", "tip_en": "Claim 100 free IDEA tokens (rate-limited)", "tip_zh": "领取 100 个免费 IDEA 代币（有限频）"},
    "agent.card_payview":  {"en": "Pay to View","zh": "付费查看", "tip_en": "Pay 10 IDEA to unlock a full AI analysis", "tip_zh": "支付 10 IDEA 解锁完整 AI 分析"},
    "agent.card_paylb":    {"en": "Unlock Ranking","zh": "解锁排行","tip_en": "Pay 20 IDEA to unlock a leaderboard for 24h", "tip_zh": "支付 20 IDEA 解锁排行榜 24 小时"},
    "agent.card_paydraw":  {"en": "Pay for Draw","zh": "付费抽奖","tip_en": "Pay 5 IDEA for random draw access", "tip_zh": "支付 5 IDEA 获得随机抽取权限"},
    "agent.card_mine":     {"en": "Idea Mining",  "zh": "创意挖矿", "tip_en": "AI evaluates a random method×problem pair across 8 dimensions", "tip_zh": "AI 从 8 个维度评估随机方法×问题组合"},
    "agent.card_bufclass": {"en": "Buffer Classify","zh": "缓冲分类","tip_en": "Vote on pending submissions to earn classifier rewards", "tip_zh": "对缓冲区的待定提交进行投票分类并赚取奖励"},
    "agent.card_submit_m": {"en": "Submit Method","zh": "提交方法", "tip_en": "Add a new creative method to the matrix", "tip_zh": "向矩阵中添加新方法"},
    "agent.card_submit_p": {"en": "Submit Problem","zh":"提交问题", "tip_en": "Add a new unsolved problem to the matrix", "tip_zh": "向矩阵中添加未解决的问题"},
    "agent.card_rate":     {"en": "Rate",          "zh": "评分",     "tip_en": "Rate a combo 1-5 stars after viewing it", "tip_zh": "查看后为组合评分 1-5 星"},
    "agent.card_collections":{"en":"Collections",  "zh": "合集浏览", "tip_en": "Browse community-curated method & problem collections", "tip_zh": "浏览社区策划的方法和问题合集"},
    "agent.card_math":     {"en": "Math Zone",     "zh": "数学区",   "tip_en": "Explore math research with MCTS tree search", "tip_zh": "基于 MCTS 树搜索探索数学研究问题"},
    "agent.card_buffer":   {"en": "Buffer Zone",   "zh": "缓冲区",   "tip_en": "Check pending consensus and buffer status", "tip_zh": "查看待定共识和缓冲区状态"},
    "agent.card_peers":    {"en": "Network Peers", "zh": "网络节点", "tip_en": "Show connected P2P nodes in the federation", "tip_zh": "显示联邦中已连接的 P2P 节点"},
    "agent.card_settings": {"en": "Settings",     "zh": "系统设置", "tip_en": "View and customize API key, model, and address config", "tip_zh": "查看和自定义 API 密钥、模型、地址等配置"},
    "agent.sending":       {"en": "Sending...",    "zh": "发送中..."},
    "agent.sb_address":    {"en": "Address",       "zh": "地址"},
    "agent.sb_balance":    {"en": "Balance",       "zh": "余额"},
    "agent.sb_not_logged": {"en": "Not logged in", "zh": "未登录"},
    "agent.sb_staked":     {"en": "Staked",        "zh": "质押"},
    "agent.welcome":         {"en": "Hello! I'm the HammerWorld assistant. "
                                     "Try asking me something like 'show me the leaderboard' or 'get free tokens'.",
                               "zh": "你好！我是 HammerWorld 助手。试试对我说「帮我看看排行榜」或「领取免费代币」。"},
    # Settings page
    "settings.title":        {"en": "Settings",                   "zh": "系统设置"},
    "settings.api_key":      {"en": "API Key",                    "zh": "API 密钥"},
    "settings.api_base":     {"en": "API Base URL",               "zh": "API 地址"},
    "settings.default_model": {"en": "Default Model",             "zh": "默认模型"},
    "settings.agent_model":  {"en": "Agent Model",                "zh": "Agent 模型"},
    "settings.mining_model": {"en": "Mining Model",               "zh": "挖矿模型"},
    "settings.triz_model":   {"en": "TRIZ Model",                 "zh": "TRIZ 模型"},
    "settings.address":      {"en": "Your Address",               "zh": "你的地址"},
    "settings.save":         {"en": "Save Settings",              "zh": "保存设置"},
    "settings.saved":        {"en": "Settings saved. Changes take effect immediately.", "zh": "设置已保存，修改立即生效。"},
    "settings.description":  {"en": "Configure your HammerWorld environment. Leave a field empty to use the default value.", "zh": "配置你的 HammerWorld 环境。留空则使用默认值。"},
    "settings.config_file":  {"en": "Config file",                "zh": "配置文件"},
}


def _t(key: str, lang: str = "en", **kwargs) -> str:
    """Look up a translation key for *lang* (``"en"`` or ``"zh"``).
    Falls back to English when a key or language entry is missing.
    ``**kwargs`` are used to format the translated template string.
    """
    entry = _T.get(key, {})
    text = entry.get(lang) or entry.get("en")
    if text is None:
        return key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


def _lang_toggle(lang: str) -> str:
    """Return the HTML link that toggles between English and Chinese."""
    next_lang = "zh" if lang == "en" else "en"
    label = _t("common.lang_toggle", lang)
    return f'<a href="?lang={next_lang}" class="lang-toggle" title="Switch language">{label}</a>'


# ------------------------------------------------------------------
# CSS (shared across all pages)
# ------------------------------------------------------------------

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
"""


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


def _score_bar(score: float, max_score: float = 10.0) -> str:
    pct = min(score / max_score * 100, 100)
    if pct >= 70:
        cls = "bar-high"
    elif pct >= 40:
        cls = "bar-mid"
    else:
        cls = "bar-low"
    return f'<span class="bar-bg"><span class="bar-fill {cls}" style="width:{pct:.0f}%"></span></span>{score:.1f}'


def _entry_table(entries: list[LeaderboardEntry], start_rank: int = 1, lang: str = "en") -> str:
    if not entries:
        return f'<div class="empty">{_t("common.no_entries", lang)}</div>'

    rows = []
    for i, e in enumerate(entries):
        row = (
            f"<tr>"
            f"<td>{start_rank + i}</td>"
            f"<td>{_score_bar(e.best_score)}</td>"
            f"<td>{e.best_dimension}</td>"
            f"<td><a href='/web/entry/{e.combo_id}?lang={lang}'>{_esc(e.method_name[:30])}</a></td>"
            f"<td>{_esc(e.problem_title[:40])}</td>"
            f"<td><span class='dim-label'>{e.problem_domain}</span></td>"
            f"<td><span class='dim-label'>{_esc(e.miner_address[:12])}...</span></td>"
            f"</tr>"
        )
        rows.append(row)

    return f"""
    <table>
    <thead><tr>
        <th>{_t("th.rank", lang)}</th><th>{_t("th.score", lang)}</th><th>{_t("th.dim", lang)}</th><th>{_t("th.method", lang)}</th><th>{_t("th.problem", lang)}</th>
        <th>{_t("th.domain", lang)}</th><th>{_t("th.miner", lang)}</th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>"""


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


# ------------------------------------------------------------------
# Page renderers
# ------------------------------------------------------------------

def render_dashboard(db: LeaderboardDB, pm: PeerManager, lang: str = "en", viewer_addr: str = "") -> str:
    total = db.total_entries()
    peers = len(pm.get_peers())
    uptime_m = int(pm.uptime / 60)
    uptime_str = f"{uptime_m // 60}h {uptime_m % 60}m" if uptime_m >= 60 else f"{uptime_m}m"

    # Top 10 entries
    top = db.get_top(limit=10)

    # Quick links
    dim_links = "".join(
        f'<a href="/web/leaderboard?dim={d.value}&lang={lang}">{d.value.title()}</a>'
        for d in EvalDimension
    )
    domain_links = "".join(
        f'<a href="/web/leaderboard?domain={d.value}&lang={lang}">{d.value.title()}</a>'
        for d in Domain
    )

    content = f"""
    <div class="stats">
        <div class="stat-card"><div class="num">{total}</div><div class="label">{_t("dash.entries", lang)}</div></div>
        <div class="stat-card"><div class="num">{peers}</div><div class="label">{_t("dash.peers", lang)}</div></div>
        <div class="stat-card"><div class="num">{uptime_str}</div><div class="label">{_t("dash.uptime", lang)}</div></div>
    </div>

    <h2>{_t("dash.by_dimension", lang)}</h2>
    <div class="quick-links">{dim_links}</div>

    <h2>{_t("dash.by_domain", lang)}</h2>
    <div class="quick-links">{domain_links}</div>

    <h2>{_t("dash.top_entries", lang)}</h2>
    {_entry_table(top, lang=lang)}
    """
    return _base_page(_t("dash.title", lang), content, "dashboard", lang=lang, viewer_addr=viewer_addr)


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

    # Filter form
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

    # Build filter links (keep current params)
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

    # Always query stats (drawn count / total) even behind paywall
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


def _render_previously_drawn(draw, lang: str) -> str:
    """Render list of entries the viewer has previously drawn from this board."""
    prev = draw.previously_drawn
    if not prev:
        return ""
    rows = ""
    for e in prev:
        rows += (
            f'<div class="card" style="opacity:0.7;border-left:3px solid #9ca3af;">'
            f'<span style="font-size:12px;color:#6b7280;margin-right:8px;">&#10003; {_t("random.drawn_before", lang)}</span>'
            f'<a href="/web/entry/{e.combo_id}?lang={lang}">{_esc(e.method_name)} &times; {_esc(e.problem_title)}</a>'
            f'</div>'
        )
    return f"""
    <h3 style="margin-top:24px;color:#555;">{_t("random.drawn_before", lang)} ({len(prev)})</h3>
    {rows}
    """


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


def render_entry(db: LeaderboardDB, combo_id: str,
                 viewer_addr: str = "", token_gate=None, lang: str = "en") -> str:
    entry = db._get_by_id(combo_id)
    if not entry:
        content = f'<div class="empty">{_t("common.not_found", lang)}</div>'
        return _base_page(_t("entry.title", lang), content, lang=lang, viewer_addr=viewer_addr)

    scores = [
        ("Elegance", entry.elegance),
        ("Weirdness", entry.weirdness),
        ("Human Feasibility", entry.human_feasibility),
        ("AI Feasibility", entry.ai_feasibility),
        ("Novelty", entry.novelty),
        ("Analogy Distance", entry.analogy_distance),
        ("Scaling Potential", entry.scaling_potential),
        ("Side Effects", entry.side_effects),
    ]

    score_rows = "".join(
        f"<tr><td>{name}</td><td>{_score_bar(score)}</td></tr>"
        for name, score in scores
    )

    # ---- Payment gating ----
    access = token_gate.check_view_access(viewer_addr, combo_id) if token_gate else "own"

    if access in ("own", "paid"):
        analysis_html = f"""
        <div class="card" style="line-height:1.8;font-size:14px;">
            <p>{_esc(entry.analysis_text) if entry.analysis_text else f'<span class="empty" style="padding:0;">{_t("entry.no_analysis", lang)}</span>'}</p>
        </div>"""
    else:
        fee = token_gate.VIEW_FEE_N if token_gate else 10
        analysis_html = f"""
        <div class="card" style="text-align:center;padding:32px;">
            <p style="font-size:16px;color:#555;margin-bottom:16px;">{_t("entry.paywalled", lang)}</p>
            <form method="post" action="/web/pay/view/{combo_id}">
                <input type="hidden" name="viewer_addr" value="{_esc(viewer_addr)}">
                <input type="hidden" name="redirect" value="/web/entry/{combo_id}?viewer={_esc(viewer_addr)}&lang={lang}">
                <input type="text" name="viewer_addr_input" value="{_esc(viewer_addr)}" placeholder="{_t("entry.your_address", lang)}" style="width:260px;margin-bottom:8px;display:block;margin-left:auto;margin-right:auto;">
                <button type="submit" style="font-size:15px;padding:10px 32px;">{_t("entry.pay_view", lang, fee=fee)}</button>
            </form>
        </div>"""

    # ---- Ratings section ----
    ratings = db.get_ratings_for_combo(combo_id)
    avg_rating = db.get_avg_rating_for_combo(combo_id)
    ratings_html = ""
    if ratings:
        stars = "&#x2605;" * int(avg_rating) + "&#x2606;" * (5 - int(avg_rating))
        ratings_html = f'<p style="margin-bottom:8px;">{_t("entry.avg_rating", lang)}: <b>{stars}</b> ({avg_rating}/5 {_t("entry.from_n_viewers", lang, n=len(ratings))})</p>'
        for r in ratings[:10]:
            r_stars = "&#x2605;" * r["rating"] + "&#x2606;" * (5 - r["rating"])
            comment = _esc(r.get("comment", ""))
            ratings_html += f'<p style="font-size:13px;color:#555;">{r_stars} — {_esc(r["viewer_addr"][:14])}… {comment}</p>'

    rate_form = ""
    if access in ("own", "paid") and viewer_addr:
        rate_form = f"""
        <form method="post" action="/web/rate/{combo_id}" style="margin-top:12px;">
            <input type="hidden" name="viewer_addr" value="{_esc(viewer_addr)}">
            <input type="hidden" name="redirect" value="/web/entry/{combo_id}?viewer={_esc(viewer_addr)}&lang={lang}">
            <select name="rating" style="width:auto;">
                <option value="">{_t("entry.rate_placeholder", lang)}</option>
                <option value="5">5 — {_t("entry.excellent", lang)}</option>
                <option value="4">4 — {_t("entry.good", lang)}</option>
                <option value="3">3 — {_t("entry.average", lang)}</option>
                <option value="2">2 — {_t("entry.poor", lang)}</option>
                <option value="1">1 — {_t("entry.terrible", lang)}</option>
            </select>
            <input type="text" name="comment" placeholder="{_t("entry.optional_comment", lang)}" style="width:200px;">
            <button type="submit">{_t("entry.submit_rating", lang)}</button>
        </form>"""

    content = f"""
    <div class="card">
        <h3>{_esc(entry.method_name)} &times; {_esc(entry.problem_title)}</h3>
        <table style="margin-top:12px;">
            <tr><td style="color:#777;width:140px;">{_t("entry.combo_id", lang)}</td><td>{entry.combo_id}</td></tr>
            <tr><td style="color:#777;">{_t("entry.method", lang)}</td><td>{_esc(entry.method_name)}</td></tr>
            <tr><td style="color:#777;">{_t("entry.method_domain", lang)}</td><td>{entry.method_domain}</td></tr>
            <tr><td style="color:#777;">{_t("entry.method_level", lang)}</td><td>{entry.method_level}</td></tr>
            <tr><td style="color:#777;">{_t("entry.problem_title", lang)}</td><td>{_esc(entry.problem_title)}</td></tr>
            <tr><td style="color:#777;">{_t("entry.problem_domain", lang)}</td><td>{entry.problem_domain}</td></tr>
            <tr><td style="color:#777;">{_t("entry.best_dimension", lang)}</td><td><b>{entry.best_dimension}</b></td></tr>
            <tr><td style="color:#777;">{_t("entry.best_score", lang)}</td><td><b>{entry.best_score:.1f}</b></td></tr>
            <tr><td style="color:#777;">{_t("entry.miner", lang)}</td><td>{entry.miner_address}</td></tr>
        </table>
    </div>

    <h2>{_t("entry.ai_analysis", lang)}</h2>
    {analysis_html}

    <h2>{_t("entry.scores", lang)}</h2>
    <table>{score_rows}</table>

    <h2>{_t("entry.ratings", lang)}</h2>
    <div class="card">
        {ratings_html if ratings_html else f'<p style="color:#999;">{_t("entry.no_ratings", lang)}</p>'}
        {rate_form}
    </div>
    """
    return _base_page(f"{entry.method_name} × {entry.problem_title}", content, lang=lang, viewer_addr=viewer_addr)


# ------------------------------------------------------------------
# My Mined Entries page
# ------------------------------------------------------------------

def render_my_entries(db: LeaderboardDB, viewer_addr: str = "", lang: str = "en") -> str:
    """Show all entries mined by the current user."""
    if not viewer_addr:
        content = f'<div class="empty">{_t("agent.sb_not_logged", lang)}</div>'
        return _base_page(_t("my_entries.title", lang), content, "my-entries", lang=lang, viewer_addr=viewer_addr)

    entries = db.get_entries_by_miner(viewer_addr, limit=50)

    if not entries:
        content = f'<div class="empty">{_t("my_entries.empty", lang)}</div>'
        return _base_page(_t("my_entries.title", lang), content, "my-entries", lang=lang, viewer_addr=viewer_addr)

    rows = []
    for e in entries:
        created = ""
        if e.created_at:
            import datetime
            created = datetime.datetime.fromtimestamp(e.created_at).strftime("%Y-%m-%d %H:%M")
        rows.append(f"""<tr>
            <td>{e.rank}</td>
            <td><a href="/web/entry/{_esc(e.combo_id)}?lang={lang}">{_esc(e.method_name)} × {_esc(e.problem_title)}</a></td>
            <td>{_esc(e.best_dimension)}</td>
            <td>{e.best_score:.1f}</td>
            <td style="font-size:12px;color:#999;">{created}</td>
            <td><a href="/web/entry/{_esc(e.combo_id)}?lang={lang}" class="btn" style="padding:4px 12px;font-size:12px;">{_t("my_entries.view", lang)}</a></td>
        </tr>""")

    content = f"""
    <h1>{_t("my_entries.title", lang)}</h1>
    <p style="color:#777;margin-bottom:16px;">{_t("my_entries.count", lang, n=len(entries))}</p>
    <table>
    <thead><tr>
        <th>#</th>
        <th>{_t("th.combo", lang)}</th>
        <th>{_t("th.best_dim", lang)}</th>
        <th>{_t("th.score", lang)}</th>
        <th>{_t("th.created", lang)}</th>
        <th></th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page(_t("my_entries.title", lang), content, "my-entries", lang=lang, viewer_addr=viewer_addr)


# ------------------------------------------------------------------
# Token Dashboard page
# ------------------------------------------------------------------

def render_token_dashboard(db: LeaderboardDB, token_gate=None,
                           viewer_addr: str = "", lang: str = "en",
                           path: str = "") -> str:
    from urllib.parse import parse_qs
    params = _parse_query(path) if path else {}
    msg = params.get("msg", "")
    summary = token_gate.get_viewer_summary(viewer_addr) if token_gate else {
        "address": viewer_addr, "balance": 0, "staked": 0,
        "total_earned": 0, "total_slashed": 0,
        "total_payments": 0, "total_spent": 0, "payments": [],
    }

    payment_rows = ""
    for p in summary.get("payments", []):
        p_combo = _esc(p.get("combo_id", "")[:12])
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


# ------------------------------------------------------------------
# Matrix Marketplace — Collection pages
# ------------------------------------------------------------------

_COLLECTION_CATEGORIES_METHOD = [
    "triz", "biology", "physics", "chemistry", "mathematics",
    "economics", "machine_learning", "heuristic", "engineering",
    "design", "systems", "other",
]
_COLLECTION_CATEGORIES_PROBLEM = [
    "medicine", "energy", "environment", "information", "materials",
    "society", "transportation", "agriculture", "space", "other",
]


def render_collections(db: LeaderboardDB, path: str, lang: str = "en", viewer_addr: str = "") -> str:
    """Browse method and problem collections with tab switching."""
    params = _parse_query(path)
    ctype = params.get("type", "method")
    sort_by = params.get("sort", "stars")
    category = params.get("category", None)
    mine = params.get("mine", None)

    if ctype not in ("method", "problem"):
        ctype = "method"

    collections = db.get_collections(ctype, sort_by=sort_by, category=category)

    if mine:
        collections = [c for c in collections if c.get("creator") == mine]

    # Tabs
    method_tab = f'<a href="/web/collections?type=method&sort=stars" class="{"active" if ctype == "method" else ""}">Methods</a>'
    problem_tab = f'<a href="/web/collections?type=problem&sort=imports" class="{"active" if ctype == "problem" else ""}">Problems</a>'

    # Sort links
    method_sorts = [
        ("stars", "Stars"),
        ("imports", "Imports"),
        ("newest", "Newest"),
    ]
    sort_links = " | ".join(
        f'<a href="/web/collections?type={ctype}&sort={s}&category={category or ""}&mine={mine or ""}" style="{"font-weight:bold;color:#2563eb;" if sort_by == s else "font-weight:normal;"}">{label}</a>'
        for s, label in method_sorts
    )

    # Category filter chips
    cats = _COLLECTION_CATEGORIES_METHOD if ctype == "method" else _COLLECTION_CATEGORIES_PROBLEM
    cat_links = "".join(
        f'<a href="/web/collections?type={ctype}&sort={sort_by}&category={c}" class="{"active" if category == c else ""}">{c.replace("_", " ").title()}</a>'
        for c in cats
    )

    # Cards
    cards = []
    for c in collections:
        cid = c["id"]
        items_json = c.get("methods_json") or c.get("problems_json") or "[]"
        try:
            items = json.loads(items_json)
        except Exception:
            items = []
        item_count = len(items)
        stars = c.get("stars", 0)
        imports = c.get("import_count", 0)
        name = _esc(c.get("name", "Unknown"))
        desc = _esc((c.get("description") or "")[:200])
        creator = _esc((c.get("creator") or "unknown")[:16])
        cat = c.get("category", "other").replace("_", " ").title()
        import_label = "import" if imports == 1 else "imports"

        cards.append(f"""
        <div class="card">
            <h3><a href="/web/collections/{ctype}/{cid}">{name}</a></h3>
            <p style="color:#777;font-size:13px;margin-bottom:4px;">
                <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
                &nbsp; {item_count} items &nbsp; &#x2605; {stars} &nbsp; {imports} {import_label} &nbsp; by {creator}
            </p>
            <p style="font-size:13px;color:#555;">{desc}</p>
        </div>""")

    if not cards:
        query_info = f" by <b>{_esc(mine)}</b>" if mine else ""
        cards_html = f'<div class="empty">No collections found{query_info}. <a href="/web/collections/new">Create the first one</a>.</div>'
    else:
        cards_html = "".join(cards)

    mine_link = f' | <a href="/web/collections?type={ctype}&mine=my">My Collections</a>' if not mine else f' | <a href="/web/collections?type={ctype}&sort={sort_by}">All Collections</a>'

    content = f"""
    <div class="quick-links" style="margin-bottom:12px;">
        {method_tab}{problem_tab}
        <span class="sep">|</span>
        <a href="/web/collections/new">+ New Collection</a>
        {mine_link}
    </div>
    <p style="color:#777;font-size:13px;margin-bottom:8px;">Sort: {sort_links}</p>
    <div class="quick-links" style="margin-bottom:16px;">{cat_links}</div>
    {cards_html}
    """
    return _base_page("Collections", content, "collections", lang=lang, viewer_addr=viewer_addr)


def render_collection_new(form: dict | None = None, errors: list[str] | None = None, success: str = "", lang: str = "en") -> str:
    """Render the collection creation form."""
    f = form or {}
    err_html = "".join(f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>' for e in (errors or []))
    ok_html = f'<p style="color:#22c55e;margin:8px 0;">{_esc(success)}</p>' if success else ""

    sel_method = 'selected' if f.get("ctype", "method") == "method" else ""
    sel_problem = 'selected' if f.get("ctype") == "problem" else ""

    method_cats = "".join(
        f'<option value="{c}" {"selected" if f.get("category") == c else ""}>{c.replace("_", " ").title()}</option>'
        for c in _COLLECTION_CATEGORIES_METHOD
    )
    problem_cats = "".join(
        f'<option value="{c}" {"selected" if f.get("category") == c else ""}>{c.title()}</option>'
        for c in _COLLECTION_CATEGORIES_PROBLEM
    )

    items_json = _esc(f.get("items_json", "[{\n  \n}]"))

    content = f"""
    {err_html}{ok_html}
    <form method="post" action="/web/collections/new">
        <table style="max-width:750px;">
            <tr><td style="color:#777;width:140px;padding:8px;">Type *</td>
                <td><select name="ctype" id="ctype-select" onchange="document.getElementById('cat-method').style.display=this.value==='problem'?'none':'block';document.getElementById('cat-problem').style.display=this.value==='method'?'none':'block';">
                    <option value="method" {sel_method}>Method Collection</option>
                    <option value="problem" {sel_problem}>Problem Collection</option>
                </select></td></tr>
            <tr><td style="color:#777;padding:8px;">Name *</td>
                <td><input type="text" name="name" value="{_esc(f.get('name', ''))}" required style="width:100%;" placeholder="e.g. Quantum Methods Pack"></td></tr>
            <tr><td style="color:#777;padding:8px;">Category *</td>
                <td>
                    <select name="category" id="cat-method" style="display:{'block' if f.get('ctype', 'method') == 'method' else 'none'};">{method_cats}</select>
                    <select name="category" id="cat-problem" style="display:{'block' if f.get('ctype') == 'problem' else 'none'};">{problem_cats}</select>
                </td></tr>
            <tr><td style="color:#777;padding:8px;">Description</td>
                <td><textarea name="description" rows="3" style="width:100%;" placeholder="Describe what this collection is about...">{_esc(f.get('description', ''))}</textarea></td></tr>
            <tr><td style="color:#777;padding:8px;">Items (JSON) *</td>
                <td><textarea name="items_json" rows="12" required style="width:100%;font-family:monospace;font-size:12px;" placeholder='[&#10;  {{"name": "...", "domain": "...", "level": 2, "description": "..."}}&#10;]'>{items_json}</textarea>
                <p style="font-size:11px;color:#999;margin-top:4px;">Paste a JSON array of method or problem objects.</p></td></tr>
            <tr><td style="color:#777;padding:8px;">Creator</td>
                <td><input type="text" name="creator" value="{_esc(f.get('creator', 'anonymous'))}" style="width:100%;"></td></tr>
        </table>
        <button type="submit" style="margin-top:12px;padding:10px 28px;">Create Collection</button>
    </form>
    """
    return _base_page("New Collection", content, "collections", lang=lang)


def render_collection_detail(db: LeaderboardDB, ctype: str, cid: int, starrer: str = "", starred: bool = False, lang: str = "en") -> str:
    """Render a single collection's detail page with items and star button."""
    c = db.get_collection(ctype, cid)
    if not c:
        content = '<div class="empty">Collection not found.</div>'
        return _base_page("Not Found", content, lang=lang)

    items = json.loads(c.get("methods_json") or c.get("problems_json") or "[]")
    stars = c.get("stars", 0)
    imports = c.get("import_count", 0)
    name = _esc(c.get("name", "Unknown"))
    desc = _esc(c.get("description") or "")
    creator = _esc(c.get("creator", "unknown"))
    cat = (c.get("category") or "other").replace("_", " ").title()
    created = c.get("created_at", 0)

    star_verb = "Unstar" if starred else "Star"
    star_link = f"/web/collections/{ctype}/{cid}/star?starrer={_esc(starrer)}" if starrer else "#"
    star_disabled = "" if starrer else "disabled"

    item_rows = []
    for i, item in enumerate(items):
        if ctype == "method":
            label = f"{_esc(item.get('name', '?'))}"
            sub = f"Domain: {_esc(item.get('domain', '?'))} | Level: {item.get('level', '?')}"
        else:
            label = f"{_esc(item.get('title', '?'))}"
            sub = f"Domain: {_esc(item.get('domain', '?'))} | Maturity: {item.get('maturity', '?')}"
        desc_item = _esc((item.get("description") or "")[:150])
        item_rows.append(f"""
        <tr>
            <td>{i + 1}</td>
            <td><b>{label}</b><br><span style="font-size:11px;color:#999;">{sub}</span></td>
            <td style="font-size:12px;">{desc_item}</td>
        </tr>""")

    import_label = "import" if imports == 1 else "imports"

    content = f"""
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;">
            <div>
                <h3 style="margin-bottom:4px;">{name}</h3>
                <p style="color:#777;font-size:13px;">
                    <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
                    &nbsp; {len(items)} items &nbsp; &#x2605; {stars} &nbsp; {imports} {import_label} &nbsp; by {creator}
                </p>
            </div>
            <div style="text-align:center;">
                <a href="{star_link}" style="display:inline-block;padding:8px 16px;background:#2563eb;color:#fff;border-radius:6px;font-size:14px;text-decoration:none;{star_disabled}">{star_verb} &#x2605;</a>
                <p style="font-size:11px;color:#999;margin-top:4px;">{stars} stars</p>
            </div>
        </div>
        <p style="margin-top:12px;font-size:14px;color:#555;">{desc}</p>
    </div>

    <h2>Items ({len(items)})</h2>
    <table>
    <thead><tr><th>#</th><th>{"Method" if ctype == "method" else "Problem"}</th><th>Description</th></tr></thead>
    <tbody>{"".join(item_rows) if item_rows else '<tr><td colspan="3" class="empty">No items in this collection.</td></tr>'}</tbody>
    </table>

    <h2>Import</h2>
    <div class="card">
        <p style="font-size:13px;color:#555;">Use this command to mine with this collection:</p>
        <pre style="background:#f0f3f7;padding:12px;border-radius:6px;font-size:13px;overflow-x:auto;">python3 -m src.cli.main mine --{"methods" if ctype == "method" else "problems"}-collection "{name}" --batch 5</pre>
    </div>

    <p style="margin-top:16px;"><a href="/web/collections?type={ctype}">&larr; Back to Collections</a></p>
    """
    return _base_page(name, content, "collections", lang=lang)


def render_collections_mine(db: LeaderboardDB, creator: str) -> str:
    """Redirect to collections filtered by creator."""
    params = f"type=method&mine={_esc(creator)}"
    return f'<html><head><meta http-equiv="refresh" content="0;url=/web/collections?{params}"></head><body>Redirecting...</body></html>'


# ------------------------------------------------------------------
# Math Research Zone pages
# ------------------------------------------------------------------

_MATH_CATEGORIES = [
    "number_theory", "analysis", "algebra", "geometry",
    "topology", "combinatorics", "logic", "other",
]


def render_math_home(db: LeaderboardDB, lang: str = "en", viewer_addr: str = "") -> str:
    """Math Zone home page — list all math problems."""
    problems = db.get_math_problems()
    cards = []
    for p in problems:
        pid = p["id"]
        title = _esc(p["title"])
        desc = _esc((p.get("description") or "")[:180])
        cat = (p.get("category") or "other").replace("_", " ").title()
        creator = _esc((p.get("creator") or "unknown")[:16])
        # Count solutions
        with db._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM math_solutions WHERE problem_id = ?", (pid,)
            ).fetchone()
        solution_count = row[0] if row else 0
        cards.append(f"""
        <div class="card">
            <h3><a href="/web/math/{pid}">{title}</a></h3>
            <p style="color:#777;font-size:13px;margin-bottom:4px;">
                <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
                &nbsp; {solution_count} solution(s) &nbsp; by {creator}
            </p>
            <p style="font-size:13px;color:#555;">{desc}</p>
        </div>""")

    content = f"""
    <div class="quick-links" style="margin-bottom:16px;">
        <a href="/web/math/new">+ New Problem</a>
    </div>
    {"".join(cards) if cards else '<div class="empty">No math problem zones yet. <a href="/web/math/new">Apply to create the first one</a>.</div>'}
    """
    return _base_page("Math Research Zone", content, "math", lang=lang, viewer_addr=viewer_addr)


def render_math_new(form: dict | None = None, errors: list[str] | None = None, success: str = "", lang: str = "en", viewer_addr: str = "") -> str:
    """Form to create a new math problem zone."""
    f = form or {}
    err_html = "".join(f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>' for e in (errors or []))
    ok_html = f'<p style="color:#22c55e;margin:8px 0;">{_esc(success)}</p>' if success else ""

    cat_opts = "".join(
        f'<option value="{c}" {"selected" if f.get("category") == c else ""}>{c.replace("_", " ").title()}</option>'
        for c in _MATH_CATEGORIES
    )

    content = f"""
    {err_html}{ok_html}
    <form method="post" action="/web/math/new">
        <table style="max-width:700px;">
            <tr><td style="color:#777;width:140px;padding:8px;">Title *</td>
                <td><input type="text" name="title" value="{_esc(f.get('title', ''))}" required style="width:100%;" placeholder="e.g. Riemann Hypothesis"></td></tr>
            <tr><td style="color:#777;padding:8px;">Category *</td>
                <td><select name="category">{cat_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Description</td>
                <td><textarea name="description" rows="4" style="width:100%;" placeholder="Describe the problem...">{_esc(f.get('description', ''))}</textarea></td></tr>
            <tr><td style="color:#777;padding:8px;">Creator</td>
                <td><input type="text" name="creator" value="{_esc(f.get('creator', 'anonymous'))}" style="width:100%;"></td></tr>
        </table>
        <button type="submit" style="margin-top:12px;padding:10px 28px;">Create Problem Zone</button>
    </form>
    """
    return _base_page("New Math Problem", content, "math", lang=lang, viewer_addr=viewer_addr)


def render_math_problem(db: LeaderboardDB, pid: int, path: str, lang: str = "en") -> str:
    """Problem area page — sub-divisions by method collection."""
    problem = db.get_math_problem(pid)
    if not problem:
        return _base_page("Not Found", '<div class="empty">Math problem not found.</div>', lang=lang)

    title = _esc(problem["title"])
    desc = _esc(problem.get("description") or "")
    cat = (problem.get("category") or "other").replace("_", " ").title()
    creator = _esc((problem.get("creator") or "unknown")[:16])

    params = _parse_query(path)
    user_addr = params.get("user_address", "")

    # Get math method collections (category=mathematics)
    method_colls = db.get_collections("method", sort_by="stars", category="mathematics")

    rows = []
    for c in method_colls:
        mid = c["id"]
        mname = _esc(c["name"])
        mitems = len(json.loads(c.get("methods_json") or "[]"))
        accessed = db.check_math_access(pid, mid, user_addr) if user_addr else False

        # Count solutions
        with db._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*), MAX(max_correct_step) FROM math_solutions "
                "WHERE problem_id = ? AND method_collection_id = ?",
                (pid, mid),
            ).fetchone()
        sol_count = row[0] if row else 0
        top_step = row[1] or 0

        access_label = '<span style="color:#22c55e;">&#x2713; Unlocked</span>' if accessed else '<a href="/web/math/{pid}/{mid}/unlock" style="color:#ef4444;">Locked — Unlock</a>'
        zone_link = f'/web/math/{pid}/{mid}' if accessed else f'/web/math/{pid}/{mid}/unlock'

        rows.append(f"""
        <tr>
            <td><a href="{zone_link}"><b>{mname}</b></a><br><span style="font-size:11px;color:#999;">{mitems} tools</span></td>
            <td>{access_label}</td>
            <td><b>{top_step}</b> steps</td>
            <td>{sol_count} solution(s)</td>
        </tr>""")

    content = f"""
    <div class="card">
        <h3>{title}</h3>
        <p style="color:#777;font-size:13px;margin-bottom:4px;">
            <span style="background:#e8f0fe;color:#2563eb;padding:1px 8px;border-radius:3px;font-size:11px;">{cat}</span>
            &nbsp; by {creator}
        </p>
        <p style="font-size:14px;color:#555;margin-top:8px;">{desc}</p>
    </div>

    <form method="get" action="/web/math/{pid}" style="margin-bottom:12px;">
        <input type="text" name="user_address" value="{_esc(user_addr)}" placeholder="Your address (e.g. 0xALICE)" style="flex:1;min-width:260px;">
        <button type="submit">Check Access</button>
    </form>

    <h2>Method Zones</h2>
    <table>
    <thead><tr><th>Method Collection</th><th>Access</th><th>Top Step</th><th>Solutions</th></tr></thead>
    <tbody>{"".join(rows) if rows else '<tr><td colspan="4" class="empty">No math method collections yet. <a href="/web/collections/new">Create one</a> with category "mathematics".</td></tr>'}</tbody>
    </table>

    <p style="margin-top:16px;"><a href="/web/math">&larr; Back to Math Zone</a></p>
    """
    return _base_page(title, content, "math", lang=lang)


def render_math_method_zone(db: LeaderboardDB, pid: int, mid: int, path: str, lang: str = "en") -> str:
    """All solutions for a (problem, method), ranked by max_correct_step."""
    problem = db.get_math_problem(pid)
    coll = db.get_collection("method", mid)
    if not problem or not coll:
        return _base_page("Not Found", '<div class="empty">Problem or method collection not found.</div>', lang=lang)

    params = _parse_query(path)
    user_addr = params.get("user_address", "")

    accessed = db.check_math_access(pid, mid, user_addr) if user_addr else False
    if not accessed:
        return _base_page("Access Required", f"""
        <div class="card">
            <h3>Access Required</h3>
            <p style="color:#777;margin:12px 0;">You must unlock this zone before viewing solutions.</p>
            <pre style="background:#f0f3f7;padding:12px;border-radius:6px;font-size:13px;">python3 -m src.cli.main math-mine --problem-id {pid} --methods-collection "{_esc(coll['name'])}" --address {"0xYOUR_ADDRESS" if not user_addr else _esc(user_addr)} --batch 3</pre>
            <p style="margin-top:8px;"><a href="/web/math/{pid}/{mid}/unlock?user_address={_esc(user_addr)}">Manual Unlock</a></p>
            <p style="margin-top:8px;"><a href="/web/math/{pid}/{mid}/tree?lang={lang}">Tree View</a></p>
            <p style="margin-top:16px;"><a href="/web/math/{pid}">&larr; Back to Problem</a></p>
        </div>
        """, "math")

    solutions = db.get_math_solutions(pid, mid)

    sol_rows = []
    for i, s in enumerate(solutions):
        sid = s["id"]
        try:
            steps = json.loads(s["steps_json"])
        except Exception:
            steps = []
        step_count = len(steps)
        max_step = s["max_correct_step"]
        user = _esc((s.get("user_address") or "unknown")[:16])
        parent = s.get("parent_solution_id")
        fork_info = f' <span style="font-size:11px;color:#999;">(forked from #{parent})</span>' if parent else ""
        sol_rows.append(f"""
        <tr>
            <td>{i + 1}</td>
            <td><a href="/web/math/{pid}/{mid}/{sid}">{user}</a>{fork_info}</td>
            <td>{_score_bar(max_step, max(10, max_step + 5))}</td>
            <td>{step_count} steps</td>
            <td><a href="/web/math/{pid}/{mid}/{sid}?fork=1&user_address={_esc(user_addr)}" style="color:#2563eb;">Fork</a></td>
        </tr>""")

    content = f"""
    <div class="card">
        <h3>{_esc(problem['title'])} &mdash; {_esc(coll['name'])}</h3>
        <p style="color:#777;font-size:13px;">
            {json.loads(coll.get("methods_json") or "[]") if False else ''}
            Access: <span style="color:#22c55e;">&#x2713; Unlocked</span>
        </p>
    </div>

    <h2>Solutions ({len(solutions)})</h2>
    <table>
    <thead><tr><th>#</th><th>User</th><th>Max Correct Step</th><th>Steps</th><th>Action</th></tr></thead>
    <tbody>{"".join(sol_rows) if sol_rows else '<tr><td colspan="5" class="empty">No solutions yet. <a href="/web/math/{pid}/{mid}/unlock">Submit the first one</a>.</td></tr>'}</tbody>
    </table>

    <p style="margin-top:16px;">
        <a href="/web/math/{pid}">&larr; Back to Problem</a>
        &nbsp;|&nbsp; <a href="/web/math/{pid}/{mid}/tree?lang={lang}">Tree View</a>
    </p>
    """
    return _base_page(f"{problem['title']} — {coll['name']}", content, "math", lang=lang)


def render_math_solution(db: LeaderboardDB, pid: int, mid: int, sid: int, path: str, lang: str = "en") -> str:
    """Single solution detail — full steps, fork button, submit improvement."""
    solution = db.get_math_solution(sid)
    if not solution:
        return _base_page("Not Found", '<div class="empty">Solution not found.</div>', lang=lang)

    problem = db.get_math_problem(pid)
    coll = db.get_collection("method", mid)

    try:
        steps = json.loads(solution["steps_json"])
    except Exception:
        steps = []

    max_step = solution["max_correct_step"]
    user = _esc((solution.get("user_address") or "unknown")[:16])
    parent = solution.get("parent_solution_id")
    created = solution.get("created_at", 0)
    updated = solution.get("updated_at", 0)

    step_rows = []
    for s in sorted(steps, key=lambda x: x.get("step_num", 0)):
        sn = s.get("step_num", "?")
        verified = s.get("verified", False)
        content_text = _esc(s.get("content", ""))
        v_badge = '<span style="color:#22c55e;">&#x2713;</span>' if verified else '<span style="color:#ef4444;">&#x2717;</span>'
        step_rows.append(f"""
        <tr>
            <td>{sn}</td>
            <td style="max-width:600px;">{content_text}</td>
            <td>{v_badge}</td>
        </tr>""")

    params = _parse_query(path)
    fork = params.get("fork")

    fork_form = ""
    if fork:
        fork_form = f"""
        <div class="card" style="margin-top:16px;">
            <h3>Fork Solution #{sid}</h3>
            <form method="post" action="/web/math/{pid}/{mid}/{sid}/fork">
                <input type="hidden" name="user_address" value="{_esc(params.get('user_address', 'anonymous'))}">
                <p style="color:#777;font-size:13px;">This will create a copy of all {len(steps)} steps as your own solution.</p>
                <button type="submit" style="margin-top:8px;">Confirm Fork</button>
            </form>
        </div>"""

    submit_form = f"""
    <div class="card" style="margin-top:16px;">
        <h3>Submit Improvement</h3>
        <form method="post" action="/web/math/{pid}/{mid}/{sid}/submit">
            <input type="hidden" name="user_address" value="{_esc(params.get('user_address', 'anonymous'))}">
            <textarea name="steps_json" rows="8" style="width:100%;font-family:monospace;font-size:12px;">{_esc(json.dumps(steps, indent=2, ensure_ascii=False))}</textarea>
            <p style="font-size:11px;color:#999;margin-top:4px;">Edit the JSON above and submit. max_correct_step will be recalculated.</p>
            <button type="submit" style="margin-top:8px;">Submit Update</button>
        </form>
    </div>"""

    parent_info = f'<p style="color:#777;font-size:13px;">Forked from <a href="/web/math/{pid}/{mid}/{parent}">Solution #{parent}</a></p>' if parent else ""

    content = f"""
    <div style="background:#fefce8;border:1px solid #facc15;border-radius:6px;padding:8px 12px;margin-bottom:16px;font-size:13px;color:#92400e;">
        This flat solution view is deprecated. See the <a href="/web/math/{pid}/{mid}/tree?lang={lang}">Tree View</a> for the new MCTS exploration interface.
    </div>
    <div class="card">
        <h3>Solution #{sid}</h3>
        <p style="color:#777;font-size:13px;">
            Problem: <b>{_esc(problem['title']) if problem else '?'}</b> &nbsp;
            Method: <b>{_esc(coll['name']) if coll else '?'}</b>
        </p>
        <p style="color:#777;font-size:13px;">
            By: <b>{user}</b> &nbsp;
            Max Correct Step: <b>{max_step}</b> &nbsp;
            Steps: <b>{len(steps)}</b>
        </p>
        {parent_info}
    </div>

    <h2>Steps</h2>
    <table>
    <thead><tr><th>#</th><th>Content</th><th>Verified</th></tr></thead>
    <tbody>{"".join(step_rows) if step_rows else '<tr><td colspan="3" class="empty">No steps.</td></tr>'}</tbody>
    </table>

    <div class="quick-links" style="margin-top:16px;">
        <a href="/web/math/{pid}/{mid}/{sid}?fork=1&user_address={_esc(params.get('user_address', ''))}">Fork Solution</a>
    </div>
    {fork_form}
    {submit_form}

    <p style="margin-top:16px;"><a href="/web/math/{pid}/{mid}">&larr; Back to Method Zone</a></p>
    """
    return _base_page(f"Solution #{sid}", content, "math", lang=lang)


def render_math_unlock(db: LeaderboardDB, pid: int, mid: int, path: str, lang: str = "en") -> str:
    """Gate unlock page — shows CLI command or manual unlock."""
    problem = db.get_math_problem(pid)
    coll = db.get_collection("method", mid)
    if not problem or not coll:
        return _base_page("Not Found", '<div class="empty">Problem or method collection not found.</div>', lang=lang)

    params = _parse_query(path)
    user_addr = params.get("user_address", "")

    accessed = db.check_math_access(pid, mid, user_addr) if user_addr else False

    if accessed:
        return _base_page("Zone Unlocked", f"""
        <div class="card">
            <h3 style="color:#22c55e;">&#x2713; Zone Already Unlocked</h3>
            <p style="color:#777;margin:12px 0;">You have access to this zone.</p>
            <a href="/web/math/{pid}/{mid}?user_address={_esc(user_addr)}">Go to Method Zone</a>
        </div>
        """, "math")

    pname = _esc(problem["title"])
    cname = _esc(coll["name"])

    content = f"""
    <div class="card">
        <h3>Unlock: {cname} &rarr; {pname}</h3>
        <p style="color:#777;margin:12px 0;">
            To view solutions in this zone, you must first run a <b>math-mine</b> operation.
            This combines methods from the collection with the problem and generates an AI seed analysis.
        </p>

        <h3 style="margin-top:16px;">Step 1: Run CLI command</h3>
        <pre style="background:#f0f3f7;padding:12px;border-radius:6px;font-size:13px;overflow-x:auto;">python3 -m src.cli.main math-mine \\
  --problem-id {pid} \\
  --methods-collection "{cname}" \\
  --address {"0xYOUR_ADDRESS" if not user_addr else _esc(user_addr)} \\
  --batch 3</pre>

        <h3 style="margin-top:16px;">Step 2: Manual unlock (if needed)</h3>
        <form method="post" action="/web/math/{pid}/{mid}/unlock">
            <input type="text" name="user_address" value="{_esc(user_addr)}" placeholder="Your address" required style="width:100%;margin-bottom:8px;">
            <input type="text" name="combo_id" placeholder="Combo ID from math-mine output" required style="width:100%;margin-bottom:8px;">
            <button type="submit">Unlock</button>
        </form>
    </div>

    <p style="margin-top:16px;"><a href="/web/math/{pid}">&larr; Back to Problem</a></p>
    """
    return _base_page(f"Unlock: {cname}", content, "math", lang=lang)


# ------------------------------------------------------------------
# Math Tree Visualization (MCTS)
# ------------------------------------------------------------------

def _render_tree_stats(db: LeaderboardDB, pid: int, mid: int) -> str:
    """Render summary statistics bar for a tree zone."""
    nodes = db.get_tree_nodes_for_zone(pid, mid)
    terms = db.get_terminal_nodes(pid, mid)
    success = [n for n in terms if n["node_type"] == "terminal_success"]
    root = db.get_root_node(pid, mid)

    max_depth = 0
    for n in nodes:
        path = db._get_path_to_root(n["id"])
        if len(path) > max_depth:
            max_depth = len(path)

    return f"""<div class="stats">
        <div class="stat-card"><div class="num">{len(nodes)}</div><div class="dim-label">States</div></div>
        <div class="stat-card"><div class="num">{len(success)}</div><div class="dim-label">Proofs</div></div>
        <div class="stat-card"><div class="num">{max_depth}</div><div class="dim-label">Max Depth</div></div>
        <div class="stat-card"><div class="num">{root['q_value']:.2f}</div><div class="dim-label">Root Q</div></div>
        <div class="stat-card"><div class="num">{root['visit_count']}</div><div class="dim-label">Root N</div></div>
    </div>"""


def _render_tree_recursive(db: LeaderboardDB, node_id: int, depth: int = 0,
                           max_depth: int = 12, lang: str = "en") -> str:
    """Recursively render a tree node and its children as nested HTML."""
    node = db.get_tree_node(node_id)
    if not node or depth > max_depth:
        return ""

    node_type = node["node_type"]
    type_css = {"terminal_success": "terminal-success",
                "terminal_failure": "terminal-failure",
                "pruned": "pruned"}.get(node_type, "")

    type_badge = {
        "terminal_success": '<span class="node-type-badge success">TERMINAL: Proved</span>',
        "terminal_failure": '<span class="node-type-badge failure">TERMINAL: Dead End</span>',
        "pruned": '<span class="node-type-badge pruned">PRUNED</span>',
    }.get(node_type, "")

    collapsed = depth >= 3
    checkbox_id = f"tc_{node_id}"

    children = db.get_children(node_id)
    has_children = len(children) > 0

    # Node HTML
    node_html = f"""<div class="tree-node {type_css}">
    <div class="tree-node-header">
        {type_badge}
        <strong>Q: {node['q_value']:.3f}</strong>
        <span style="color:#999;font-size:12px;">N={node['visit_count']}</span>
        <span style="color:#999;font-size:11px;margin-left:4px;">#{node_id}</span>
        <a href="/web/math/{node['problem_id']}/{node['method_collection_id']}/tree/node/{node_id}?lang={lang}" style="font-size:11px;margin-left:8px;">Details</a>
    </div>
    <div class="tree-node-content">{_esc(node['content'][:200])}{'...' if len(node['content']) > 200 else ''}</div>
    <div style="font-size:11px;color:#999;">by {_esc(node['user_address'][:16]) or 'anonymous'}</div>
</div>"""

    if not has_children:
        return node_html

    # Children with edge labels
    children_html = ""
    for c in children:
        uct_str = ""
        if c.get("uct_score") is not None and c["uct_score"] != float('inf'):
            uct_str = f' UCT:{c["uct_score"]:.3f}'
        elif c.get("uct_score") == float('inf'):
            uct_str = ' UCT:∞'

        edge_tag = f'<span class="edge-label">→ {_esc(c["action_label"])}{uct_str}</span>'
        child_tree = _render_tree_recursive(db, c["child_id"], depth + 1, max_depth, lang)
        children_html += f'<div class="tree-child-wrapper">{edge_tag}{child_tree}</div>'

    if collapsed:
        return f"""{node_html}
<label class="tree-toggle collapsed" for="{checkbox_id}">{len(children)} branches</label>
<input type="checkbox" id="{checkbox_id}" style="display:none;">
<div class="tree-child-list tree-collapsible">{children_html}</div>"""
    else:
        return f"""{node_html}
<div class="tree-child-list">{children_html}</div>"""


def render_math_tree(db: LeaderboardDB, pid: int, mid: int, path: str,
                     lang: str = "en") -> str:
    """Render the MCTS tree visualization page for a (problem, method) zone."""
    problem = db.get_math_problem(pid)
    if not problem:
        return _base_page("Not Found", "<p>Problem not found.</p>", "math", lang=lang)

    coll = db.get_collection("method", mid)
    if not coll:
        return _base_page("Not Found", "<p>Method collection not found.</p>", "math", lang=lang)

    root = db.get_root_node(pid, mid)
    if not root:
        return _base_page("Empty Tree", "<p>No tree root. Run math-mine first.</p>", "math", lang=lang)

    stats_html = _render_tree_stats(db, pid, mid)
    tree_html = _render_tree_recursive(db, root["id"], lang=lang)

    content = f"""
    <div class="quick-links">
        <a href="/web/math/{pid}?lang={lang}">Problem</a>
        <a href="/web/math/{pid}/{mid}?lang={lang}">Solutions</a>
        <span class="sep">Tree View</span>
    </div>

    {stats_html}

    <h2>{_esc(coll['name'])} — {_t('math.tree.title', lang)}</h2>

    <div style="margin:12px 0;">
        <a href="/web/math/{pid}/{mid}/tree/node/{root['id']}?lang={lang}" class="tree-toggle">Root Node Detail</a>
    </div>

    <div class="tree-container">
        {tree_html}
    </div>
    """
    title = f"{_esc(problem['title'])} — Tree"
    return _base_page(title, content, "math", lang=lang)


def render_math_tree_node(db: LeaderboardDB, pid: int, mid: int, nid: int,
                          path: str, lang: str = "en",
                          errors: list[str] | None = None) -> str:
    """Render the detail page for a single tree node."""
    problem = db.get_math_problem(pid)
    if not problem:
        return _base_page("Not Found", "<p>Problem not found.</p>", "math", lang=lang)

    coll = db.get_collection("method", mid)
    node = db.get_tree_node(nid)
    if not node:
        return _base_page("Not Found", "<p>Node not found.</p>", "math", lang=lang)

    children = db.get_children(nid)
    uct_scores = db.get_uct_scores(nid)
    path_to_root = db._get_path_to_root(nid)
    parent = db._get_parent_node(nid)

    # Path breadcrumb
    breadcrumb_parts = []
    for pnid in reversed(path_to_root):
        pn = db.get_tree_node(pnid)
        if pn:
            breadcrumb_parts.append(
                f'<a href="/web/math/{pid}/{mid}/tree/node/{pnid}?lang={lang}">'
                f'{_esc((pn["content"] or "Root")[:40])}</a>'
            )
    breadcrumb = " → ".join(breadcrumb_parts)

    # Node type badge
    type_css = {"terminal_success": "terminal-success",
                "terminal_failure": "terminal-failure",
                "pruned": "pruned"}.get(node["node_type"], "")
    type_badge_html = {
        "terminal_success": '<span class="node-type-badge success">TERMINAL: Proved</span>',
        "terminal_failure": '<span class="node-type-badge failure">TERMINAL: Dead End</span>',
        "pruned": '<span class="node-type-badge pruned">PRUNED</span>',
        "normal": '<span class="node-type-badge normal">Normal</span>',
    }.get(node["node_type"], "")

    # Error display
    err_html = ""
    if errors:
        err_html = "".join(
            f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>'
            for e in errors
        )

    # Children table with UCT scores
    children_rows = ""
    for c in children:
        uct_str = ""
        for u in uct_scores:
            if u["child_id"] == c["child_id"]:
                if u.get("uct_score") == float('inf'):
                    uct_str = "∞"
                else:
                    uct_str = f'{u.get("uct_score", 0):.3f}'
                break
        children_rows += f"""<tr>
            <td><a href="/web/math/{pid}/{mid}/tree/node/{c['child_id']}?lang={lang}">{_esc(c['child_content'][:60])}</a></td>
            <td>{_esc(c['action_label'])}</td>
            <td>{c['child_q_value']:.3f}</td>
            <td>{c['child_visit_count']}</td>
            <td>{uct_str}</td>
            <td>{c['child_node_type']}</td>
        </tr>"""

    # Add child form
    add_form = f"""<div class="card" style="margin-top:24px;">
    <h3>Add Child Node</h3>
    {err_html}
    <form method="post" action="/web/math/{pid}/{mid}/tree/node/{nid}/add_child">
        <table style="width:100%;">
            <tr><td style="color:#777;width:120px;padding:4px;">Content *</td>
                <td><input type="text" name="content" required style="width:100%;" placeholder="Mathematical state description"></td></tr>
            <tr><td style="color:#777;padding:4px;">Action Label</td>
                <td><input type="text" name="action_label" style="width:100%;" placeholder="Method/theorem applied (e.g. 因式分解)"></td></tr>
            <tr><td style="color:#777;padding:4px;">Action Detail</td>
                <td><input type="text" name="action_description" style="width:100%;" placeholder="Optional description"></td></tr>
            <tr><td style="color:#777;padding:4px;">Type</td>
                <td><select name="node_type">
                    <option value="normal">Normal</option>
                    <option value="terminal_success">Terminal Success</option>
                    <option value="terminal_failure">Terminal Failure</option>
                </select></td></tr>
            <tr><td style="color:#777;padding:4px;">Reward</td>
                <td><input type="number" name="reward" value="1.0" min="0" max="1" step="0.1" style="width:100px;"></td></tr>
            <tr><td style="color:#777;padding:4px;">Your Address</td>
                <td><input type="text" name="user_address" value="0xEXPLORER" style="width:200px;"></td></tr>
            <tr><td></td><td><button type="submit">Add Child</button></td></tr>
        </table>
    </form>
</div>"""

    # Terminal actions
    terminal_form = ""
    if node["node_type"] not in ("terminal_success", "terminal_failure", "pruned"):
        terminal_form = f"""
        <div class="card" style="margin-top:16px;">
            <h3>Mark Terminal & Backpropagate</h3>
            <form method="post" action="/web/math/{pid}/{mid}/tree/node/{nid}/backpropagate" style="display:flex;gap:8px;align-items:center;">
                <select name="terminal_type">
                    <option value="terminal_success">Success (Proof Found)</option>
                    <option value="terminal_failure">Failure (Dead End)</option>
                </select>
                <input type="number" name="reward" value="1.0" min="0" max="1" step="0.1" style="width:80px;">
                <button type="submit">Backprop</button>
            </form>
        </div>
        <div class="card" style="margin-top:8px;">
            <h3>Prune Node</h3>
            <form method="post" action="/web/math/{pid}/{mid}/tree/node/{nid}/prune">
                <p style="color:#777;font-size:13px;margin-bottom:8px;">Mark as pruned (complexity explosion, contradiction, etc.) — backpropagates neutral reward.</p>
                <button type="submit" style="background:#9ca3af;border-color:#9ca3af;">Prune</button>
            </form>
        </div>"""

    content = f"""
    <div class="quick-links">
        <a href="/web/math/{pid}?lang={lang}">Problem</a>
        <a href="/web/math/{pid}/{mid}?lang={lang}">Method Zone</a>
        <a href="/web/math/{pid}/{mid}/tree?lang={lang}">Tree View</a>
        <span class="sep">Node #{nid}</span>
    </div>

    <div style="font-size:13px;color:#999;margin-bottom:16px;">{breadcrumb}</div>

    <div class="card tree-node {type_css}">
        <div style="margin-bottom:8px;">{type_badge_html}</div>
        <h3>{_esc(node['content'])}</h3>
        <div class="stats" style="margin-top:12px;">
            <div class="stat-card"><div class="num">{node['q_value']:.3f}</div><div class="dim-label">Q-Value</div></div>
            <div class="stat-card"><div class="num">{node['visit_count']}</div><div class="dim-label">Visits (N)</div></div>
            <div class="stat-card"><div class="num">{node['reward']:.2f}</div><div class="dim-label">Reward</div></div>
            <div class="stat-card"><div class="num">{len(children)}</div><div class="dim-label">Children</div></div>
            {f'<div class="stat-card"><div class="num">{node["user_address"][:12]}</div><div class="dim-label">Author</div></div>' if node['user_address'] else ''}
        </div>
        <p style="color:#777;font-size:12px;margin-top:8px;">
            Created: {time.strftime('%Y-%m-%d %H:%M', time.localtime(node['created_at'])) if node['created_at'] else 'N/A'}
            {f' | Parent: <a href="/web/math/{pid}/{mid}/tree/node/{parent["id"]}?lang={lang}">#{parent["id"]}</a>' if parent else ' | Root Node'}
        </p>
    </div>

    {'<h2 style="margin-top:24px;">Children (' + str(len(children)) + ')</h2>' if children else '<p style="color:#999;margin-top:16px;">No children yet. Expand the tree!</p>'}
    {'<table><tr><th>State</th><th>Action</th><th>Q</th><th>N</th><th>UCT</th><th>Type</th></tr>' + children_rows + '</table>' if children else ''}
    {terminal_form}
    {add_form}
    """
    title = f"Node #{nid} — {_esc(problem['title'])}"
    return _base_page(title, content, "math", lang=lang)


# ------------------------------------------------------------------
# Community Submission pages
# ------------------------------------------------------------------

def render_submit_home(lang: str = "en", viewer_addr: str = "") -> str:
    """Landing page for community submissions."""
    content = """
    <div class="stats">
        <div class="stat-card" style="flex:1;min-width:200px;">
            <div style="font-size:40px;margin-bottom:8px;">&#x1F9E0;</div>
            <div class="label">Submit a new thinking method to the matrix</div>
            <a href="/web/submit/method" style="display:inline-block;margin-top:12px;padding:8px 20px;background:#2563eb;color:#fff;border-radius:6px;">Submit Method</a>
        </div>
        <div class="stat-card" style="flex:1;min-width:200px;">
            <div style="font-size:40px;margin-bottom:8px;">&#x1F50D;</div>
            <div class="label">Submit an unsolved problem for the matrix</div>
            <a href="/web/submit/problem" style="display:inline-block;margin-top:12px;padding:8px 20px;background:#2563eb;color:#fff;border-radius:6px;">Submit Problem</a>
        </div>
    </div>
    <p style="color:#777;margin-top:16px;">All submissions are reviewed before joining the active matrix.</p>
    """
    return _base_page("Community Submit", content, "submit", lang=lang, viewer_addr=viewer_addr)


def render_submit_method(form: dict | None = None, errors: list[str] | None = None, success: str = "", lang: str = "en", viewer_addr: str = "") -> str:
    """Render the method submission form."""
    f = form or {}
    err_html = "".join(f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>' for e in (errors or []))
    ok_html = f'<p style="color:#22c55e;margin:8px 0;">{_esc(success)}</p>' if success else ""

    domains = ["triz", "biology", "physics", "chemistry", "mathematics", "economics",
               "machine_learning", "heuristic", "engineering", "design", "systems", "other"]
    domain_opts = "".join(
        f'<option value="{d}" {"selected" if f.get("domain") == d else ""}>{d.replace("_", " ").title()}</option>'
        for d in domains
    )
    level_opts = "".join(
        f'<option value="{l}" {"selected" if str(f.get("level", "")) == str(l) else ""}>Level {l}</option>'
        for l in range(1, 5)
    )

    content = f"""
    {err_html}{ok_html}
    <form method="post" action="/submit/method">
        <table style="max-width:700px;">
            <tr><td style="color:#777;width:140px;padding:8px;">Name *</td>
                <td><input type="text" name="name" value="{_esc(f.get('name', ''))}" required style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Domain *</td>
                <td><select name="domain" required>{domain_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Level *</td>
                <td><select name="level" required>{level_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Description *</td>
                <td><textarea name="description" rows="4" required style="width:100%;">{_esc(f.get('description', ''))}</textarea></td></tr>
            <tr><td style="color:#777;padding:8px;">Examples</td>
                <td><input type="text" name="examples" value="{_esc(f.get('examples', ''))}" placeholder="comma-separated" style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Prerequisites</td>
                <td><input type="text" name="prerequisites" value="{_esc(f.get('prerequisites', ''))}" placeholder="comma-separated method IDs" style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Compatible With</td>
                <td><input type="text" name="compatible_with" value="{_esc(f.get('compatible_with', ''))}" placeholder="comma-separated method IDs" style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Submitter</td>
                <td><input type="text" name="submitter" value="{_esc(f.get('submitter', 'anonymous'))}" style="width:100%;"></td></tr>
        </table>
        <button type="submit" style="margin-top:12px;padding:10px 28px;">Submit Method</button>
    </form>
    """
    return _base_page("Submit Method", content, "submit", lang=lang, viewer_addr=viewer_addr)


def render_submit_problem(form: dict | None = None, errors: list[str] | None = None, success: str = "", lang: str = "en", viewer_addr: str = "") -> str:
    """Render the problem submission form."""
    f = form or {}
    err_html = "".join(f'<p style="color:#ef4444;margin:4px 0;">{_esc(e)}</p>' for e in (errors or []))
    ok_html = f'<p style="color:#22c55e;margin:8px 0;">{_esc(success)}</p>' if success else ""

    domains = ["medicine", "energy", "environment", "information", "materials", "society",
               "transportation", "agriculture", "space", "other"]
    domain_opts = "".join(
        f'<option value="{d}" {"selected" if f.get("domain") == d else ""}>{d.title()}</option>'
        for d in domains
    )
    mat_opts = "".join(
        f'<option value="{l}" {"selected" if str(f.get("maturity", "")) == str(l) else ""}>Level {l} — {["","Only problem description","Partial solutions, poor results","Solutions exist but too costly","Bottleneck clear, path unknown"][l]}</option>'
        for l in range(1, 5)
    )
    constraint_opts = ["physical_limit", "resource", "time", "complexity", "ethical"]
    constraint_html = "".join(
        f'<label style="margin-right:12px;"><input type="checkbox" name="constraints" value="{c}" {"checked" if c in f.get("constraints", []) else ""}> {c.replace("_", " ").title()}</label>'
        for c in constraint_opts
    )

    content = f"""
    {err_html}{ok_html}
    <form method="post" action="/submit/problem">
        <table style="max-width:700px;">
            <tr><td style="color:#777;width:140px;padding:8px;">Title *</td>
                <td><input type="text" name="title" value="{_esc(f.get('title', ''))}" required style="width:100%;"></td></tr>
            <tr><td style="color:#777;padding:8px;">Domain *</td>
                <td><select name="domain" required>{domain_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Description *</td>
                <td><textarea name="description" rows="4" required style="width:100%;">{_esc(f.get('description', ''))}</textarea></td></tr>
            <tr><td style="color:#777;padding:8px;">Maturity</td>
                <td><select name="maturity">{mat_opts}</select></td></tr>
            <tr><td style="color:#777;padding:8px;">Constraint Types</td>
                <td>{constraint_html}</td></tr>
            <tr><td style="color:#777;padding:8px;">Submitter</td>
                <td><input type="text" name="submitter" value="{_esc(f.get('submitter', 'anonymous'))}" style="width:100%;"></td></tr>
        </table>
        <button type="submit" style="margin-top:12px;padding:10px 28px;">Submit Problem</button>
    </form>
    """
    return _base_page("Submit Problem", content, "submit", lang=lang, viewer_addr=viewer_addr)


def render_submissions(db: LeaderboardDB, lang: str = "en", viewer_addr: str = "") -> str:
    """Render the pending submissions list (operator review page)."""
    pending = db.get_pending_submissions()
    total = db.total_pending()

    if not pending:
        content = '<div class="empty">No pending submissions.</div>'
        return _base_page("Submissions", content, "submit", lang=lang, viewer_addr=viewer_addr)

    rows = []
    for sub in pending:
        data = json.loads(sub["data"])
        preview = _esc(str(data)[:120])
        sub_id = sub["id"]
        stype = sub["type"]
        submitter = _esc(sub.get("submitter", "")[:16])
        rows.append(f"""
        <tr>
            <td>{sub_id}</td>
            <td><span style="background:#e8f0fe;color:#2563eb;padding:2px 8px;border-radius:3px;font-size:12px;">{stype}</span></td>
            <td style="font-size:12px;max-width:300px;overflow:hidden;">{preview}</td>
            <td>{submitter}</td>
            <td>
                <a href="/web/submissions?approve={sub_id}" style="color:#22c55e;margin-right:8px;">Approve</a>
                <a href="/web/submissions?reject={sub_id}" style="color:#ef4444;">Reject</a>
            </td>
        </tr>""")

    content = f"""
    <p style="color:#777;margin-bottom:12px;">{total} pending submission(s)</p>
    <table>
    <thead><tr><th>ID</th><th>Type</th><th>Preview</th><th>Submitter</th><th>Action</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
    </table>
    """
    return _base_page("Submissions", content, "submit", lang=lang, viewer_addr=viewer_addr)


# ------------------------------------------------------------------
# Blockchain Buffer Zone Pages
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# Settings Page
# ------------------------------------------------------------------

def render_settings(path: str = "", lang: str = "en", viewer_addr: str = "",
                    saved: bool = False, error: str = "") -> str:
    """Render the system configuration settings page with pre-filled form."""
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


# ------------------------------------------------------------------
# Agent Assistant Chat UI
# ------------------------------------------------------------------

def _agent_category_sections(lang: str = "en") -> str:
    """Render categorized feature cards with tooltip descriptions.

    Each category is a <details> block containing a horizontal row of compact cards.
    Cards show only icon + name; a tooltip appears on hover with a full description.
    """
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
            # Try to get tooltip from the _T dict directly
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
    """Render the agent chat interface page."""
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

    import json
    conv_json = json.dumps(conversation, ensure_ascii=False)

    sending_text = _t("agent.sending", lang)

    # Build sidebar with user info
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
