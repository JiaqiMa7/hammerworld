# HammerWorld 項目交接文檔

## 日期

2026-05-14

---

# Part 1: 項目快速上手

## 1. 項目概覽

HammerWorld 是一個**去中心化創意挖礦網絡**（Idea Mining Network），結合 TRIZ 方法論、AI 跨域分析和區塊鏈風格的代幣經濟。

**核心流程：**

```
方法矩陣 × 問題矩陣 → 隨機組合 → 多維度 AI 評估 → 排行榜 → 代幣獎勵
```

- **零強制依賴**：核心模塊只用 Python 3.8+ 標準庫
- **AI 可插拔**：兼容 OpenAI / DeepSeek / Ollama 等任何 OpenAI 兼容 API
- **可選依賴**：`pip install cryptography`（Ed25519 身份簽名）
- **語言**：代碼和文檔用英文，用戶界面支持英文/繁體中文雙語

## 2. 目錄結構

```
hammerworld/
├── src/
│   ├── cli/main.py          # CLI 入口（24 條命令）
│   ├── engine/              # 核心引擎：數據模型、加載器、組合生成器
│   │   ├── models.py        # Method, Problem, Combination, EvalDimension 等
│   │   ├── loader.py        # 從 JSON 加載方法和問題
│   │   ├── combiner.py      # 確定性 Fisher-Yates 組合生成
│   │   └── config.py        # HammerConfig 全局配置單例
│   ├── triz/                # TRIZ 方法論
│   │   ├── knowledge.py     # 39 個工程參數 + 40 個發明原理
│   │   ├── agent.py         # TRIZAgent：問題標準化與分析
│   │   ├── contradiction_matrix.py  # 39×39 矛盾矩陣
│   │   └── prompts.py       # LLM prompt 模板
│   ├── evaluation/          # AI 評估
│   │   ├── scorer.py        # 8 維度評分管線 + 非對稱閾值（任一維度 ≥8.0 即通過）
│   │   └── providers.py     # OpenAI 兼容 API 客戶端（純 urllib，無需 openai 包）
│   ├── hub/                 # P2P 聯邦網絡與 Web 界面
│   │   ├── leaderboard.py   # SQLite 數據庫（~1800 行）：存儲、查詢、遷移
│   │   ├── peer.py          # P2P Gossip 協議（Push+Pull，30s 間隔）
│   │   ├── server.py        # HTTP 服務器（stdlib http.server）
│   │   ├── web.py           # 服務端 HTML 渲染（~1700 行，雙語）
│   │   ├── discovery.py     # 發現服務器（BT tracker 模式）
│   │   ├── token_layer.py   # 代幣付費門控
│   │   ├── identity.py      # Ed25519 身份管理
│   │   └── agent_assistant.py  # Web AI 助手（18 種意圖）
│   └── blockchain/          # 區塊鏈緩衝區
│       ├── buffer.py        # 提交→分類→共識→發布管線
│       └── contracts.py     # IDEA 代幣 + 質押合約
├── tests/                   # 21 個測試文件，413 條測試
├── data/
│   ├── methods.json         # 35 種思維方法（4 個等級）
│   ├── problems.json        # 22 個未解決問題（6 個領域）
│   └── leaderboard.db       # SQLite 數據庫
├── docs/                    # 內部文檔
├── readme/                  # 詳細功能文檔（教程、模塊說明、P2P hub 指南）
├── README.md                # 項目的主要文檔
├── DESIGN.md                # 架構設計文檔
├── CLAUDE.md                # Claude Code 指導文件
└── .env                     # HAMMERWORLD_API_KEY, HAMMERWORLD_API_BASE, HAMMERWORLD_MODEL
```

## 3. 核心模塊職責

### src/engine/ — 核心引擎

