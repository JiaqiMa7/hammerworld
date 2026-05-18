# HammerWorld 項目交接文檔

## 日期

2026-05-17

---

# Part 1: 項目全貌

## 1. 項目定位

HammerWorld（創意挖礦網絡 / Idea Mining Network）是一個**去中心化的 AI 輔助創意生成與評估系統**。核心思想是：將人類的思維方法（Methods）與未解決的問題（Problems）進行隨機交叉組合，用 AI 從 8 個維度評估每個組合的潛力，結果存入分佈式排行榜，並用區塊鏈風格的代幣經濟激勵參與。

**一句話概括**：`方法矩陣 × 問題矩陣 → 隨機組合 → 多維度 AI 評估 → P2P 排行榜 → 代幣獎勵`

**技術哲學**：零強制依賴，全部核心模塊只使用 Python 3.8+ 標準庫。AI 提供商通過 Protocol 接口可插拔。可選依賴只有 `cryptography`（Ed25519 身份簽名）。

## 2. 目錄樹

```
hammerworld/
├── README.md                    # 項目的主要英文文檔（快速開始、CLI 參考、架構概述）
├── DESIGN.md                    # 完整架構設計文檔（中文，~800 行）
├── CLAUDE.md                    # Claude Code 指導文件（構建/測試命令、架構決策記錄）
├── .env                         # 環境變量（HAMMERWORLD_API_KEY, HAMMERWORLD_API_BASE, HAMMERWORLD_MODEL）
├── .gitignore                   # 忽略 __pycache__/, .db, .sqlite3, .claude/, .env
│
├── src/                         # 全部源碼
│   ├── cli/
│   │   └── main.py              # CLI 入口點（~1300 行，24 個子命令，argparse）
│   │
│   ├── engine/                  # 核心引擎層
│   │   ├── models.py            # 數據模型：Method, Problem, Combination, EvalScore,
│   │   │                        #   AIAnalysis, Submission；枚舉：EvalDimension(8維度),
│   │   │                        #   Domain(7領域), MethodLevel(4級), ProblemMaturity(4級),
│   │   │                        #   ConstraintType(5類)
│   │   ├── loader.py            # JSON 加載器：load_methods(), load_problems(),
│   │   │                        #   filter_methods(), filter_problems()
│   │   ├── combiner.py          # 組合生成器：SHA256 確定性種子 + Fisher-Yates 洗牌 +
│   │   │                        #   互質步進算法，generate_combinations() 自動調參
│   │   └── config.py            # HammerConfig 全局配置單例：環境變量 > ~/.hammerworld/config > 默認值
│   │
│   ├── triz/                    # TRIZ 方法論層
│   │   ├── knowledge.py         # TRIZ 知識庫：39 個工程參數 + 40 個發明原理（含說明和示例）
│   │   ├── models.py            # TRIZ dataclass：EngineeringParameter, InventivePrinciple,
│   │   │                        #   TechnicalContradiction, PhysicalContradiction, TRIZAnalysis
│   │   ├── agent.py             # TRIZAgent：standardize()/analyze()；支持 AI 和規則雙模式
│   │   ├── contradiction_matrix.py  # 39×39 矛盾矩陣（稀疏），映射 (改善參數, 惡化參數) → 推薦原理
│   │   └── prompts.py           # LLM prompt 模板：系統提示、問題標準化、評估模板
│   │
│   ├── evaluation/              # AI 評估層
│   │   ├── scorer.py            # EvaluationPipeline：評估管線，evaluate()/evaluate_batch()/
│   │   │                        #   evaluate_and_filter()；JSON 解析 + 關鍵詞回退評分；
│   │   │                        #   非對稱閾值（任一維度 ≥8.0 即通過）；SHA-256 推理哈希
│   │   └── providers.py         # OpenAIProvider：只用 urllib.request，無需 openai 包；
│   │                            #   實現 AIProvider Protocol（generate() 方法）
│   │
│   ├── hub/                     # P2P 聯邦網絡 + Web 界面層
│   │   ├── leaderboard.py       # LeaderboardDB（~1800 行）：SQLite 存儲核心
│   │   │                        #   Schema v2：run_id PK + combo_group_id 分組
│   │   │                        #   自動遷移 _migrate_math_to_tree (v0→v1) + _migrate_schema_v2 (v1→v2)
│   │   │                        #   LeaderboardEntry, RandomDrawResult dataclass
│   │   ├── peer.py              # PeerManager：P2P Gossip 協議
│   │   │                        #   Push+Pull 每 30s；TTL 防無限傳播；PeerConfig 配置
│   │   │                        #   _entry_to_json() / _json_to_entry() 序列化
│   │   ├── server.py            # HubServer：HTTP 服務器（stdlib http.server + ThreadingMixIn）
│   │   │                        #   _HubHandler：路由分發（do_GET 35+ 路由，do_POST 25+ 路由）
│   │   │                        #   HubAPI：REST API 處理器（health, stats, sync, announce）
│   │   │                        #   發現服務器端點：discovery announce / peers / heartbeat
│   │   ├── web.py               # 服務端 HTML 渲染（~3000 行）
│   │   │                        #   雙語翻譯系統 _T（~120 個翻譯鍵）
│   │   │                        #   30+ render_*() 頁面渲染函數
│   │   │                        #   _base_page() 統一的 HTML 框架 + _login_widget()
│   │   ├── discovery.py         # DiscoveryServer：BT tracker 風格的發現服務器
│   │   │                        #   RateLimiter（每 IP 滑動窗口限流）、LRU 淘汰、NAT 感知
│   │   │                        #   Ed25519 簽名公告驗證、隱私保護（最多返回 30 個隨機 peer）
│   │   ├── token_layer.py       # TokenGate：付費門控
│   │   │                        #   VIEW_FEE=10, LEADERBOARD_FEE=20, DRAW_FEE=5 IDEA
│   │   │                        #   費用分配：80% 礦工 + 10% 發現者 + 10% 協議
│   │   ├── identity.py          # IdentityManager：Ed25519 密鑰管理
│   │   │                        #   generate_keypair(), sign_announce(), verify_announce()
│   │   ├── user_identity.py     # 用戶身份：地址派生 0x+SHA256(pubkey)[:40]，隨機種子回退
│   │   └── agent_assistant.py   # Web AI 助手（~500 行）
│   │                            #   18 種意圖類型；LLM 結構化 JSON 或關鍵詞匹配回退
│   │                            #   支持英文和中文
│   │
│   └── blockchain/              # 區塊鏈緩衝區層
│       ├── buffer.py            # BufferZone：提交→分類→共識→發布管線
│       │                        #   MIN_CLASSIFICATIONS=3, MAX_CLASSIFICATIONS=7
│       │                        #   CONSENSUS_THRESHOLD=0.6, SPAM_DETECTOR_BONUS=5
│       │                        #   classify() + _check_consensus() + _distribute_rewards()
│       └── contracts.py         # SimulatedToken（IDEA 代幣）：mint/transfer/balance_of/faucet
│                                #   StakingContract：stake/release_stake/slash_stake
│
├── tests/                       # 測試（21 個文件，413 條測試，unittest 框架）
│   ├── test_models.py           # 核心 dataclass、枚舉、Combination.make_id/make_run_id
│   ├── test_loader.py           # 方法/問題加載和過濾
│   ├── test_combiner.py         # 組合生成算法
│   ├── test_evaluation.py       # 評估管線、評分解析、閾值邏輯
│   ├── test_leaderboard.py      # SQLite 存儲、CRUD、搜索、分頁
│   ├── test_token_layer.py      # 付費查看、排行榜解鎖、抽取付費、評分
│   ├── test_web.py              # HTML 渲染、翻譯系統、XSS 防護
│   ├── test_server.py           # HTTP 端點、路由
│   ├── test_peer.py             # Peer 管理、Gossip 同步、序列化往返
│   ├── test_discovery.py        # 發現服務器註冊、限流
│   ├── test_identity.py         # Ed25519 密鑰生成、簽名、驗證
│   ├── test_blockchain.py       # 代幣、質押、緩衝區管線
│   ├── test_cli.py              # CLI 參數解析、身份管理、挖礦輸出
│   ├── test_contradiction_matrix.py  # TRIZ 矛盾矩陣查詢
│   ├── test_triz_agent.py       # TRIZ 標準化、規則/ AI 分析
│   ├── test_triz_knowledge.py   # 工程參數和發明原理結構完整性
│   ├── test_collections.py      # 合集市場（創建、星標、導入）
│   ├── test_submit.py           # 方法/問題提交到矩陣
│   └── test_math_zone.py        # 數學區門控機制、解答、MCTS 樹
│
├── data/                        # 數據文件
│   ├── methods.json             # 35 種思維方法（跨 4 個等級，含示例和觸發條件）
│   ├── problems.json            # 22 個未解決問題（跨 6 個領域/7 個領域含 mathematics）
│   └── leaderboard.db           # SQLite 數據庫（默認路徑，可通過 --db 參數指定）
│
├── docs/                        # 內部文檔
│   └── schema-redesign-handover.md  # 本文檔
│
└── readme/                      # 詳細功能文檔
    ├── tutorial.md              # 完整教程
    ├── modules.md               # 模塊說明
    ├── p2p-hub.md               # P2P Hub 指南
    └── development.md           # 開發指南
```

