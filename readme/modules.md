# 模塊詳解

## 1. `src/engine/models.py` — 核心數據模型

定義整個系統共用的所有數據結構。

**枚舉類型：**

| 類 | 值 | 說明 |
|----|-----|------|
| `MethodLevel` | 1-4 | 方法分級：基礎啟發式 / 結構化 / 領域專業 / 複合範式 |
| `ProblemMaturity` | 1-4 | 問題成熟度：無方案 / 部分方案 / 成本過高 / 瓶頸已知 |
| `ConstraintType` | physical_limit, resource, time, complexity, ethical | 問題約束類型 |
| `EvalDimension` | elegance, weirdness, human_feasibility, ai_feasibility, novelty, analogy_distance, scaling_potential, side_effects | 8 個評估維度 |
| `Domain` | medicine, energy, environment, information, materials, society, mathematics | 7 大問題領域 |

**數據類：**

```python
from src.engine.models import Method, Problem, Combination, AIAnalysis, EvalScore, Submission

# Method：一個思維方法條目
method = Method(
    id="method_triz_001",
    name="40 Inventive Principles (TRIZ)",
    domain="TRIZ",
    level=MethodLevel(2),
    description="...",
    trigger_conditions=["..."],
    examples=["..."],
    prerequisites=["method_triz_contradiction"],
    compatible_with=["method_ml_005"],
)

# Problem：一個未解決問題
problem = Problem(
    id="problem_medicine_001",
    title="Antibiotic Resistance",
    domain=Domain.MEDICINE,
    description="...",
    constraint_types=[ConstraintType.TIME],
    maturity=ProblemMaturity.PARTIAL_POOR,
    triz_standardized=None,  # 可選，TRIZ Agent 分析後填入
)

# EvalScore：單維度評分
score = EvalScore(dimension=EvalDimension.ELEGANCE, score=8.5, explanation="...")

# AIAnalysis：一次完整的 AI 評估
analysis = AIAnalysis(
    scores=[score, ...],
    analysis_text="...",
    model_name="claude-opus-4-7",
    model_version="20250514",
    inference_hash="abc123",
)
analysis.is_high_score(threshold=8.0)  # → True 如果任一維度 >= 8.0
analysis.high_dimensions(threshold=8.0)  # → [EvalDimension.ELEGANCE]

# Combination：方法×問題的配對
combo = Combination(
    id=Combination.make_id(method.id, problem.id),
    method=method,
    problem=problem,
)
combo.analyses.append(analysis)
combo.best_score       # → 最高分數
combo.best_dimension   # → 最高分的維度

# Submission：提交到區塊鏈緩衝區的條目
sub = Submission(
    method_id=method.id,
    problem_id=problem.id,
    submitter="0xADDRESS",
)
```

---

## 2. `src/engine/loader.py` — 數據加載器

從 `data/` 目錄加載 JSON 數據並轉換為 Python 對象。

```python
from src.engine.loader import load_methods, load_problems, filter_methods, filter_problems
from src.engine.models import MethodLevel, Domain, ProblemMaturity

# 加載全部數據
methods = load_methods()          # → list[Method]
problems = load_problems()        # → list[Problem]

# 從自定義路徑加載
methods = load_methods("custom/path/methods.json")

# 過濾方法
level3 = filter_methods(methods, level=MethodLevel.DOMAIN_SPECIFIC)
triz_methods = filter_methods(methods, domain="TRIZ")
triz_level2 = filter_methods(methods, level=MethodLevel.STRUCTURED, domain="TRIZ")

# 過濾問題
med = filter_problems(problems, domain=Domain.MEDICINE)
hard = filter_problems(problems, maturity=ProblemMaturity.NO_SOLUTION)
```

---

## 3. `src/engine/combiner.py` — 隨機組合引擎

使用 Fisher-Yates 洗牌算法，基於區塊鏈參數生成確定性隨機種子。