| 文件 | 職責 |
|------|------|
| `models.py` | `Method`, `Problem`, `EvalScore`, `AIAnalysis`, `Combination` 等 dataclass；`EvalDimension`（8 維度）、`Domain`（7 領域）等枚舉 |
| `loader.py` | `load_methods()` / `load_problems()` 從 JSON 加載並反序列化 |
| `combiner.py` | `generate_combinations()` 確定性組合生成，基於 `SHA256(block_height + address + nonce)` 種子 |
| `config.py` | 配置優先級：環境變量 > `~/.hammerworld/config` > 內置默認值 |

### src/evaluation/ — AI 評估

- **8 個評估維度**：elegance, weirdness, human_feasibility, ai_feasibility, novelty, analogy_distance, scaling_potential, side_effects
- **非對稱閾值**：任一維度 ≥ 8.0 即通過（保護「怪但有趣」的想法）
- `OpenAIProvider` 只使用 `urllib.request`，無需 `pip install openai`

### src/hub/ — P2P 聯邦與 Web

- **LeaderboardDB**：SQLite 存儲，自動 schema 遷移（當前 v2）
- **PeerManager**：Push+Pull Gossip，30s 增量同步，TTL 防無限傳播
- **Web UI**：雙語（英文/繁體中文），服務端渲染 HTML
- **發現服務器**：BT tracker 模式，hub 自動註冊/發現，零手動配置

### src/blockchain/ — 區塊鏈緩衝區

- **BufferZone**：提交→分類→共識→發布（最少 3 個分類者，共識閾值 0.6）
- **SimulatedToken**：IDEA 代幣，水龍頭（1000 代幣/小時，最多 10 次）
- **費用**：查看分析 10 IDEA（80% 礦工 + 10% 發現者 + 10% 協議），解鎖排行榜 20 IDEA，隨機抽取 5 IDEA

## 4. 快速啓動

```bash
# 基本驗證（無需 API key）
python3 -c "
from src.engine.loader import load_methods, load_problems
from src.engine.combiner import generate_combinations
methods = load_methods()
problems = load_problems()
print(f'{len(methods)} methods, {len(problems)} problems OK')
"

# 挖礦（需要 API key）
export HAMMERWORLD_API_KEY=sk-...
python3 -m src.cli.main mine --batch 5

# 查看排行榜
python3 -m src.cli.main top --limit 10

# 啓動 Web 服務器
python3 -m src.cli.main web --port 8765
# 然後訪問 http://localhost:8765/

# P2P 聯邦（多 hub）
python3 -m src.cli.main hub --port 8765                              # 發現服務器
python3 -m src.cli.main web --port 8766 --discovery-url http://localhost:8765  # 工作節點 A
python3 -m src.cli.main web --port 8767 --discovery-url http://localhost:8765  # 工作節點 B

# 運行全部測試
python3 -m unittest discover tests/ -v
```

## 5. 配置

優先級（高到低）：
1. 環境變量：`HAMMERWORLD_API_KEY`, `HAMMERWORLD_API_BASE`, `HAMMERWORLD_MODEL`
2. `~/.hammerworld/config` 文件（key=value 格式）
3. 內置默認值（OpenAI, gpt-4o）

`~/.hammerworld/config` 示例：
```
api_key=sk-xxx
api_base=https://api.deepseek.com
model=gpt-4o
agent_model=gpt-4o
mining_model=deepseek-v4-pro
HAMMERWORLD_ADDRESS=0x...
```

## 6. CLI 命令一覽

| 類別 | 命令 | 說明 |
|------|------|------|
| 核心 | `mine` | 生成 method×problem 組合 |
| | `top` | 排行榜 |
| | `search` | 搜索 |
| | `random` | 隨機抽取 |
| | `hub` | 啓動 P2P hub（API） |
| | `web` | 啓動 hub + Web UI |
| | `keygen` | 生成 Ed25519 身份密鑰 |
| | `triz-analyze` | TRIZ 問題標準化分析 |
| 矩陣市場 | `submit-method` | 提交思維方法 |
| | `submit-problem` | 提交未解決問題 |
| 數學區 | `math-mine` | 解鎖數學問題區 |
| | `math-submit` | 提交數學解答 |
| 緩衝區 | `buffer-submit` | 提交分析到緩衝區 |
| | `buffer-classify` | 分類投票 |
| 代幣 | `pay-view` | 付費查看分析 |
| | `token-balance` | 查看代幣餘額 |
| | `identity` | 顯示/設置身份地址 |