## 3. 完整數據模型

### 3.1 枚舉類型

```python
EvalDimension    # 8 個評估維度（1-10 分）
├── ELEGANCE           # 優雅度
├── WEIRDNESS           # 怪異度
├── HUMAN_FEASIBILITY    # 人類可行性
├── AI_FEASIBILITY       # AI 可行性
├── NOVELTY             # 新穎度
├── ANALOGY_DISTANCE    # 類比距離
├── SCALING_POTENTIAL   # 規模化潛力
└── SIDE_EFFECTS        # 副作用

Domain           # 7 個問題領域
├── MEDICINE      # 醫學
├── ENERGY        # 能源
├── ENVIRONMENT   # 環境
├── INFORMATION   # 信息
├── MATERIALS     # 材料
├── SOCIETY       # 社會
└── MATHEMATICS   # 數學

MethodLevel      # 4 個方法等級
├── BASIC_HEURISTIC   (1)  # 基本啓發式
├── STRUCTURED        (2)  # 結構化方法
├── DOMAIN_SPECIFIC   (3)  # 領域特定方法
└── COMPOSITE         (4)  # 複合方法

ProblemMaturity  # 4 個問題成熟度
├── NO_SOLUTION       (1)  # 無解決方案
├── PARTIAL_POOR      (2)  # 部分/不佳方案
├── TOO_EXPENSIVE     (3)  # 方案太貴
└── BOTTLENECK_KNOWN  (4)  # 瓶頸已知

ConstraintType   # 5 種約束類型
├── PHYSICAL_LIMIT  # 物理限制
├── RESOURCE        # 資源約束
├── TIME            # 時間約束
├── COMPLEXITY      # 複雜度約束
└── ETHICAL         # 倫理約束
```

### 3.2 核心 Dataclass

```python
@dataclass
class Method:
    id: str                          # "method_{domain}_{index:03d}"
    name: str                        # 人類可讀名稱
    domain: str                      # 方法所屬領域
    level: MethodLevel               # 1-4
    description: str
    trigger_conditions: list[str]    # 何時適用此方法
    examples: list[str]              # 使用示例
    prerequisites: list[str]         # 前置要求
    compatible_with: list[str]       # 兼容的其他方法 ID

@dataclass
class Problem:
    id: str                          # "problem_{domain}_{index:03d}"
    title: str                       # 人類可讀標題
    domain: Domain                   # 問題所屬領域
    description: str
    constraint_types: list[ConstraintType]
    maturity: ProblemMaturity        # 1-4
    triz_standardized: Optional[dict] # TRIZ 標準化結果

@dataclass
class EvalScore:
    dimension: EvalDimension         # 哪個維度
    score: float                     # 1.0-10.0
    explanation: str                 # AI 給出的解釋

@dataclass
class AIAnalysis:
    scores: list[EvalScore]          # 8 個維度的評分
    analysis_text: str               # AI 的完整分析文本
    model_name: str                  # 使用的模型
    model_version: str
    inference_hash: str              # SHA-256 哈希（可復現性）

@dataclass
class Combination:
    id: str                          # combo_group_id = "combo_{method_id}_{problem_id}"
    method: Method
    problem: Problem
    analyses: list[AIAnalysis]
    created_at: float

@dataclass
class LeaderboardEntry:              # 排行榜中的一條記錄
    rank: int                        # 排名（查詢時計算）
    run_id: str                      # 本次挖礦的唯一 ID（PK）
    combo_group_id: str              # method×problem 組合標識（分組鍵）
    method_name: str
    method_domain: str
    method_level: int
    problem_title: str
    problem_domain: str
    best_dimension: str              # 得分最高的維度名
    best_score: float
    elegance: float                  # 8 個維度的具體分數
    weirdness: float
    human_feasibility: float
    ai_feasibility: float
    novelty: float
    analogy_distance: float
    scaling_potential: float
    side_effects: float
    miner_address: str               # 礦工地址
    created_at: float                # Unix 時間戳
    analysis_text: str               # AI 分析全文

    # 向後兼容
    @property
    def combo_id(self) -> str:
        return self.run_id
```

### 3.3 ID 生成規則

| ID 類型 | 格式 | 示例 | 生成方法 |
|---------|------|------|---------|
| method_id | `method_{domain}_{index:03d}` | `method_physics_001` | `Method.make_id()` |
| problem_id | `problem_{domain}_{index:03d}` | `problem_energy_005` | `Problem.make_id()` |
| combo_group_id | `combo_{method_id}_{problem_id}` | `combo_method_physics_001_problem_energy_005` | `Combination.make_id()` |
| run_id | `combo_{method_id}_{problem_id}_{ts_ms}_{rand4}` | `combo_method_physics_001_problem_energy_005_1712345678000_abcd` | `Combination.make_run_id()` |

## 4. 完整數據庫 Schema（SQLite，WAL 模式，當前 v2）

### 4.1 combinations（核心表，~1800 行代碼管理）

```sql
CREATE TABLE combinations (
    run_id TEXT PRIMARY KEY,              -- 每次挖礦唯一標識（v2 新增）
    combo_group_id TEXT NOT NULL,         -- method×problem 組標識（v2 新增）
    method_name TEXT NOT NULL,
    method_domain TEXT NOT NULL,
    method_level INTEGER NOT NULL,
    problem_title TEXT NOT NULL,
    problem_domain TEXT NOT NULL,
    best_dim TEXT NOT NULL,               -- 得分最高的維度
    best_score REAL NOT NULL DEFAULT 0,
    elegance REAL DEFAULT 0,              -- 8 個維度的評分
    weirdness REAL DEFAULT 0,
    human_feasibility REAL DEFAULT 0,
    ai_feasibility REAL DEFAULT 0,
    novelty REAL DEFAULT 0,
    analogy_distance REAL DEFAULT 0,
    scaling_potential REAL DEFAULT 0,
    side_effects REAL DEFAULT 0,
    miner_addr TEXT DEFAULT '',           -- 礦工地址
    created_at REAL DEFAULT 0,            -- Unix 時間戳
    analysis_text TEXT DEFAULT ''         -- AI 分析全文
);
-- 索引
CREATE INDEX idx_combo_group_id ON combinations(combo_group_id);
CREATE INDEX idx_best_dim ON combinations(best_dim);
CREATE INDEX idx_best_score ON combinations(best_score DESC);
CREATE INDEX idx_problem_domain ON combinations(problem_domain);
CREATE INDEX idx_method_domain ON combinations(method_domain);
```

