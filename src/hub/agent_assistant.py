"""Intelligent agent assistant: LLM-powered intent recognition + keyword fallback.

Architecture
------------
1. If an API key is configured, the user message is sent to an LLM with a
   system prompt that enumerates every available tool and its parameters.
   The LLM returns structured JSON: either a tool invocation or a chat response.

2. If the LLM call fails (timeout, parse error, no API key), the agent falls
   back to pure keyword matching (same 18 intents as before).

Flow::

    user message
      → LLM (structured JSON)
        → valid tool intent  → execute handler → format reply
        → "chat" intent      → return LLM's reply directly
      → on failure → keyword matching → execute handler
"""
from __future__ import annotations

import json
import re
import time
from typing import Optional

from src.hub.leaderboard import LeaderboardDB
from src.hub.peer import PeerManager
from src.engine.models import EvalDimension, Domain

# ---------------------------------------------------------------------------
# System prompt — describes every tool the LLM can invoke
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are the intelligent assistant for HammerWorld (創意挖礦網絡), a decentralized
idea-mining platform. Your job is to understand the user's intent in natural
language (English or Chinese) and return a structured JSON response.

RESPONSE FORMAT
===============
You MUST respond with ONLY a JSON object (no markdown fences, no explanations):

## Tool invocation:
{
  "intent": "<tool_name>",
  "params": { <tool_params> },
  "message_zh": "<简短中文回复告诉用户正在做什么>",
  "message_en": "<short English reply>"
}

## Direct chat (greeting, chit-chat, unclear requests):
{
  "intent": "chat",
  "response_zh": "<中文回复>",
  "response_en": "<English reply>"
}

AVAILABLE TOOLS
===============

1. dashboard
   - description: Show project overview (total entries, peer count, token balance)
   - params: {}

2. leaderboard
   - description: Show ranking of method×problem combinations
   - params: {"dimension"?: str, "domain"?: str, "limit"?: int}
   - dimensions: elegance, weirdness, human_feasibility, ai_feasibility, novelty, analogy_distance, scaling_potential, side_effects
   - domains: medicine, energy, environment, information, materials, society, mathematics

3. search
   - description: Search across methods and problems
   - params: {"query": str, "dimension"?: str}

4. random_draw
   - description: Randomly draw entries from the leaderboard
   - params: {"count"?: int, "dimension"?: str, "domain"?: str}

5. token_balance
   - description: Check IDEA token balance
   - params: {}

6. faucet
   - description: Claim free IDEA tokens (rate-limited)
   - params: {}

7. pay_view
   - description: Pay 10 IDEA to unlock an AI analysis
   - params: {"combo_id": str}

8. pay_draw
   - description: Pay 5 IDEA for random draw access
   - params: {}

9. pay_leaderboard
   - description: Pay 20 IDEA to unlock a leaderboard for 24h
   - params: {"dimension"?: str, "domain"?: str}

10. entry_detail
    - description: Show details of a specific method×problem combination
    - params: {"combo_id": str}

11. rate
    - description: Rate a combination 1-5 stars
    - params: {"combo_id": str, "rating": int (1-5)}

12. peers
    - description: Show connected P2P network nodes
    - params: {}

13. identity
    - description: Show current user address
    - params: {}

14. collections
    - description: Browse community collections (methods or problems)
    - params: {"type"?: "method" | "problem"}

15. math_zone
    - description: Explore the math research problem space
    - params: {}

16. buffer_zone
    - description: Check buffer zone consensus status
    - params: {}

17. mine
    - description: Run an idea mining evaluation. When the user asks to mine, do NOT run immediately. Instead, respond with TWO clear choices: (A) Default config — show current default settings (model, all domains, all levels, batch=1) and tell them to reply "default" to run; (B) Custom config — tell them to reply "custom" to get a configuration form. Only skip this two-option flow if the user already said "default" or "custom".
    - params: {"action"?: "default" | "custom"}

18. buffer_classify
    - description: Vote on a pending buffer zone submission — classify its domain
    - params: {"submission_id"?: str}

19. submit_method
    - description: Explain how to submit a new method
    - params: {}

18. submit_problem
    - description: Explain how to submit a new problem
    - params: {}

19. config
    - description: Show current system configuration (API key, model, address). When users ask about configuration options, settings, or customization, respond with TWO clear choices: (A) Default config — show the current values; (B) Custom config — tell them to visit /web/settings. Always list the current values explicitly when showing default config.
    - params: {}

RULES
=====
- Understand both English and Chinese naturally.
- If the user is just saying hello, asking who you are, or being vague,
  use "chat" intent with a friendly introduction.
- For "help" or "what can you do", use "chat" intent.
- Extract dimensions and domains from context (e.g. "elegance" or "优雅").
- If the user says "top N" or "show N", pass limit=N to leaderboard/search.
- Always set message_zh and message_en (for tool intents) so the UI can display
  a brief status message before the handler result is appended.
