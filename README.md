# Idea Mining Network (創意挖礦網絡)

去中心化創意挖掘網絡：結合 TRIZ 方法論、AI 跨領域分析、區塊鏈經濟，將「思維方法矩陣」與「未解決問題矩陣」隨機組合，由 AI 多維度評估，激勵全球算力挖掘突破性創意。

```
Methods Matrix × Problems Matrix → Random Combination → AI Multi-Dimension Evaluation → Leaderboards → Token Rewards
```

---

## 環境要求

- Python 3.8+
- 零強制依賴（核心模塊僅使用標準庫）
- AI 功能由用戶自行提供 API Key（支持 Anthropic、OpenAI、Ollama 等）

---

## 項目結構

```
hammerworld/
│
├── src/
│   ├── engine/                        # 核心引擎層
│   │   ├── models.py                  #   所有數據模型定義
│   │   ├── combiner.py                #   隨機組合生成器
│   │   └── loader.py                  #   JSON 數據加載器
│   │
│   ├── triz/                          # TRIZ 理論層
│   │   ├── models.py                  #   TRIZ 專用數據結構
│   │   ├── knowledge.py               #   39 工程參數 + 40 發明原理
│   │   ├── contradiction_matrix.py    #   39×39 矛盾矩陣
│   │   ├── agent.py                   #   TRIZ Agent（問題標準化）
│   │   └── prompts.py                 #   LLM 提示詞模板
│   │
│   ├── evaluation/                    # AI 評估層
│   │   └── scorer.py                  #   8 維度評分流水線
│   │
│   ├── hub/                           # 排行榜層
│   │   └── leaderboard.py             #   SQLite 排行榜（排名/搜索/隨機抽取）
│   │
│   └── cli/                           # 命令行層
│       └── main.py                    #   CLI 入口（mine/top/search/random）
│
├── data/
│   ├── methods.json                   # 方法矩陣（35 條，4 個級別）
│   └── problems.json                  # 問題矩陣（22 條，6 個領域）
│
├── tests/                             # 測試目錄
├── DESIGN.md                          # 完整系統設計文檔
├── CLAUDE.md                          # Claude Code 指引
└── README.md                          # 本文件
```

---

## 模塊詳解

### 1. `src/engine/models.py` — 核心數據模型

定義整個系統共用的所有數據結構。

**枚舉類型：**

| 類 | 值 | 說明 |
|----|-----|------|
| `MethodLevel` | 1-4 | 方法分級：基礎啟發式 / 結構化 / 領域專業 / 複合範式 |
| `ProblemMaturity` | 1-4 | 問題成熟度：無方案 / 部分方案 / 成本過高 / 瓶頸已知 |
| `ConstraintType` | physical_limit, resource, time, complexity, ethical | 問題約束類型 |
| `EvalDimension` | elegance, weirdness, human_feasibility, ai_feasibility, novelty, analogy_distance, scaling_potential, side_effects | 8 個評估維度 |
| `Domain` | medicine, energy, environment, information, materials, society | 6 大問題領域 |

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

### 2. `src/engine/loader.py` — 數據加載器

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

**JSON 數據格式（方法）：**

```json
{
  "methods": [{
    "id": "method_triz_001",
    "name": "40 Inventive Principles (TRIZ)",
    "domain": "TRIZ",
    "level": 2,
    "description": "Systematically apply 40 proven patterns...",
    "trigger_conditions": ["Technical contradiction identified"],
    "examples": ["Segmentation → modular smartphone"],
    "prerequisites": ["method_triz_contradiction"],
    "compatible_with": ["method_ml_005"]
  }]
}
```

**JSON 數據格式（問題）：**

```json
{
  "problems": [{
    "id": "problem_medicine_001",
    "title": "Antibiotic Resistance",
    "domain": "medicine",
    "description": "Bacteria evolve resistance...",
    "constraint_types": ["time", "complexity"],
    "maturity": 2,
    "triz_standardized": {
      "contradiction": {"improving": "...", "worsening": "..."},
      "ifr": "...",
      "triz_params": [31, 35],
      "functional_model": {"actors": [...], "useful_functions": [...], "harmful_functions": [...]}
    }
  }]
}
```

