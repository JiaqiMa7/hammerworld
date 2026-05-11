# P2P Hub（小中心聯邦網絡）

## 架構

多個獨立 Hub 通過 P2P gossip 協議組成分佈式排行榜網絡：

```
Hub A (port 8765)              Hub B (port 8766)
┌─────────────────┐            ┌─────────────────┐
│  LeaderboardDB  │            │  LeaderboardDB  │
│  (SQLite)       │            │  (SQLite)       │
└────────┬────────┘            └────────┬────────┘
         │                              │
┌────────▼────────┐            ┌────────▼────────┐
│   PeerManager   │◄── gossip ──│   PeerManager   │
│  (push + pull)  │            │  (push + pull)  │
└────────┬────────┘            └────────┬────────┘
         │                              │
┌────────▼────────┐            ┌────────▼────────┐
│  HTTP REST API  │            │  HTTP REST API  │
│  (port 8765)    │            │  (port 8766)    │
└─────────────────┘            └─────────────────┘
```

## 新增模塊

### `src/hub/peer.py` — Peer 管理 + Gossip 協議

```python
from src.hub.peer import PeerManager, PeerConfig, PeerInfo
from src.hub.leaderboard import LeaderboardDB

db = LeaderboardDB("data/hub_a.db")

# 配置
config = PeerConfig(
    port=8765,
    bootstrap=["localhost:8766"],  # 加入網絡的初始節點
    gossip_interval=30.0,          # 同步間隔（秒）
    peer_timeout=300.0,            # Peer 超時（秒）
    max_peers=50,
)

# 啟動
manager = PeerManager(db, config)
manager.start()   # 啟動 gossip 線程，連接到 bootstrap peers

# Peer 管理
manager.add_peer("192.168.1.5", 8765)
manager.get_peers()       # → list[PeerInfo]
manager.remove_peer("peer_id")

# 廣播新條目
manager.broadcast(entry, ttl=3)  # push 給所有 peers

manager.stop()
```

**Gossip 策略：Push + Pull 混合**
- Push：本地新條目即時推送到所有已知 peers
- Pull：每 30 秒從一個隨機 peer 增量拉取
- Peer 交換：每 5 分鐘交換 peer 列表
- TTL 防無限傳播（默認 3 跳）

### `src/hub/server.py` — HTTP REST API

```python
from src.hub.server import HubServer
from src.hub.leaderboard import LeaderboardDB
from src.hub.peer import PeerConfig

db = LeaderboardDB("data/hub.db")
server = HubServer(db, PeerConfig(port=8765))
server.start()  # 阻塞，監聽 0.0.0.0:8765
```

**API 端點：**

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查 `{"status":"ok","peer_id":"...","entries":N}` |
| GET | `/stats` | 統計信息 `{"entries":N,"peers":N,"uptime":T}` |
| GET | `/combinations?since=<ts>&limit=<n>` | 增量獲取條目 |
| POST | `/combinations` | 接收遠程條目（body: `{"entries":[...],"ttl":[...]}`） |
| GET | `/peers` | 已知 peer 列表 |
| POST | `/peers/announce` | 宣告自身（加入網絡） |

### `src/hub/leaderboard.py` — 新增同步方法

```python
# 接收遠程條目（僅 LeaderboardEntry JSON，不同步 paid_views/user_draws）
db.insert_from_sync(entry)  # → bool（是否新條目）

# 增量同步查詢
db.get_since(timestamp, limit=100)  # → list[LeaderboardEntry]
```

## 數據同步範圍

只同步 `combinations` 表（排行榜條目）。**不同步**的本地狀態：
- `paid_views`（付費記錄 — 每個 Hub 獨立計費）
- `user_draws`（抽獎記錄 — 防止同一用戶在同一 Hub 重複抽取）

## CLI 使用

```bash
# 啟動 Hub A（第一個節點）
python3 -m src.cli.main hub --port 8765 --db /tmp/hub_a.db

# 啟動 Hub B，連接 A
python3 -m src.cli.main hub --port 8766 --db /tmp/hub_b.db --bootstrap localhost:8765

# 啟動 Hub C，連接多個 bootstrap
python3 -m src.cli.main hub --port 8767 --db /tmp/hub_c.db \
    --bootstrap localhost:8765 --bootstrap localhost:8766

# 完整參數
python3 -m src.cli.main hub \
    --port 8765 \
    --db data/leaderboard.db \
    --bootstrap hub1.example.com:8765 \
    --gossip-interval 30 \
    --peer-timeout 300 \
    --max-peers 50
```

## 手動測試

```bash
# Terminal 1: 啟動 Hub A
python3 -m src.cli.main hub --port 8765 --db /tmp/a.db

# Terminal 2: 啟動 Hub B
python3 -m src.cli.main hub --port 8766 --db /tmp/b.db --bootstrap localhost:8765

# Terminal 3: 在 A 上挖礦
python3 -m src.cli.main mine --address 0xMINER --batch 5

# 驗證 B 同步了數據
python3 -m src.cli.main search "Method" --db /tmp/b.db
python3 -m src.cli.main top --db /tmp/b.db
```

## 同步流程

```
Hub A 剛啟動                     Hub B (已運行)
     │                                │
     ├─ POST /peers/announce ────────►│  "我是 A"
     │◄────── {peer_id, peers} ───────┤  "歡迎，其他 peers: [...]"
     │                                │
     ├─ GET /combinations?since=0 ───►│  拉取歷史數據
     │◄────── [entry1, entry2...] ────┤
     │                                │
     ═══ 之後互相同步 ═══               │
     ├─ POST /combinations ──────────►│  A 挖到新條目，push 給 B
     │◄──── POST /combinations ───────┤  B 挖到新條目，push 給 A
     │                                │
     ├─ GET /combinations?since=... ─►│  每 30s 增量同步
     │◄──────── [new entries] ────────┤
```

## 安全考量（Phase 3）

目前 Phase 2 不做但未來計劃：
- TLS 加密傳輸
- 鏈上簽名身份驗證
- 速率限制 + IP 黑名單
- 防 Sybil 攻擊（多假節點泛洪）