### 4.2 paid_views（付費查看記錄）

```sql
CREATE TABLE paid_views (
    viewer_addr TEXT NOT NULL,
    combo_group_id TEXT NOT NULL,         -- v2：改爲按組付費
    paid_at REAL DEFAULT 0,
    paid_amount INTEGER DEFAULT 0,        -- 付費金額
    analyzer_addr TEXT DEFAULT '',        -- 分析者（收款方）
    protocol_addr TEXT DEFAULT '',        -- 協議費收款方
    PRIMARY KEY (viewer_addr, combo_group_id)
);
```

### 4.3 viewer_ratings（用戶評分）

```sql
CREATE TABLE viewer_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    viewer_addr TEXT NOT NULL,
    run_id TEXT NOT NULL,                 -- v2：改爲評 run_id
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    comment TEXT DEFAULT '',
    created_at REAL DEFAULT 0,
    UNIQUE(viewer_addr, run_id)
);
```

### 4.4 user_draws（隨機抽取記錄）

```sql
CREATE TABLE user_draws (
    viewer_addr TEXT NOT NULL,
    board_name TEXT NOT NULL,
    drawn_run_ids TEXT NOT NULL,          -- v2：改爲逗號分隔的 run_id 列表
    draw_seed INTEGER NOT NULL,
    drawn_at REAL DEFAULT 0
);
```

### 4.5 leaderboard_access（排行榜解鎖）

```sql
CREATE TABLE leaderboard_access (
    viewer_addr TEXT NOT NULL,
    board_name TEXT NOT NULL,             -- 排行榜名（如 "weirdness_all"）
    paid_at REAL DEFAULT 0,
    expires_at REAL DEFAULT 0,            -- 24 小時後過期
    PRIMARY KEY (viewer_addr, board_name)
);
```

### 4.6 token_accounts（代幣賬戶）

```sql
CREATE TABLE token_accounts (
    address TEXT PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    staked INTEGER DEFAULT 0,
    total_earned INTEGER DEFAULT 0,
    total_slashed INTEGER DEFAULT 0,
    consecutive_correct INTEGER DEFAULT 0,   -- 連續正確分類次數
    total_classifications INTEGER DEFAULT 0,
    correct_classifications INTEGER DEFAULT 0,
    last_faucet_at REAL DEFAULT 0,           -- 上次領水時間
    faucet_count INTEGER DEFAULT 0            -- 累計領水次數（最多 10 次）
);
```

### 4.7 stake_records（質押記錄）

```sql
CREATE TABLE stake_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT DEFAULT 'active',            -- active / released / slashed
    submission_id TEXT DEFAULT '',            -- 關聯的提交 ID
    created_at REAL DEFAULT 0,
    released_at REAL DEFAULT 0
);
```

### 4.8 buffer_submissions + buffer_classifications（區塊鏈緩衝區）

```sql
CREATE TABLE buffer_submissions (
    id TEXT PRIMARY KEY,
    combo_id TEXT NOT NULL,                  -- 引用 combo_group_id（未遷移列名）
    method_id TEXT NOT NULL,
    method_name TEXT DEFAULT '',
    problem_id TEXT NOT NULL,
    problem_title TEXT DEFAULT '',
    submitter TEXT NOT NULL,
    status TEXT DEFAULT 'pending',           -- pending → classified → published / disputed
    analysis_json TEXT NOT NULL,
    analysis_text TEXT DEFAULT '',
    domain_label TEXT DEFAULT '',
    nsfw INTEGER DEFAULT 0,
    spam INTEGER DEFAULT 0,
    classifier_count INTEGER DEFAULT 0,
    consensus_domain TEXT DEFAULT '',
    consensus_nsfw INTEGER DEFAULT 0,
    consensus_spam INTEGER DEFAULT 0,
    staked_amount INTEGER DEFAULT 0,
    created_at REAL DEFAULT 0,
    classified_at REAL DEFAULT 0
);

CREATE TABLE buffer_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id TEXT NOT NULL,
    classifier_addr TEXT NOT NULL,
    domain_label TEXT NOT NULL,
    is_nsfw INTEGER DEFAULT 0,
    is_spam INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    matched_consensus INTEGER DEFAULT 0,     -- 是否匹配最終共識
    reward_earned INTEGER DEFAULT 0,
    created_at REAL DEFAULT 0
);
```

### 4.9 math_problems + math_solutions + math_access_log（數學區）

```sql
CREATE TABLE math_problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'number_theory',
    creator TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    created_at REAL DEFAULT 0
);

CREATE TABLE math_solutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    method_collection_id INTEGER NOT NULL,
    user_address TEXT DEFAULT '',
    parent_solution_id INTEGER DEFAULT NULL,  -- 父解答（MCTS 樹父節點）
    steps_json TEXT NOT NULL,                  -- JSON 步驟列表
    max_correct_step INTEGER DEFAULT 0,
    seed_combo_id TEXT DEFAULT '',             -- 解鎖用的 combo_id
    seed_analysis_json TEXT DEFAULT '',
    created_at REAL DEFAULT 0,
    updated_at REAL DEFAULT 0
);

CREATE TABLE math_access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    method_collection_id INTEGER NOT NULL,
    user_address TEXT NOT NULL,
    combo_id TEXT NOT NULL,                    -- 解鎖時使用的 combo
    analysis_json TEXT DEFAULT '',
    created_at REAL DEFAULT 0
);
```

### 4.10 math_tree_nodes + math_tree_edges（MCTS 數學樹）

```sql
CREATE TABLE math_tree_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    method_collection_id INTEGER NOT NULL,
    user_address TEXT DEFAULT '',
    content TEXT NOT NULL,
    node_type TEXT NOT NULL DEFAULT 'normal',  -- normal / terminal_success / terminal_failure
    q_value REAL NOT NULL DEFAULT 0.0,
    visit_count INTEGER NOT NULL DEFAULT 0,
    reward REAL DEFAULT 0.0,
    is_root INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT DEFAULT '{}',
    created_at REAL DEFAULT 0,
    updated_at REAL DEFAULT 0
);

CREATE TABLE math_tree_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_node_id INTEGER NOT NULL,
    child_node_id INTEGER NOT NULL,
    action_label TEXT NOT NULL,                -- 如 "step_1"
    action_description TEXT DEFAULT '',
    created_at REAL DEFAULT 0
);
```

### 4.11 其他表

```sql
-- 合集市場
CREATE TABLE method_collections (id, name, description, category, creator, stars, import_count, methods_json, created_at);
CREATE TABLE problem_collections (id, name, description, category, creator, stars, import_count, problems_json, created_at);
CREATE TABLE collection_stars (collection_type, collection_id, starrer, starred_at, PK(type, id, starrer));

-- 通用提交
CREATE TABLE submissions (id, type, data, submitter, status, submitted_at);

-- 抽取付費追蹤
CREATE TABLE draw_payments (viewer_addr TEXT PRIMARY KEY, paid_at REAL DEFAULT 0);

-- Schema 版本管理
CREATE TABLE _schema_version (version INTEGER PRIMARY KEY);
```

### 4.12 主要 DB 方法索引

| 方法 | 用途 |
|------|------|
| `insert(combo, miner_addr)` | 插入新挖礦結果（生成 run_id，返回 LeaderboardEntry） |
| `insert_from_sync(entry)` | 從 P2P 同步插入（檢查 run_id 和時間戳去重） |
| `_get_by_id(run_id)` | 按 run_id 查詢 |
| `get_group_runs(combo_group_id)` | 獲取某組合的全部運行記錄 |
| `get_top(dimension, domain, level, limit, offset)` | 排行榜查詢（支持維度/領域/等級篩選 + 分頁） |
| `get_since(timestamp, limit)` | P2P 增量同步：獲取某時間戳之後的條目 |
| `search(query, limit)` | 全文搜索（LIKE 匹配方法和問題名） |
| `random_draw(draw_count, viewer_addr)` | 隨機抽取（排除已抽取的，返回 RandomDrawResult） |
| `total_entries(domain)` | 計數（可選領域篩選） |
| `has_paid(viewer, combo_group_id)` | 檢查是否已付費 |
| `record_payment(viewer, combo_group_id, amount, ...)` | 記錄付費 |
| `record_rating(viewer, run_id, rating)` | 記錄評分 |
| `get_avg_rating_for_run(run_id)` | 獲取平均評分 |