---

### 3. `src/engine/combiner.py` — 隨機組合引擎

使用 Fisher-Yates 洗牌算法，基於區塊鏈參數生成確定性隨機種子，將方法與問題配對。

```python
from src.engine.combiner import generate_combinations, MiningState
from src.engine.loader import load_methods, load_problems

methods = load_methods()
problems = load_problems()

# 單次生成
combos = generate_combinations(
    methods=methods,
    problems=problems,
    block_height=100,       # 區塊高度（或用時間戳替代）
    user_address="0xABCD",  # 礦工地址
    nonce=0,                # 批次編號（遞增防止重複）
    batch_size=10,          # 每批數量
    seen_ids=None,          # 可選，傳入已見過的組合 ID 集合
)

# 使用 MiningState 管理挖礦進度
state = MiningState(user_address="0xABCD")
batch1 = state.mine_batch(methods, problems, block_height=100, batch_size=10)
batch2 = state.mine_batch(methods, problems, block_height=100, batch_size=10)
# batch1 和 batch2 不重複
print(state.total_mined)  # 20
print(state.nonce)        # 2
```

**核心算法：**

```
seed = SHA256(block_height + user_address + nonce)
shuffled_methods  = FisherYates(methods, seed)
shuffled_problems = FisherYates(problems, seed + 1)
pairs = walked at different rates through both lists to maximize diversity
```

不同用戶對相同矩陣會得到不同配對（地址參與種子計算）。同一用戶相同參數的結果可復現。

---

### 4. `src/triz/models.py` — TRIZ 數據結構

```python
from src.triz.models import (
    EngineeringParameter,    # 39 個通用工程參數之一
    InventivePrinciple,      # 40 個發明原理之一
    TechnicalContradiction,  # 技術矛盾：改善 A 惡化 B
    PhysicalContradiction,   # 物理矛盾：同時需要 X 和 非X
    StandardSolution,        # 76 個標準解之一
    FunctionalModel,         # 功能分析結果
    TRIZAnalysis,            # 完整 TRIZ 分析
    EvolutionTrend,          # 技術進化趨勢
)

# 技術矛盾
tc = TechnicalContradiction(
    improving_param=EngineeringParameter(9, "Speed", "Velocity of an object or process"),
    worsening_param=EngineeringParameter(25, "Loss of time", "Time wasted"),
)
print(tc.matrix_key)  # → (9, 25)

# 物理矛盾
pc = PhysicalContradiction(
    parameter="temperature",
    requirement_a="Must be hot to sterilize",
    requirement_b="Must be cold to preserve nutrients",
    separation_strategy="time",  # 時間分離：先加熱殺菌，後冷卻
)
```

---

### 5. `src/triz/knowledge.py` — TRIZ 知識庫

包含全部 39 個工程參數和 40 個發明原理的完整定義。

```python
from src.triz.knowledge import ENGINEERING_PARAMETERS, INVENTIVE_PRINCIPLES

# 查詢參數
param = ENGINEERING_PARAMETERS[9]
print(param.name)         # "Speed"
print(param.description)  # "Velocity of an object or process."

# 查詢原理
principle = INVENTIVE_PRINCIPLES[1]
print(principle.name)             # "Segmentation"
print(principle.description)      # "Divide an object into independent parts."
print(principle.examples)         # ["Modular furniture", "Microservices", ...]
print(principle.sub_principles)   # ["Divide into independent parts", ...]
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

### 6. `src/triz/contradiction_matrix.py` — 矛盾矩陣

39×39 稀疏矩陣，將 (改善參數, 惡化參數) 映射到推薦的發明原理。

```python
from src.triz.contradiction_matrix import query_matrix, CONTRADICTION_MATRIX

# 查詢推薦原理
principles = query_matrix(9, 25)
# 改善 Speed(9) 但 Loss of time(25) 惡化 → [10, 37, 28, 35]