```python
from src.engine.combiner import generate_combinations, MiningState
from src.engine.loader import load_methods, load_problems

methods = load_methods()
problems = load_problems()

# 單次生成
combos = generate_combinations(
    methods=methods, problems=problems,
    block_height=100, user_address="0xABCD", nonce=0,
    batch_size=10, seen_ids=None,
)

# 使用 MiningState 管理挖礦進度
state = MiningState(user_address="0xABCD")
batch1 = state.mine_batch(methods, problems, block_height=100, batch_size=10)
batch2 = state.mine_batch(methods, problems, block_height=100, batch_size=10)
# batch1 和 batch2 不重複
```

**核心算法：**
```
seed = SHA256(block_height + user_address + nonce)
shuffled_methods  = FisherYates(methods, seed)
shuffled_problems = FisherYates(problems, seed + 1)
pairs walked at different rates for maximum diversity
```

---

## 4. `src/triz/models.py` — TRIZ 數據結構

```python
from src.triz.models import (
    EngineeringParameter, InventivePrinciple,
    TechnicalContradiction, PhysicalContradiction,
    StandardSolution, FunctionalModel, TRIZAnalysis, EvolutionTrend,
)

# 技術矛盾
tc = TechnicalContradiction(
    improving_param=EngineeringParameter(9, "Speed", ""),
    worsening_param=EngineeringParameter(25, "Loss of time", ""),
)
print(tc.matrix_key)  # → (9, 25)

# 物理矛盾
pc = PhysicalContradiction(
    parameter="temperature",
    requirement_a="Must be hot to sterilize",
    requirement_b="Must be cold to preserve nutrients",
    separation_strategy="time",
)
```

---

## 5. `src/triz/knowledge.py` — TRIZ 知識庫

全部 39 個工程參數和 40 個發明原理。

```python
from src.triz.knowledge import ENGINEERING_PARAMETERS, INVENTIVE_PRINCIPLES

param = ENGINEERING_PARAMETERS[9]
print(param.name)  # "Speed"

principle = INVENTIVE_PRINCIPLES[1]
print(principle.name)        # "Segmentation"
print(principle.examples)    # ["Modular furniture", "Microservices", ...]
```

**39 參數快速索引：**

| ID | 名稱 | ID | 名稱 | ID | 名稱 |
|----|------|----|------|----|------|
| 1 | Weight of moving object | 14 | Strength | 27 | Reliability |
| 2 | Weight of stationary obj | 15 | Duration of moving obj | 28 | Measurement accuracy |
| 3 | Length of moving object | 16 | Duration of stationary obj | 29 | Manufacturing precision |
| 4 | Length of stationary obj | 17 | Temperature | 30 | External harm on object |
| 5 | Area of moving object | 18 | Illumination intensity | 31 | Harmful side effects |
| 6 | Area of stationary object | 19 | Use of energy (moving) | 32 | Ease of manufacture |
| 7 | Volume of moving object | 20 | Use of energy (stationary) | 33 | Ease of operation |
| 8 | Volume of stationary obj | 21 | Power | 34 | Ease of repair |
| 9 | Speed | 22 | Loss of energy | 35 | Adaptability |
| 10 | Force | 23 | Loss of substance | 36 | Device complexity |
| 11 | Stress or pressure | 24 | Loss of information | 37 | Difficulty of detection |
| 12 | Shape | 25 | Loss of time | 38 | Level of automation |
| 13 | Stability of object | 26 | Quantity of substance | 39 | Productivity |

---

## 6. `src/triz/contradiction_matrix.py` — 矛盾矩陣

39×39 稀疏矩陣，映射 (改善參數, 惡化參數) → 推薦原理。

```python
from src.triz.contradiction_matrix import query_matrix, get_principle_recommendations
from src.triz.knowledge import ENGINEERING_PARAMETERS

principles = query_matrix(9, 25)
# 改善 Speed(9) 但 Loss of time(25) 惡化 → [10, 37, 28, 35]

principles = get_principle_recommendations("Speed", "Loss of time", ENGINEERING_PARAMETERS)
```

---

## 7. `src/triz/agent.py` — TRIZ Agent

雙模式：AI 分析 或 規則關鍵詞匹配。

