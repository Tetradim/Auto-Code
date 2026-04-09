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