# 使用參數名稱查詢
from src.triz.contradiction_matrix import get_principle_recommendations
from src.triz.knowledge import ENGINEERING_PARAMETERS
principles = get_principle_recommendations(
    "Speed", "Loss of time", ENGINEERING_PARAMETERS
)

# 直接訪問矩陣
cell = CONTRADICTION_MATRIX.get((9, 25), [])
# 無映射時返回空列表
```

**常用查詢示例：**

```python
query_matrix(1, 2)   # 減輕移動物體重量但靜止重量增加    → [15, 8, 29, 34]
query_matrix(27, 28) # 提高可靠性但測量精度下降           → [32, 3, 11, 23]
query_matrix(39, 22) # 提高生產力但能量損失增加           → [28, 10, 29, 35]
```

---

### 7. `src/triz/agent.py` — TRIZ Agent

將自然語言描述的科學問題標準化為 TRIZ 格式，支持 AI 模式（需要 API Key）和規則模式（純本地關鍵詞匹配）。

```python
from src.triz.agent import TRIZAgent, AIProvider
from src.engine.loader import load_problems

# === 規則模式（無 AI，零依賴） ===
agent = TRIZAgent()
problems = load_problems()

# 分析已有問題（使用 triz_standardized 字段或關鍵詞匹配）
analysis = agent.analyze(problems[0])
print(analysis.ifr)                      # Ideal Final Result
print(analysis.recommended_principles)   # [31, 35]
print(analysis.technical_contradictions) # [TechnicalContradiction, ...]

# 從原始文本分析
analysis = agent._rule_based_from_text(
    "We need a faster and more reliable system that wastes less energy",
    "engineering",
)
print(analysis.recommended_principles)  # 基於關鍵詞匹配

# 標準化新問題（返回 Problem 對象，含 triz_standardized 字段）
problem = agent.standardize(
    "Bees are dying due to pesticides but we need pest control for agriculture",
    domain="environment",
)

# === AI 模式（需要 API Key） ===
class MyAIProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # 調用你的 AI API
        import anthropic
        client = anthropic.Anthropic(api_key="...")
        msg = client.messages.create(
            model="claude-opus-4-7",
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=4096,
        )
        return msg.content[0].text

agent = TRIZAgent(ai_provider=MyAIProvider())
analysis = agent.analyze(problems[0])  # 使用 AI 深度分析

# 查詢矛盾矩陣並獲取原理詳情
result = agent.get_principle_recommendations(9, 25)
# → {
#     "principle_ids": [10, 37, 28, 35],
#     "principles": [
#       {"id": 10, "name": "Preliminary action", "description": "...", "examples": [...]},
#       ...
#     ]
#   }
```

---

### 8. `src/triz/prompts.py` — LLM 提示模板

```python
from src.triz.prompts import (
    SYSTEM_PROMPT,                        # TRIZ 專家系統提示詞
    PROBLEM_STANDARDIZATION_TEMPLATE,     # 問題標準化模板
    EVALUATION_PROMPT_TEMPLATE,           # 創意評估模板
)

# 自定義模板
prompt = PROBLEM_STANDARDIZATION_TEMPLATE.format(
    problem_description="Describe the problem here...",
    domain="medicine",
)
```

---

### 9. `src/evaluation/scorer.py` — AI 評估流水線

對方法×問題組合進行 8 維度評分，支持不對稱閾值（任一維度高分即通過）。

```python
from src.evaluation.scorer import EvaluationPipeline, EvaluationResult
from src.engine.models import EvalDimension, Combination
from src.engine.loader import load_methods, load_problems
from src.engine.combiner import generate_combinations

# 初始化（需要 AI Provider，同上）
pipeline = EvaluationPipeline(
    ai_provider=MyAIProvider(),
    threshold=8.0,              # 高分閾值
    model_name="claude-opus-4-7",
    model_version="20250514",
)

# 獲取組合
methods = load_methods()
problems = load_problems()
combos = generate_combinations(methods, problems, 100, "0xMINER", 0, batch_size=5)

# 單個評估
result = pipeline.evaluate(combos[0])
print(result.passed_threshold)   # True/False
print(result.high_dimensions)    # [EvalDimension.WEIRDNESS]
for s in result.analysis.scores:
    print(f"  {s.dimension.value}: {s.score} — {s.explanation}")