## 5. 完整 HTTP API 參考

### 5.1 P2P API（GET 端點）

| 路徑 | 處理器 | 用途 |
|------|--------|------|
| `GET /health` | `handle_health()` | 健康檢查：返回 status, peer_id, entries 數 |
| `GET /stats` | `handle_stats()` | 統計：peer_id, entries, peers 數, uptime |
| `GET /peers` | `handle_get_peers()` | 獲取已知 peer 列表 |
| `GET /combinations?since={ts}&limit={n}` | `handle_get_combinations()` | P2P 增量同步：獲取 ts 之後的條目，返回 JSON |
| `GET /discovery/peers` | `handle_discovery_peers()` | 發現服務器：返回隨機 peer 列表（最多 30 個） |

### 5.2 P2P API（POST 端點）

| 路徑 | 處理器 | 用途 |
|------|--------|------|
| `POST /combinations` | `handle_post_combinations()` | P2P Gossip 接收：{entries: [...], ttl: [...]} |
| `POST /peers/announce` | `handle_announce()` | Peer 公告：註冊自己到其他 hub |
| `POST /discovery/announce` | `handle_discovery_announce()` | 發現服務器：公告自己，支持 Ed25519 簽名驗證 |
| `POST /discovery/heartbeat` | `handle_discovery_heartbeat()` | 發現服務器：心跳（保持活躍） |

### 5.3 Web UI 頁面（GET 端點）

| 路徑 | 渲染函數 | 說明 |
|------|---------|------|
| `GET /` 或 `/web` | `render_dashboard()` | 儀表板：總條目數、peer 數、按維度/領域分佈、熱門條目 |
| `GET /web/leaderboard?dim={d}&domain={d}&level={l}&limit={n}&offset={o}` | `render_leaderboard()` | 排行榜：支持維度/領域/等級篩選 + 分頁 + 付費解鎖 |
| `GET /web/search?q={query}` | `render_search()` | 搜索頁面：LIKE 匹配方法和問題名 |
| `GET /web/random?dim={d}&count={n}` | `render_random()` | 隨機抽取：排除已抽取的，顯示付費門控 |
| `GET /web/peers` | `render_peers()` | 節點列表：顯示已知 peer 的 IP、端口、最後在線時間 |
| `GET /web/entry/{run_id}` | `render_entry()` | 條目詳情：顯示分析全文、評分、評分表單；支持付費門控 |
| `GET /web/combo/{combo_group_id}` | `render_combo_group()` | **v2 新增**：顯示該組合的全部分析，按組付費 |
| `GET /web/my-entries?addr={address}` | `render_my_entries()` | 我的挖掘：顯示該地址的所有挖掘記錄 |
| `GET /web/tokens` | `render_token_dashboard()` | 代幣儀表板：餘額、付費歷史、消費統計 |
| `GET /web/submit` / `method` / `problem` | `render_submit_*()` | 矩陣市場：提交方法/問題表單 |
| `GET /web/submissions` | `render_submissions()` | 查看提交列表 |
| `GET /web/collections` / `new` / `{id}` | `render_collections()` | 合集市場：瀏覽、創建、詳情 |
| `GET /web/math` / `new` / `{pid}` / `{pid}/{mid}` / ... | `render_math_*()` | 數學區：問題列表、解答、MCTS 樹、解鎖 |
| `GET /web/buffer` / `pending` / `submissions` / `tokens` / `leaderboard` / `classify/{id}` | `render_buffer_*()` | 緩衝區：儀表板、待分類、提交列表、代幣、分類 |
| `GET /web/settings` | `render_settings()` | 設置頁面 |
| `GET /web/agent` | `render_agent_chat()` | AI 助手聊天界面 |
| `GET /web/logout` | 重定向到 `/` | 清除會話 Cookie |

### 5.4 Web 操作（POST 端點）

| 路徑 | 處理邏輯 | 說明 |
|------|---------|------|
| `POST /web/login` | 設置 Cookie | 用地址登錄（設置 viewer_addr Cookie） |
| `POST /web/create-address` | 生成 Ed25519 密鑰 | 創建新地址（可選 `--identity` 持久化） |
| `POST /web/pay/view/{run_id}` | `_handle_pay_view()` | 付費查看：扣 10 IDEA，80% 給礦工 |
| `POST /web/pay/leaderboard/{board}` | `_handle_pay_leaderboard()` | 付費解鎖排行榜：扣 20 IDEA，24h 有效 |
| `POST /web/pay/draw` | `_handle_pay_draw()` | 付費隨機抽取：扣 5 IDEA |
| `POST /web/rate/{run_id}` | `_handle_rate()` | 評分：1-5 星，需先付費 |
| `POST /web/faucet` | 發放 1000 IDEA | 水龍頭：1h 冷卻，最多 10 次 |
| `POST /web/submit/method` | 保存到 DB | 提交新方法 |
| `POST /web/submit/problem` | 保存到 DB | 提交新問題 |
| `POST /web/collections/new` | 保存到 DB | 創建新合集 |
| `POST /web/math/new` | 保存到 DB | 創建新數學問題 |
| `POST /web/math/{pid}/{mid}/unlock` | `grant_math_access()` | 解鎖數學區（用 combo_id） |
| `POST /web/buffer/classify/{sub_id}` | `buffer_zone.classify()` | 緩衝區分類投票 |
| `POST /web/settings/save` | 寫入 `~/.hammerworld/config` | 保存設置 |
| `POST /web/agent/chat` | agent_assistant | AI 助手對話 |
| `POST /web/agent/chat/json` | agent_assistant | AI 助手結構化對話 |
| `POST /web/agent/mine/run` | agent_assistant._run_mine() | 通過助手觸發挖礦 |
| `POST /web/agent/balance/json` | 返回代幣餘額 | 助手查詢餘額 |

## 6. P2P 網絡協議詳解

### 6.1 架構

採用 **混合 P2P 架構**：發現服務器（BT tracker 模式）+ Gossip 協議。

```
┌─────────────────┐     ┌─────────────────┐
│  Discovery Hub  │     │  Discovery Hub  │  (可多個，互相備份)
│  :8765          │     │  :8766          │
└────────┬────────┘     └────────┬────────┘
         │   announce/discover   │
    ┌────┴───────────────────────┴────┐
    │                                 │
┌───┴────┐  gossip(Push+Pull)  ┌──────┴───┐
│ Hub A  │◄───────────────────►│  Hub B   │
│ :8770  │                     │  :8771   │
└────────┘                     └──────────┘
```

### 6.2 PeerManager 生命週期

```
start()
  ├── 啓動 _run_loop 後臺線程（daemon）
  ├── 從 discovery_urls 獲取 peer 列表（discover_peers）
  │   └── GET /discovery/peers → [{peer_id, address, port, ...}]
  ├── 對每個發現的 peer 執行 _announce_and_join()
  │   ├── POST /peers/announce → {peer_id, address, port}
  │   │   └── 響應包含 peer 的 peer_id + 已知 peer 列表
  │   └── GET /combinations?since=0&limit=100  (_pull_from_peer)
  │       └── 拉取初始數據，_json_to_entry → insert_from_sync
  ├── announce_to_discovery() → POST /discovery/announce
  └── 對每個 bootstrap peer 執行 _announce_and_join()

_run_loop() (每 30s 一個循環)
  ├── 從隨機 peer 拉取數據 (_pull_from_peer)
  ├── 每 300s：與隨機 peer 交換 peer 列表 (_exchange_peers)
  ├── 每 60s：重新從 discovery servers 拉取 peer 列表
  ├── 每 120s：發送心跳到 discovery servers
  └── 清理過期 peer (_cleanup_stale_peers, 默認 300s 超時)
```

