# Idea Mining Network (創意挖礦網絡)

去中心化創意挖掘網絡：結合 TRIZ 方法論、AI 跨領域分析、區塊鏈經濟，將「思維方法矩陣」與「未解決問題矩陣」隨機組合，由 AI 多維度評估，激勵全球算力挖掘突破性創意。

```
Methods Matrix × Problems Matrix → Random Combination → Multi-Dimension AI Evaluation → Leaderboards → Token Rewards
```

## 環境要求

- Python 3.8+
- 零強制依賴（核心模塊僅使用標準庫）
- AI 功能由用戶自行提供 API Key（支持 OpenAI 兼容接口）
- P2P 身份簽名可選安裝 `cryptography`（`pip install cryptography`）

## 項目結構

```
hammerworld/
├── src/
│   ├── engine/          # 核心引擎：models, combiner, loader
│   ├── triz/            # TRIZ 理論：knowledge, matrix, agent, prompts
│   ├── evaluation/      # AI 評估：8 維度評分流水線
│   ├── hub/             # P2P 聯邦：leaderboard, peer, server, web, discovery, identity, token_layer
│   ├── blockchain/      # 區塊鏈緩衝區：token, staking, buffer zone
│   └── cli/             # CLI：21 個命令（mine/top/search/hub/web/keygen/triz-analyze/...）
├── data/                # methods.json (35 條) + problems.json (22 條)
├── tests/               # 361 單元測試
├── readme/              # 詳細文檔 + 教程
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

# TRIZ 問題分析
python3 -m src.cli.main triz-analyze \
  --description "We need to increase engine power without increasing fuel consumption"

# 啟動 P2P Hub (含 Web UI)
python3 -m src.cli.main web --port 8765

# 多 Hub P2P 聯邦（通過 Discovery Server 自動發現）
python3 -m src.cli.main hub --port 8765 --db /tmp/discovery.db                # Discovery Hub
python3 -m src.cli.main web --port 8766 --discovery-url http://localhost:8765  # Worker A
python3 -m src.cli.main web --port 8767 --discovery-url http://localhost:8765  # Worker B

# 生成 ed25519 身份密鑰（防節點偽造）
python3 -m src.cli.main keygen -o identity.key

# 帶身份簽名啟動
python3 -m src.cli.main web --port 8766 --discovery-url http://localhost:8765 --identity identity.key

# Math Zone：解鎖數學問題區域
python3 -m src.cli.main math-mine --problem-id 1 --methods-collection "Complex Analysis" --batch 3

# Math Zone：提交解法
python3 -m src.cli.main math-submit --problem-id 1 --method-collection-id 1 \
  --steps-json '[{"step_num":1,"content":"define the problem","verified":true}]'

# Buffer Zone：提交分析到區塊鏈緩衝區
python3 -m src.cli.main buffer-submit --combo-id my_combo --method-name "Test" \
  --problem-title "Problem" --analysis-json '{"scores":[{"dim":"elegance","score":9.0}]}' \
  --address 0xALICE

# Buffer Zone：對待分類提交進行投票
python3 -m src.cli.main buffer-classify --submission-id <ID> --domain medicine --address 0xBOB

# Buffer Zone：查看分類員排行榜
python3 -m src.cli.main buffer-tokens --address 0xBOB

# 運行測試
python3 -m unittest discover tests/ -v
```

## 所有 CLI 命令（24 個）

### 核心命令 | Core
| 命令 | Command | 說明 |
|------|---------|------|
| `mine` | | AI 挖掘方法×問題組合 |
| `top` | | 排行榜 |
| `search` | | 搜索 |
| `random` | | 隨機抽取 |
| `hub` | | P2P Hub 服務器 |
| `web` | | P2P Hub + Web UI |
| `keygen` | | 生成 ed25519 身份密鑰 |
| `triz-analyze` | | TRIZ 標準化分析 |

### Matrix Marketplace
| 命令 | Command | 說明 |
|------|---------|------|
| `submit-method` | | 提交新方法 |
| `submit-problem` | | 提交新問題 |