## 7. 數據庫

- **文件**：`data/leaderboard.db`（可通過 `--db` 參數指定）
- **引擎**：SQLite，WAL 模式
- **Schema 版本**：v2（`_schema_version` 表追蹤）
- **核心表**：`combinations`（run_id PK）、`paid_views`、`viewer_ratings`、`user_draws`、`token_accounts`、`buffer_submissions`、`math_problems`、`math_solutions` 等

## 8. 關鍵設計決策

- **零強制依賴**：只用 Python 標準庫，AI 提供商通過 `AIProvider` 協議可插拔
- **非對稱閾值**：保留「怪但有趣」的想法（任一維度高分即通過，不看平均分）
- **確定性隨機**：SHA256 種子 + Fisher-Yates，可復現
- **P2P 去中心化**：多 hub 自組織，無中心服務器
- **6 層安全**：Ed25519 簽名身份、IP 反欺騙、速率限制、隱私保護、LRU 淘汰、NAT 感知

## 9. 測試

```bash
# 全部測試（413 條）
python3 -m unittest discover tests/ -v

# 單文件
python3 -m unittest tests.test_leaderboard -v
```

21 個測試文件覆蓋所有核心模塊：models、loader、combiner、evaluation、leaderboard、token_layer、web、server、peer、discovery、identity、blockchain、cli、triz、collections、math_zone。

---

# Part 2: Schema 重構詳情

## 背景

舊設計用 `combo_id`（method×problem 組合標識）作 PK，導致同一 method×problem 只能存一條記錄，新的挖礦結果會覆蓋舊數據。本次重構引入 `run_id`（每次挖礦唯一）作 PK，`combo_group_id` 作分組鍵，支持同一組合的多條分析共存，並將付費模型改爲按組付費。

## 核心概念

| 概念 | 格式 | 說明 |
|------|------|------|
| `run_id` (PK) | `combo_{method_id}_{problem_id}_{ts_ms}_{rand4}` | 每次挖礦唯一標識 |
| `combo_group_id` | `combo_{method_id}_{problem_id}` | method×problem 組合標識，等於舊 `combo.id` |
| `combo_id` (property) | 返回 `run_id` | LeaderboardEntry 的向後兼容屬性，舊代碼讀取 `entry.combo_id` 不受影響 |

## 付費模型變更

- **舊**：每個 entry 單獨付費
- **新**：按 combo_group 付費，付一次費解鎖該組全部分析
- `paid_views` 的 PK 從 `(viewer_addr, combo_id)` 改爲 `(viewer_addr, combo_group_id)`
- `viewer_ratings` 仍按 `run_id` 評分（每個礦工的分析獨立評分）

## 文件改動

| File | Change |
|------|--------|
| `src/engine/models.py` | 新增 `Combination.make_run_id()` 靜態方法 |
| `src/hub/leaderboard.py` | **核心改動**：LeaderboardEntry dataclass、schema v2、migration、查詢重寫 |
| `src/hub/token_layer.py` | 按組付費：`check_view_access` / `pay_for_view` / `rate_analysis` |
| `src/hub/web.py` | 新增 `render_combo_group()` 頁面 + 8 個翻譯鍵 + URL 鏈接更新 |
| `src/hub/server.py` | 新增 `/web/combo/{combo_group_id}` 路由 |
| `src/hub/peer.py` | P2P 序列化：發送 `run_id` + `combo_group_id` + `combo_id`（向後兼容） |
| `src/hub/agent_assistant.py` | 挖礦輸出使用 `entry.run_id` |
| `tests/` (6 files) | 構造函數、斷言、序列化測試更新 |