### 6.3 Wire Format（P2P 序列化）

**發送格式**（`_entry_to_json`，peer.py:336）：
```json
{
    "run_id": "combo_m1_p1_1712345678000_abcd",
    "combo_group_id": "combo_m1_p1",
    "combo_id": "combo_m1_p1_1712345678000_abcd",   // 向後兼容舊 peer
    "method_name": "Adversarial Generation (GAN)",
    "method_domain": "Machine Learning",
    "method_level": 3,
    "problem_title": "Long-Duration Energy Storage",
    "problem_domain": "energy",
    "best_dimension": "weirdness",
    "best_score": 9.0,
    "elegance": 7.0, "weirdness": 9.0, "human_feasibility": 4.0,
    "ai_feasibility": 6.0, "novelty": 9.0, "analogy_distance": 8.0,
    "scaling_potential": 7.0, "side_effects": 5.0,
    "miner_address": "0xMINER",
    "created_at": 1778551574.47,
    "analysis_text": "..."
}
```

**接收兼容性**（`_json_to_entry`，peer.py:362）：
- 新 peer 發送的數據有 `run_id` + `combo_group_id` + `combo_id`，優先使用 `run_id`
- 舊 peer 發送的數據只有 `combo_id`，自動轉爲 `run_id` 和 `combo_group_id`
- `combo_group_id` 缺失時回退到 `run_id`

### 6.4 Gossip 傳播

- **Push**：本地新條目 → `broadcast(entry, ttl=3)` → POST 到所有已知 peer
- **Pull**：定時從隨機 peer 拉取 `GET /combinations?since={last_sync_ts}`
- **TTL 衰減**：接收到的條目若 TTL > 0，重新廣播給其他 peer（TTL-1）
- **去重**：`insert_from_sync` 按 `run_id` 和時間戳去重

### 6.5 PeerConfig 默認參數

| 參數 | 默認值 | 說明 |
|------|--------|------|
| `port` | 8765 | 監聽端口 |
| `bootstrap` | [] | 初始 peer 列表 ["host:port", ...] |
| `discovery_urls` | [] | 發現服務器 URL 列表 |
| `gossip_interval` | 30.0s | Gossip 同步間隔 |
| `peer_exchange_interval` | 300.0s | Peer 列表交換間隔 |
| `peer_timeout` | 300.0s | Peer 過期時間 |
| `max_peers` | 50 | 最大 peer 數 |
| `request_timeout` | 10.0s | HTTP 請求超時（PeerManager） |
| `_REQUEST_TIMEOUT` | 10s | HTTP 請求超時（Discovery 模塊，獨立常量） |

## 7. 代幣經濟詳解

### 7.1 IDEA 代幣（SimulatedToken）

- 每個用戶初始餘額：0 IDEA
- **水龍頭**：`faucet(address)` → 發放 1000 IDEA
  - 冷卻時間：1 小時（`last_faucet_at`）
  - 終生限額：10 次（`faucet_count`）
- 轉賬：`transfer(from, to, amount)`，需檢查餘額
- 鑄幣：`mint(address, amount)`，無權限檢查（模擬環境）

### 7.2 費用結構（TokenGate）

| 操作 | 費用 | 費用分配 |
|------|------|---------|
| 查看分析（pay_for_view） | 10 IDEA | 80% 礦工（分析者） + 10% 發現者 + 10% 協議 |
| 解鎖排行榜（pay_for_leaderboard） | 20 IDEA | 協議收取，24h 有效期 |
| 隨機抽取（pay_for_random_draw） | 5 IDEA | 協議收取 |

### 7.3 緩衝區質押與獎勵（BufferZone + StakingContract）

- **提交質押**：提交分析到緩衝區時質押 10 IDEA
- **分類獎勵**：分類者從水龍頭獲 1000 IDEA 初始資金
- **正確分類**：獎勵 2 IDEA + 連續正確獎金（streak bonus）
- **錯誤分類**：沒收質押中的 5 IDEA（slash）
- **垃圾檢測獎金**：標記垃圾內容的額外 5 IDEA 獎金
- **速度獎金**：連續正確分類的速度獎金

### 7.4 協議地址

- `PROTOCOL_ADDR = "0xPROTOCOL"` — 協議費收款方
- `FAUCET_ADDR = "0xFAUCET"` — 水龍頭資金來源

## 8. 配置系統詳解

### 8.1 優先級鏈（從高到低）

1. **環境變量**：`HAMMERWORLD_API_KEY`, `HAMMERWORLD_API_BASE`, `HAMMERWORLD_MODEL`, `HAMMERWORLD_ADDRESS`
2. **`~/.hammerworld/config` 文件**：key=value 格式，支持註釋
3. **內置默認值**：OpenAI API (`https://api.openai.com/v1`)，模型 `gpt-4o`

### 8.2 `~/.hammerworld/config` 示例

```ini
# AI 提供商配置
api_key=sk-xxxxxxxxxxxxxxxxxxxxxxxx
api_base=https://api.deepseek.com
model=deepseek-v4-pro

# 按任務類型的模型配置（可選，不設置則使用 model）
agent_model=gpt-4o
mining_model=deepseek-v4-pro
triz_model=gpt-4o

# 用戶身份地址（手動設置，無 Ed25519 密鑰備份）
HAMMERWORLD_ADDRESS=0xABCDEF1234567890123456789012345678901234
```

### 8.3 HammerConfig 配置優先級邏輯

```python
class HammerConfig:
    # 每個配置鍵按以下順序查找：
    # 1. os.environ.get("HAMMERWORLD_API_KEY")
    # 2. 讀取 ~/.hammerworld/config 中的 api_key=
    # 3. 內置默認值
```

## 9. AI 評估系統詳解

### 9.1 評估維度（8 個）

每個 method×problem 組合的 AI 分析包含 8 個維度的 1-10 評分：

1. **elegance（優雅度）**：解決方案的簡潔和美感
2. **weirdness（怪異度）**：非傳統、反直覺的程度
3. **human_feasibility（人類可行性）**：當前人類技術能實現的程度
4. **ai_feasibility（AI 可行性）**：AI 能輔助實現的程度
5. **novelty（新穎度）**：與現有方案的不同程度
6. **analogy_distance（類比距離）**：方法與問題原始領域的跨度
7. **scaling_potential（規模化潛力）**：方案能大規模應用的潛力
8. **side_effects（副作用）**：可能產生的負面影響

### 9.2 非對稱閾值（Asymmetric Threshold）

**關鍵設計決策**：檢查的是**任一維度** ≥ 8.0，而非平均分。

```python
def is_high_score(self, threshold: float = 8.0) -> bool:
    return any(s.score >= threshold for s in self.scores)
```

設計意圖：保護「怪但有趣」（weird but interesting）的想法。一個 idea 在 elegance 上可能只有 3 分，但在 weirdness 和 novelty 上拿到 9 分，它仍然通過。

### 9.3 評分管線流程（EvaluationPipeline）

```
method + problem → 構建 prompt → 發送 AI → 解析 JSON 響應 →
  ├── 成功：提取 8 個維度評分 → 構建 AIAnalysis（含推理哈希）
  └── 失敗（JSON 解析錯誤）→ 關鍵詞回退評分 → 構建 AIAnalysis
```

### 9.4 AIProvider 協議

```python
class AIProvider(Protocol):
    def generate(self, prompt: str, model: str | None = None) -> str:
        """生成 AI 響應。model 參數可選，覆蓋默認模型。"""
        ...
```