```python
from src.triz.agent import TRIZAgent

# 規則模式（無 AI）
agent = TRIZAgent()
analysis = agent.analyze(problem)
problem = agent.standardize("描述一個技術問題...", domain="energy")

# AI 模式
class MyAIProvider:
    def generate(self, system_prompt, user_prompt): ...
agent = TRIZAgent(ai_provider=MyAIProvider())
```

---

## 8. `src/evaluation/scorer.py` — AI 評估流水線

8 維度評分，不對稱閾值（任一維度高分即通過）。

```python
from src.evaluation.scorer import EvaluationPipeline

pipeline = EvaluationPipeline(ai_provider=MyProvider(), threshold=8.0)
result = pipeline.evaluate(combo)
print(result.passed_threshold)  # True/False

passed, failed = pipeline.evaluate_and_filter(combos)
```

**8 維度：**

| 維度 | 英文 | 高分含義 |
|------|------|---------|
| 優雅度 | elegance | 方案簡潔、對稱、自洽 |
| 奇怪度 | weirdness | 反直覺、挑戰常識 |
| 人類可行性 | human_feasibility | 現有技術可實現 |
| AI 可行性 | ai_feasibility | AI 可自主執行 |
| 新穎度 | novelty | 從未被提出過 |
| 類比距離 | analogy_distance | 跨界跨度大 |
| 縮放潛力 | scaling_potential | 可指數級擴展 |
| 副作用 | side_effects | 負面影響小 |

---

## 9. `src/evaluation/providers.py` — AI 供應商插件

OpenAI 兼容 API 的 stdlib-only 實現。

```python
from src.evaluation.providers import OpenAIProvider, get_api_key, get_api_base, get_model

# 默認配置
api_key = get_api_key()                             # ~/.hammerworld/config or env
api_base = get_api_base()                           # https://api.openai.com/v1
model = get_model()                                 # gpt-4o

provider = OpenAIProvider(api_key=api_key, api_base=api_base, model=model)
response = provider.generate("System prompt", "User prompt")
```

**配置優先級：** 函數參數 > 環境變量 > `~/.hammerworld/config`

---

## 10. `src/hub/leaderboard.py` — SQLite 排行榜存儲

SQLite 後端，WAL 模式，支持排名、搜索、隨機抽取。

**表結構：**
- `combinations` — 所有方法×問題組合及其評分
- `paid_views` — 付費查看記錄
- `user_draws` — 用戶隨機抽取記錄
- `submissions` — 社區提交（方法/問題）
- `method_collections` / `problem_collections` — Matrix Marketplace 集合
- `collection_stars` — 集合標星
- `math_problems` / `math_solutions` / `math_access_log` — Math Research Zone

```python
from src.hub.leaderboard import LeaderboardDB

db = LeaderboardDB("data/leaderboard.db")
entry = db.insert(combo, miner_addr="0xABC")
top = db.get_top(dimension=EvalDimension.ELEGANCE, limit=10)
results = db.search("antibiotic")
draw = db.random_draw(domain=Domain.MEDICINE, draw_count=5)
```

---

## 11. `src/hub/web/` — 服務端 HTML 渲染（頁面模塊包）

純 Python HTML 渲染（無前端框架、無 JS）。由單一 4157 行 `web.py` 重構為按頁面分類的模塊包。

**目錄結構：**

| 模塊 | 說明 |
|------|------|
| `_translation.py` | 中英翻譯字典 + `_t()` |
| `_utils.py` | `_esc()`, `_parse_query()`, `_score_bar()` |
| `_layout.py` | `_CSS`, `_base_page()`, `_lang_toggle()`, `_login_widget()` |
| `_components.py` | `_entry_table()`, `_render_triz_analysis()`, `_render_previously_drawn()` |
| `dashboard.py` | Dashboard 儀表板 |
| `leaderboard.py` | Leaderboard + Search + Random Draw |
| `peers.py` | Peers 節點列表 |
| `entry.py` | Entry Detail + Combo Group + My Entries |
| `tokens.py` | Token Dashboard |
| `collections.py` | Collections Browse / Create / Detail |
| `math.py` | Math Zone（問題/解法/樹狀視圖/解鎖） |
| `submit.py` | Community Submit（方法/問題/審核） |
| `buffer.py` | Buffer Zone（儀表板/分類/代幣/排行榜） |
| `settings.py` | Settings 系統配置 |
| `agent.py` | Agent Chat 對話界面 |
| `triz.py` | TRIZ Agent 分析界面 |
| `bounties.py` | Bounties 懸賞列表 |

