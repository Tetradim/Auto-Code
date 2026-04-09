# Sentinel Edge — Product Requirements Document

## Original Problem Statement
Combine the Set-Trader and sentinel-edge repos into a single Sentinel Edge sidecar application.
Build a real-time trading analyst sidecar (Python/FastAPI) that tracks ORB (Opening Range Breakout),
ATR, Volume anomalies, and Trend bias per ticker. It must make trade decisions and expose Prometheus
metrics. A React frontend is required to display 4 specific Grafana-style dashboards: Trading Overview,
Broker Health, P&L Tracking, and Market Coverage.

## Architecture
```
/app/
├── backend/
│   ├── server.py         # FastAPI app + /api router
│   ├── scheduler.py      # EvaluationScheduler with ticker_state, CorrelationEngine, MongoDB persistence
│   ├── correlation.py    # CorrelationEngine: rolling window cluster detection
│   ├── orb.py            # ORB tracker (multi-timeframe)
│   ├── atr.py            # ATR calculator
│   ├── signals.py        # Signal engine (trend, signal_strength)
│   ├── engine.py         # Decision engine (BUY/STOP/TRAILING/TIGHTEN/EXIT)
│   ├── metrics.py        # Prometheus metrics (incl. correlation_clusters_total)
│   ├── market_hours.py   # Global market hours tracker
│   ├── price_fetcher.py  # yfinance price fetcher
│   ├── pulse_client.py   # Circuit-breaker Pulse API client
│   └── tests/
│       ├── test_sentinel_edge.py  # 40 regression tests
│       └── test_p1_features.py    # 39 P1 feature tests
├── frontend/
│   ├── vite.config.ts    # loadEnv + process.env.REACT_APP_BACKEND_URL define
│   ├── index.html        # Clean entry
│   └── src/
│       ├── App.tsx           # 4-tab shell + mock mode toggle
│       ├── lib/api.ts        # Native fetch client (NO axios), getCorrelation()
│       ├── lib/mockData.ts   # Mock price simulator (MOCK_BASE_PRICES + drift)
│       ├── store/useStore.ts # Zustand: tickers, markets, stats, mockMode, correlationAlerts
│       ├── types/index.ts    # TickerData with last_decision, confidence, last_updated
│       └── components/
│           ├── cards/
│           │   ├── MetricCard.tsx  # KPI cards with framer-motion
│           │   ├── ChartCard.tsx   # SVG area/line chart (no recharts)
│           │   └── TickerCard.tsx  # Per-ticker card with SVG sparkline, data-testid
│           └── dashboards/
│               ├── TradingOverview.tsx  # Tab 1: tickers + breadth panel + ORB chart
│               ├── BrokerHealth.tsx     # Tab 2: circuit breaker status
│               ├── PnLTracking.tsx      # Tab 3: P&L charts + table
│               └── MarketCoverage.tsx   # Tab 4: live global markets (real API data)
```

## Tech Stack
- **Frontend**: React 18, TypeScript, Vite 5, Tailwind CSS, Zustand, framer-motion, lucide-react
  - **NO axios**, **NO recharts** (both removed; using native fetch + SVG charts)
- **Backend**: Python, FastAPI, asyncio, Motor (MongoDB async), Prometheus client
- **Infra**: MongoDB, Prometheus, Grafana, Docker Compose

## What Has Been Implemented

### Session 1 (Previous)
- All backend Python modules: metrics.py, orb.py, atr.py, signals.py, engine.py, pulse_client.py ✅
- FastAPI server with /api router, lifespan context manager ✅
- Scheduler with async evaluation loop (1s interval) ✅
- Per-ticker Prometheus metric toggles (MongoDB, scheduler) ✅
- Docker Compose, Prometheus, Grafana provisioning JSONs ✅

### Session 2 (2026-04-09) — Dashboard Restoration
- Full 4-tab dashboard restored after blank screen debugging ✅
- api.ts rewritten with native fetch ✅
- ChartCard/TickerCard: custom SVG charts replacing recharts ✅
- App.tsx: full tabbed layout (sticky header, 4 tabs, pause/resume, connection) ✅
- vite.config.ts: loadEnv() + process.env.REACT_APP_BACKEND_URL define ✅
- index.html cleaned (removed hardcoded diagnostic HTML) ✅
- MarketCoverage.tsx: live API data updating local state ✅
- Backend test suite: 40 regression tests (100% pass) ✅

### Session 3 (2026-04-09) — P1 Sprint
- **Enriched /api/tickers**: returns full TickerData (price, ORB, ATR, signal, trend, decision, confidence) ✅
- **CorrelationEngine** (`correlation.py`): rolling 90s window, ≥3 symbol cluster detection ✅
- **GET /api/correlation**: breadth (bullish/bearish/neutral %) + recent clusters ✅
- **MongoDB ORB Persistence**: `_persist_orb()` saves per-symbol-per-day, `_load_orb_from_db()` restores on startup ✅
- **Auto Trailing Stop** (`Decision.TIGHTEN_TRAILING_STOP`): triggers at signal≥7.0 + pnl_pct>5.0 → 0.5% ✅
- **Mock Data Mode** toggle in header (FlaskConical icon): simulates realistic drifting prices ✅
- **Market Breadth panel** in TradingOverview: bull/bear/neutral % bar + cluster alert display ✅
- TypeScript `TickerData` type updated with `last_decision`, `confidence`, `last_updated` ✅
- P1 test suite: 39 new tests (100% pass); total 79/79 tests ✅