# 批量評估並分離通過/未通過
passed, failed = pipeline.evaluate_and_filter(combos)
print(f"Passed: {len(passed)}, Failed: {len(failed)}")

# 創建緩衝區提交
submission = pipeline.create_submission(result, submitter="0xMINER")
```

**8 維度說明：**

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

### 10. `src/hub/leaderboard.py` — 本地排行榜

SQLite 存儲的排行榜，支持排名、過濾、搜索、隨機抽取、查看付費。

```python
from src.hub.leaderboard import LeaderboardDB, LeaderboardEntry, RandomDrawResult
from src.engine.models import EvalDimension, Domain, MethodLevel

# 初始化（數據庫文件自動創建）
db = LeaderboardDB("data/leaderboard.db")

# === 寫入 ===
# 插入一個組合的評估結果
db.insert(combo, miner_addr="0xMINER")
# combo 必須至少有一個 AIAnalysis

# === 排名查詢 ===
# 全部排名
top_all = db.get_top(limit=50)

# 按維度排名
top_weird = db.get_top(dimension=EvalDimension.WEIRDNESS, limit=20)

# 按領域過濾
top_med = db.get_top(domain=Domain.MEDICINE, limit=20)

# 按方法級別過濾
top_l4 = db.get_top(method_level=MethodLevel(4), limit=20)

# 組合過濾
top = db.get_top(
    dimension=EvalDimension.NOVELTY,
    domain=Domain.ENERGY,
    method_level=MethodLevel(3),
    limit=20,
)

# 分頁
page2 = db.get_top(dimension=EvalDimension.ELEGANCE, limit=20, offset=20)

# 返回 LeaderboardEntry 列表，每個包含：
# entry.rank, entry.combo_id, entry.method_name, entry.problem_title,
# entry.best_dimension, entry.best_score,
# entry.elegance, entry.weirdness, entry.human_feasibility, ...

# === 隨機抽取（推薦查看模式） ===
draw = db.random_draw(
    dimension=EvalDimension.WEIRDNESS,  # 可選，不指定則按 best_score
    domain=Domain.MEDICINE,             # 可選，不指定則全領域
    draw_count=10,
    viewer_addr="0xVIEWER",
)
print(f"從 {draw.total_in_board} 條中抽取了 {len(draw.entries)} 條")
# 同一用戶再次抽取不會重複已抽過的條目

# === 搜索 ===
results = db.search("antibiotic", limit=20)
results = db.search("抗生素", dimension=EvalDimension.NOVELTY, limit=10)
# 搜索範圍：方法名、問題標題、方法領域、問題領域、最佳維度

# === 付費查看 ===
paid = db.has_paid("0xVIEWER", "combo_method_triz_001_problem_medicine_001")
if not paid:
    db.record_payment("0xVIEWER", "combo_method_triz_001_problem_medicine_001")

# === 統計 ===
total = db.total_entries()
total_med = db.total_entries(domain=Domain.MEDICINE)
```

**數據庫表結構：**

```sql
-- combinations：排行榜主表
combo_id, method_name, method_domain, method_level,
problem_title, problem_domain, best_dim, best_score,
elegance, weirdness, human_feasibility, ai_feasibility,
novelty, analogy_distance, scaling_potential, side_effects,
miner_addr, created_at

-- paid_views：付費記錄
viewer_addr, combo_id, paid_at

-- user_draws：用戶抽取記錄（防重複）
viewer_addr, board_name, drawn_combo_ids, draw_seed
```

---

### 11. `src/cli/main.py` — 命令行工具

```bash
# 挖礦：生成方法×問題組合
python3 src/cli/main.py mine \
    --address 0xYOUR_ADDRESS \
    --block-height 100 \
    --nonce 0 \
    --batch 10

# 排行榜：查看 Top N
python3 src/cli/main.py top \
    --dimension weirdness \
    --domain medicine \
    --level 3 \
    --limit 20 \
    --db data/leaderboard.db