"""

# ---------------------------------------------------------------------------
# Keyword-matching fallback patterns
# ---------------------------------------------------------------------------

_INTENTS: dict[str, list[str]] = {
    "help":             ["help", "what can you do", "功能", "能做什么", "介绍", "命令", "guide"],
    "dashboard":        ["dashboard", "overview", "stats", "status", "仪表盘", "首页", "总览", "统计"],
    "identity":         ["who am i", "my address", "my id", "身份", "地址", "我是谁", "我的地址"],
    "leaderboard":      ["leaderboard", "top", "ranking", "rank", "排行", "排名", "排行榜", "前十"],
    "search":           ["search", "find", "query", "lookup", "搜索", "查找", "查询", "找"],
    "random_draw":      ["random", "draw", "lucky", "抽奖", "随机", "抽取", "抽一个"],
    "token_balance":    ["balance", "token", "wallet", "余额", "代币", "钱包", "我有多少"],
    "faucet":           ["faucet", "get token", "free token", "claim",
                         "领取免费代币", "领取代币", "领取", "免费"],
    "pay_view":         ["pay view", "unlock view", "pay to view", "支付查看", "解锁"],
    "pay_draw":         ["pay draw", "pay random", "付费抽取", "支付抽奖"],
    "pay_leaderboard":  ["pay leaderboard", "unlock leaderboard", "解锁排行", "付费排行"],
    "submit_method":    ["submit method", "new method", "add method", "提交方法", "新方法", "添加方法"],
    "submit_problem":   ["submit problem", "new problem", "add problem", "提交问题", "新问题", "添加问题"],
    "entry_detail":     ["entry", "detail", "view entry", "show entry", "详情", "查看", "条目"],
    "rate":             ["rate", "rating", "review", "评分", "评价", "打分"],
    "peers":            ["peer", "peers", "network", "nodes", "connected", "节点", "网络", "连接"],
    "collections":      ["collection", "marketplace", "matrix", "合集", "市场", "集合"],
    "math_zone":        ["math", "research", "数学", "研究", "数学区"],
    "mine":             ["mine", "mining", "start mining", "挖矿", "挖掘", "挖掘创意", "idea mining",
                         "默认配置挖矿", "自定义挖矿", "立即挖矿", "自定义", "custom", "默认", "default"],
    "buffer_classify":  ["classify submission", "classify buffer", "vote on submission", "缓冲区分", "投票分类", "分类投票"],
    "buffer_zone":      ["buffer", "consensus", "缓冲", "共识"],
    "config":           ["config", "settings", "configuration", "setup", "配置", "设置", "设定", "自定义"],
}

# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class AgentAssistant:
    """Natural-language to tool-call assistant (LLM + keyword fallback).

    Usage::

        agent = AgentAssistant(db, token_gate, peer_manager)
        reply = agent.process("show me the leaderboard", viewer_addr="0x...", lang="en")
    """

    def __init__(
        self,
        db: LeaderboardDB,
        token_gate=None,
        peer_manager: Optional[PeerManager] = None,
    ):
        self.db = db
        self.token_gate = token_gate
        self.peer_manager = peer_manager
        self.last_form_html: Optional[str] = None  # Set by handlers to trigger inline form

        # Try to set up LLM provider
        self._llm = None
        self._llm_model = None
        try:
            from src.evaluation.providers import OpenAIProvider
            from src.engine.config import HammerConfig
            cfg = HammerConfig.load()
            if cfg.api_key:
                self._llm = OpenAIProvider(
                    api_key=cfg.api_key,
                    api_base=cfg.api_base,
                    model=cfg.get_model("agent"),
                )
                self._llm_model = cfg.get_model("agent")
        except Exception:
            pass  # No LLM available; pure keyword fallback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, message: str, viewer_addr: str = "", lang: str = "zh") -> str:
        """Process a natural-language message and return a response."""
        msg = message.strip()
        if not msg:
            return self._t("common.no_entries", lang)

        # 1. Try LLM first
        if self._llm is not None:
            result = self._try_llm(msg, viewer_addr, lang)
            if result is not None:
                return result

        # 2. Fallback: keyword matching
        intent = self._detect_intent(msg)
        handler = getattr(self, f"_handle_{intent}", None)
        if handler is None:
            return self._t("agent.unknown", lang, msg=msg)
        try:
            return handler(msg, viewer_addr, lang)
        except Exception as exc:
            return self._t("agent.error", lang, intent=intent, error=str(exc))

    # ------------------------------------------------------------------
    # LLM-powered intent resolution
    # ------------------------------------------------------------------

    def _try_llm(self, msg: str, viewer_addr: str, lang: str) -> Optional[str]:
        """Attempt to process *msg* via LLM. Returns None if it fails."""
        try:
            raw = self._llm.generate(
                system_prompt=self._build_system_prompt(viewer_addr, lang),
                user_prompt=msg,
            )
        except Exception:
            return None  # fallback

        # Parse JSON
        data = self._parse_llm_response(raw)
        if data is None:
            return None

        intent = data.get("intent", "")

        if intent == "chat":
            return data.get(f"response_{lang}") or data.get("response_en") or ""

        # Tool invocation
        params = data.get("params", {}) or {}
        handler = getattr(self, f"_handle_{intent}", None)
        if handler is None:
            return None

        try:
            # Show status message first
            status_msg = data.get(f"message_{lang}") or data.get("message_en") or ""
            result = handler(msg, viewer_addr, lang, **params)
            if status_msg:
                return f"{status_msg}\n{result}"
            return result
        except Exception as exc:
            return self._t("agent.error", lang, intent=intent, error=str(exc))

    def _build_system_prompt(self, viewer_addr: str, lang: str) -> str:
        """Build the system prompt with user context."""
        addr_info = f"\nCurrent user address: {viewer_addr}" if viewer_addr else ""
        lang_info = f"\nCurrent UI language: {'Chinese' if lang == 'zh' else 'English'}"
        return _SYSTEM_PROMPT + addr_info + lang_info

    @staticmethod
    def _parse_llm_response(raw: str) -> Optional[dict]:
        """Extract JSON from an LLM response (handles markdown fences)."""
        text = raw.strip()
        # Remove markdown code fences
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    # Keyword-based intent detection (fallback)
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_intent(message: str) -> str:
        """Return the best-matching intent key for *message* (longest match wins)."""
        lower = message.lower().strip()
        best_intent = "help"
        best_len = 0
        for intent, patterns in _INTENTS.items():
            for pat in patterns:
                if pat in lower and len(pat) > best_len:
                    best_len = len(pat)
                    best_intent = intent
        return best_intent

    @staticmethod
    def _extract_count(msg: str, default: int = 10) -> int:
        m = re.search(r"(\d+)", msg)
        if m:
            n = int(m.group(1))
            return max(1, min(n, 100))
        cn_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                  "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        for ch, n in cn_map.items():
            if ch in msg:
                return n
        return default

    @staticmethod
    def _extract_dimension(msg: str) -> Optional[EvalDimension]:
        for d in EvalDimension:
            if d.value.lower() in msg.lower() or d.name.lower() in msg.lower():
                return d
        mapping = {
            "优雅": EvalDimension.ELEGANCE,
            "古怪": EvalDimension.WEIRDNESS,
            "人可行": EvalDimension.HUMAN_FEASIBILITY,
            "ai可行": EvalDimension.AI_FEASIBILITY,
            "新颖": EvalDimension.NOVELTY,
            "类比": EvalDimension.ANALOGY_DISTANCE,
            "扩展": EvalDimension.SCALING_POTENTIAL,
            "副作用": EvalDimension.SIDE_EFFECTS,
        }
        for cn, dim in mapping.items():
            if cn in msg:
                return dim
        return None

    @staticmethod
    def _extract_domain(msg: str) -> Optional[Domain]:
        for d in Domain:
            if d.value.lower() in msg.lower():
                return d
        cn_mapping = {
            "医学": Domain.MEDICINE, "医疗": Domain.MEDICINE,
            "能源": Domain.ENERGY,
            "环境": Domain.ENVIRONMENT,
            "信息": Domain.INFORMATION,
            "材料": Domain.MATERIALS,
            "社会": Domain.SOCIETY,
            "数学": Domain.MATHEMATICS,
        }
        for cn, dom in cn_mapping.items():
            if cn in msg:
                return dom
        return None

    @staticmethod
    def _extract_combo_id(msg: str) -> str:
        m = re.search(r"combo_[a-zA-Z0-9_]+", msg)
        return m.group(0) if m else ""

    @staticmethod
    def _extract_rating(msg: str) -> int:
        m = re.search(r"\b([1-5])\b", msg)
        return int(m.group(1)) if m else 0

    # ------------------------------------------------------------------
    # Intent handlers (same interface: (msg, viewer_addr, lang) -> str)
    # Some also accept **kwargs from LLM params.
    # ------------------------------------------------------------------

    def _handle_mine(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        """Mining flow: show config + two options, or run with chosen settings."""
        from src.engine.config import HammerConfig
        cfg = HammerConfig.load()
        if not cfg.api_key:
            return self._t("agent.mine_no_key", lang)

        lower = msg.lower()

        # Branch 1: User chose default → run immediately
        if kw.get("action") == "default" or any(x in lower for x in ["default", "默认", "立即", "now", "run"]):
            return self._run_mine(viewer_addr, lang)

        # Branch 2: User chose custom → show form
        if kw.get("action") == "custom" or any(x in lower for x in ["custom", "自定义", "自定", "配置表单"]):
            self.last_form_html = self._build_mine_form(lang, cfg)
            return self._t("agent.mine_custom_form", lang)

        # Branch 3: First contact → show current config + two options
        return self._t("agent.mine_config", lang,
                      default_model=cfg.get_model("mining") or "(default)",
                      api_base=cfg.api_base or "(default)")

    def _run_mine(self, viewer_addr: str, lang: str, **kw) -> str:
        """Execute the actual mining evaluation with given params."""
        try:
            from src.engine.config import HammerConfig
            cfg = HammerConfig.load()
            from src.engine.loader import load_methods, load_problems
            from src.engine.combiner import generate_combinations
            from src.evaluation.scorer import EvaluationPipeline
            from src.evaluation.providers import OpenAIProvider

            methods = load_methods()
            problems = load_problems()

            # Apply domain filter
            domain = kw.get("domain", "")
            if domain:
                problems = [p for p in problems if p.domain.value == domain]
                if not problems:
                    return self._t("agent.mine_no_match", lang, filter=f"domain={domain}")

            # Apply method level filter
            level = kw.get("level", "")
            if level:
                try:
                    lv = int(level)
                    methods = [m for m in methods if m.level.value == lv]
                    if not methods:
                        return self._t("agent.mine_no_match", lang, filter=f"level={lv}")
                except ValueError:
                    pass

            batch = int(kw.get("batch_size", 1))
            batch = max(1, min(batch, 10))

            model = kw.get("model", "") or cfg.get_model("mining")

            combos = generate_combinations(methods, problems, block_height=0,
                                           user_address=viewer_addr or "0xAGENT",
                                           nonce=int(time.time() * 1000), batch_size=batch)
            if not combos:
                return self._t("agent.mine_no_match", lang, filter="")

            pipeline = EvaluationPipeline(OpenAIProvider(
                api_key=cfg.api_key, api_base=cfg.api_base, model=model))

            results = []
            for combo in combos:
                result = pipeline.evaluate(combo)
                entry = self.db.insert(combo, miner_addr=viewer_addr or "0xAGENT")
                scores = result.analysis.scores
                best = max(scores, key=lambda s: s.score)
                results.append((combo, best, entry.run_id))

            if batch == 1:
                combo, best, run_id = results[0]
                return self._t("agent.mine_ok", lang,
                              method=combo.method.name, problem=combo.problem.title,
                              combo_id=run_id,
                              dim=best.dimension.value, score=best.score)
            else:
                lines = [self._t("agent.mine_ok_batch", lang, n=len(results))]
                for combo, best, run_id in results:
                    lines.append(f"  · {combo.method.name} × {combo.problem.title} "
                                f"[{best.dimension.value}: {best.score:.1f}]"
                                f"\n    ID: {run_id}")
                return "\n".join(lines)
        except Exception as e:
            return self._t("agent.mine_fail", lang, error=str(e))

    def _build_mine_form(self, lang: str, cfg) -> str:
        """Build an HTML form for custom mining configuration."""
        from src.engine.loader import load_problems

        problems = load_problems()
        domains = sorted(set(p.domain.value for p in problems))

        domain_opts = ""
        for d in domains:
            domain_opts += f'<option value="{d}">{d}</option>'

        default_model = cfg.get_model("mining") or ""
        api_base = cfg.api_base or "https://api.openai.com/v1"

        labels = {
            "domain": {"en": "Problem Domain", "zh": "问题领域"},
            "level": {"en": "Method Level", "zh": "方法等级"},
            "batch": {"en": "Batch Size", "zh": "并发数量"},
            "model": {"en": "Model", "zh": "模型"},
            "submit": {"en": "Start Mining", "zh": "开始挖矿"},
            "cancel": {"en": "Use Default", "zh": "使用默认"},
            "domain_desc": {"en": "Filter problems by domain (empty = all)", "zh": "按领域筛选问题（空白=全部）"},
            "level_desc": {"en": "Filter methods by level 1-4 (empty = all)", "zh": "按等级筛选方法 1-4（空白=全部）"},
            "batch_desc": {"en": "Number of combos to evaluate (1-10)", "zh": "评估组合数量 (1-10)"},
            "model_desc": {"en": "AI model for evaluation", "zh": "评估使用的 AI 模型"},
        }
        t = lambda k: labels[k].get(lang, labels[k]["en"])

        return f"""
        <form class="inline-form" id="mine-custom-form" onsubmit="return submitMineForm(event)">
            <div class="inline-field">
                <label>{t("domain")} <span class="field-desc">{t("domain_desc")}</span></label>
                <select name="domain"><option value="">-- all --</option>{domain_opts}</select>
            </div>
            <div class="inline-field">
                <label>{t("level")} <span class="field-desc">{t("level_desc")}</span></label>
                <select name="level">
                    <option value="">-- all --</option>
                    <option value="1">1 — 基础</option><option value="2">2 — 进阶</option>
                    <option value="3">3 — 高级</option><option value="4">4 — 专家</option>
                </select>
            </div>
            <div class="inline-field">
                <label>{t("batch")} <span class="field-desc">{t("batch_desc")}</span></label>
                <input type="number" name="batch_size" value="1" min="1" max="10" style="width:80px;">
            </div>
            <div class="inline-field">
                <label>{t("model")} <span class="field-desc">{t("model_desc")}</span></label>
                <input type="text" name="model" value="{default_model}" placeholder="{api_base}" style="width:200px;">
            </div>
            <div class="inline-actions">
                <button type="submit" class="btn-primary">{t("submit")}</button>
                <button type="button" onclick="document.getElementById('chat-input').value='start mining default';document.getElementById('chat-form').requestSubmit();">{t("cancel")}</button>
            </div>
        </form>"""

    def _handle_buffer_classify(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        """Show pending buffer submissions or guide classification."""
        try:
            pending = self.db.get_pending_submissions(limit=5)
        except Exception:
            pending = []
        if not pending:
            return self._t("agent.buffer_no_pending", lang)
        lines = [self._t("agent.buffer_classify_header", lang, n=len(pending))]
        for s in pending:
            sid = s.get("id", "?")
            title = s.get("title", s.get("combo_id", "?"))
            lines.append(f"  · #{sid} {title}")
        lines.append("")
        lines.append(self._t("agent.buffer_classify_hint", lang))
        return "\n".join(lines)

    def _handle_help(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        return self._get_intro_text(lang)

    def _handle_dashboard(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        db = self.db
        total = db.total_entries()
        peer_count = len(self.peer_manager.get_peers()) if self.peer_manager else 0
        bal = ""
        if self.token_gate and viewer_addr:
            summary = self.token_gate.get_viewer_summary(viewer_addr)
            bal = self._t("agent.dash_bal", lang,
                          bal=summary.get("balance", 0),
                          staked=summary.get("staked", 0))
        return self._t("agent.dash", lang, entries=total, peers=peer_count, bal=bal)

    def _handle_identity(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        if not viewer_addr:
            return self._t("agent.no_addr", lang)
        return self._t("agent.identity", lang, addr=viewer_addr)

    def _handle_leaderboard(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        dim = kw.get("dimension") or self._extract_dimension(msg)
        domain = kw.get("domain") or self._extract_domain(msg)
        limit = kw.get("limit") or self._extract_count(msg, 10)
        if isinstance(dim, str):
            try:
                dim = EvalDimension(dim)
            except ValueError:
                dim = None
        if isinstance(domain, str):
            try:
                domain = Domain(domain)
            except ValueError:
                domain = None

        entries = self.db.get_top(dimension=dim, domain=domain, limit=limit)
        if not entries:
            return self._t("agent.lb_empty", lang)
        lines = [self._t("agent.lb_header", lang)]
        for i, e in enumerate(entries, 1):
            lines.append(f"  {i}. {e.method_name} × {e.problem_title}  "
                         f"[{e.best_dimension}: {e.best_score:.1f}]")
        return "\n".join(lines)

    def _handle_search(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        query = kw.get("query", "")
        if not query:
            query = self._strip_intent_prefix(msg, ["search", "find", "query",
                                                     "搜索", "查找", "查询", "找"])
        if not query or len(query) < 2:
            return self._t("agent.search_hint", lang)
        dim = kw.get("dimension") or self._extract_dimension(msg)
        if isinstance(dim, str):
            try:
                dim = EvalDimension(dim)
            except ValueError:
                dim = None
        entries = self.db.search(query, dimension=dim, limit=10)
        if not entries:
            return self._t("agent.search_empty", lang, query=query)
        lines = [self._t("agent.search_header", lang, query=query, n=len(entries))]
        for e in entries:
            lines.append(f"  · {e.method_name} × {e.problem_title}  [{e.best_score:.1f}]")
        return "\n".join(lines)

    def _handle_random_draw(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        dim = kw.get("dimension") or self._extract_dimension(msg)
        domain = kw.get("domain") or self._extract_domain(msg)
        count = kw.get("count") or self._extract_count(msg, 3)
        if isinstance(dim, str):
            try:
                dim = EvalDimension(dim)
            except ValueError:
                dim = None
        if isinstance(domain, str):
            try:
                domain = Domain(domain)
            except ValueError:
                domain = None

        tg = self.token_gate
        if tg and viewer_addr and not tg.has_draw_access(viewer_addr):
            result = tg.pay_for_random_draw(viewer_addr)
            if not result.get("ok"):
                return self._t("agent.draw_insufficient", lang)

        viewer = viewer_addr if viewer_addr else ""
        draw = self.db.random_draw(dimension=dim, domain=domain,
                                    draw_count=count, viewer_addr=viewer)
        if not draw.entries:
            return self._t("agent.draw_empty", lang)
        lines = [self._t("agent.draw_header", lang, n=len(draw.entries), board=draw.board_name)]
        for e in draw.entries:
            lines.append(f"  · {e.method_name} × {e.problem_title}  [{e.best_score:.1f}]")
        return "\n".join(lines)

    def _handle_token_balance(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        if not viewer_addr:
            return self._t("agent.no_addr", lang)
        if not self.token_gate:
            return self._t("agent.token_unavail", lang)
        summary = self.token_gate.get_viewer_summary(viewer_addr)
        return self._t("agent.balance", lang,
                       bal=summary.get("balance", 0),
                       staked=summary.get("staked", 0),
                       earned=summary.get("total_earned", 0),
                       spent=summary.get("total_spent", 0))

    def _handle_faucet(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        if not viewer_addr:
            return self._t("agent.no_addr", lang)
        if not self.token_gate:
            return self._t("agent.token_unavail", lang)
        tg = self.token_gate
        minted = tg.token.faucet(viewer_addr, tg.FAUCET_AMOUNT)
        if minted > 0:
            return self._t("agent.faucet_ok", lang, amount=minted)
        return self._t("agent.faucet_limited", lang)

    def _handle_pay_view(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        combo_id = kw.get("combo_id") or self._extract_combo_id(msg)
        if not combo_id:
            return self._t("agent.need_combo_id", lang)
        if not viewer_addr or not self.token_gate:
            return self._t("agent.no_addr", lang)
        result = self.token_gate.pay_for_view(viewer_addr, combo_id)
        if result.get("ok"):
            return self._t("agent.pay_view_ok", lang, combo_id=combo_id)
        return self._t("agent.pay_view_fail", lang, error=result.get("error", "?"))

    def _handle_pay_draw(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        if not viewer_addr or not self.token_gate:
            return self._t("agent.no_addr", lang)
        result = self.token_gate.pay_for_random_draw(viewer_addr)
        if result.get("ok"):
            return self._t("agent.pay_draw_ok", lang)
        return self._t("agent.pay_draw_fail", lang, error=result.get("error", "?"))

    def _handle_pay_leaderboard(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        dim = kw.get("dimension") or self._extract_dimension(msg) or EvalDimension.ELEGANCE
        domain = kw.get("domain") or self._extract_domain(msg) or Domain.MEDICINE
        if isinstance(dim, str):
            try:
                dim = EvalDimension(dim)
            except ValueError:
                dim = EvalDimension.ELEGANCE
        if isinstance(domain, str):
            try:
                domain = Domain(domain)
            except ValueError:
                domain = Domain.MEDICINE
        board = f"{dim.value}_{domain.value}"
        if not viewer_addr or not self.token_gate:
            return self._t("agent.no_addr", lang)
        result = self.token_gate.pay_for_leaderboard(viewer_addr, board)
        if result.get("ok"):
            return self._t("agent.pay_lb_ok", lang, board=board)
        return self._t("agent.pay_lb_fail", lang, error=result.get("error", "?"))

    def _handle_submit_method(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        return self._t("agent.submit_method_hint", lang)

    def _handle_submit_problem(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        return self._t("agent.submit_problem_hint", lang)

    def _handle_entry_detail(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        combo_id = kw.get("combo_id") or self._extract_combo_id(msg)
        if not combo_id:
            return self._t("agent.need_combo_id", lang)
        entry = self.db._get_by_id(combo_id)
        if not entry:
            return self._t("agent.entry_missing", lang, combo_id=combo_id)
        lines = [
            self._t("agent.entry_header", lang, combo_id=combo_id),
            f"  {self._t('th.method', lang)}: {entry.method_name}",
            f"  {self._t('th.problem', lang)}: {entry.problem_title}",
            f"  {self._t('th.domain', lang)}: {entry.problem_domain}",
            f"  {self._t('th.best_dim', lang)}: {entry.best_dimension} = {entry.best_score:.1f}",
        ]
        return "\n".join(lines)

    def _handle_rate(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        combo_id = kw.get("combo_id") or self._extract_combo_id(msg)
        rating = kw.get("rating") or self._extract_rating(msg)
        if not combo_id:
            return self._t("agent.need_combo_id", lang)
        if not (1 <= rating <= 5):
            return self._t("agent.rate_hint", lang)
        if not viewer_addr or not self.token_gate:
            return self._t("agent.no_addr", lang)
        result = self.token_gate.rate_analysis(viewer_addr, combo_id, rating)
        if result.get("ok"):
            return self._t("agent.rate_ok", lang, rating=rating, avg=result.get("avg_rating", 0))
        return self._t("agent.rate_fail", lang, error=result.get("error", "?"))

    def _handle_peers(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        if not self.peer_manager:
            return self._t("agent.peers_unavail", lang)
        peers = self.peer_manager.get_peers()
        if not peers:
            return self._t("agent.peers_empty", lang)
        now = time.time()
        lines = [self._t("agent.peers_header", lang, n=len(peers))]
        for p in peers:
            ago = int(now - p.last_seen)
            lines.append(f"  {p.peer_id} @ {p.address}:{p.port}  ({ago}s ago)")
        return "\n".join(lines)

    def _handle_collections(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        ctype = kw.get("type")
        if ctype is None:
            ctype = "method" if "method" in msg.lower() or "方法" in msg else None
            ctype = "problem" if "problem" in msg.lower() or "问题" in msg else ctype
        cols = self.db.get_collections(ctype=ctype, sort_by="stars", limit=10) if ctype \
            else self.db.get_collections(sort_by="stars", limit=10)
        if not cols:
            return self._t("agent.collections_empty", lang)
        lines = [self._t("agent.collections_header", lang, n=len(cols))]
        for c in cols:
            lines.append(f"  · {c['name']} ({c.get('stars', 0)}★) — {c.get('description', '')[:60]}")
        return "\n".join(lines)

    def _handle_math_zone(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        problems = self.db.get_math_problems()
        if not problems:
            return self._t("agent.math_empty", lang)
        lines = [self._t("agent.math_header", lang, n=len(problems))]
        for p in problems:
            lines.append(f"  · #{p['id']} {p['title']} ({p.get('status', 'active')})")
        return "\n".join(lines)

    def _handle_buffer_zone(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        pending = self.db.total_pending() if hasattr(self.db, "total_pending") else 0
        total = self.db.total_entries()
        return self._t("agent.buffer", lang, pending=pending, total=total)

    def _handle_config(self, msg: str, viewer_addr: str, lang: str, **kw) -> str:
        """Show current configuration with default vs custom options."""
        try:
            from src.engine.config import HammerConfig
            cfg = HammerConfig.load()
        except Exception:
            cfg = None

        if cfg:
            api_key = cfg.api_key or self._t("agent.config.not_set", lang)
            if cfg.api_key and len(cfg.api_key) > 12:
                api_key = cfg.api_key[:8] + "..." + cfg.api_key[-4:]
            api_base = cfg.api_base or self._t("agent.config.not_set", lang)
            default_model = cfg.get_model("default") or self._t("agent.config.not_set", lang)
            agent_model = cfg.get_model("agent") or default_model
            mining_model = cfg.get_model("mining") or default_model
            triz_model = cfg.get_model("triz") or default_model
            address = cfg.address or self._t("agent.config.not_set", lang)
            if address and len(address) > 20:
                address = address[:10] + "..." + address[-6:]

            return self._t("agent.config.summary", lang,
                          api_key=api_key, api_base=api_base,
                          default_model=default_model, agent_model=agent_model,
                          mining_model=mining_model, triz_model=triz_model,
                          address=address)
        return self._t("agent.config.no_config", lang)

    # ------------------------------------------------------------------
    # Intro / Feature catalog
    # ------------------------------------------------------------------

    def _get_intro_text(self, lang: str) -> str:
        return self._t("agent.intro_full", lang)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_intent_prefix(msg: str, prefixes: list[str]) -> str:
        lower = msg.lower()
        for p in prefixes:
            if lower.startswith(p):
                rest = msg[len(p):].strip()
                if rest:
                    return rest
            if p in lower:
                idx = lower.index(p) + len(p)
                rest = msg[idx:].strip().lstrip(" 的:，, ")
                if rest:
                    return rest
        return ""

    @staticmethod
    def _t(key: str, lang: str, **kwargs) -> str:
        _T = {
            "common.no_entries":     {"en": "No entries yet.",                   "zh": "暂无条目。"},
            "agent.unknown":          {"en": "Sorry, I didn't understand: {msg}", "zh": "抱歉，我没理解: {msg}"},
            "agent.error":            {"en": "Error in {intent}: {error}",        "zh": "{intent} 出错了: {error}"},
            "agent.no_addr":          {"en": "Please log in first (enter your 0x address).", "zh": "请先登录（输入你的0x地址）。"},
            "agent.token_unavail":    {"en": "Token system not available.",       "zh": "代币系统不可用。"},
            "agent.need_combo_id":    {"en": "Please provide a combo ID (e.g. combo_xxx_xxx).", "zh": "请提供组合 ID (如 combo_xxx_xxx)。"},
            "agent.search_hint":      {"en": "Please provide a search term (e.g. 'search AI').", "zh": "请提供搜索词（如 '搜索 AI'）。"},
            "agent.rate_hint":        {"en": "Please provide a rating 1-5 and a combo ID.", "zh": "请提供 1-5 的评分和组合 ID。"},
            "agent.dash":             {"en": "Total entries: {entries} | Peers: {peers}\n{bal}",
                                       "zh": "总条目: {entries} | 节点: {peers}\n{bal}"},
            "agent.dash_bal":         {"en": "Your balance: {bal} (staked: {staked})",
                                       "zh": "你的余额: {bal} (质押: {staked})"},
            "agent.identity":         {"en": "Your address: {addr}",               "zh": "你的地址: {addr}"},
            "agent.lb_header":        {"en": "Leaderboard:",                       "zh": "排行榜："},
            "agent.lb_empty":         {"en": "No entries on the leaderboard.",     "zh": "排行榜暂无条目。"},
            "agent.search_header":    {"en": "Found {n} results for \"{query}\":",
                                       "zh": "找到 {n} 条 \"{query}\" 的结果："},
            "agent.search_empty":     {"en": "No results for \"{query}\".",        "zh": "未找到 \"{query}\" 的相关结果。"},
            "agent.draw_header":      {"en": "Drew {n} from {board}:",
                                       "zh": "从 {board} 抽取了 {n} 条："},
            "agent.draw_empty":       {"en": "No entries available for draw.",     "zh": "没有可抽取的条目。"},
            "agent.draw_insufficient": {"en": "Insufficient balance to draw. Try 'get tokens' first.",
                                        "zh": "余额不足，请先使用「领取免费代币」。"},
            "agent.balance":          {"en": "Balance: {bal} | Staked: {staked} | Earned: {earned} | Spent: {spent}",
                                       "zh": "余额: {bal} | 质押: {staked} | 收益: {earned} | 消费: {spent}"},
            "agent.faucet_ok":        {"en": "Claimed {amount} free IDEA tokens!",
                                       "zh": "已领取 {amount} 个免费 IDEA 代币！"},
            "agent.faucet_limited":   {"en": "Faucet rate-limited. Wait 1h or max 10 claims.",
                                       "zh": "水龙头已限流，需等待 1 小时或已达最大领取次数（10 次）。"},
            "agent.pay_view_ok":      {"en": "Unlocked {combo_id} for viewing!",   "zh": "已解锁 {combo_id} 的查看权限！"},
            "agent.pay_view_fail":    {"en": "Pay failed: {error}",                "zh": "支付失败: {error}"},
            "agent.pay_draw_ok":      {"en": "Draw payment successful! Now say 'draw'.", "zh": "支付成功！现在可以说「抽取」。"},
            "agent.pay_draw_fail":    {"en": "Draw payment failed: {error}",       "zh": "支付失败: {error}"},
            "agent.pay_lb_ok":        {"en": "Leaderboard {board} unlocked for 24h!",
                                       "zh": "排行榜 {board} 已解锁 24 小时！"},
            "agent.pay_lb_fail":      {"en": "Unlock failed: {error}",             "zh": "解锁失败: {error}"},
            "agent.submit_method_hint": {"en": "To submit a method, use the form at /web/submit/method\n\nFields: name, domain, level (1-4), description, examples, prerequisites.",
                                         "zh": "请通过 /web/submit/method 表单提交方法。\n\n字段：名称、领域、级别(1-4)、描述、示例、前置条件。"},
            "agent.submit_problem_hint": {"en": "To submit a problem, use the form at /web/submit/problem\n\nFields: title, domain, maturity (1-4), description, constraints.",
                                          "zh": "请通过 /web/submit/problem 表单提交问题。\n\n字段：标题、领域、成熟度(1-4)、描述、约束。"},
            "agent.entry_header":     {"en": "Entry: {combo_id}",                  "zh": "条目: {combo_id}"},
            "agent.entry_missing":    {"en": "Entry {combo_id} not found.",        "zh": "未找到条目 {combo_id}。"},
            "agent.rate_ok":          {"en": "Rated {rating}/5 OK! Avg: {avg:.1f}",
                                       "zh": "评分 {rating}/5 成功！平均分: {avg:.1f}"},
            "agent.rate_fail":        {"en": "Rate failed: {error}",               "zh": "评分失败: {error}"},
            "agent.peers_header":     {"en": "Connected peers ({n}):",
                                       "zh": "已连接节点 ({n})："},
            "agent.peers_empty":      {"en": "No peers connected.",                "zh": "暂无连接节点。"},
            "agent.peers_unavail":    {"en": "Peer manager not available.",        "zh": "节点管理器不可用。"},
            "agent.collections_header": {"en": "Top collections ({n}):",
                                         "zh": "热门合集 ({n})："},
            "agent.collections_empty": {"en": "No collections yet.",               "zh": "暂无合集。"},
            "agent.math_header":      {"en": "Math problems ({n}):",
                                       "zh": "数学问题 ({n})："},
            "agent.math_empty":       {"en": "No math problems yet.",              "zh": "暂无数学问题。"},
            "agent.mine_no_key":      {"en": "Mining requires an API key. Configure it in ~/.hammerworld/config:\n  api_key=sk-...\n  mining_model=gpt-4o\n\nThen run: python3 -m src.cli.main mine --batch 5",
                                       "zh": "挖矿需要 API 密钥。请在 ~/.hammerworld/config 中配置：\n  api_key=sk-...\n  mining_model=gpt-4o\n\n然后运行: python3 -m src.cli.main mine --batch 5"},
            "agent.mine_config":      {"en": "**⚙️ Mining Configuration**\n\n"
                                            "Default settings:\n"
                                            "  • Model: {default_model}\n"
                                            "  • API Base: {api_base}\n"
                                            "  • Problem Domain: all\n"
                                            "  • Method Level: all (1-4)\n"
                                            "  • Batch Size: 1\n\n"
                                            "**Two options:**\n"
                                            "  A) **Use defaults** — say \"default\" or \"立即挖矿\"\n"
                                            "  B) **Custom settings** — say \"custom\" or \"自定义\" to configure",
                                       "zh": "**⚙️ 挖矿配置**\n\n"
                                            "当前默认设置:\n"
                                            "  • 模型: {default_model}\n"
                                            "  • API 地址: {api_base}\n"
                                            "  • 问题领域: 全部\n"
                                            "  • 方法等级: 全部 (1-4)\n"
                                            "  • 并发数量: 1\n\n"
                                            "**两个选项:**\n"
                                            "  A) **使用默认配置** — 回复 \"默认\" 或 \"立即挖矿\"\n"
                                            "  B) **自定义配置** — 回复 \"自定义\" 打开配置表单"},
            "agent.mine_custom_form": {"en": "Fill in the form below to customize your mining run:",
                                       "zh": "请在下方表单中修改挖矿配置："},
            "agent.mine_ok":          {"en": "Mined: {method} × {problem}\nID: {combo_id}\nBest: {dim} = {score:.1f}\n\nTip: reply \"view {combo_id}\" to see details, or visit /web/my-entries",
                                       "zh": "挖矿完成: {method} × {problem}\nID: {combo_id}\n最佳维度: {dim} = {score:.1f}\n\n提示: 回复 \"view {combo_id}\" 查看详情，或访问 /web/my-entries"},
            "agent.mine_ok_batch":    {"en": "Mined {n} combos:",
                                       "zh": "挖矿完成，共 {n} 个组合："},
            "agent.mine_fail":        {"en": "Mining failed: {error}",
                                       "zh": "挖矿失败: {error}"},
            "agent.mine_no_match":    {"en": "No matching methods/problems (filter: {filter}).",
                                       "zh": "没有匹配的方法/问题（筛选条件: {filter}）。"},
            "agent.buffer_no_pending": {"en": "No pending submissions to classify.",
                                        "zh": "暂无待分类的提交。"},
            "agent.buffer_classify_header": {"en": "Pending submissions ({n}):",
                                              "zh": "待分类提交 ({n})："},
            "agent.buffer_classify_hint": {"en": "Use 'classify buffer' with a submission ID to vote. Or visit /web/buffer/pending",
                                            "zh": "使用提交 ID 进行投票分类，或访问 /web/buffer/pending"},
            "agent.buffer":           {"en": "Buffer Zone: {pending} pending · {total} total entries",
                                       "zh": "缓冲区: {pending} 待分类 · {total} 总条目"},
            "agent.config.summary":   {"en": "**Current Configuration**\n\n"
                                            "  API Key:       {api_key}\n"
                                            "  API Base:      {api_base}\n"
                                            "  Default Model: {default_model}\n"
                                            "  Agent Model:   {agent_model}\n"
                                            "  Mining Model:  {mining_model}\n"
                                            "  TRIZ Model:    {triz_model}\n"
                                            "  Address:       {address}\n\n"
                                            "**Two options:**\n"
                                            "  A) **Use defaults** — keep current settings as shown above\n"
                                            "  B) **Custom settings** — visit /web/settings to modify",
                                       "zh": "**当前配置**\n\n"
                                            "  API 密钥:      {api_key}\n"
                                            "  API 地址:      {api_base}\n"
                                            "  默认模型:      {default_model}\n"
                                            "  Agent 模型:    {agent_model}\n"
                                            "  挖矿模型:      {mining_model}\n"
                                            "  TRIZ 模型:     {triz_model}\n"
                                            "  地址:          {address}\n\n"
                                            "**两个选项：**\n"
                                            "  A) **使用默认配置** — 保持上述当前设置\n"
                                            "  B) **自定义配置** — 访问 /web/settings 进行修改"},
            "agent.config.not_set":   {"en": "(not set)",                 "zh": "（未设置）"},
            "agent.config.no_config": {"en": "No config file found. Create ~/.hammerworld/config to customize.",
                                       "zh": "未找到配置文件。创建 ~/.hammerworld/config 进行自定义。"},
            "agent.intro_full":       {"en": _INTRO_EN, "zh": _INTRO_ZH},
        }
        entry = _T.get(key, {})
        text = entry.get(lang) or entry.get("en") or key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        return text


# ============================================================================
# Feature catalog text
# ============================================================================

_INTRO_EN = """\
**HammerWorld Intelligent Assistant**