### Session 4 (2026-04-09) — Decision Feed + Ticker Management
- **Live Decision Feed** (`DecisionFeed.tsx`): scrollable log panel showing non-HOLD decisions (BUY/STOP/EXIT/TIGHTEN/TRAIL) with color-coded badges, signal bars, prices, time-ago; AnimatePresence transitions; mock mode auto-populates with simulated decisions ✅
- **Add/Remove Tickers**: input + Add button above ticker grid; red trash icon on every TickerCard; input validation (1–6 letters only); works in both live and mock mode; empty state shown when all tickers removed ✅
- **Backend `/api/decisions`**: returns up to 50 most recent non-HOLD decisions (newest first) ✅
- Total test coverage: 95/95 (16 new + 79 regression) ✅

### Session 5 (2026-04-09) — Full Analyst Package + LGTM Stack
- **`analyst/signals/base.py`**: full Signal dataclass (`action, symbol, confidence, reason, timeframe, price, atr, metadata`), `BaseSignal` ABC for drop-in strategies, `SignalConfig` Pydantic base ✅
- **`analyst/exporters/prometheus.py`**: rich pluggable exporter with `analyst_orb_breakouts_total`, `analyst_atr_value`, `analyst_pulse_overrides_total`, `analyst_signal_latency_seconds`; optional `start_server=True` for dedicated port 8002 ✅
- **`analyst/observability/otel.py`**: gRPC OTLP exporter (→ Tempo:4317), `HTTPXClientInstrumentor`, `AsyncioInstrumentor`, FastAPI auto-instrumentation ✅
- **`analyst/correlation/engine.py`**: canonical Signal import from `analyst.signals.base` ✅
- **`analyst/signals/custom/`**: drop-in strategy directory created ✅
- **Full LGTM docker-compose**: Loki 2.9.7, Tempo 2.4.1, Promtail, Grafana 10.4.2 + MongoDB replica set init ✅
- **Two Grafana dashboards**: `analyst-overview.json` (14 panels), `correlation-breadth.json` (7 panels) ✅
- **Prometheus rules.yml**: 8 alerting rules (EdgeEngineDown, HighConsecutiveLosses, SlowEvaluation, CorrelationBearishCluster, HighDrawdown, etc.) ✅
- **Root `/app/Dockerfile`** for containerised deployment ✅
- All confirmed in logs: OTel gRPC exporter, SentinelEdge wired, ORB levels restored from MongoDB

### Session 6 (2026-04-09) — Final Dashboard/Config/Docs Polish
- **`analyst-overview.json`**: 16 panels — correlation clusters (stat), ORB breakout rate (timeseries), ATR heatmap, signal strength, signal latency, decisions, live ticker table, Pulse overrides, markets open ✅
- **`correlation-breadth.json`**: 8 panels — Live Correlation Clusters (table with direction mapping), Bullish vs Bearish Clusters (donut piechart), cluster detection rate, strength distribution pie, BUY vs STOP rate timeseries ✅
- **`prometheus.yml`**: added `sentinel-analyst:8002` and `pulse:8001` scrape jobs ✅
- **`prometheus/rules.yml`**: added `StrongCorrelationCluster`, `BearishClusterOverride`, `HighPulseOverrideRate` (11 total alert rules) ✅
- **`README.md`**: full rewrite — architecture diagram, communication channel table, analyst/ package reference, API reference, pluggable strategy example, MongoDB command bus docs, env vars, Docker quick-start ✅

### Session 9 (2026-04-09) — VWAP Plugin + Volume Z-Score
- **`analyst/signals/custom/vwap_breakout.py`**: full `BaseSignal` plugin — computes VWAP from OHLCV (typical_price × volume cumsum), BUY above VWAP+buffer with vol_ratio≥1.25, SELL below VWAP−buffer; confidence scales with volume ratio + z-score boost; ATR floor avoids flat-market noise; metadata includes vwap/deviation_pct/volume_zscore ✅
- **`analyst/signals/__init__.py`**: `discover_plugins()` auto-discovery — scans `analyst/signals/custom/`, imports all `.py` files, finds `BaseSignal` subclasses, returns instantiated list ✅
- **`backend/signals.py`**: Volume Anomaly Z-Score — `compute_volume_zscore(symbol, volume)` using 60-sample rolling deque; added as Section 5 to `evaluate_signal()` (z>2.5 boosts ±1.5pts, z>3.5 boosts ±2pts, z<-1.5 dampens 25%); `edge_volume_zscore` Prometheus gauge ✅
- **`backend/metrics.py`**: added `edge_volume_zscore` Gauge and `analyst_plugin_signals_total` Counter ✅
- **`backend/scheduler.py`**: `signal_plugins` list; z-score computed before signal evaluation; plugins run after main eval with shared market_data dict; plugin signals fed into CorrelationEngine; `analyst_plugin_signals_total` counter incremented; `volume_zscore` exposed in `/api/tickers` ✅
- **`analyst/core.py`**: `set_scheduler()` now calls `discover_plugins()` and registers them — confirmed in logs: "1 plugin(s) loaded" ✅

