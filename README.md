# Idea Mining Network (創意挖礦網絡)

去中心化創意挖掘網絡：結合 TRIZ 方法論、AI 跨領域分析、區塊鏈經濟，將「思維方法矩陣」與「未解決問題矩陣」隨機組合，由 AI 多維度評估，激勵全球算力挖掘突破性創意。

```
Methods Matrix × Problems Matrix → Random Combination → Multi-Dimension AI Evaluation → Leaderboards → Token Rewards
```

## 環境要求

- Python 3.8+
- 零強制依賴（核心模塊僅使用標準庫）
- AI 功能由用戶自行提供 API Key

## 項目結構

```
hammerworld/
├── src/
│   ├── engine/          # 核心引擎：models, combiner, loader
│   ├── triz/            # TRIZ 理論：knowledge, matrix, agent, prompts
│   ├── evaluation/      # AI 評估：8 維度評分流水線
│   ├── hub/             # P2P 聯邦排行榜：leaderboard, peer, server
│   └── cli/             # CLI：mine / top / search / random / hub
├── data/                # methods.json (35 條) + problems.json (22 條)
├── tests/               # 165+ 單元測試
├── readme/              # 詳細文檔
├── DESIGN.md            # 完整系統設計
└── CLAUDE.md            # Claude Code 指引
```

## 快速開始

```bash
# 驗證模塊
python3 -c "
from src.engine.loader import load_methods, load_problems
from src.engine.combiner import generate_combinations
from src.triz.agent import TRIZAgent
methods = load_methods()
problems = load_problems()
print(f'{len(methods)} methods, {len(problems)} problems OK')
"

# 挖礦
python3 -m src.cli.main mine --batch 5

# 查看排行榜
python3 -m src.cli.main top --limit 10

# 搜索
python3 -m src.cli.main search "antibiotic"

# 啟動 P2P Hub
python3 -m src.cli.main hub --port 8765

# 運行測試
python3 -m unittest discover tests/ -v
```

## 文檔索引

| 文檔 | 內容 |
|------|------|
| [readme/modules.md](readme/modules.md) | 所有模塊詳解（models, loader, combiner, triz, evaluation） |
| [readme/p2p-hub.md](readme/p2p-hub.md) | P2P Hub：gossip 協議、REST API、CLI 使用 |
| [readme/development.md](readme/development.md) | 開發工作流、測試、完整示例、擴展指南 |
| [DESIGN.md](DESIGN.md) | 完整系統設計（經濟模型、榮譽系統、區塊鏈緩衝區） |

## 核心設計決策

- **不對稱閾值**：任一維度 ≥ 8.0 即通過（非平均分），保護怪想法
- **確定性隨機**：`SHA256(block_height + address + nonce)` 種子 Fisher-Yates
- **Push + Pull gossip**：每 30s 增量同步，TTL 防無限傳播
- **P2P 聯邦**：多 Hub 自組織，無中央服務器
- **零依賴**：純 stdlib，AI 通過協議注入
