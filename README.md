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
│   ├── hub/             # P2P 聯邦排行榜：leaderboard, peer, server, web
│   ├── blockchain/      # 區塊鏈緩衝區：token, staking, buffer zone
│   ├── hub/             # P2P 聯邦排行榜 + 付費支付層：leaderboard, peer, server, web, token_layer
│   └── cli/             # CLI：mine / top / search / random / hub / buffer-submit / buffer-classify / pay-view / pay-leaderboard / pay-draw / token-balance
├── data/                # methods.json (35 條) + problems.json (22 條)
├── tests/               # 329 單元測試
├── readme/              # 詳細文檔+教程文檔
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

# 啟動 P2P Hub (含 Web UI)
python3 -m src.cli.main web --port 8765

# Math Zone：解鎖數學問題區域
python3 -m src.cli.main math-mine --problem-id 1 --methods-collection "Complex Analysis" --batch 3

# Math Zone：提交解法
python3 -m src.cli.main math-submit --problem-id 1 --method-collection-id 1 --steps-json '[{"step_num":1,"content":"define the problem","verified":true}]'

# Buffer Zone：提交分析到區塊鏈緩衝區
python3 -m src.cli.main buffer-submit --combo-id my_combo --method-id m1 --method-name "Test" --problem-id p1 --problem-title "Problem" --analysis-json '{"scores":[{"dim":"elegance","score":9.0}]}' --address 0xALICE

# Buffer Zone：對待分類提交進行投票
python3 -m src.cli.main buffer-classify --submission-id <ID> --domain medicine --address 0xBOB

# Buffer Zone：查看分類員排行榜
python3 -m src.cli.main buffer-tokens --address 0xBOB

# 運行測試
python3 -m unittest discover tests/ -v
```

## 文檔索引

| 文檔 | 內容 |
|------|------|
| [readme/tutorial.md](readme/tutorial.md) | 命令大全 & 初學者教程（中英雙語） |
| [readme/modules.md](readme/modules.md) | 所有模塊詳解（models, loader, combiner, triz, evaluation, hub, blockchain, math-zone） |
| [readme/p2p-hub.md](readme/p2p-hub.md) | P2P Hub：gossip 協議、REST API、CLI 使用 |
| [readme/development.md](readme/development.md) | 開發工作流、測試、完整示例、擴展指南 |
| [DESIGN.md](DESIGN.md) | 完整系統設計（經濟模型、榮譽系統、區塊鏈緩衝區、Matrix Marketplace、Math Research Zone） |

## 核心設計決策

- **不對稱閾值**：任一維度 ≥ 8.0 即通過（非平均分），保護怪想法
- **確定性隨機**：`SHA256(block_height + address + nonce)` 種子 Fisher-Yates
- **Push + Pull gossip**：每 30s 增量同步，TTL 防無限傳播
- **P2P 聯邦**：多 Hub 自組織，無中央服務器
- **Matrix Marketplace**：方法/問題集合可創建、分享、標星、導入
- **Math Research Zone**：數學問題專區，閘門解鎖機制，按解法步驟數排名，支持 Fork 協作
- **Blockchain Buffer Zone**：AI 分析提交 → 社區分類員投票 → 共識達成 → 公佈至排行榜，模擬代幣質押/獎勵
- **零依賴**：純 stdlib，AI 通過協議注入
