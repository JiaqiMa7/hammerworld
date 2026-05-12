# 命令大全 & 使用教程 | Command Reference & Tutorial

> 本文檔面向初學者，從零開始介紹 Idea Mining Network 的全部命令和使用流程。
> This document is beginner-oriented, covering all CLI commands and workflows from scratch.

---

## 目錄 | Table of Contents

1. [環境準備 | Setup](#1-環境準備--setup)
2. [快速入門 | Quick Start](#2-快速入門--quick-start)
3. [命令大全 | Command Reference](#3-命令大全--command-reference)
4. [完整工作流 | Full Workflows](#4-完整工作流--full-workflows)
5. [Web UI 指南 | Web UI Guide](#5-web-ui-指南--web-ui-guide)
6. [常見問題 | FAQ](#6-常見問題--faq)

---

## 1. 環境準備 | Setup

### 安裝 | Installation

本項目**零強制依賴**，僅需 Python 3.8+。無需 pip install。

This project has **zero mandatory dependencies**. Only Python 3.8+ is required. No pip install needed.

```bash
# 檢查 Python 版本 | Check Python version
python3 --version  # 需要 ≥ 3.8

# 克隆項目 | Clone the project
git clone <repo-url> hammerworld
cd hammerworld
```

### 配置 API Key | Configure API Key

AI 挖掘功能需要 API Key。支持 OpenAI 兼容接口（DeepSeek、OpenAI 等）。

AI mining requires an API key. OpenAI-compatible APIs are supported (DeepSeek, OpenAI, etc.).

**方式一：環境變量（推薦）| Method 1: Environment variables (recommended)**

```bash
# 創建 .env 文件 | Create .env file
cat > .env << 'EOF'
HAMMERWORLD_API_KEY=sk-your-api-key-here
HAMMERWORLD_API_BASE=https://api.deepseek.com
HAMMERWORLD_MODEL=deepseek-v4-flash
EOF

# 加載環境變量 | Load environment variables
export $(grep -v '^#' .env | xargs)
```

**方式二：配置文件 | Method 2: Config file**

```bash
mkdir -p ~/.hammerworld
cat > ~/.hammerworld/config << 'EOF'
HAMMERWORLD_API_KEY=sk-your-api-key-here
HAMMERWORLD_API_BASE=https://api.deepseek.com
HAMMERWORLD_MODEL=deepseek-v4-flash
EOF
```

### 驗證安裝 | Verify Installation

```bash
python3 -c "
from src.engine.loader import load_methods, load_problems
from src.engine.combiner import generate_combinations
methods = load_methods()
problems = load_problems()
print(f'OK: {len(methods)} methods, {len(problems)} problems loaded')
"
# 預期輸出 | Expected: OK: 35 methods, 22 problems loaded
```

---

## 2. 快速入門 | Quick Start

### 第一步：第一次挖掘 | Step 1: Your First Mining

```bash
# 挖掘 3 個方法×問題組合（需要 API Key）
# Mine 3 method×problem combinations (requires API Key)
python3 -m src.cli.main mine --batch 3

# 預期輸出 | Expected output:
#   [1/3] 40 Inventive Principles (TRIZ) × Antibiotic Resistance → best=elegance=7.5
#   [2/3] Genetic Algorithm × Carbon Capture → best=novelty=8.5
#   [3/3] Biomimicry × Desalination → best=ai_feasibility=9.0
#   Saved 3/3 combinations to data/leaderboard.db
```

### 第二步：查看排行榜 | Step 2: View the Leaderboard

```bash
# 查看所有排行榜（按最高分排序）
# View all leaderboards (sorted by best score)
python3 -m src.cli.main top --limit 10

# 按維度篩選 | Filter by dimension
python3 -m src.cli.main top --dimension novelty

# 按領域篩選 | Filter by domain
python3 -m src.cli.main top --domain energy

# 組合篩選 | Combine filters
python3 -m src.cli.main top --dimension elegance --domain medicine --limit 5
```

### 第三步：搜索 | Step 3: Search

```bash
# 搜索關鍵詞 | Search by keyword
python3 -m src.cli.main search "antibiotic"

# 搜索並按維度篩選 | Search with dimension filter
python3 -m src.cli.main search "carbon" --dimension novelty
```

### 第四步：隨機抽取 | Step 4: Random Draw

```bash
# 從排行榜隨機抽取 5 條
# Random draw 5 entries from the leaderboard
python3 -m src.cli.main random --count 5

# 指定維度和領域 | With dimension and domain filter
python3 -m src.cli.main random --dimension weirdness --domain materials --count 3
```

### 第五步：啟動 Web UI | Step 5: Launch Web UI

```bash
# 啟動 Web 服務器 | Start the web server
python3 -m src.cli.main web --port 8765

# 打開瀏覽器 | Open browser:
# http://localhost:8765/web
```

---

## 3. 命令大全 | Command Reference

所有命令均以 `python3 -m src.cli.main <command>` 執行。
All commands are executed via `python3 -m src.cli.main <command>`.

### 3.1 核心命令 | Core Commands

#### `mine` — AI 挖掘 | AI Mining

生成方法×問題的隨機組合，由 AI 進行 8 維度評估。高分組合（任一維度 ≥ 8.0）自動進入排行榜。

Generate random method×problem combinations evaluated by AI across 8 dimensions. High-scoring combos (any dimension ≥ 8.0) automatically enter the leaderboard.

```bash
python3 -m src.cli.main mine [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--batch` | | `10` | 挖掘組合數量 | Number of combos to mine |
| `--parallel` | | `1` | 並行 API 請求數 | Parallel API workers |
| `--address` | | `0xMINER` | 礦工地址 | Miner address |
| `--threshold` | | `8.0` | 高分閾值 | Score threshold for "high" |
| `--model` | | (env) | 覆蓋模型名 | Override model name |
| `--api-base` | | (env) | 覆蓋 API 端點 | Override API base URL |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |
| `--method-step` | | `0` (auto) | 方法步進 | Method index stepping |
| `--problem-step` | | `0` (auto) | 問題步進 | Problem index stepping |
| `--methods` | | (built-in) | 自定義方法 JSON | Custom methods JSON file |
| `--problems` | | (built-in) | 自定義問題 JSON | Custom problems JSON file |
| `--methods-collection` | | (none) | 從 Matrix Marketplace 加載方法 | Load methods from named collection |
| `--problems-collection` | | (none) | 從 Matrix Marketplace 加載問題 | Load problems from named collection |

**示例 | Examples:**

```bash
# 基礎挖掘 | Basic mining
python3 -m src.cli.main mine --batch 5

# 大量並行挖掘 | High-parallel mining
python3 -m src.cli.main mine --batch 100 --parallel 10

# 用指定模型挖掘 | Mine with specific model
python3 -m src.cli.main mine --batch 3 --model gpt-4o --api-base https://api.openai.com/v1

# 從 Matrix Marketplace 集合挖掘 | Mine from marketplace collections
python3 -m src.cli.main mine --batch 5 --methods-collection "Physics Methods" --problems-collection "Energy Problems"
```

---

#### `top` — 排行榜 | Leaderboard

```bash
python3 -m src.cli.main top [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--dimension` | | (all) | 篩選維度 | Filter by dimension |
| `--domain` | | (all) | 篩選領域 | Filter by domain |
| `--level` | | (all) | 篩選方法等級 (1-4) | Filter by method level |
| `--limit` | | `20` | 顯示條數 | Number of entries |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**可用維度 | Available dimensions:** `elegance`, `weirdness`, `human_feasibility`, `ai_feasibility`, `novelty`, `analogy_distance`, `scaling_potential`, `side_effects`

**可用領域 | Available domains:** `medicine`, `energy`, `environment`, `information`, `materials`, `society`, `mathematics`

**示例 | Examples:**

```bash
python3 -m src.cli.main top --dimension novelty --domain energy --limit 5
python3 -m src.cli.main top --level 4 --limit 10
```

---

#### `search` — 搜索 | Search

```bash
python3 -m src.cli.main search <query> [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `query` | (required) | – | 搜索關鍵詞 | Search keyword |
| `--dimension` | | (all) | 維度篩選 | Dimension filter |
| `--limit` | | `20` | 結果數量 | Max results |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Examples:**

```bash
python3 -m src.cli.main search "hydrogen"
python3 -m src.cli.main search "cancer" --dimension weirdness --limit 10
```

---

#### `random` — 隨機抽取 | Random Draw

```bash
python3 -m src.cli.main random [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--dimension` | | (all) | 維度篩選 | Dimension filter |
| `--domain` | | (all) | 領域篩選 | Domain filter |
| `--count` | | `10` | 抽取數量 | Number to draw |
| `--address` | | `0xVIEWER` | 查看者地址 | Viewer address |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Examples:**

```bash
python3 -m src.cli.main random --count 5
python3 -m src.cli.main random --dimension elegance --count 3
```

---

#### `hub` — P2P 樞紐服務器 | P2P Hub Server

啟動一個無頭 P2P 聯邦樞紐（無 Web UI），僅 API 和 gossip 同步。

Start a headless P2P federation hub (no Web UI), API and gossip sync only.

```bash
python3 -m src.cli.main hub [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--port` | | `8765` | HTTP 端口 | HTTP port |
| `--bootstrap` | | (none) | 引導節點 (可重複) | Bootstrap peer (repeatable) |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |
| `--gossip-interval` | | `30.0` | Gossip 間隔 (秒) | Gossip interval in seconds |
| `--peer-timeout` | | `300.0` | 節點超時 (秒) | Peer timeout in seconds |
| `--max-peers` | | `50` | 最大節點數 | Maximum peers |
| `--discovery-url` | | (none) | Discovery Server URL (可重複) | Discovery server URL (repeatable) |
| `--identity` | | (none) | ed25519 身份密鑰文件路徑 | Path to ed25519 identity key file |

**示例 | Examples:**

```bash
# 啟動獨立 Hub | Start standalone hub
python3 -m src.cli.main hub --port 8765

# 通過 Discovery Server 自動發現節點 | Auto-discover peers via Discovery Server
python3 -m src.cli.main hub --port 8766 --discovery-url http://localhost:8765

# 帶簽名身份的 Hub（防偽造）| Hub with signed identity (anti-spoofing)
python3 -m src.cli.main hub --port 8766 --discovery-url http://localhost:8765 --identity /path/to/identity.key

# 手動引導（不使用 Discovery）| Manual bootstrap (without Discovery)
python3 -m src.cli.main hub --port 8766 --bootstrap localhost:8765
```

---

#### `web` — Web UI 服務器 | Web UI Server

啟動帶 Web UI 的樞紐服務器。功能和 `hub` 相同，並附加瀏覽器可訪問的完整 Web 界面。

Start a hub with a full browser-accessible Web UI. Same features as `hub` plus web interface.

```bash
python3 -m src.cli.main web [options]
```

參數同 `hub` 命令。| Same parameters as `hub`.

```bash
# 啟動 Web UI | Start Web UI
python3 -m src.cli.main web --port 8765
# 打開瀏覽器 | Open: http://localhost:8765/web

# 通過 Discovery Server 自動加入 P2P 網絡 | Auto-join P2P network via Discovery
python3 -m src.cli.main web --port 8765 --discovery-url http://<DISCOVERY_IP>:8765

# 帶身份簽名 | With signed identity
python3 -m src.cli.main web --port 8765 --discovery-url http://<DISCOVERY_IP>:8765 --identity identity.key
```

---

### 3.2 Matrix Marketplace 命令 | Matrix Marketplace Commands

#### `submit-method` — 提交新方法 | Submit New Method

向 Matrix Marketplace 提交一個新的思維方法。

Submit a new thinking method to the Matrix Marketplace.

```bash
python3 -m src.cli.main submit-method [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--name` | (required) | – | 方法名稱 | Method name |
| `--domain` | (required) | – | 方法領域 | Method domain |
| `--level` | (required) | – | 方法等級 1-4 | Method level (1-4) |
| `--description` | (required) | – | 方法描述 | Method description |
| `--examples` | | `""` | 逗號分隔示例 | Comma-separated examples |
| `--prerequisites` | | `""` | 前置方法 ID | Prerequisite method IDs |
| `--compatible-with` | | `""` | 兼容方法 ID | Compatible method IDs |
| `--submitter` | | `cli_user` | 提交者地址 | Submitter address |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Example:**

```bash
python3 -m src.cli.main submit-method \
  --name "Fermi Estimation" \
  --domain "physics" \
  --level 1 \
  --description "Break complex problems into estimable sub-problems" \
  --examples "Estimate piano tuners in Chicago,Estimate cosmic ray flux" \
  --submitter "0xALICE"
```

---

#### `submit-problem` — 提交新問題 | Submit New Problem

向 Matrix Marketplace 提交一個新的未解決問題。

Submit a new unsolved problem to the Matrix Marketplace.

```bash
python3 -m src.cli.main submit-problem [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--title` | (required) | – | 問題標題 | Problem title |
| `--domain` | (required) | – | 問題領域 | Problem domain |
| `--description` | (required) | – | 問題描述 | Problem description |
| `--constraints` | | `""` | 逗號分隔約束類型 | Comma-separated constraint types |
| `--maturity` | | `1` | 成熟度 1-4 | Problem maturity (1-4) |
| `--submitter` | | `cli_user` | 提交者地址 | Submitter address |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Example:**

```bash
python3 -m src.cli.main submit-problem \
  --title "Microplastic Filtration" \
  --domain "environment" \
  --description "Remove microplastics from drinking water at scale" \
  --constraints "cost,scalability" \
  --maturity 2 \
  --submitter "0xBOB"
```

---

#### `triz-analyze` — TRIZ 標準化分析 | TRIZ Standardization Analysis

使用 TRIZ 方法論分析問題描述，輸出矛盾矩陣、理想最終結果 (IFR)、工程參數、功能模型和推薦發明原理。

Analyze a problem description using TRIZ methodology. Outputs contradiction matrix, IFR, engineering parameters, functional model, and recommended inventive principles.

```bash
python3 -m src.cli.main triz-analyze [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--description` | (required) | – | 問題描述 | Problem description |
| `--domain` | | `general` | 問題領域 | Problem domain |

**示例 | Example:**

```bash
python3 -m src.cli.main triz-analyze \
  --description "We need to increase engine power without increasing fuel consumption" \
  --domain "mechanical"

# 輸出示例 | Example output:
# === TRIZ Standardization ===
# Domain: mechanical
# Contradictions:
#   Improve: power (#21) — Worsen: fuel_consumption (#22)
# Ideal Final Result (IFR):
#   The engine increases power without consuming additional fuel
# Recommended Principles:
#   #10 Preliminary Action — Perform the required change ahead of time
#   #35 Parameter Change — Change the physical state
# Functional Model:
#   engine → produces → power
#   fuel → consumed_by → engine
```

當 API Key 可用時使用 AI 分析，否則使用基於 26 個關鍵詞的規則匹配。TRIZ 標準化也會自動應用於 `submit-problem` 提交的問題。

Uses AI analysis when API key is available; falls back to 26-keyword rule-based matching otherwise. TRIZ standardization is also auto-applied to problems submitted via `submit-problem`.

---

#### `keygen` — 生成身份密鑰 | Generate Identity Key

生成 ed25519 密鑰對用於 P2P 發現宣告的簽名驗證，防止節點偽造。

Generate an ed25519 keypair for signing P2P discovery announcements. Prevents node impersonation.

```bash
python3 -m src.cli.main keygen [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--output`, `-o` | | `identity.key` | 私鑰輸出路徑 | Private key output path |
| `--force`, `-f` | | (flag) | 覆蓋已存在的文件 | Overwrite existing file |

**示例 | Example:**

```bash
# 生成密鑰對 | Generate keypair
python3 -m src.cli.main keygen -o ~/.hammerworld/identity.key

# 使用該密鑰啟動 Hub | Start hub with this identity
python3 -m src.cli.main hub --port 8766 \
  --discovery-url http://<DISCOVERY_IP>:8765 \
  --identity ~/.hammerworld/identity.key
```

需要 `cryptography` 庫（可選依賴）：`pip install cryptography`。未安裝時 Hub 以未驗證降級模式運行。

Requires `cryptography` library (optional dependency): `pip install cryptography`. Hub runs in unverified degraded mode without it.

---

### 3.3 Math Research Zone 命令 | Math Research Zone Commands

#### `math-mine` — 數學挖掘 | Math Mining

生成種子分析以解鎖數學問題區域。

Generate seed analysis to unlock a math problem zone.

```bash
python3 -m src.cli.main math-mine [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--problem-id` | (required) | – | 數學問題 ID | Math problem ID |
| `--methods-collection` | (required) | – | 方法集合名 | Method collection name |
| `--address` | | `0xMINER` | 礦工地址 | Miner address |
| `--batch` | | `3` | 批次大小 | Batch size |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |
| `--threshold` | | `8.0` | 高分閾值 | Score threshold |
| `--parallel` | | `1` | 並行請求數 | Parallel workers |

**示例 | Example:**

```bash
python3 -m src.cli.main math-mine \
  --problem-id 1 \
  --methods-collection "Complex Analysis" \
  --batch 3
```

---

#### `math-submit` — 提交數學解法 | Submit Math Solution

```bash
python3 -m src.cli.main math-submit [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--problem-id` | (required) | – | 數學問題 ID | Math problem ID |
| `--method-collection-id` | (required) | – | 方法集合 ID | Method collection ID |
| `--steps-json` | (required) | – | JSON 步驟數組 | JSON array of solution steps |
| `--parent-id` | | (none) | Fork 來源解法 ID | Solution ID to fork from |
| `--address` | | `0xSOLVER` | 解答者地址 | Solver address |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Example:**

```bash
python3 -m src.cli.main math-submit \
  --problem-id 1 \
  --method-collection-id 1 \
  --steps-json '[
    {"step_num":1,"content":"Define the problem domain","verified":true},
    {"step_num":2,"content":"Apply Cauchy Integral Formula","verified":true}
  ]' \
  --address "0xEULER"
```

---

### 3.4 區塊鏈緩衝區命令 | Blockchain Buffer Zone Commands

緩衝區管線：提交 AI 分析 → 社區分類員投票 → 共識達成 → 發布至排行榜。

Buffer pipeline: Submit AI analysis → community classifiers vote → consensus reached → publish to leaderboard.

#### `buffer-submit` — 提交分析到緩衝區 | Submit Analysis to Buffer

```bash
python3 -m src.cli.main buffer-submit [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--combo-id` | (required) | – | 組合 ID | Combination ID |
| `--method-name` | | `""` | 方法名稱 | Method name |
| `--problem-title` | | `""` | 問題標題 | Problem title |
| `--analysis-json` | | `{}` | 分析 JSON 字符串 | Analysis JSON string |
| `--analysis-file` | | (none) | 從文件讀取 JSON | Read analysis JSON from file |
| `--analysis-text` | | `""` | 分析摘要文本 | Analysis summary text |
| `--address` | | `0xBUFFER` | 提交者地址 | Submitter address |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Example:**

```bash
python3 -m src.cli.main buffer-submit \
  --combo-id "my_discovery_001" \
  --method-name "Genetic Algorithm" \
  --problem-title "Carbon Capture" \
  --analysis-json '{"novelty":9.0,"elegance":8.0,"ai_feasibility":7.5}' \
  --analysis-text "Applying genetic algorithms to optimize carbon capture materials..." \
  --address "0xALICE"
```

---

#### `buffer-classify` — 對待分類提交投票 | Classify a Pending Submission

```bash
python3 -m src.cli.main buffer-classify [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--submission-id` | (required) | – | 緩衝區提交 ID | Buffer submission ID |
| `--domain` | (required) | – | 領域標籤 | Domain label |
| `--nsfw` | | (flag) | 標記不當內容 | Mark as NSFW |
| `--spam` | | (flag) | 標記垃圾/AI 幻覺 | Mark as spam / AI hallucination |
| `--notes` | | `""` | 備註 | Classification notes |
| `--address` | | `0xCLASSIFIER` | 分類員地址 | Classifier address |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Example:**

```bash
python3 -m src.cli.main buffer-classify \
  --submission-id "abc123-def" \
  --domain "energy" \
  --notes "Solid analysis, validates novelty claim" \
  --address "0xBOB"
```

---

#### `buffer-status` — 查看提交狀態 | Check Submission Status

```bash
python3 -m src.cli.main buffer-status [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--submission-id` | | (all) | 指定提交 ID | Specific submission ID |
| `--address` | | (all) | 按提交者篩選 | Filter by submitter address |

**示例 | Example:**

```bash
python3 -m src.cli.main buffer-status --submission-id "abc123-def"
python3 -m src.cli.main buffer-status --address "0xALICE"
```

---

#### `buffer-stake` — 管理質押 | Manage Staking

```bash
python3 -m src.cli.main buffer-stake [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--address` | (required) | – | 質押者地址 | Staker address |
| `--amount` | | `100` | 質押/取回數量 | Amount to stake/unstake |
| `--action` | | `stake` | `stake` 或 `unstake` | stake or unstake |

**示例 | Example:**

```bash
python3 -m src.cli.main buffer-stake --address "0xALICE" --amount 200 --action stake
python3 -m src.cli.main buffer-stake --address "0xALICE" --amount 50 --action unstake
```

---

#### `buffer-tokens` — 查看代幣和分類員統計 | View Tokens & Classifier Stats

```bash
python3 -m src.cli.main buffer-tokens [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--address` | | `0xVIEWER` | 查詢地址 | Address to query |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Example:**

```bash
python3 -m src.cli.main buffer-tokens --address "0xCLASSIFIER_1"
```

---

### 3.5 代幣經濟命令 | Token Economy Commands

#### `pay-view` — 支付查看 AI 分析 | Pay to View AI Analysis

支付 10 IDEA 解鎖一次 AI 分析查看。

Pay 10 IDEA to unlock viewing one AI analysis.

```bash
python3 -m src.cli.main pay-view [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--combo-id` | (required) | – | 組合 ID | Combo ID to view |
| `--address` | (required) | – | 查看者地址 | Viewer address |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**費用分配 | Fee Split (80/10/10):** 8 → 分析者, 1 → 發現者, 1 → 協議費。

**示例 | Example:**

```bash
python3 -m src.cli.main pay-view \
  --combo-id "combo_method_triz_001_problem_energy_002" \
  --address "0xVIEWER"
```

---

#### `pay-leaderboard` — 支付解鎖排行榜 | Pay to Unlock Leaderboard

支付 20 IDEA 解鎖排行榜 24 小時。

Pay 20 IDEA to unlock a leaderboard for 24 hours.

```bash
python3 -m src.cli.main pay-leaderboard [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--dimension` | | `elegance` | 排行榜維度 | Leaderboard dimension |
| `--domain` | | `medicine` | 排行榜領域 | Leaderboard domain |
| `--address` | (required) | – | 查看者地址 | Viewer address |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Example:**

```bash
python3 -m src.cli.main pay-leaderboard \
  --dimension "novelty" \
  --domain "energy" \
  --address "0xVIEWER"
```

---

#### `pay-draw` — 支付隨機抽取 | Pay for Random Draw

支付 5 IDEA 進行一次隨機抽取。

Pay 5 IDEA for one random draw.

```bash
python3 -m src.cli.main pay-draw [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--dimension` | | (all) | 維度篩選 | Dimension filter |
| `--domain` | | (all) | 領域篩選 | Domain filter |
| `--count` | | `10` | 抽取數量 | Number of entries to draw |
| `--address` | (required) | – | 查看者地址 | Viewer address |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Example:**

```bash
python3 -m src.cli.main pay-draw \
  --dimension "weirdness" \
  --count 5 \
  --address "0xVIEWER"
```

---

#### `token-balance` — 查詢代幣餘額 | Check Token Balance

```bash
python3 -m src.cli.main token-balance [options]
```

| 參數 | Parameter | 默認值 | Default | 說明 / Description |
|------|-----------|---------|----------|--------------|
| `--address` | | `0xVIEWER` | 查詢地址 | Address to query |
| `--db` | | `data/leaderboard.db` | 數據庫路徑 | Database path |

**示例 | Example:**

```bash
python3 -m src.cli.main token-balance --address "0xALICE"

# 輸出示例 | Example output:
# Account: 0xALICE
#   Token: Idea Token (IDEA)
#   Balance: 90 IDEA
#   Staked: 200 IDEA
#   Total Earned: 500 IDEA
#   Total Slashed: 0 IDEA
#   Total Spent: 10 IDEA
#   Payments: 1
```

---

## 4. 完整工作流 | Full Workflows

### 4.1 單機全管線 | Solo Full Pipeline

從挖掘到支付查看的端到端流程。| End-to-end flow from mining to paid viewing.

```bash
# 1. 挖掘 5 個組合 | Mine 5 combos
python3 -m src.cli.main mine --batch 5 --address 0xMINER

# 2. 查看排行榜 | Check leaderboard
python3 -m src.cli.main top --limit 5

# 3. 提交高分組合到緩衝區 | Submit high-scoring combo to buffer
python3 -m src.cli.main buffer-submit \
  --combo-id "combo_method_xxx_problem_yyy" \
  --method-name "My Method" \
  --problem-title "My Problem" \
  --analysis-json '{"novelty":9.0,"elegance":8.0}' \
  --analysis-text "A novel approach..." \
  --address 0xMINER

# 4. 三個分類員投票 | Three classifiers vote
for i in 1 2 3; do
  python3 -m src.cli.main buffer-classify \
    --submission-id "<SUBMISSION_ID>" \
    --domain "energy" \
    --address "0xCLASSIFIER_$i"
done

# 5. 檢查共識狀態 | Check consensus status
python3 -m src.cli.main buffer-status --submission-id "<SUBMISSION_ID>"

# 6. 支付查看 | Pay to view
python3 -m src.cli.main pay-view \
  --combo-id "combo_method_xxx_problem_yyy" \
  --address "0xVIEWER"

# 7. 查詢代幣餘額 | Check balance
python3 -m src.cli.main token-balance --address "0xVIEWER"
```

### 4.2 多樞紐 P2P 聯邦（通過 Discovery Server）| Multi-Hub P2P Federation (via Discovery Server)

使用 Discovery Server 實現零配置節點發現，無需手動 `--bootstrap`。

Zero-config peer discovery via Discovery Server — no manual `--bootstrap` needed.

```bash
# 終端 1 | Terminal 1: 啟動 Discovery Hub（輕量 Tracker）
python3 -m src.cli.main hub --port 8765 --db /tmp/discovery.db

# 終端 2 | Terminal 2: 啟動 Worker Hub A（自動發現，帶身份簽名）
python3 -m src.cli.main web --port 8766 --db /tmp/hub_a.db \
  --discovery-url http://localhost:8765 \
  --identity identity.key

# 終端 3 | Terminal 3: 啟動 Worker Hub B（自動發現 Hub A）
python3 -m src.cli.main web --port 8767 --db /tmp/hub_b.db \
  --discovery-url http://localhost:8765

# 終端 4 | Terminal 4: 向 Hub A 挖掘
python3 -m src.cli.main mine --batch 5 --db /tmp/hub_a.db

# Hub B 在加入時自動從 Hub A 拉取數據（即時同步）
# Hub B auto-pulls data from Hub A on join (instant sync)
curl -s "http://localhost:8767/combinations?since=0&limit=10" | python3 -m json.tool
```

**手動引導模式（無 Discovery Server）：| Manual bootstrap mode (no Discovery Server):**

```bash
# 終端 1 | Terminal 1: 啟動 Hub A
python3 -m src.cli.main web --port 8765 --db /tmp/hub_a.db

# 終端 2 | Terminal 2: 啟動 Hub B，手動引導至 Hub A
python3 -m src.cli.main web --port 8766 --db /tmp/hub_b.db --bootstrap localhost:8765
```

### 4.3 Web UI 支付流程 | Web UI Payment Flow

```bash
# 啟動服務器 | Start server
python3 -m src.cli.main web --port 8765

# 然後在瀏覽器中操作 | Then in browser:
# 1. http://localhost:8765/web                     — 首頁 | Home
# 2. 點擊任意條目 → 看到付費牆 | Click entry → see paywall
# 3. 點擊 "Pay 10 IDEA" → 支付成功 | Click "Pay 10 IDEA" → paid
# 4. 看到完整 AI 分析 | See full AI analysis
# 5. http://localhost:8765/web/tokens?viewer=0xVIEWER — 代幣儀表板 | Token dashboard
```

---

## 5. Web UI 指南 | Web UI Guide

啟動 Web 服務器後，瀏覽器訪問 `http://localhost:8765/web`，可訪問以下頁面：

After starting the web server, visit `http://localhost:8765/web` to access:

| 路徑 | Path | 說明 | Description |
|------|------|------|-------------|
| `/web` | | 儀表板首頁 | Dashboard home |
| `/web/entry/<combo_id>` | | 條目詳情（含支付門控） | Entry detail (with paywall) |
| `/web/leaderboard/<dim>/<domain>` | | 排行榜 | Leaderboard |
| `/web/random/<dim>` | | 隨機抽取 | Random draw |
| `/web/search?q=...` | | 搜索 | Search |
| `/web/tokens` | | 代幣儀表板 | Token dashboard |
| `/web/buffer` | | 緩衝區概覽 | Buffer zone overview |
| `/web/buffer/pending` | | 待分類列表 | Pending classification list |
| `/web/buffer/classify/<id>` | | 分類投票 | Classify a submission |
| `/web/buffer/submissions` | | 所有提交 | All submissions |
| `/web/buffer/tokens` | | 緩衝區代幣 | Buffer tokens |
| `/web/peers` | | P2P 節點 | P2P peers |
| `/discovery/peers` | | Discovery 節點列表 | Discovery peer list (JSON) |
| `/web/marketplace` | | 方法/問題集市 | Method/problem marketplace |
| `/web/math` | | 數學研究區 | Math research zone |

**代幣經濟費用 | Token Economy Fees:**

| 操作 | Operation | 費用 | Fee | 說明 / Note |
|------|-----------|------|-----|--------------|
| 查看 AI 分析 | View AI analysis | 10 IDEA | 80%→分析者 / 10%→發現者 / 10%→協議 | — |
| 解鎖排行榜 | Unlock leaderboard | 20 IDEA | 24 小時有效 | Valid 24h |
| 隨機抽取 | Random draw | 5 IDEA | 每次 | Per draw |
| 新用戶 Faucet | New user faucet | +100 IDEA | 自動發放 | Auto-granted |

---

## 6. 常見問題 | FAQ

### Q: 如何獲取 API Key？

A: 註冊 DeepSeek (platform.deepseek.com) 或 OpenAI (platform.openai.com)，生成 API Key。推薦 DeepSeek（價格更低，效果相當）。

Sign up at DeepSeek (platform.deepseek.com) or OpenAI (platform.openai.com) to get an API key. DeepSeek is recommended (lower cost, comparable quality).

### Q: 沒有 API Key 可以使用嗎？

A: 可以！搜索、排行榜、隨機抽取、P2P 同步、緩衝區查看、Web UI 等均無需 API Key。僅 `mine` 和 `math-mine` 命令需要。

Yes! Search, leaderboard, random draw, P2P sync, buffer viewing, Web UI all work without API key. Only `mine` and `math-mine` need it.

### Q: 經濟模型是真實代幣嗎？

A: 目前是模擬代幣（SimulatedToken），純內存運算。未來可遷移到真實 ERC-20 合約。

Currently simulated tokens (in-memory only). Migratable to real ERC-20 contracts in the future.

### Q: 數據庫文件可以共享嗎？

A: 可以！`.db` 文件是 SQLite 格式，可以複製、備份、通過 P2P gossip 自動同步。

Yes! The `.db` file is SQLite, can be copied, backed up, and auto-synced via P2P gossip.

### Q: 如何貢獻新方法或問題？

A: 使用 `submit-method` 和 `submit-problem` 命令提交到 Matrix Marketplace。也可以通過 Web UI 操作。

Use `submit-method` and `submit-problem` commands. Also available via Web UI.

### Q: 緩衝區共識需要多少投票？

A: 最少 3 個分類員投票，60% 一致即達成共識。最多 5 個分類員。

Minimum 3 classifiers, 60% agreement for consensus. Maximum 5 classifiers.

### Q: 支持哪些 AI 模型？

A: 任何 OpenAI 兼容接口的模型。已測試 DeepSeek (deepseek-v4-flash, deepseek-chat) 和 OpenAI (gpt-4o)。

Any OpenAI-compatible API. Tested with DeepSeek (deepseek-v4-flash, deepseek-chat) and OpenAI (gpt-4o).

### Q: 什麼是 Discovery Server？為什麼需要它？

A: Discovery Server 是一個輕量級節點發現服務器（類似 BitTorrent Tracker）。它解決了 P2P 網絡中的核心問題：新節點如何找到其他節點而不需要手動配置 IP 地址。啟動一個 Hub 作為 Discovery Server，其他 Hub 通過 `--discovery-url` 自動宣告自己和發現其他節點。

A lightweight peer discovery server (like a BitTorrent tracker). It solves the core P2P problem: how new nodes find others without manual IP configuration. Start one hub as Discovery Server; other hubs auto-announce and discover peers via `--discovery-url`.

### Q: 如何保護 Discovery Server 不被攻擊？

A: 內建 6 層安全防護：(1) ed25519 簽名身份驗證 — 防止節點偽造；(2) IP 反欺騙 — 服務器檢測真實來源 IP；(3) 速率限制 — 每 IP 60 請求/分鐘；(4) 隱私保護 — 節點列表隨機返回最多 30 個；(5) LRU 淘汰 — 防止內存耗盡；(6) NAT 感知 — 返回檢測到的公網 IP。

Built-in 6-layer security: (1) ed25519 signed identity to prevent impersonation; (2) IP anti-spoofing via source IP detection; (3) rate limiting at 60 req/min per IP; (4) privacy via random subset (max 30 peers); (5) LRU eviction to prevent memory exhaustion; (6) NAT awareness returning detected public IP.

### Q: 如何運行測試？

```bash
# 全部測試 | All tests (361 tests)
python3 -m unittest discover -s tests -p "test_*.py" -v

# 單個模塊 | Single module
python3 -m unittest tests/test_token_layer.py -v
```

---

> 更多技術細節參見 [DESIGN.md](../DESIGN.md)、[modules.md](modules.md)、[p2p-hub.md](p2p-hub.md)。
> For more technical details, see [DESIGN.md](../DESIGN.md), [modules.md](modules.md), [p2p-hub.md](p2p-hub.md).