## DB 遷移機制

### 版本管理

- `_schema_version` 表追蹤版本，使用 `MAX(version)` 判斷當前版本（防止多行問題）
- 初始創建時不插入默認版本，遷移完成後由遷移腳本設置
- 版本設置使用 `DELETE + INSERT` 確保只有一行

### 遷移流程 (`_migrate_schema_v2`)

1. 檢查 `MAX(version) >= 2` → 跳過
2. 檢測已是 v2 schema（通過 `PRAGMA table_info` 檢查有 `combo_group_id` 無 `combo_id` 列）→ 僅設置版本，跳過
3. 重建 4 個表：`combinations`、`paid_views`、`viewer_ratings`、`user_draws`
4. 遷移模式：`CREATE v2_table → INSERT SELECT FROM old → DROP old → ALTER RENAME`

### 向後兼容

- `LeaderboardEntry.combo_id` 是 `@property`，返回 `run_id`
- `get_ratings_for_combo()` / `get_avg_rating_for_combo()` 保留爲別名
- P2P wire format 同時發送 `run_id`、`combo_group_id`、`combo_id`（= run_id）
- 收到舊 peer 的 `combo_id` 時自動轉爲 `run_id` 和 `combo_group_id`

## 修復的 Bug

1. **`idx_combo_group_id` 在遷移前創建** — 索引引用了尚不存在的 `combo_group_id` 列，改爲遷移後創建
2. **`_schema_version` 多行問題** — 初始 `INSERT OR IGNORE INTO _schema_version VALUES (2)` 在已有 version=1 的 DB 中插入了第二行，導致遷移檢查跳過。改用 `MAX(version)` 查詢
3. **`:memory:` DB 的版本錯亂** — `_migrate_math_to_tree` 在空表時設置 version=1，導致 `_migrate_schema_v2` 以爲需要遷移。新增 v2 schema 檢測（`PRAGMA table_info`）
4. **`viewer_ratings.comment` 列缺失** — 舊 v1 表無此列，遷移前新增 `ALTER TABLE ADD COLUMN`

## 新增 URL 路由

| Path | Handler |
|------|---------|
| `/web/combo/{combo_group_id}` | `render_combo_group()` — 顯示該組所有分析 |

## 驗證

```bash
# 運行全部測試
python3 -m unittest discover tests/ -v

# 手動測試
python3 -m src.cli.main web --port 8765

# 1. 挖礦 → 查看 run_id 格式（帶時間戳和隨機碼）
# 2. 訪問 /web/my-entries → 看到挖礦結果
# 3. 再次挖同一個 method×problem → 兩條都保留（不覆蓋）
# 4. 訪問 /web/combo/{combo_group_id} → 看到全部分析
# 5. 付費一次 → 解鎖該組全部分析（非單條）
```

## 注意事項

- **Web URL 中的 `combo_id` 參數**現在實際上是 `run_id`，`render_entry()` 對兩者都能處理（先按 run_id 查，找不到則重定向到 combo group 頁面）
- **`math_access_log.combo_id`** 列未遷移，可能混雜 run_id 和 combo_group_id 值（不影響功能，PK 在 `(problem_id, method_collection_id, user_address)`）
- **P2P 舊 peer** 收到新條目時 `combo_id` = run_id（帶時間戳），舊 peer 無法對同組條目去重，但不會丟數據
- **HTTP server 在 discovery 完成後才啓動**（約 3-10 秒延遲），這是原有設計，非本次改動引入
- **所有構造 `LeaderboardEntry` 的地方必須傳 `run_id` 和 `combo_group_id`**，不要傳舊的 `combo_id` 參數（已從 dataclass 中移除）