# 搜索
python3 src/cli/main.py search "antibiotic" \
    --dimension novelty \
    --limit 20

# 隨機抽取
python3 src/cli/main.py random \
    --dimension elegance \
    --domain energy \
    --count 10 \
    --address 0xVIEWER \
    --db data/leaderboard.db
```

---

## 開發工作流

**必須使用 git worktree，禁止直接在 master 上開發：**

```bash
# 1. 為每個模塊創建獨立 worktree
git worktree add ../hammerworld-<module-name> -b <module-branch>

# 2. 在 worktree 中開發
cd ../hammerworld-<module-name>
# ... 修改、測試 ...

# 3. 提交
git add -A
git commit -m "描述你的改動"

# 4. 合併回 master
cd /home/li/Desktop/hammerworld
git merge <module-branch>

# 5. 清理
git worktree remove ../hammerworld-<module-name> --force
git branch -d <module-branch>
```

**分支命名規範：** `data-models`、`method-matrix`、`triz-agent`、`eval-pipeline`、`hub-leaderboard`

**提交信息規範：** 英文，描述清楚做了什麼，結尾附 `Co-Authored-By: ...`

---

## 完整示例：從數據到排行榜

```python
from src.engine.loader import load_methods, load_problems
from src.engine.combiner import generate_combinations
from src.evaluation.scorer import EvaluationPipeline
from src.hub.leaderboard import LeaderboardDB

# 1. 加載數據
methods = load_methods()
problems = load_problems()

# 2. 生成組合
combos = generate_combinations(
    methods, problems,
    block_height=42, user_address="0xEXAMPLE", nonce=0,
    batch_size=10,
)

# 3. AI 評估（需要提供 AIProvider 實現）
pipeline = EvaluationPipeline(ai_provider=my_provider, model_name="claude-opus-4-7")
passed, failed = pipeline.evaluate_and_filter(combos)
print(f"通過: {len(passed)}, 未通過: {len(failed)}")

# 4. 寫入排行榜
db = LeaderboardDB("data/leaderboard.db")
for result in passed:
    db.insert(result.combination, miner_addr="0xEXAMPLE")

# 5. 查詢
top_novel = db.get_top(dimension=EvalDimension.NOVELTY, limit=5)
for entry in top_novel:
    print(f"#{entry.rank} [{entry.best_dimension}={entry.best_score:.1f}] "
          f"{entry.method_name} × {entry.problem_title}")
```

---

## 擴展指南

### 添加新方法

編輯 `data/methods.json`，遵循格式：

```json
{
  "id": "method_YOURDOMAIN_XXX",
  "name": "...",
  "domain": "YourDomain",
  "level": 1-4,
  "description": "...",
  "trigger_conditions": ["..."],
  "examples": ["..."],
  "prerequisites": [],
  "compatible_with": []
}
```

### 添加新問題

編輯 `data/problems.json`，可選提供 `triz_standardized` 字段（由 TRIZ Agent 預分析）：

```json
{
  "id": "problem_YOURDOMAIN_XXX",
  "title": "...",
  "domain": "medicine|energy|environment|information|materials|society",
  "description": "...",
  "constraint_types": ["time", "resource", ...],
  "maturity": 1-4
}
```

### 接入自定義 AI 模型

實現 `AIProvider` 協議即可：

```python
class MyProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # 調用任何 LLM API
        ...

# 用於 TRIZ Agent
agent = TRIZAgent(ai_provider=MyProvider())

# 用於評估流水線
pipeline = EvaluationPipeline(ai_provider=MyProvider())
```

### 添加新評估維度

1. 在 `src/engine/models.py` 的 `EvalDimension` 枚舉中添加
2. 在 `src/evaluation/scorer.py` 的 `DIMENSION_NAMES` 中添加
3. 在 `src/triz/prompts.py` 的 `EVALUATION_PROMPT_TEMPLATE` 中添加
4. 在 `src/hub/leaderboard.py` 的數據庫 schema 中添加對應列

---

## 設計文檔

完整系統設計（經濟模型、榮譽系統、緩衝區、P2P 聯邦架構）見 [DESIGN.md](DESIGN.md)。