**Web 頁面覆蓋：**
| 頁面 | 路徑 |
|------|------|
| Dashboard | `/` |
| Leaderboard (含過濾器) | `/web/leaderboard` |
| Search | `/web/search` |
| Random Draw | `/web/random` |
| Peers | `/web/peers` |
| Entry Detail | `/web/entry/{id}` |
| Combo Group | `/web/combo/{id}` |
| My Entries | `/web/my-entries` |
| Token Dashboard | `/web/tokens` |
| Collections Browse | `/web/collections` |
| Collection Detail | `/web/collections/{type}/{id}` |
| Submit Method/Problem | `/web/submit` |
| Submissions Review | `/web/submissions` |
| Buffer Zone | `/web/buffer` |
| Settings | `/web/settings` |
| Agent Chat | `/web/agent` |
| TRIZ Agent | `/web/triz` |
| Bounties | `/web/bounties` |
| Math Zone Home | `/web/math` |
| Math Problem | `/web/math/{pid}` |
| Math Method Zone | `/web/math/{pid}/{mid}` |
| Math Solution Detail | `/web/math/{pid}/{mid}/{sid}` |
| Math Unlock | `/web/math/{pid}/{mid}/unlock` |
| Math Tree View | `/web/math/{pid}/{mid}/tree` |

---

## 12. `src/hub/server.py` — HTTP Server + REST API

基於 stdlib `http.server` / `ThreadingMixIn`，提供 Web UI + P2P REST API。

```python
from src.hub.server import HubServer
from src.hub.leaderboard import LeaderboardDB
from src.hub.peer import PeerConfig

db = LeaderboardDB("data/leaderboard.db")
server = HubServer(db, PeerConfig(port=8765))
server.start()  # blocks, handles Web UI + P2P API + gossip
```

**P2P API 端點：** `/health`, `/stats`, `/peers`, `/combinations` (GET/POST), `/peers/announce`

---

## 13. Matrix Marketplace

命名的問題/方法集合可創建、瀏覽、標星、導入。

```bash
# Web UI 創建集合
http://localhost:8765/web/collections/new

# CLI：導入集合挖礦
python3 -m src.cli.main mine --methods-collection "Quantum Methods" --batch 5
python3 -m src.cli.main mine --problems-collection "Energy Challenges" --batch 5
```

**排序規則：** 方法集合按 stars DESC（鼓勵質量），問題集合按 import_count ASC（鼓勵探索冷門問題）。

---

## 14. Math Research Zone

數學問題專屬研究區域，閘門解鎖機制，按解法步驟排名。

**數據模型：**
```
math_problems          — 數學問題區（title, category, creator）
math_solutions         — 解法（steps_json, max_correct_step, parent_solution_id）
math_access_log        — 訪問權限記錄
```

**閘門機制：**
```
用戶 → 運行 math-mine → 方法庫×問題 隨機組合 → AI 分析 → 自動授予訪問權
```

**層級結構：**
```
Math Problem (e.g., Riemann Hypothesis)
  ├── Method Collection A (Complex Analysis)
  │     ├── Solution 1 (Alice) - max_correct_step: 15
  │     ├── Solution 2 (Bob, forked from #1) - max_correct_step: 18
  │     └── Solution 3 (Charlie) - max_correct_step: 5
  └── Method Collection B (Fourier Analysis)
        └── Solution 4 (Dave) - max_correct_step: 10
```