I can help you use all features of the Idea Mining Network.
Just tell me what you want in natural language!

**Dashboard** — `dashboard`, `stats`
  View total entries, peer connections, and your token summary.

**Leaderboard** — `leaderboard`, `top 10 medicine`
  Browse method×problem combinations filtered by domain/dimension.

**Search** — `search AI`, `find quantum`
  Search across methods, problems, and domains.

**Random Draw** — `random draw`, `draw 5`
  Randomly pull entries. View what you've drawn before.

**Tokens** — `balance`, `get tokens`, `faucet`
  View your IDEA balance, claim free tokens (rate-limited).

**Payments** — `pay to view combo_xxx`, `pay draw`, `unlock leaderboard`
  Pay IDEA tokens to unlock analysis, drawings, or leaderboards.

**Submit** — `submit method`, `submit problem`
  Submit new methods or problems for community review.

**Entry Detail** — `view combo_xxx_xxx`
  See full details of a method×problem combination.

**Rate** — `rate combo_xxx_xxx 5`
  Rate a combination you've viewed (1-5 stars).

**Peers** — `peers`, `nodes`, `network`
  See connected P2P nodes.

**Collections** — `collections`, `marketplace`
  Browse community-curated method and problem collections.

**Math Zone** — `math`, `math research`, `math zone`
  Explore the math research problem space with MCTS tree search.

