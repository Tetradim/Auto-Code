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
│   ├── server.py         # FastAPI app + API router (/api prefix)
│   ├── scheduler.py      # EvaluationScheduler (async ticker loop)
│   ├── orb.py            # Opening Range Breakout tracker
│   ├── atr.py            # ATR calculator
│   ├── signals.py        # Signal engine (trend, signal strength)
│   ├── engine.py         # Decision engine (BUY/STOP/TRAILING/EXIT)
│   ├── metrics.py        # Prometheus metrics definitions
│   ├── market_hours.py   # Global market hours tracker
│   ├── price_fetcher.py  # yfinance price fetcher
│   ├── pulse_client.py   # Circuit-breaker Pulse API client
│   └── requirements.txt
├── frontend/
│   ├── vite.config.ts    # Vite config (loadEnv, process.env define)
│   ├── index.html        # Clean entry (no static diagnostic content)
│   └── src/
│       ├── App.tsx           # 4-tab shell (sticky header + nav)
│       ├── lib/api.ts        # Native fetch client (NO axios)
│       ├── store/useStore.ts # Zustand store
│       ├── types/index.ts    # TypeScript types
│       └── components/
│           ├── cards/
│           │   ├── MetricCard.tsx  # KPI cards
│           │   ├── ChartCard.tsx   # SVG area/line chart (no recharts)
│           │   └── TickerCard.tsx  # Per-ticker card (SVG sparkline)
│           └── dashboards/
│               ├── TradingOverview.tsx  # Tab 1: tickers + ORB chart
│               ├── BrokerHealth.tsx     # Tab 2: circuit breaker status
│               ├── PnLTracking.tsx      # Tab 3: P&L charts + table
│               └── MarketCoverage.tsx   # Tab 4: live global markets
├── prometheus/
└── grafana/
```

## Tech Stack
- **Frontend**: React 18, TypeScript, Vite 5, Tailwind CSS, Zustand, framer-motion, lucide-react
  - **NO axios** (caused blank screen bug in Vite — removed permanently)
  - **NO recharts** (had react-is version conflict — replaced with custom SVG charts)
- **Backend**: Python, FastAPI, asyncio, Motor (MongoDB), Prometheus client
- **Infra**: MongoDB, Prometheus, Grafana, Docker Compose

## What Has Been Implemented

### Session 1 (Previous)
- All backend Python modules: metrics.py, orb.py, atr.py, signals.py, engine.py, pulse_client.py ✅
- FastAPI server with /api router, lifespan context manager ✅
- Scheduler with async evaluation loop (1s interval) ✅
- Per-ticker Prometheus metric toggles (store in MongoDB, apply in scheduler) ✅
- Docker Compose, Prometheus, Grafana provisioning JSONs ✅
- Vite + Tailwind setup fixed (host checking, PostCSS module format) ✅

### Session 2 (2026-04-09)
- Full 4-tab dashboard restored after blank screen debugging ✅
- api.ts rewritten with native fetch (axios removed) ✅
- ChartCard.tsx replaced recharts with custom SVG area/line chart ✅
- TickerCard.tsx: removed recharts LineChart, SVG sparkline ✅
- App.tsx: full tabbed layout (sticky header, 4 nav tabs, pause/resume, connection status) ✅
- vite.config.ts: added loadEnv() + define process.env.REACT_APP_BACKEND_URL ✅
- index.html cleaned (removed hardcoded static diagnostic HTML) ✅
- MarketCoverage.tsx: fixed to update local state from live API response ✅
- Deprecated @app.on_event("shutdown") removed from server.py ✅
- axios removed from package.json ✅
- SVG chart X-axis label clipping fixed (start/end anchors) ✅
- Backend test suite created: /app/backend/tests/test_sentinel_edge.py (40 tests, 100% pass) ✅

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Health check (running, paused, active_tickers count) |
| GET | /api/tickers | List active ticker symbols |
| POST | /api/tickers/{symbol} | Add ticker to watchlist |
| DELETE | /api/tickers/{symbol} | Remove ticker |
| GET | /api/tickers/{symbol}/config | Get Prometheus metric toggles |
| PUT | /api/tickers/{symbol}/config | Update metric toggles |
| GET | /api/stats | Full system stats |
| GET | /api/orb/{symbol} | ORB levels for symbol |
| GET | /api/markets | Live global market status |
| POST | /api/control/pause | Pause scheduler |
| POST | /api/control/resume | Resume scheduler |
| GET | /metrics | Prometheus scrape endpoint |

## Prioritized Backlog

### P0 — Critical
- None (all blocking issues resolved)

### P1 — High Priority (Next Sprint)
- **Correlation Detection**: detect when multiple symbols break out simultaneously → trigger market-wide alert banner in Trading Overview
- **Auto Trailing Stop Logic**: in engine.py, if strong_breakout AND pnl > threshold → tighten_trailing_stop(0.5%)
- **Backend /api/tickers enrichment**: return full TickerData objects (current_price, signal_strength, orb_levels, atr, volume_ratio) not just symbol strings — removes hardcoded yfinance rate-limit dependency on ticker card rendering

### P2 — Medium Priority
- **Volume Anomaly Z-score**: statistical volume spike detection in signals.py
- **MongoDB State Persistence**: store ORB levels, last decisions, trade streaks in MongoDB to survive restarts
- **P&L data from Pulse API**: replace static mock data in PnLTracking.tsx with live Pulse API data
- **Broker Health live data**: replace static BrokerHealth mock data with live circuit breaker state from pulse_client

### P3 — Backlog
- Add ticker management UI (add/remove tickers from dashboard)
- Real-time WebSocket streaming for ticker prices
- Alert history / trade log view
- Grafana provisioning walkthrough in README

## Known Constraints
- yfinance rate-limits cause "Too Many Requests" when queried every second per ticker. Ticker cards show 0.0 signal/price when rate-limited — this is expected non-market-hours behavior.
- Pulse API (pulse_client.py) uses a mock/localhost URL by default — real trades require PULSE_API_URL and PULSE_API_KEY env vars set.