### 9.5 OpenAIProvider 實現

- 只使用 `urllib.request`（標準庫），**無需 pip install openai**
- 支持自定義 API Base URL（兼容 DeepSeek、Ollama、Anthropic 代理等）
- 使用 `HammerConfig` 獲取 api_key、api_base、model

## 10. TRIZ 系統詳解

### 10.1 TRIZ 知識庫

- **39 個工程參數**（EngineeringParameter）：如重量、速度、溫度、複雜度等
- **40 個發明原理**（InventivePrinciple）：如分割、抽取、合併、反向等，每個含子原理和示例
- **39×39 矛盾矩陣**：稀疏矩陣，映射 (改善參數, 惡化參數) → 推薦原理 ID 列表

### 10.2 TRIZAgent 工作模式

1. **standardize(problem_description)**：將自然語言問題標準化爲 TRIZ 格式
   - AI 模式：調用 LLM 提取工程參數、矛盾、理想最終結果（IFR）
   - 規則模式：關鍵詞匹配識別問題類型
2. **analyze(standardized_problem)**：基於標準化結果生成矛盾分析和推薦原理
3. **get_principle_recommendations(param_ids)**：查詢矛盾矩陣獲取推薦原理

### 10.3 TRIZ 標準化輸出格式

```json
{
    "improving_parameter": "Speed",
    "improving_param_id": 9,
    "worsening_parameter": "Energy consumption",
    "worsening_param_id": 22,
    "technical_contradiction": "Increasing speed leads to higher energy use",
    "ifr": "The system achieves high speed without additional energy input",
    "recommended_principles": [15, 28, 35]
}
```

## 11. 組合生成算法詳解（combiner.py）

### 11.1 確定性隨機

```python
seed = int(hashlib.sha256(f"{block_height}|{user_address}|{nonce}".encode()).hexdigest(), 16)
```

### 11.2 算法步驟

1. 對方法列表和問題列表分別執行 Fisher-Yates 洗牌（用同一個種子）
2. 用互質步進（coprime stepping）遍歷兩個列表生成組合
3. 追蹤已見過的 `combo_group_id`（`combo_{method.id}_{problem.id}`）避免重複
4. 自動調整步進參數以覆蓋不同組合
5. `MiningState` 追蹤每個用戶的挖礦進度（block_height + nonce）

### 11.3 組合 ID 關係

```
Combo.id (combo_group_id) = "combo_" + Method.id + "_" + Problem.id
                              └────────── 舊的 PK，新的分組鍵 ────────┘

run_id = Combo.id + "_" + timestamp_ms + "_" + uuid4[:4]
         └─────────────────── 每次挖礦唯一的 PK ──────────────────────┘
```

## 12. 翻譯系統（i18n）

### 12.1 用法

```python
from src.hub.web import _t
_t("nav.dashboard", lang)           # → "Dashboard" (en) / "仪表板" (zh)
_t("lb.showing", lang, n=5)         # → "Showing 5 results" / "筛选 5 条结果"
```

### 12.2 語言檢測

- Cookie `lang` → URL 參數 `?lang=zh` → 默認 `"en"`
- 用戶可在任何頁面通過導航欄切換語言

### 12.3 翻譯鍵總數

約 120 個翻譯鍵，按模塊分組（nav.*, dash.*, lb.*, th.*, common.*, entry.*, combo_group.*, math.*, buffer.*, token.*, agent.* 等）。

## 13. Web 頁面架構

### 13.1 頁面結構

所有頁面共用 `_base_page(title, content, active_nav, lang, viewer_addr)` 框架：

```html
<!DOCTYPE html>
<html>
<head>
    <title>{title} — Idea Mining Network</title>
    <style>/* 內聯 CSS，約 300 行 */</style>
</head>
<body>
    <nav>  <!-- 導航欄 + _login_widget + 語言切換 --> </nav>
    <main> {content} </main>
    <footer> Idea Mining Network — Phase 2 MVP </footer>
</body>
</html>
```

### 13.2 登錄系統

- **無密碼登錄**：用戶輸入地址（如 `0xABCDEF...`）即可登錄
- **地址創建**：可自動生成 Ed25519 密鑰對，地址 = `0x` + SHA256(pubkey)[:40]
- **Cookie 會話**：`viewer_addr` Cookie，30 天有效期
- **註銷**：清除 Cookie，重定向到首頁

### 13.3 _login_widget 狀態

- **未登錄**：顯示地址輸入框 + 登錄按鈕 + 創建新地址按鈕
- **已登錄**：顯示縮短地址（前 6 位）+ 註銷鏈接

## 14. AI 助手（agent_assistant.py）

### 14.1 18 種意圖類型

| 意圖 | 觸發詞（英文） | 觸發詞（中文） |
|------|--------------|--------------|
| `start_mining` | start mining, mine ideas | 開始挖礦, 挖礦 |
| `stop_mining` | stop mining | 停止挖礦 |
| `show_leaderboard` | leaderboard, top entries | 排行榜 |
| `search_entries` | search, find | 搜索, 查找 |
| `random_draw` | random draw | 隨機抽取 |
| `show_entry_detail` | show entry, details | 查看詳情, 詳情 |
| `pay_for_view` | pay for view, unlock | 付費查看, 解鎖 |
| `rate_entry` | rate, rating | 評分 |
| `token_balance` | balance, tokens | 餘額, 代幣 |
| `show_peers` | peers, network | 節點, 網絡 |
| `submit_method` | submit method | 提交方法 |
| `submit_problem` | submit problem | 提交問題 |
| `math_zone` | math zone, math problem | 數學區 |
| `buffer_zone` | buffer zone, classify | 緩衝區, 分類 |
| `faucet` | faucet, get tokens | 水龍頭, 領幣 |
| `settings` | settings, config | 設置, 配置 |
| `help` | help, what can you do | 幫助 |
| `unknown` | （無法匹配時） | |

### 14.2 雙模式處理

1. **LLM 模式**（有 API key）：發送對話歷史 + 系統提示，返回結構化 JSON `{intent, params}`
2. **關鍵詞回退**（無 API key 或 LLM 失敗）：正則匹配關鍵詞，返回意圖和參數

### 14.3 挖礦流程

```
用戶說「開始挖礦」→ agent 觸發 start_mining →
  後臺調用 _run_mine() →
    load_methods() + load_problems() →
    generate_combinations() →
    EvaluationPipeline.evaluate_batch() →
    leaderboard.insert()（返回 entry） →
    顯示結果：entry.run_id + 評分摘要
```

## 15. 緩衝區管線詳解（BufferZone）

### 15.1 狀態機

```
pending → (收集 3-7 個分類) → classified → publish_to_leaderboard
                            ↓ (無共識)
                         disputed
```

### 15.2 常量

| 常量 | 值 | 說明 |
|------|-----|------|
| `MIN_CLASSIFICATIONS` | 3 | 最少分類數 |
| `MAX_CLASSIFICATIONS` | 7 | 最多分類數 |
| `CONSENSUS_THRESHOLD` | 0.6 | 共識閾值（60% 一致） |
| `STAKE_AMOUNT` | 10 IDEA | 提交質押 |
| `PENALTY_AMOUNT` | 5 IDEA | 錯誤分類罰金 |
| `REWARD_CORRECT` | 2 IDEA | 正確分類獎勵 |
| `SPAM_DETECTOR_BONUS` | 5 IDEA | 垃圾檢測獎金 |

### 15.3 管線流程

```
submit_analysis(combo_id, method_id, ..., submitter) →
  質押 10 IDEA → 狀態=pending →
  classify(sub_id, classifier, domain_label) × N →
    _check_consensus(sub_id) → 檢查達共識？
      ├── 是 → _distribute_rewards() → 狀態=classified → publish_to_leaderboard()
      └── 否且分類數達上限 → 狀態=disputed
```

## 16. 安全模型

