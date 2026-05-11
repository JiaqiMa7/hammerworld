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