## Key API Endpoints
- **`prometheus/alertmanager.yml`**: full advanced routing tree — 4 receivers (`pulse-override`, `trading-team`, `regime-alerts`, `default`); Slack + Telegram + Echo webhook; `--config.expand-env` for secrets; smart inhibit rules (critical silences warning for same direction, cluster silences individual symbol breakouts); time-based muting (outside 9:30–16:00 ET weekdays) ✅
- **`prometheus/rules.yml`**: 3 new alert rules — `CriticalBearishCorrelation` (bearish clusters ≥3 for 90s, action=global_risk_reduction), `BullishMomentumRegime` (bullish ORB rate >8/5m for 3m, action=increase_aggression), `SingleSymbolBreakout` (isolated non-index breakout, severity=info) ✅
- **`analyst/webhook/alert_handler.py`**: 2 new endpoints — `/api/webhook/pulse-override` (dedicated critical override handler with full action→command mapping: tighten/relax/pause/exit) + `/api/webhook/general` (general logging receiver) ✅
- **`docker-compose.yml`**: alertmanager service updated with `--config.expand-env` flag + env vars for `WEBHOOK_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_TRADING_CHAT`, `SLACK_WEBHOOK_URL` ✅

## Key API Endpoints
- **`prometheus/alertmanager.yml`**: updated with `group_by: [alertname, direction]`, per-route configs (BearishClusterOverride = 0s wait, critical = 30m repeat), inhibit rules suppressing warning when critical fires for same direction ✅
- **`analyst/webhook/alert_handler.py`**: FastAPI router at `/api/webhook/alert`; dispatches `BearishClusterOverride` / `HighDrawdown` / `StrongCorrelationCluster` → `send_override()`; `EdgeEngineDown` logged; resolved alerts ACK'd without action; optional Basic Auth via `WEBHOOK_SECRET` env var; records overrides to `prom_exporter` ✅
- **`analyst/core.py`**: `analyst_instance` module-level singleton set by server.py lifespan ✅
- **`server.py`**: router included at `/api/webhook/*` prefix (K8s ingress compatible); `_analyst_core.analyst_instance = edge` set before background tasks start ✅
- **Verified**: `/api/webhook/health` returns `{analyst_ready: true}`, firing + resolved test payloads both dispatch correctly ✅

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Health check |
| GET | /api/tickers | Enriched per-ticker data (price, ORB, ATR, signal, etc.) |
| POST | /api/tickers/{symbol} | Add ticker |
| DELETE | /api/tickers/{symbol} | Remove ticker |
| GET/PUT | /api/tickers/{symbol}/config | Prometheus metric toggles |
| GET | /api/stats | System stats |
| GET | /api/orb/{symbol} | ORB levels |
| GET | /api/correlation | Correlation clusters + market breadth |
| GET | /api/markets | Live global market open/closed status |
| POST | /api/control/pause | Pause scheduler |
| POST | /api/control/resume | Resume scheduler |
| GET | /metrics | Prometheus scrape (internal-only — not routed via K8s ingress) |

## Prioritized Backlog

### P1 — Done ✅
- Enriched /api/tickers ✅
- Correlation Detection Engine ✅  
- Auto Trailing Stop Logic ✅
- MongoDB ORB Persistence ✅
- Mock Data Mode ✅

### P1 — Remaining
- **Live Correlation-triggered Pulse override**: correlation engine detects BEARISH cluster → auto-call `pulse.stop_buying()` for all symbols in cluster (currently only logs)
- **Telegram alert integration**: when cluster detected, send Telegram message

### P2 — Medium Priority
- **Volume Anomaly Z-score**: statistical volume spike detection in signals.py
- **P&L data from Pulse API**: replace static mock data in PnLTracking.tsx with live Pulse API data
- **Broker Health live data**: replace static BrokerHealth mock data with live circuit breaker state
- **Add/Remove ticker UI**: allow adding tickers from the dashboard (input + button)

### P3 — Backlog
- Real-time WebSocket streaming for ticker prices (eliminate polling)
- Alert history / trade log view
- /api/metrics accessible via /api/metrics path (move from /metrics for K8s compatibility)
- Grafana provisioning documentation in README

## Known Constraints
- yfinance rate-limits during off-market hours → signal_strength = 0.0 → use Mock Mode to demo UI
- Pulse API defaults to localhost:8002 — requires PULSE_API_URL and PULSE_API_KEY env vars for real trades
- Prometheus /metrics at root path, not proxied by K8s ingress — internal scraping only