### 16.1 6 層安全防護（發現服務器）

1. **Ed25519 簽名身份**：可選的密鑰對簽名，防止 peer_id 僞造
2. **IP 反欺騙**：對比公告的 address 與實際連接 IP，防止 IP 僞造
3. **速率限制**：每 IP 滑動窗口限流（默認 30 req/60s），防止 DoS
4. **隱私保護**：最多返回 30 個隨機 peer（而非全部），防止網絡掃描
5. **LRU 淘汰**：過期 peer 自動淘汰（默認 180s）
6. **NAT 感知**：服務器檢測並返回真實外部 IP，支持 NAT 後的 hub

### 16.2 Web 安全

- HTML 轉義：所有用戶輸入通過 `html.escape()` 處理（XSS 防護）
- Cookie 安全：`HttpOnly`、`SameSite=Strict`
- SQL 注入防護：所有查詢使用參數化查詢（`?` 佔位符）

## 17. 測試策略

### 17.1 運行方式

```bash
python3 -m unittest discover tests/ -v          # 全部 413 條
python3 -m unittest tests.test_leaderboard -v   # 單文件
python3 -m unittest tests.test_models.TestCombination -v  # 單類
```

### 17.2 模式

- **`:memory:` 數據庫**：大多數測試使用內存 SQLite（隔離、快速）
- **文件數據庫**：CLI 測試使用 `tempfile.mkdtemp()` 中的真實文件
- **HTTP 集成測試**：`test_server.py` 啓動真實 HTTP 服務器進行端到端測試
- **無外部依賴**：所有測試可在無網絡環境中運行（AI 相關測試使用 mock 或跳過）

---

# Part 3: Schema 重構詳情（本次交付內容）

## 18. 背景與動機

**問題**：舊設計用 `combo_id`（method×problem 組合標識，如 `combo_method_ml_001_problem_energy_003`）作爲 `combinations` 表的 PRIMARY KEY。SQLite 的 `INSERT OR REPLACE` 行爲導致：同一個 method×problem 組合被不同礦工（或同一礦工在不同時間）挖礦時，新的結果會覆蓋舊的數據。

**需求**：
1. 同一 method×problem 組合允許多條記錄共存
2. 爲每個 method×problem 組合提供專屬頁面，展示不同礦工/AI 的分析
3. 付費改爲按組付費：付一次費解鎖該組全部分析

## 19. 核心設計

### 19.1 三級標識體系

| 概念 | 格式 | 用途 |
|------|------|------|
| `run_id`（PK） | `combo_{method_id}_{problem_id}_{ts_ms}_{rand4}` | 每次挖礦的唯一標識，替代舊 combo_id 作爲主鍵 |
| `combo_group_id` | `combo_{method_id}_{problem_id}` | method×problem 組合標識，等於舊 combo.id，用於分組 |
| `combo_id`（property） | 返回 `run_id` | LeaderboardEntry 的 @property，向後兼容讀取 `entry.combo_id` 的代碼 |

### 19.2 新舊對比

| 方面 | 舊設計（v1） | 新設計（v2） |
|------|------------|------------|
| PK | `combo_id` = method×problem 組合 | `run_id` = 每次挖礦唯一 |
| 同組合多記錄 | 不允許（INSERT OR REPLACE 覆蓋） | 允許（INSERT OR IGNORE） |
| 分組 | 無（PK 即分組） | `combo_group_id` 列 + 索引 |
| 付費粒度 | 按單條記錄 | 按組（付一次費看全部） |
| 評分粒度 | 按單條記錄 | 按 run_id（每個礦工獨立評分） |

## 20. 文件改動詳情

### 20.1 src/engine/models.py

```python
# 新增方法
@staticmethod
def make_run_id(method_id: str, problem_id: str) -> str:
    return f"combo_{method_id}_{problem_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
```

### 20.2 src/hub/leaderboard.py（核心改動，~300 行變更）

**LeaderboardEntry dataclass**：
```python
# 舊
combo_id: str

# 新
run_id: str
combo_group_id: str

@property
def combo_id(self) -> str:
    return self.run_id  # 向後兼容
```

**`insert()` 方法**：
- 舊：`INSERT OR REPLACE INTO combinations (combo_id, ...)` — combo.id 作 PK
- 新：調用 `Combination.make_run_id()` 生成唯一 run_id，`INSERT OR IGNORE INTO combinations (run_id, combo_group_id, ...)` — run_id 作 PK，combo_group_id 存 combo.id

**`insert_from_sync()` 方法**：
- 舊：按 `combo_id` 檢查存在與時間戳
- 新：按 `run_id` 檢查存在與時間戳

**`_get_by_id()` 方法**：
- 舊：`WHERE combo_id = ?`
- 新：`WHERE run_id = ?`

**新增方法**：
- `get_group_runs(combo_group_id)` — 返回該組合的所有運行記錄（按 created_at DESC 排序）
- `get_ratings_for_run(run_id)` / `get_avg_rating_for_run(run_id)` — 按 run_id 評分查詢

**向後兼容別名**：
- `get_ratings_for_combo()` → `get_ratings_for_run()`
- `get_avg_rating_for_combo()` → `get_avg_rating_for_run()`

### 20.3 src/hub/token_layer.py

**`check_view_access(viewer_addr, run_id)`**：
```python
# 檢查 access 的邏輯改爲：
# 1. 礦工本人 → "own"
# 2. 已爲該 combo_group_id 付費 → "paid"
# 3. 其他 → "no_access"
entry = self.db._get_by_id(run_id)
if entry and entry.miner_address == viewer_addr:
    return "own"
if entry and self.db.has_paid(viewer_addr, entry.combo_group_id):
    return "paid"
return "no_access"
```

**`pay_for_view(viewer_addr, run_id)`**：
- 記錄付費到 `(viewer_addr, combo_group_id)` 而非 `(viewer_addr, combo_id)`
- 費用轉給 `entry.miner_address`

**`rate_analysis(viewer_addr, run_id, rating)`**：
- 評分記錄到 `(viewer_addr, run_id)` — 每個礦工的獨立分析可單獨評分

### 20.4 src/hub/web.py

**新增 `render_combo_group(db, combo_group_id, ...)`**（~100 行）：
- Header：method×problem 基本信息（只顯示一次）
- 付費門控：付費一次解鎖全部（未付費時隱藏分析文本）
- 運行列表：每條顯示礦工、時間、最佳維度+分數
- 評分表單：每條可獨立評分
- 每個 run_id 鏈接到 `/web/entry/{run_id}`

**翻譯鍵**（8 個新增）：
```python
"combo_group.title":       {"en": "All Analyses for {combo}", "zh": "全部分析 - {combo}"}
"combo_group.n_runs":      {"en": "{n} run(s)", "zh": "共 {n} 条分析"}
"combo_group.pay_all":     {"en": "Pay {fee} IDEA to Unlock All Analyses", "zh": "支付 {fee} IDEA 解锁全部分析"}
"combo_group.paywalled":   {"en": "Pay once to view all analyses in this group.", "zh": "一次性支付即可查看该组全部分析。"}
"combo_group.miner":       {"en": "Miner", "zh": "矿工"}
"combo_group.view_run":    {"en": "Detail", "zh": "详情"}
"combo_group.view_all":    {"en": "View all {n} analyses for this pair", "zh": "查看全部 {n} 条分析"}
"combo_group.all_runs":    {"en": "All Analysis Runs", "zh": "全部分析记录"}
```

**URL 更新**：所有鏈接使用 `e.combo_id`（property，返回 run_id）：
- `/web/entry/{e.combo_id}` — `render_entry()` 同時支持 run_id 和舊 combo_group_id
- 排行榜、隨機抽取、我的挖掘等列表中的鏈接

### 20.5 src/hub/server.py