**CLI 命令：**
```bash
# 閘門解鎖
python3 -m src.cli.main math-mine \
  --problem-id 1 --methods-collection "Complex Analysis" \
  --address 0xMINER --batch 3

# 提交解法
python3 -m src.cli.main math-submit \
  --problem-id 1 --method-collection-id 3 \
  --steps-json '[{"step_num":1,"content":"Define zeta...","verified":true}]'

# Fork 現有解法
python3 -m src.cli.main math-submit \
  --problem-id 1 --method-collection-id 3 \
  --steps-json '[...]' --parent-id 5
```

## 15. `src/blockchain/` — 區塊鏈緩衝區

模擬鏈上提交、分類、共識與代幣經濟。

### 核心組件

**`SimulatedToken`** (`contracts.py`) — 模擬 ERC-20 代幣：

```python
from src.blockchain.contracts import SimulatedToken
from src.hub.leaderboard import LeaderboardDB

db = LeaderboardDB("data/leaderboard.db")
token = SimulatedToken(db, name="Idea Token", symbol="IDEA")

token.faucet("0xALICE", 1000)          # 新用戶獲取初始代幣
token.mint("0xALICE", 500)            # 鑄造（獎勵）
balance = token.balance_of("0xALICE")  # 查詢餘額
token.transfer("0xALICE", "0xBOB", 200)  # 轉賬
total = token.total_supply()           # 總供應量
```

**`StakingContract`** (`contracts.py`) — 模擬質押合約：

```python
from src.blockchain.contracts import StakingContract

staking = StakingContract(db, token)

sid = staking.stake("0xALICE", 200)     # 質押 200 代幣
staking.release_stake(sid)              # 釋放質押
staking.slash_stake(sid, 100)           # 罰沒部分質押
active = staking.get_active_stake("0xALICE")  # 查詢活躍質押
```

**`BufferZone`** (`buffer.py`) — 緩衝區編排：

```python
from src.blockchain.buffer import BufferZone

buffer_zone = BufferZone(db, token, staking)

# 提交 AI 分析
sub_id = buffer_zone.submit_analysis(
    combo_id="combo_001", method_id="m1", method_name="TRIZ Method",
    problem_id="p1", problem_title="Antibiotic Resistance",
    submitter="0xALICE",
    analysis_json='{"scores":[{"dim":"elegance","score":8.5}]}',
)

# 分類員投票
result = buffer_zone.classify(sub_id, "0xBOB", "medicine")
result = buffer_zone.classify(sub_id, "0xCAROL", "medicine")
result = buffer_zone.classify(sub_id, "0xDAVE", "medicine")

# 3 人一致 → 共識達成，自動分發獎勵
status = buffer_zone.get_status(sub_id)
# status['status'] == 'classified'
# status['consensus_domain'] == 'medicine'

# 查看分類員統計
stats = buffer_zone.get_classifier_stats("0xBOB")
dashboard = buffer_zone.get_dashboard_stats()
```

### 緩衝區流程

```
AI Analysis → Buffer Zone (pending, only submitter visible)
    → Classifiers vote (domain, NSFW, spam)
        → 3+ votes, ≥60% domain consensus → classified (public)
            → publish_to_leaderboard() → published (on leaderboard)
        → 7 votes, no consensus → disputed
```

### 代幣經濟常量

| 常量 | 值 | 說明 |
|------|-----|------|
| `STAKE_PER_SUBMISSION` | 50 | 每次提交需質押 |
| `STAKE_PER_CLASSIFICATION` | 10 | 每次分類需質押 |
| `REWARD_CORRECT` | 10 | 正確分類獎勵 |
| `REWARD_SPAM` | 25 | 檢舉垃圾額外獎勵 |
| `PENALTY_WRONG` | 5 | 錯誤分類罰沒 |
| `MIN_CLASSIFICATIONS` | 3 | 最少分類人數 |
| `CONSENSUS_THRESHOLD` | 0.6 | 共識閾值（60%） |
| `SPEED_BONUS_RATE` | 0.1 | 連續正確加成（10%/次） |

### Web 頁面

