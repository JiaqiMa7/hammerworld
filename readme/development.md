# 開發指南

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

**分支命名：** `data-models`、`method-matrix`、`triz-agent`、`eval-pipeline`、`hub-p2p`

**提交信息：** 英文，描述清楚做了什麼。結尾附 `Co-Authored-By: ...`

## 測試

```bash
# 全部測試（零依賴）
python3 -m unittest discover tests/ -v

# 單個模塊
python3 -m unittest tests.test_peer -v
python3 -m unittest tests.test_server -v
python3 -m unittest tests.test_leaderboard -v

# 單個測試類
python3 -m unittest tests.test_peer.TestPeerManager -v

# 單個測試方法
python3 -m unittest tests.test_server.TestHubAPI.test_health -v
```

## 完整示例：從挖礦到 P2P 同步

```python
from src.engine.loader import load_methods, load_problems
from src.engine.combiner import generate_combinations
from src.evaluation.scorer import EvaluationPipeline
from src.hub.leaderboard import LeaderboardDB
from src.hub.peer import PeerManager, PeerConfig
from src.engine.models import EvalDimension

# 1. 加載數據
methods = load_methods()
problems = load_problems()

# 2. 生成組合
combos = generate_combinations(
    methods, problems, block_height=42, user_address="0xEXAMPLE", nonce=0, batch_size=10,
)

# 3. AI 評估（需要實現 AIProvider）
pipeline = EvaluationPipeline(ai_provider=my_provider, model_name="claude-opus-4-7")
passed, failed = pipeline.evaluate_and_filter(combos)
print(f"通過: {len(passed)}, 未通過: {len(failed)}")

# 4. 寫入本地排行榜
db = LeaderboardDB("data/leaderboard.db")
for result in passed:
    entry = db.insert(result.combination, miner_addr="0xEXAMPLE")

# 5. 啟動 P2P 同步
config = PeerConfig(port=8765, bootstrap=["hub.example.com:8765"])
manager = PeerManager(db, config)
manager.start()

# 6. 新條目會自動廣播給 peers
# 遠程條目會自動同步到本地
```

## 擴展指南

### 添加新方法

編輯 `data/methods.json`：

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

編輯 `data/problems.json`，可選 `triz_standardized` 字段：

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

```python
class MyProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # 調用任何 LLM API
        ...

agent = TRIZAgent(ai_provider=MyProvider())
pipeline = EvaluationPipeline(ai_provider=MyProvider())
```

### 添加新評估維度

1. `src/engine/models.py` — `EvalDimension` 枚舉添加新值
2. `src/evaluation/scorer.py` — `DIMENSION_NAMES` 添加名稱
3. `src/triz/prompts.py` — `EVALUATION_PROMPT_TEMPLATE` 添加維度描述
4. `src/hub/leaderboard.py` — SQLite schema 添加對應列