**新增路由**：
```python
elif path.startswith("/web/combo/"):
    combo_group_id = path.split("/web/combo/", 1)[1]
    html = render_combo_group(db, combo_group_id, viewer_addr=viewer, token_gate=tg, lang=lang)
```

### 20.6 src/hub/peer.py（P2P 兼容）

**`_entry_to_json()`**：同時發送三種標識
```python
{
    "run_id": entry.run_id,           # 新 peer 優先使用
    "combo_group_id": entry.combo_group_id,  # 分組
    "combo_id": entry.run_id,         # 舊 peer 向後兼容
    ...
}
```

**`_json_to_entry()`**：兼容三種格式
```python
run_id = data.get("run_id", data.get("combo_id", ""))       # 優先 run_id，回退 combo_id
combo_group_id = data.get("combo_group_id", run_id)         # 優先 combo_group_id，回退 run_id
```

### 20.7 src/hub/agent_assistant.py

挖礦輸出改用 `entry.run_id`：
```python
entry = self.db.insert(combo, miner_addr=viewer_addr or "0xAGENT")
results.append((combo, best, entry.run_id))
```

## 21. DB 遷移機制

### 21.1 版本管理

- `_schema_version` 表（單列 `version INTEGER PRIMARY KEY`）
- **查詢當前版本**：`SELECT MAX(version) FROM _schema_version`
- **設置版本**：`DELETE FROM _schema_version; INSERT INTO _schema_version (version) VALUES (N)`
- 使用 MAX() 和 DELETE+INSERT 的原因是防止多行問題（詳見 Bug #2）

### 21.2 遷移時序

```
_init_db()
  ├── CREATE TABLE IF NOT EXISTS（全部表，v2 schema）
  ├── ALTER TABLE 兼容性遷移（analysis_text, paid_views 額外列, comment 列, faucet 列）
  ├── _migrate_math_to_tree(conn)     # v0 → v1
  │   └── 檢查 MAX(version) >= 1 → 是則跳過
  │   └── 將 math_solutions 行轉換爲 MCTS tree nodes/edges
  ├── _migrate_schema_v2(conn)        # v1 → v2
  │   ├── 檢查 MAX(version) >= 2 → 是則跳過
  │   ├── PRAGMA table_info 檢查已是 v2 → 是則僅設版本
  │   ├── 重建 combinations、paid_views、viewer_ratings、user_draws
  │   └── 設置 version = 2
  ├── CREATE INDEX idx_combo_group_id（遷移後執行）
  └── 若表爲空：INSERT INTO _schema_version VALUES (2)（全新數據庫）
```

### 21.3 表重建模式

每個需要遷移的表使用相同模式：
```sql
CREATE TABLE IF NOT EXISTS {table}_v2 (新 schema);
INSERT INTO {table}_v2 SELECT ... FROM {table};   -- 列映射
DROP TABLE {table};
ALTER TABLE {table}_v2 RENAME TO {table};
```

## 22. 修復的 Bug

### Bug #1：`idx_combo_group_id` 在遷移前創建
- **症狀**：現有 v1 數據庫啓動時報 `sqlite3.OperationalError: no such column: combo_group_id`
- **根因**：索引創建語句在初始 `executescript` 中，先於 `_migrate_schema_v2` 執行
- **修復**：將 `CREATE INDEX idx_combo_group_id` 移到遷移完成之後

### Bug #2：`_schema_version` 多行
- **症狀**：遷移檢查 `WHERE version >= 2` 意外找到行，跳過遷移
- **根因**：初始 `INSERT OR IGNORE INTO _schema_version VALUES (2)` 在有 version=1 的數據庫中插入了第二行（PK 不同，不衝突）
- **修復**：改用 `SELECT MAX(version)` 查詢；版本設置改用 `DELETE + INSERT`

### Bug #3：`:memory:` DB 版本錯亂
- **症狀**：空 `:memory:` 數據庫中 `_migrate_math_to_tree` 設置 version=1，導致 `_migrate_schema_v2` 誤以爲需要遷移
- **根因**：`_migrate_math_to_tree` 在空 `math_solutions` 表時仍設置 version=1
- **修復**：`_migrate_schema_v2` 增加 v2 schema 檢測：通過 `PRAGMA table_info` 檢查有 `combo_group_id` 無 `combo_id` 列

### Bug #4：`viewer_ratings.comment` 列缺失
- **症狀**：v1 數據庫遷移時 `INSERT SELECT ... comment ... FROM viewer_ratings` 失敗
- **根因**：舊 v1 `viewer_ratings` 表無 `comment` 列
- **修復**：遷移前添加 `ALTER TABLE viewer_ratings ADD COLUMN comment TEXT DEFAULT ''`

## 23. 驗證清單

```bash
# 1. 全部測試（413 條）
python3 -m unittest discover tests/ -v

# 2. 啓動 Web 服務器
python3 -m src.cli.main web --port 8765

# 3. 功能性驗證
#   a. 挖礦 → 觀察輸出中的 run_id（格式：combo_X_Y_ts_rand4）
#   b. 訪問 /web/my-entries → 查看挖礦記錄
#   c. 再次挖同一個 method×problem → 確認兩條記錄共存（total_entries 增加）
#   d. 訪問 /web/combo/{combo_group_id} → 看到全部分析列表
#   e. 付費一次查看 → 該組所有分析全部解鎖
#   f. 對不同 run 分別評分 → 每個 run 獨立評分

# 4. P2P 驗證
#   終端 1: python3 -m src.cli.main hub --port 8765
#   終端 2: python3 -m src.cli.main web --port 8766 --discovery-url http://localhost:8765
#   確認終端 2 的 /peers 返回終端 1
#   確認終端 2 的 /combinations 能拉取到終端 1 的數據

# 5. 現有數據庫升級驗證
#   備份 data/leaderboard.db
#   啓動 hub → 自動遷移到 v2
#   檢查 _schema_version 只有一行 version=2
#   檢查 combinations 表有 run_id 和 combo_group_id 列
```

## 24. 注意事項（Gotchas）

1. **URL 參數命名**：Web URL 中名爲 `combo_id` 的參數實際上是 `run_id`。`render_entry()` 對兩者都兼容（先按 run_id 查，找不到則按 combo_group_id 重定向到組合頁面）。

2. **`buffer_submissions.combo_id` 列**：該表仍保留了 `combo_id` 列名（未遷移），實際存儲的是 combo_group_id。緩衝區模塊的 `publish_to_leaderboard()` 內部處理了這個映射。

3. **`math_access_log.combo_id` 列**：未遷移，可能混雜 run_id 和 combo_group_id 值。該表的 PK 是 `(problem_id, method_collection_id, user_address)`，所以不影響功能，但未來如需 JOIN 此列需注意。

4. **舊 peer 兼容性**：P2P 發送的 `combo_id` = run_id（帶時間戳後綴）。舊 peer 會將其作爲 PK 存儲，這意味着舊 peer 無法將同組的多個 run 關聯起來（它們有不同的 PK），但不會丟失數據。

5. **構造 LeaderboardEntry**：已從 dataclass 中移除 `combo_id` 參數。必須傳 `run_id` 和 `combo_group_id`。讀取 `entry.combo_id` 的代碼不受影響（通過 property）。

6. **HTTP 服務器啓動延遲**：`HubServer.start()` 先執行 `PeerManager.start()`（包括 discovery 和初始數據同步），然後才啓動 HTTP 服務器。這意味着服務器在啓動後 3-10 秒才能接受 HTTP 請求。這是原有設計，非本次改動引入。

7. **`_schema_version` 至少有 1 行**：不依賴 `SELECT version FROM _schema_version` 返回 0 或 1 行。使用 `SELECT MAX(version)` 確保一致性。

8. **INSERT OR IGNORE**：`insert()` 使用 `INSERT OR IGNORE`（而非舊的 `INSERT OR REPLACE`），因爲 run_id 總是唯一的。如果因某種原因出現重複 run_id，新記錄會被靜默忽略。