| 路徑 | 頁面 | 說明 |
|------|------|------|
| `/web/buffer` | 緩衝區面板 | 各狀態統計、快捷入口 |
| `/web/buffer/pending` | 待分類列表 | 等待分類的提交 |
| `/web/buffer/classify/{sid}` | 分類表單 | 提交分類投票 |
| `/web/buffer/submissions` | 我的提交 | 按提交者查詢 |
| `/web/buffer/detail/{sid}` | 提交詳情 | 含所有分類記錄 |
| `/web/buffer/tokens` | 代幣儀表板 | 餘額/質押/獎勵 |
| `/web/buffer/leaderboard` | 分類員排行榜 | Top 50 分類員 |

### CLI 命令

```bash
# 提交至緩衝區
python3 -m src.cli.main buffer-submit \
  --combo-id my_combo --method-id m1 --method-name "Test" \
  --problem-id p1 --problem-title "Problem" \
  --analysis-json '{"scores":[{"dim":"elegance","score":9.0}]}' \
  --address 0xALICE

# 分類投票
python3 -m src.cli.main buffer-classify \
  --submission-id abc123 --domain medicine --address 0xBOB

# 查看狀態
python3 -m src.cli.main buffer-status
python3 -m src.cli.main buffer-status --address 0xALICE

# 代幣管理
python3 -m src.cli.main buffer-tokens --address 0xBOB
```

### 數據庫表

4 個新表：`buffer_submissions`, `buffer_classifications`, `token_accounts`, `stake_records`

詳見 `src/hub/leaderboard.py` `_init_db()` 和 `# --- Blockchain Buffer Zone ---` 區塊。

---

## 7. `src/hub/token_layer.py` — 付費支付層（TokenGate）

連接 SimulatedToken 與應用層經濟流：**付費查看 AI 分析、排行榜解鎖、隨機抽取付費**。

### TokenGate 類

```python
class TokenGate:
    VIEW_FEE_N = 10        # 查看一個 AI 分析
    LEADERBOARD_FEE_P = 20  # 解鎖排行榜 24h
    DRAW_FEE_Q = 5          # 隨機抽取一次
    FAUCET_AMOUNT = 100     # 新用戶自動獲得（不同於緩衝區的 1000）

    def pay_for_view(viewer_addr, combo_id) -> dict
    def check_view_access(viewer_addr, combo_id) -> str  # "own"|"paid"|"no_access"
    def pay_for_leaderboard(viewer_addr, board_name) -> dict
    def check_leaderboard_access(viewer_addr, board_name) -> bool
    def pay_for_random_draw(viewer_addr) -> dict
    def rate_analysis(viewer_addr, combo_id, rating, comment="") -> dict
    def get_viewer_summary(viewer_addr) -> dict
```

### 費用分配（80/10/10）

```
VIEW_FEE_N (10) → 80% = 8 → 分析者 (miner)
                   10% = 1 → 發現者 (MVP: 也給 miner)
                   10% = 1 → 協議費 (0xPROTOCOL)
```

### 新增數據庫表

- `leaderboard_access(viewer_addr, board_name, paid_at, expires_at)` — 排行榜 24h 解鎖
- `viewer_ratings(id, viewer_addr, combo_id, rating, comment, created_at)` — 付費用戶評分
- `paid_views` 新增列：`paid_amount`, `analyzer_addr`, `protocol_addr`

### CLI 命令

```bash
# 支付查看分析
python3 -m src.cli.main pay-view --combo-id COMBO --address 0xALICE

# 解鎖排行榜
python3 -m src.cli.main pay-leaderboard --dimension elegance --domain medicine --address 0xALICE

# 付費隨機抽取
python3 -m src.cli.main pay-draw --dimension elegance --count 10 --address 0xALICE

# 查看餘額
python3 -m src.cli.main token-balance --address 0xALICE
```

### Web 路由

- `GET /web/tokens` — Token 儀表板（餘額、支付歷史）
- `POST /web/pay/view/{combo_id}` — 支付並解鎖分析
- `POST /web/pay/leaderboard/{board}` — 支付解鎖排行榜
- `POST /web/pay/draw` — 支付後觸發隨機抽取
- `POST /web/rate/{combo_id}` — 評分
- `POST /web/faucet` — 手動水龍頭