**Buffer Zone** — `buffer`, `consensus`, `classify`
  Browse pending classifications and consensus state.

---

**Tip:** Try typing something like:
  * "show me the leaderboard"
  * "search for AI"
  * "draw 3 random entries"
  * "what's my balance"
  * "get free tokens"
  * "how many peers are connected"
"""

_INTRO_ZH = """\
**HammerWorld 智能助手**

我可以用自然语言帮你使用创意挖矿网络的所有功能！

**仪表盘** — `仪表盘`, `总览`, `统计`
  查看总条目数、节点连接、代币概览。

**排行榜** — `排行榜`, `排名`, `top 10`
  按领域/维度筛选浏览方法×问题的组合。

**搜索** — `搜索 AI`, `查找量子`
  跨方法、问题、领域搜索。

**随机抽取** — `随机抽取`, `抽三个`
  随机拉取条目，查看已抽过哪些。

**代币** — `余额`, `领取代币`, `faucet`
  查看 IDEA 余额，领取免费代币（有限频）。

**支付** — `支付查看 combo_xxx`, `付费抽取`, `解锁排行榜`
  支付 IDEA 代币解锁分析、抽奖或排行榜。

**提交** — `提交方法`, `提交问题`
  提交新方法或问题供社区审核。

**条目详情** — `查看 combo_xxx_xxx`
  查看方法×问题组合的完整详情。

**评分** — `评分 combo_xxx_xxx 5`
  为你查看过的组合打分（1-5星）。

**节点** — `节点`, `网络`, `连接`
  查看已连接的 P2P 节点。

**合集** — `合集`, `市场`
  浏览社区策划的方法和问题合集。

**数学区** — `math`, `数学`, `数学研究`
  基于 MCTS 树搜索探索数学研究问题的解法空间。

**缓冲区** — `buffer`, `共识`, `分类`
  浏览待分类的提交和共识状态。

---

**提示：** 试试输入：
  * "帮我看看排行榜"
  * "搜索一下 AI"
  * "抽 3 个随机条目"
  * "我有多少代币"
  * "领取免费代币"
  * "看看有哪些节点"
"""