### Math Research Zone
| 命令 | Command | 說明 |
|------|---------|------|
| `math-mine` | | 數學問題挖掘解鎖 |
| `math-submit` | | 提交數學解法 |

### Buffer Zone
| 命令 | Command | 說明 |
|------|---------|------|
| `buffer-submit` | | 提交分析到緩衝區 |
| `buffer-classify` | | 分類投票 |
| `buffer-status` | | 查看提交狀態 |
| `buffer-stake` | | 管理質押 |
| `buffer-tokens` | | 查看代幣/分類員統計 |

### Token Economy
| 命令 | Command | 說明 |
|------|---------|------|
| `pay-view` | | 支付查看 AI 分析 (10 IDEA) |
| `pay-leaderboard` | | 支付解鎖排行榜 (20 IDEA/24h) |
| `pay-draw` | | 支付隨機抽取 (5 IDEA) |
| `token-balance` | | 查詢代幣餘額 |

## 文檔索引

| 文檔 | 內容 |
|------|------|
| [readme/tutorial.md](readme/tutorial.md) | 命令大全 & 初學者教程（中英雙語，含 Discovery + 安全） |
| [readme/modules.md](readme/modules.md) | 所有模塊詳解（models, loader, combiner, triz, evaluation, hub, blockchain, math-zone） |
| [readme/p2p-hub.md](readme/p2p-hub.md) | P2P Hub：gossip 協議、REST API、Discovery Server、CLI 使用 |
| [readme/development.md](readme/development.md) | 開發工作流、測試、完整示例、擴展指南 |
| [DESIGN.md](DESIGN.md) | 完整系統設計（經濟模型、榮譽系統、區塊鏈緩衝區、Matrix Marketplace、Math Research Zone） |

## AI 智能助手 Web 對話界面

通過自然語言與整個系統交互，無需記憶命令或 URL。

```bash
# 啟動 Web 服務後，訪問 /web/agent
python3 -m src.cli.main web --port 8765
# 瀏覽器打開 http://localhost:8765/web/agent
```

支持的對話示例：
- **🏆 查看排行榜** — `show me the leaderboard` / `排行榜`
- **🔍 搜索** — `search for AI` / `搜索量子`
- **🎲 隨機抽取** — `random draw` / `抽三個`
- **💰 代幣** — `my balance` / `余额` / `get free tokens` / `领取免费代币`
- **📄 條目詳情** — `view combo_xxx_xxx` / `查看 combo_m1_p1`
- **⭐ 評分** — `rate combo_xxx 5` / `评分`
- **🔗 節點** — `peers` / `节点`
- **📋 功能介紹** — `help` / `功能介绍`

詳見 [`src/hub/agent_assistant.py`](src/hub/agent_assistant.py) — 基於中英文關鍵詞匹配的 18 種意圖識別 + 直接調用內部 Python 工具。

## 核心設計決策

- **不對稱閾值**：任一維度 ≥ 8.0 即通過（非平均分），保護怪想法
- **確定性隨機**：`SHA256(block_height + address + nonce)` 種子 Fisher-Yates
- **Push + Pull gossip**：每 30s 增量同步，TTL 防無限傳播
- **P2P 聯邦**：多 Hub 自組織，無中央服務器
- **Discovery Server**：迅雷 Tracker 模式，Hub 自動宣告/發現節點，零手動配置
- **6 層安全防護**：ed25519 簽名身份、IP 反欺騙、速率限制、隱私保護、LRU 淘汰、NAT 感知
- **Matrix Marketplace**：方法/問題集合可創建、分享、標星、導入
- **Math Research Zone**：數學問題專區，閘門解鎖機制，按解法步驟數排名，支持 Fork 協作
- **Blockchain Buffer Zone**：AI 分析提交 → 社區分類員投票 → 共識達成 → 公佈至排行榜，模擬代幣質押/獎勵
- **TRIZ 標準化**：用戶提交問題自動經 TRIZ Agent 轉換為結構化矛盾矩陣 + 發明原理推薦
- **零強制依賴**：純 stdlib，AI 通過協議注入，身份簽名可選
