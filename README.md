# Sentinel Edge

**Production-Ready Trading Analyst Sidecar for Sentinel Pulse**

Sentinel Edge is a full-stack trading analysis system that monitors Opening Range Breakouts (ORB) across multiple timeframes, calculates ATR-based volatility, generates scored bullish/bearish signals with volume Z-score anomaly detection, makes intelligent autonomous trading decisions, and exposes complete observability through the Grafana LGTM stack (Prometheus, Loki, Tempo, Alertmanager).

It acts as the **Intelligence & Risk Layer** that sits alongside **Sentinel Pulse** (the execution engine) and autonomously controls trailing stops, position sizing, and emergency exits based on real-time market conditions.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Repository Layout](#repository-layout)
3. [Backend — File-by-File Reference](#backend--file-by-file-reference)
4. [analyst/ Package](#analyst-package)
5. [Frontend](#frontend)
6. [Grafana Dashboards](#grafana-dashboards)
7. [Observability Stack](#observability-stack)
8. [Prometheus Metrics Reference](#prometheus-metrics-reference)
9. [Prometheus Alert Rules](#prometheus-alert-rules)
10. [API Reference](#api-reference)
11. [Pluggable Signal Strategies](#pluggable-signal-strategies)
12. [MongoDB Change Stream Command Bus](#mongodb-change-stream-command-bus)
13. [Testing](#testing)
14. [Environment Variables](#environment-variables)
15. [Quick Start](#quick-start)

---

## Architecture

### Communication Channels (Robust & Redundant)

| Channel | Purpose | Latency | Use Case |
|---|---|---|---|
| WebSocket | Real-time signals & confirmations to Pulse | <100 ms | Primary live path |
| MongoDB Change Streams | Persistent commands & cross-service state | ~200 ms | Reliable fallback |
| REST (circuit breaker) | One-off control actions & admin overrides | 300–800 ms | Last-resort fallback |
| Prometheus `/metrics` | Observability scraping | — | Metrics only |
| OpenTelemetry gRPC | Distributed tracing → Grafana Tempo | — | Debugging |

### System Diagram

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                        Sentinel Edge (port 8001)                     │
  │                                                                     │
  │  ┌──────────────────────┐   ┌─────────────────────────────────────┐ │
  │  │  analyst/core.py     │   │  EvaluationScheduler (scheduler.py) │ │
  │  │  SentinelEdge        │◄──│  • Ticker loop (every 1 s)          │ │
  │  │  • OTel tracing      │   │  • PriceFetcher (yfinance, 5 s cache)│ │
  │  │  • WebSocket ↔ Pulse │   │  • ORBTracker  (5m / 15m / 30m)     │ │
  │  │  • Change stream bus │   │  • ATRCalculator (14-period)         │ │
  │  │  • Plugin discovery  │   │  • SignalEngine (5-layer scoring)    │ │
  │  └──────────┬───────────┘   │  • DecisionEngine (risk guards)      │ │
  │             │ shares        └────────────────┬────────────────────┘ │
  │  ┌──────────▼─────────────────────────────┐  │                      │
  │  │  analyst/correlation/engine.py          │◄─┘                      │
  │  │  CorrelationEngine                      │                         │
  │  │  • 120 s rolling window per symbol      │                         │
  │  │  • ≥ 3 symbols same direction → cluster │                         │
  │  │  • BEARISH cluster → Pulse override     │                         │
  │  └─────────────────────────────────────────┘                         │
  │                                                                     │
  │  /metrics (Prometheus)  :8001     OTel gRPC → Tempo :4317           │
  └──────────────────────┬──────────────────────────────────────────────┘
                         │  REST / WebSocket / Change Streams
             ┌───────────▼──────────────┐
             │     Sentinel Pulse        │
             │  (trade execution engine) │
             └───────────────────────────┘
```

### Decision Flow (per ticker, every evaluation cycle)

```
  PriceFetcher.get_price_with_volume(symbol)
          │
          ▼
  SignalEngine.update_avg_volume()
  SignalEngine.compute_volume_zscore()     ← rolling 60-reading z-score
          │
          ▼
  ORBTracker.update(symbol, price, ts)     ← update / auto-lock ranges
  ORBTracker.check_breakout(symbol, price) ← emit breakout events
          │
          ▼
  ATRCalculator.update(symbol, H, L, C)   ← 14-period true range
          │
          ▼
  SignalEngine.evaluate_signal(            ← 5-layer ±10 score
      orb_high, orb_low,
      volume_ratio, atr,
      price_change_pct, volume_zscore
  )
          │
          ▼
  DecisionEngine.decide(                   ← risk-guarded Decision enum
      trend, signal_strength,
      pnl_pct, drawdown,
      has_position, trailing_enabled
  )
          │
          ├── BUY / STOP_BUYING → PulseClient.send_override()
          ├── ENABLE_TRAILING_STOP → PulseClient.update_ticker()
          ├── TIGHTEN_TRAILING_STOP → PulseClient.update_ticker()
          └── EMERGENCY_EXIT → PulseClient.emergency_stop()

  CorrelationEngine.record_signal()        ← feeds cluster detection
```

---

## Repository Layout

```
sentinel-edge/
│
├── backend/                          # Python FastAPI application
│   ├── server.py                     # App entrypoint — FastAPI, lifespan, all routes
│   ├── scheduler.py                  # EvaluationScheduler — main ticker evaluation loop
│   ├── engine.py                     # DecisionEngine — BUY/STOP/EXIT/TIGHTEN logic
│   ├── signals.py                    # SignalEngine — 5-layer ±10 score + volume Z-score
│   ├── orb.py                        # ORBTracker — multi-timeframe ORB (5m/15m/30m)
│   ├── atr.py                        # ATRCalculator — 14-period true range
│   ├── price_fetcher.py              # PriceFetcher — yfinance with 5 s in-memory cache
│   ├── pulse_client.py               # PulseClient — circuit-breaker HTTP client for Pulse
│   ├── market_hours.py               # MarketHours — NYSE, NASDAQ, LSE, TSE, HKEX, SSE, BSE
│   ├── metrics.py                    # All 40+ prometheus_client metric definitions
│   ├── correlation.py                # Backward-compat shim → analyst/correlation/engine.py
│   ├── Dockerfile                    # Python 3.12-slim image
│   ├── requirements.txt              # Pinned Python dependencies
│   │
│   ├── analyst/                      # Orchestration & extensibility layer
│   │   ├── core.py                   # SentinelEdge — OTel, WebSocket, change streams
│   │   ├── correlation/
│   │   │   └── engine.py             # CorrelationEngine (canonical location)
│   │   ├── signals/
│   │   │   ├── base.py               # BaseSignal ABC, Signal dataclass, SignalConfig
│   │   │   ├── __init__.py           # discover_plugins() — auto-scans custom/
│   │   │   └── custom/
│   │   │       └── vwap_breakout.py  # Example plugin: VWAP cross + volume confirmation
│   │   ├── exporters/
│   │   │   └── prometheus.py         # PrometheusExporter — optional standalone :8002
│   │   ├── observability/
│   │   │   └── otel.py               # setup_otel(), instrument_fastapi(), get_tracer()
│   │   └── webhook/
│   │       └── alert_handler.py      # Alertmanager webhook receiver (/api/webhook/alert)
│   │
│   └── tests/                        # pytest test suite
│       ├── test_sentinel_edge.py     # ORB, ATR, signal, decision integration tests
│       ├── test_p1_features.py       # Volume Z-score, TIGHTEN_TRAILING_STOP, plugins
│       ├── test_correlation_engine.py# CorrelationEngine cluster detection tests
│       └── test_decision_feed_and_tickers.py
│
├── frontend/                         # TypeScript + React + Vite dashboard
│   ├── src/
│   │   ├── App.tsx                   # Root — routing, layout
│   │   ├── components/
│   │   │   ├── dashboards/           # 6 dashboard panels (TradingOverview, BrokerHealth …)
│   │   │   ├── cards/                # MetricCard, ChartCard, TickerCard
│   │   │   └── ui/                   # shadcn/ui component library (30+ primitives)
│   │   ├── store/useStore.ts         # Zustand global state store
│   │   ├── lib/
│   │   │   ├── api.ts                # typed API client (axios)
│   │   │   └── mockData.ts           # drifting mock prices for dev/demo
│   │   └── types/index.ts            # Shared TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
│
├── grafana/
│   ├── dashboards/                   # Auto-provisioned dashboard JSON files
│   │   ├── analyst-overview.json     # Engine state, ORB rate, ATR heatmap, latency
│   │   ├── correlation-breadth.json  # Cluster table, bull/bear pie, breadth timeseries
│   │   ├── trading_overview.json     # ORB levels, signal strength, current prices
│   │   ├── broker_health.json        # Circuit breaker state, Pulse API latency
│   │   ├── pnl_tracking.json         # Realised / unrealised P&L, win rate
│   │   ├── market_coverage.json      # Global exchange open/closed status
│   │   ├── executive-overview.json   # ★ NEW — KPI tiles, ORB breakout rate, override timeline
│   │   ├── market-breadth.json       # ★ NEW — Correlation heatmap, bull/bear distribution
│   │   ├── risk-management.json      # ★ NEW — Auto-overrides, trailing stop events, drawdown
│   │   └── signal-quality.json       # ★ NEW — Win rate heatmap, signal confidence P95, P&L lift
│   └── provisioning/
│       ├── dashboards/
│       │   └── sentinel_edge.yml     # Provider config → /var/lib/grafana/dashboards
│       └── datasources/
│           └── prometheus.yml        # Prometheus + Loki + Tempo datasource definitions
│
├── prometheus/
│   ├── prometheus.yml                # Scrape configs (sentinel-edge :8001, :8002, cadvisor …)
│   ├── rules.yml                     # Recording rules
│   └── alerts/
│       └── sentinel_edge_rules.yml   # 11 alert rules (see Alert Rules section)
│
├── docker-compose.yml                # Full LGTM stack (see Observability section)
├── Dockerfile                        # Root-level image (alternative build target)
├── IMPLEMENTATION_PLAN.md            # Engineering roadmap
└── README.md                         # This file
```

---

## Backend — File-by-File Reference

### `backend/server.py` — Application Entrypoint
FastAPI application with async lifespan. On startup, instantiates all components (PulsClient, PriceFetcher, ORBTracker, ATRCalculator, SignalEngine, DecisionEngine, MarketHours), wires them into `EvaluationScheduler`, creates the `SentinelEdge` orchestrator, and starts background tasks. Registers all API routes under `/api`, the Prometheus `/metrics` endpoint, and the Alertmanager webhook receiver.

### `backend/scheduler.py` — Evaluation Loop
`EvaluationScheduler` runs an `asyncio` loop that evaluates every active ticker approximately once per second during market hours. For each ticker it fetches price + volume, updates the ORB tracker and ATR calculator, scores the signal, makes a decision, and forwards non-HOLD decisions to Pulse. Maintains `ticker_state` (enriched live data for the API) and `recent_decisions` (last 50 non-HOLD decisions for the decision feed). Supports `pause()` / `resume()` / `add_ticker()` / `remove_ticker()` at runtime.

### `backend/engine.py` — Decision Engine
`DecisionEngine` translates a `(TrendDirection, signal_strength)` pair into a `Decision` enum value, applying risk guards first:

| Decision | Condition |
|---|---|
| `EMERGENCY_EXIT` | ≥ 3 consecutive losses **or** drawdown > 10 % |
| `TIGHTEN_TRAILING_STOP` | trailing active + signal ≥ 7 + PnL > 5 % |
| `ENABLE_TRAILING_STOP` | has position + PnL > 2 % + trailing not yet active |
| `TIGHTEN_STOP` | has position + bearish reversal (strength < −3) |
| `BUY` | bullish + strength ≥ 5 (unconditional) or ≥ 3 (< 2 loss streak) |
| `STOP_BUYING` | bearish + strength ≤ −5 (or −3 if has position) |
| `HOLD` | everything else |

Tracks consecutive losses, win rate, and total trades per symbol and updates Prometheus counters on every decision.

### `backend/signals.py` — Signal Scoring Engine
`SignalEngine` produces a float score in **[−10, +10]** from five independent layers:

| Layer | Range | Logic |
|---|---|---|
| 1. ORB breakout | ±3 | price above/below locked ORB high/low |
| 2. Volume confirmation | ±2 | volume ratio vs EMA average; low ratio dampens score |
| 3. Price momentum | ±2 | price_change_pct thresholds at ±1 % and ±2 % |
| 4. Volatility adjustment | ±1 | high ATR/price > 4 % dampens; low < 1 % boosts |
| 5. Volume Z-score anomaly | ±2 | z ≥ 3.5 = extreme boost; z ≤ −1.5 = dampened |

Score ≥ 2 → `BULLISH`, ≤ −2 → `BEARISH`, otherwise `NEUTRAL`.

### `backend/orb.py` — ORB Tracker
`ORBTracker` maintains per-symbol ORB levels for three timeframes (5 m, 15 m, 30 m). Each level auto-locks when the configured window elapses from market open (09:30 ET). Once locked, `check_breakout()` emits breakout events and increments the `edge_orb_breakouts_total` counter. Levels reset automatically on a new trading day (date mismatch). Persists high/low/range-width to Prometheus gauges in real time.

### `backend/atr.py` — ATR Calculator
`ATRCalculator` computes a 14-period simple moving average of True Range from a rolling deque of (High, Low, Close) bars. Exposes `get_trailing_stop_offset(symbol, multiplier=2.0)` and `is_high_volatility(symbol, threshold_pct=3.0)` helpers. Updates `edge_atr_value` and `edge_volatility_percentile` metrics continuously.

### `backend/price_fetcher.py` — Price Data
`PriceFetcher` wraps yfinance with a 5-second in-memory cache. Provides:
- `get_current_price(symbol)` — latest Close
- `get_price_with_volume(symbol)` — Close + Volume (used by the scheduler)
- `get_ohlcv(symbol, period, interval)` — full OHLCV DataFrame for ATR seeding

Tracks fetch latency (`price_fetch_latency` histogram) and failure counts per symbol.

### `backend/pulse_client.py` — Pulse API Client
`PulseClient` uses a **circuit breaker** pattern (half-open after 60 s, opens after 5 failures) to make the Pulse REST API resilient to network issues. Exposes `send_override(symbol, action, params)`, `update_ticker(symbol, config)`, and `emergency_stop()`. All calls are retried once after a short backoff.

### `backend/market_hours.py` — Global Market Hours
`MarketHours` tracks open/closed/lunch-break status for 7 exchanges: NYSE, NASDAQ, LSE, TSE (with lunch), HKEX (with lunch), SSE (with lunch), and BSE. Used by the scheduler to gate evaluations to active market hours. Exposes `/api/markets` endpoint showing real-time status for all exchanges.

### `backend/metrics.py` — Prometheus Definitions
Central module that defines every `prometheus_client` metric object (Counter, Gauge, Histogram, Info). All other modules import metric objects from here — no metric is defined inline in business logic. See [Prometheus Metrics Reference](#prometheus-metrics-reference) for the full list.

### `backend/correlation.py` — Backward-Compat Shim
Thin re-export of `analyst/correlation/engine.py`. Allows `from correlation import CorrelationEngine` in legacy code while the canonical implementation lives in the `analyst/` package.

---

## analyst/ Package

The `analyst/` package extends the core backend with advanced orchestration, extensibility, and observability capabilities.

### `analyst/core.py` — SentinelEdge Orchestrator
The top-level `SentinelEdge` class wraps `EvaluationScheduler` and adds:

- **OpenTelemetry** — `setup_otel()` initialises gRPC OTLP export to Tempo. Every evaluation cycle is instrumented with spans and attributes.
- **WebSocket ↔ Pulse** — bidirectional connection for sub-100 ms signal delivery. Falls back to REST on disconnect.
- **MongoDB Change Stream** — listens to the `analyst_commands` collection for commands (pause, resume, add_ticker, override) without a REST round-trip. Requires a MongoDB replica set.
- **Plugin discovery** — calls `discover_plugins()` on startup, auto-registering all `BaseSignal` subclasses from `analyst/signals/custom/`.
- **Shared CorrelationEngine** — replaces the scheduler's own correlation engine with the `SentinelEdge` instance so both share a single event window.

### `analyst/correlation/engine.py` — Correlation Engine
`CorrelationEngine` maintains a 120-second rolling window of signal events per symbol. When ≥ 3 symbols break out in the same direction within the window, it:
1. Emits a cluster event
2. Persists to MongoDB (`correlation_clusters` collection)
3. Increments `correlation_clusters_total` Prometheus counter
4. If the cluster is bearish **and** mean confidence > 0.65, fires a Pulse override (`tighten_trailing_global` or `emergency_stop`)
5. Respects a per-direction 300-second cooldown to prevent alert storms

Exposes `get_recent_clusters()` / `get_current_breadth()` / `get_latest_cluster()` for the REST API.

### `analyst/signals/base.py` — Plugin Interface

```python
@dataclass
class Signal:
    symbol: str
    action: str          # "BUY" | "SELL" | "HOLD"
    confidence: float    # 0.0 – 1.0
    reason: str
    timeframe: str
    price: float
    timestamp: datetime

class BaseSignal(ABC):
    name: str            # unique identifier
    version: str
    description: str
    tags: list[str]
    requires_history_bars: int = 0

    @abstractmethod
    async def generate(
        self,
        symbol: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]: ...
```

### `analyst/signals/custom/vwap_breakout.py` — Built-in Plugin
VWAP (Volume-Weighted Average Price) cross with volume confirmation. Computes cumulative VWAP from OHLCV history, signals BUY when `price > VWAP × (1 + buffer)` and `volume_ratio ≥ 1.25`, SELL for the inverse. Confidence scales with distance from VWAP and volume ratio. A volume Z-score above the configured threshold provides an additional confidence boost.

### `analyst/observability/otel.py`
Initialises the OpenTelemetry SDK with gRPC OTLP export. Patches `HTTPXAsyncClient` and asyncio for automatic instrumentation. Provides `instrument_fastapi(app)` for automatic request span generation and `get_tracer(name)` for manual span creation.

### `analyst/webhook/alert_handler.py`
FastAPI router (`/api/webhook/alert`, `/api/webhook/health`) that receives Alertmanager POST webhooks. Maps alert names to autonomous actions: `HighConsecutiveLosses` → pause scheduler, `HighDrawdown` → emergency exit all positions, `BearishClusterOverride` → tighten stops globally. Validates an optional `WEBHOOK_SECRET` shared with Alertmanager.

---

## Frontend

The React/TypeScript frontend (`frontend/`) provides a real-time operations dashboard.

### Dashboard Panels

| Component | File | Description |
|---|---|---|
| Trading Overview | `dashboards/TradingOverview.tsx` | Live price, signal strength, ORB levels, trend indicator per ticker |
| Broker Health | `dashboards/BrokerHealth.tsx` | Pulse API circuit breaker state, response times, failure counts |
| P&L Tracking | `dashboards/PnLTracking.tsx` | Realised / unrealised P&L, win rate, consecutive loss streak |
| Market Breadth | `dashboards/MarketBreadth.tsx` | Bull/bear % bar, correlation cluster card, latest cluster details |
| Decision Feed | `dashboards/DecisionFeed.tsx` | Live log of last 50 non-HOLD decisions with timestamp and price |
| Market Coverage | `dashboards/MarketCoverage.tsx` | Global exchange open/closed status with countdown |

### Key Libraries

| Library | Use |
|---|---|
| React 18 + TypeScript | UI framework |
| Vite | Dev server & bundler |
| Zustand | Global state (`useStore.ts`) |
| axios (`lib/api.ts`) | Typed API client |
| shadcn/ui | 30+ accessible UI primitives |
| Recharts | Metric charts |
| Tailwind CSS | Utility-first styling |

### Mock Data Mode
Set `VITE_MOCK_DATA=true` to enable drifting simulated prices without a backend connection. Useful for UI development and demos.

---

## Grafana Dashboards

All dashboards live in `grafana/dashboards/` and are **auto-provisioned** by Grafana on startup via `grafana/provisioning/dashboards/sentinel_edge.yml` (provider path: `/var/lib/grafana/dashboards`). No manual import needed.

The provisioning YAML is mounted read-only at `/etc/grafana/provisioning/dashboards/` while the dashboard JSON files are mounted separately at `/var/lib/grafana/dashboards/` — preventing the common volume-shadowing bug where a directory mount silently hides a sibling file mount.

### Dashboard Inventory

#### Existing Dashboards

| File | Title | UID | Key Panels |
|---|---|---|---|
| `analyst-overview.json` | Sentinel Edge — Analyst Overview | `se-analyst-overview` | Engine state, ORB breakout rate, ATR heatmap, per-symbol signal strength, decision table, evaluation latency p99 |
| `correlation-breadth.json` | Sentinel Edge — Market Breadth & Correlation | `se-correlation-breadth` | Active clusters table, bull/bear pie, cluster detection rate, breadth timeseries |
| `trading_overview.json` | Trading Overview | varies | Live ORB high/low levels, current prices, signal strength per timeframe |
| `broker_health.json` | Broker Health | varies | Pulse API circuit breaker state, REST latency histogram, failure rate |
| `pnl_tracking.json` | P&L Tracking | varies | Realised / unrealised P&L, win rate gauge, consecutive loss counter |
| `market_coverage.json` | Market Coverage | varies | NYSE / NASDAQ / LSE / TSE / HKEX open status, minutes to close |

#### New Dashboards (from `codex/continue-sentinel-edge-readme-rework-jejpy8`)

| File | Title | UID | Key Panels | Template Variables |
|---|---|---|---|---|
| `executive-overview.json` | Executive Sentinel Overview | `sentinel-executive` | Live correlation strength stat, active Pulse overrides count, ORB breakout rate timeseries, top symbols by win rate table, override timeline with severity thresholds | `symbol`, `timeframe`, `direction`, `severity` |
| `market-breadth.json` | Market Breadth & Correlation | `sentinel-breadth` | Live cluster count stat, correlation heatmap (symbol × direction), bull/bear pie chart, rolling 30 m cluster strength | `symbol`, `timeframe`, `direction`, `severity` |
| `risk-management.json` | Risk Management & Overrides | `sentinel-risk` | Auto-overrides sent to Pulse (timeseries), trailing stop tightening events (bar chart), position size reductions (table), drawdown protection effectiveness %, override severity timeline | `symbol`, `timeframe`, `direction`, `severity` |
| `signal-quality.json` | Signal Quality & Performance | `sentinel-signal-quality` | Win rate heatmap (symbol × timeframe), signal confidence P95 timeseries, false positive rate, P&L lift vs baseline Pulse | `symbol`, `timeframe`, `direction`, `severity` |

#### Dashboard Metrics Reference

The new dashboards query the following `analyst_*` metrics (exposed by the `analyst/` package):

| Metric | Type | Description |
|---|---|---|
| `analyst_orb_breakouts_total` | Counter | `{symbol, direction, timeframe}` — total breakouts detected |
| `analyst_orb_win_rate` | Gauge | `{symbol, timeframe}` — win rate for ORB signals (0–1) |
| `analyst_signal_confidence` | Histogram | `{symbol, direction}` — signal confidence distribution |
| `analyst_correlation_clusters_total` | Counter | `{symbol, direction}` — correlation cluster events |
| `analyst_pulse_overrides_total` | Counter | `{symbol, action, severity}` — Pulse override commands sent |
| `analyst_position_reductions` | Gauge | `{symbol, direction}` — position size reduction events |
| `analyst_drawdown_protection_pct` | Gauge | `{symbol, severity}` — drawdown protection effectiveness |
| `analyst_pnl_lift_vs_pulse` | Gauge | `{symbol, severity}` — P&L improvement over baseline Pulse |

#### Adding More Dashboards

Drop additional `*.json` files into `grafana/dashboards/` — they are provisioned automatically without restarting Grafana (the provider polls every 10 seconds, `updateIntervalSeconds: 10`).

---

## Observability Stack

Deployed via `docker-compose.yml`:

| Service | Image | Port(s) | Purpose |
|---|---|---|---|
| `sentinel-edge` | `./backend` | 8001, 8002 | FastAPI + `/metrics` + analyst metrics |
| `mongodb` | `mongo:7.0` | 27017 | State persistence + Change Streams (replica set `rs0`) |
| `mongodb-init` | `mongo:7.0` | — | One-shot: `rs.initiate()` after MongoDB is healthy |
| `prometheus` | `prom/prometheus:2.53` | 9090 | Metrics scraping + alerting rules evaluation |
| `alertmanager` | `prom/alertmanager` | 9093 | Alert routing → webhook receiver |
| `grafana` | `grafana/grafana:10.4.2` | 3001 | Dashboards + provisioning |
| `loki` | `grafana/loki` | 3100 | Log aggregation |
| `promtail` | `grafana/promtail` | — | Log shipping (Docker log driver → Loki) |
| `tempo` | `grafana/tempo` | 3200, 4317 | Distributed trace storage |
| `frontend` | `./frontend` | 3000 | React operations dashboard |

### Datasource Correlations

Grafana is provisioned with all three LGTM datasources wired together:
- **Prometheus → Tempo**: exemplar links on metric panels open the related trace in Tempo
- **Loki → Tempo**: log lines with `"trace_id"` become clickable trace links
- **Tempo → Loki**: traces show correlated logs in the sidebar

---

## Prometheus Metrics Reference

All core metrics use the `edge_` prefix. The `analyst/` package exposes additional `analyst_` metrics.

### ORB Metrics (`edge_orb_*`)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `edge_orb_breakouts_total` | Counter | `symbol`, `direction`, `timeframe` | Total breakouts detected |
| `edge_orb_high` | Gauge | `symbol`, `timeframe` | Locked ORB high level |
| `edge_orb_low` | Gauge | `symbol`, `timeframe` | Locked ORB low level |
| `edge_orb_range_width` | Gauge | `symbol`, `timeframe` | ORB range width (high − low) |

### Signal Metrics (`edge_signal_*`, `edge_trend_*`, `edge_volume_*`)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `edge_signal_strength` | Gauge | `symbol` | Current score −10 to +10 |
| `edge_trend_direction` | Gauge | `symbol` | 1 = bullish, 0 = neutral, −1 = bearish |
| `edge_volume_ratio` | Gauge | `symbol` | Current volume ÷ EMA average |
| `edge_volume_zscore` | Gauge | `symbol` | Volume rolling z-score (60-reading window) |
| `edge_atr_value` | Gauge | `symbol`, `period` | ATR value |
| `edge_volatility_percentile` | Gauge | `symbol` | ATR/price × 100 |

### Decision Metrics (`edge_decision_*`)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `edge_decision_total` | Counter | `symbol`, `decision` | Decisions by type |
| `edge_active_positions` | Gauge | `symbol` | Active position count |
| `edge_consecutive_losses` | Gauge | `symbol` | Current loss streak |
| `edge_win_rate` | Gauge | `symbol` | Win rate (0–100 %) |

### Infrastructure Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `current_price` | Gauge | `symbol` | Live price |
| `price_fetch_latency` | Histogram | `source` | yfinance fetch duration |
| `price_fetch_failures_total` | Counter | `symbol`, `source` | Fetch failures |
| `pulse_override_total` | Counter | `symbol`, `action` | Overrides sent to Pulse |
| `pulse_circuit_state` | Gauge | — | 0 = closed, 1 = open, 2 = half-open |
| `evaluation_duration_seconds` | Histogram | `symbol` | End-to-end evaluation latency |
| `market_open_status` | Gauge | `market` | 1 = open, 0 = closed |
| `correlation_clusters_total` | Counter | `direction` | Cluster detection events |

---

## Prometheus Alert Rules

Defined in `prometheus/alerts/sentinel_edge_rules.yml`:

| Alert Name | Severity | Trigger Condition | Auto-Action |
|---|---|---|---|
| `EdgeEngineDown` | critical | engine not running > 1 m | — |
| `EdgeEnginePaused` | warning | engine paused > 10 m | — |
| `HighConsecutiveLosses` | warning | any symbol consecutive losses ≥ 3 | Webhook → pause scheduler |
| `LowWinRate` | warning | win rate < 40 % sustained 30 m | — |
| `SlowEvaluation` | warning | evaluation p99 > 1 s for 3 m | — |
| `PriceFetchFailures` | warning | fetch failure rate > 0.5 /s | — |
| `CorrelationBearishCluster` | warning | bearish cluster detected | — |
| `HighDrawdown` | critical | drawdown > 8 % | Webhook → emergency exit all |
| `StrongCorrelationCluster` | warning | high-strength clusters > 1 | — |
| `BearishClusterOverride` | critical | high-strength bearish cluster → Pulse override sent | Webhook → tighten stops globally |
| `HighPulseOverrideRate` | warning | override rate > 0.5 /s | — |

Alerts route via `prometheus/alertmanager.yml` to a webhook that hits `/api/webhook/alert` for autonomous remediation.

---

## API Reference

Base URL: `http://localhost:8001`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness check — running, paused, active ticker count |
| `GET` | `/api/tickers` | All active tickers with enriched live state (price, signal, ORB, ATR) |
| `POST` | `/api/tickers/{symbol}` | Add ticker to watch list |
| `DELETE` | `/api/tickers/{symbol}` | Remove ticker |
| `GET` | `/api/tickers/{symbol}/config` | Per-ticker metric enable/disable config |
| `PUT` | `/api/tickers/{symbol}/config` | Update per-ticker metric config (persisted to MongoDB) |
| `GET` | `/api/orb/{symbol}` | ORB levels for all timeframes (5m/15m/30m) |
| `GET` | `/api/decisions` | Last 50 non-HOLD decisions (decision feed) |
| `GET` | `/api/correlation` | Cluster list + market breadth + latest cluster |
| `GET` | `/api/markets` | Global exchange open/closed status |
| `GET` | `/api/stats` | System stats (tickers, circuit state, failure count) |
| `POST` | `/api/control/pause` | Pause the evaluation scheduler |
| `POST` | `/api/control/resume` | Resume the evaluation scheduler |
| `POST` | `/api/webhook/alert` | Alertmanager webhook receiver |
| `GET` | `/metrics` | Prometheus text-format scrape endpoint |

---

## Pluggable Signal Strategies

Drop any subclass of `BaseSignal` into `analyst/signals/custom/` and it is **auto-discovered** at startup — no registration required.

```python
# analyst/signals/custom/my_strategy.py
from analyst.signals.base import BaseSignal, Signal
from typing import Dict, Any, Optional

class MyStrategy(BaseSignal):
    name = "my_strategy"
    version = "1.0.0"
    description = "Custom strategy"
    tags = ["custom"]
    requires_history_bars = 20   # minimum OHLCV bars needed

    async def generate(
        self,
        symbol: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        price        = market_data["price"]
        volume_ratio = market_data.get("volume_ratio", 1.0)
        vwap         = market_data.get("vwap", price)

        if price > vwap * 1.005 and volume_ratio > 1.5:
            return Signal(
                symbol=symbol,
                action="BUY",
                confidence=0.82,
                reason="Price above VWAP with elevated volume",
                timeframe="15m",
                price=price,
            )
        return None
```

**Available `market_data` keys:** `price`, `volume`, `volume_ratio`, `volume_zscore`, `orb_high`, `orb_low`, `atr`, `price_change_pct`, `vwap`, `ohlcv` (DataFrame).

---

## MongoDB Change Stream Command Bus

Insert a document into `analyst_commands` to send a command without a REST call. Requires MongoDB replica set (handled automatically by `mongodb-init` in docker-compose).

```js
// Pause the scheduler
db.analyst_commands.insertOne({ command: "pause", source: "ops" })

// Resume
db.analyst_commands.insertOne({ command: "resume" })

// Add ticker
db.analyst_commands.insertOne({ command: "add_ticker", symbol: "TSLA" })

// Remove ticker
db.analyst_commands.insertOne({ command: "remove_ticker", symbol: "TSLA" })

// Tighten all trailing stops globally (e.g. ahead of FOMC)
db.analyst_commands.insertOne({ command: "override", action: "tighten_trailing_global" })

// Emergency exit all positions
db.analyst_commands.insertOne({ command: "override", action: "emergency_stop" })
```

---

## Testing

```bash
cd backend
pytest tests/ -v

# Run a specific test file
pytest tests/test_p1_features.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

| Test File | What It Covers |
|---|---|
| `test_sentinel_edge.py` | ORB locking, ATR calculation, signal scoring, decision guard conditions |
| `test_p1_features.py` | Volume Z-score, `TIGHTEN_TRAILING_STOP`, plugin auto-discovery |
| `test_correlation_engine.py` | Cluster detection, cooldown enforcement, Pulse override triggering |
| `test_decision_feed_and_tickers.py` | Decision ring buffer, ticker CRUD, enriched state |

Test reports are written to `test_reports/` (JSON summaries + JUnit XML for CI ingestion).

---

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `MONGO_URL` | — | ✅ | MongoDB connection string (`mongodb://mongodb:27017`) |
| `DB_NAME` | — | ✅ | MongoDB database name (`sentinel_edge`) |
| `PULSE_API_URL` | `http://localhost:8002` | — | Sentinel Pulse base URL |
| `PULSE_API_KEY` | — | — | Optional API key for Pulse authentication |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://tempo:4317` | — | Tempo gRPC endpoint for distributed traces |
| `OTEL_SERVICE_NAME` | `sentinel-edge` | — | OpenTelemetry service name |
| `ANALYST_START_METRICS_SERVER` | `false` | — | Set `true` to expose a dedicated `:8002/metrics` endpoint |
| `CORS_ORIGINS` | `*` | — | Comma-separated allowed CORS origins |
| `WEBHOOK_SECRET` | — | — | Shared secret validated on `/api/webhook/alert` requests |

---

## Quick Start

```bash
git clone https://github.com/Tetradim/sentinel-edge
cd sentinel-edge
git checkout Further

# Start the full stack (backend + frontend + LGTM observability)
docker compose up -d --build

# Tail the bot logs
docker compose logs -f sentinel-edge

# Access services
open http://localhost:3001   # Grafana  (admin / sentinel123)
open http://localhost:9090   # Prometheus
open http://localhost:3000   # React frontend
open http://localhost:3200   # Grafana Tempo (traces)
open http://localhost:9093   # Alertmanager

# Add a ticker at runtime
curl -X POST http://localhost:8001/api/tickers/NVDA

# Check live ticker state
curl http://localhost:8001/api/tickers | jq .

# Get ORB levels for SPY
curl http://localhost:8001/api/orb/SPY | jq .

# See recent decisions
curl http://localhost:8001/api/decisions | jq .decisions[:5]

# Pause / resume the scheduler
curl -X POST http://localhost:8001/api/control/pause
curl -X POST http://localhost:8001/api/control/resume
```

### Running Without Docker

```bash
cd backend

# Runtime only
pip install -r requirements.txt

# Runtime + dev/test tools
pip install -r requirements-dev.txt

export MONGO_URL=mongodb://localhost:27017
export DB_NAME=sentinel_edge
export PULSE_API_URL=http://localhost:8002

uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

---

## Dependency Audit Log

**Audited:** 2026-04-12  
**Files scanned:** 29 Python files across `backend/` and `backend/analyst/`  
**Result:** `requirements.txt` reduced from 145 packages to 22 direct runtime dependencies. Dev tools split into `requirements-dev.txt`.

The original `requirements.txt` was generated by `pip freeze` from a full development environment rather than curated by hand. It contained packages from several experimental features that were never shipped. Below is a record of every removed package group, what it was likely built for, and why it was safe to remove.

---

### Removed: LLM / AI Integration Suite

**Packages removed:**
`openai==1.99.9`, `litellm==1.80.0`, `google-genai==1.70.0`, `google-generativeai==0.8.6`, `google-ai-generativelanguage==0.6.15`, `tiktoken==0.12.0`

**What it was for:** An experimental feature to pass ORB signal data and trade context to a large language model (OpenAI GPT or Google Gemini) for natural-language trade explanations or autonomous strategy suggestions. `litellm` is a proxy library that allows switching between multiple LLM providers (OpenAI, Anthropic, Google, etc.) without changing application code. `tiktoken` is OpenAI's token counter, used to stay within model context limits.

**Why removed:** No import of any of these packages exists anywhere in the codebase. The feature was not implemented — or was implemented and then deleted — but the dependencies were left behind. The `analyst/signals/base.py` `BaseSignal` plugin interface is the intended extensibility path for custom signal logic; an LLM plugin could be added there if required.

---

### Removed: AWS / Cloud Storage

**Packages removed:**
`boto3==1.42.84`, `botocore==1.42.84`, `s3transfer==0.16.0`, `jmespath==1.1.0`, `s5cmd==0.2.0`

**What it was for:** AWS SDK integration, almost certainly for writing trade history, ORB level snapshots, or model weights to an S3 bucket. `s5cmd` is a high-performance S3 file transfer CLI written in Go — its presence as a Python package entry suggests it was being used to ship large data files (historical OHLCV data or Hugging Face model checkpoints) to/from S3. `jmespath` is the JSON path query engine used internally by boto3 to filter API responses.

**Why removed:** All state persistence in the current codebase goes through MongoDB (`motor`). No `boto3` or `s3` import exists anywhere. No S3 bucket configuration appears in `docker-compose.yml` or environment variable documentation.

---

### Removed: Machine Learning / NLP Stack

**Packages removed:**
`huggingface_hub==1.9.0`, `hf-xet==1.4.3`, `tokenizers==0.22.2`, `pillow==12.2.0`

**What it was for:** Integration with Hugging Face to load a pre-trained model (likely a time-series forecasting model or a financial sentiment classifier) directly into the bot for signal generation. `pillow` is an image processing library — in this context it was likely used to generate OHLCV candlestick chart images to feed into a vision model, or to render chart thumbnails in a report. `hf-xet` is Hugging Face's large-file transfer protocol used when downloading multi-GB model weight files.

**Why removed:** No import of `huggingface_hub`, `tokenizers`, or `PIL` exists in any Python file. The ML feature was never wired into the evaluation pipeline. The `analyst/signals/custom/` plugin directory is the correct place to add an ML-based signal if this is revisited.

---

### Removed: Payment Processing

**Packages removed:**
`stripe==15.0.1`

**What it was for:** The Stripe Python SDK for accepting credit card payments. In the context of a trading bot, this most likely supported a planned SaaS billing model — charging subscribers for access to Sentinel Edge as a managed service, or metering API usage. Stripe's SDK handles payment intent creation, subscription lifecycle, and webhook verification.

**Why removed:** No Stripe import, no payment route, no webhook handler for Stripe events exists anywhere in the codebase. The bot is self-hosted with no monetization layer.

---

### Removed: SQL ORM

**Packages removed:**
`peewee==4.0.4`

**What it was for:** Peewee is a lightweight Python ORM that supports SQLite, PostgreSQL, and MySQL. Its presence strongly suggests the bot originally persisted state (ORB levels, trade history, ticker configuration) to a relational database before the architecture was switched to MongoDB. SQLite would have been the natural choice for a single-node deployment before replication and change streams became requirements.

**Why removed:** The entire persistence layer uses `motor` (async MongoDB). No `peewee` import or model definition exists. The schema would have been superseded by MongoDB collections (`tickers`, `orb_levels`, `correlation_clusters`, `analyst_commands`).

---

### Removed: Google Workspace / API Platform

**Packages removed:**
`google-api-python-client==2.193.0`, `google-api-core==2.30.2`, `google-auth==2.49.1`, `google-auth-httplib2==0.3.1`, `googleapis-common-protos==1.74.0`, `proto-plus==1.27.2`, `uritemplate==4.2.0`, `httplib2==0.31.2`, `pyasn1==0.6.3`, `pyasn1-modules==0.4.2`

**What it was for:** The Google API Python client library stack, used to integrate with Google Workspace services. In a trading context this was most likely a **Google Sheets integration** — writing live P&L, ORB levels, or decision logs to a shared spreadsheet for team visibility — or a **Gmail / Google Chat alerting** channel for breakout notifications. `google-auth` handles OAuth2 service account authentication against any Google API.

**Why removed:** No Google API import exists. Alerting goes through Prometheus Alertmanager → webhook receiver. Logging goes through the structured JSON logger → Promtail → Loki.

---

### Removed: Authentication System

**Packages removed:**
`PyJWT==2.12.1`, `python-jose==3.5.0`, `passlib==1.7.4`, `bcrypt==4.1.3`, `email-validator==2.3.0`

**What it was for:** A full user authentication system with JWT session tokens and bcrypt password hashing — the standard stack for building a login-protected web application. `python-jose` supports JWT, JWE (encrypted tokens), and JWS (signed tokens). `passlib` is an abstraction layer over multiple hashing algorithms (bcrypt, argon2, scrypt). `email-validator` was used to validate user email addresses at registration. This points to a planned **multi-user SaaS interface** where each user would log in, manage their own tickers, and see their own P&L.

**Why removed:** The current API has no login endpoint, no user session concept, and no per-user data isolation. The only authentication present is an optional HMAC secret check on the Alertmanager webhook receiver (`secrets.compare_digest` — Python stdlib, no external dependency). If authentication is added in future, use FastAPI's built-in `OAuth2PasswordBearer` with `python-jose` and `passlib[bcrypt]`.

---

### Removed: Web Scraping

**Packages removed:**
`beautifulsoup4==4.14.3`, `soupsieve==2.8.3`

**What it was for:** HTML/XML scraping using BeautifulSoup. In a trading bot context this was most likely scraping financial news sites, SEC EDGAR filings, or earnings announcement pages to extract text for sentiment analysis (potentially feeding the LLM integration above). `soupsieve` is the CSS selector engine used by BeautifulSoup 4 for `soup.select()` queries.

**Why removed:** No `bs4` import exists. yfinance handles its own internal HTML parsing for financial data. A proper news/events integration would use a structured API (Benzinga, NewsAPI, Alpaca news feed) rather than scraping.

---

### Removed: Unused Utilities & Miscellaneous

**Packages removed:**
`emergentintegrations==0.1.0`, `PyYAML==6.0.3`, `Pygments==2.20.0`, `jq==1.11.0`, `regex==2026.4.4`, `fastuuid==0.14.0`, `frozendict==2.4.7`, `tqdm==4.67.3`, `rich==14.3.3`, `tenacity==9.1.4`, `typer==0.24.1`, `python-multipart==0.0.24`, `watchfiles==1.1.1`, `librt==0.8.1`, `distro==1.9.0`, `fsspec==2026.3.0`, `curl_cffi==0.15.0`, `multitasking==0.0.12`, `annotated-doc==0.0.4`, `pytokens==0.4.1`

| Package | Likely purpose |
|---|---|
| `emergentintegrations` | Unknown commercial integration platform; not imported anywhere |
| `PyYAML` | YAML config parsing; all configuration is via environment variables |
| `Pygments` | Syntax highlighting for terminal or HTML output; no formatted code output in service |
| `jq` | Python bindings for the `jq` JSON CLI tool; Python's `json` module is sufficient |
| `regex` | Extended regex with Unicode support; standard `re` module is used throughout |
| `fastuuid` | C-extension UUID generation; Python's built-in `uuid` module is adequate |
| `frozendict` | Immutable dict type; standard `dict` used everywhere |
| `tqdm` | Progress bars for batch loops; no batch processing in the async service |
| `rich` | Formatted terminal output (tables, panels, colour); standard `logging` module used |
| `tenacity` | Retry decorator library; pulse_client.py implements inline circuit-breaker instead |
| `typer` | CLI application framework (Click wrapper); no management CLI exists |
| `python-multipart` | Multipart form/file upload parsing; no file upload endpoints |
| `watchfiles` | File system watcher for uvicorn `--reload` in dev; not needed in the image |
| `librt` | POSIX real-time library binding; no high-resolution clock calls |
| `distro` | Linux distribution detection; irrelevant inside a Docker container |
| `fsspec` | Filesystem abstraction (local, S3, GCS, HDFS); only local + MongoDB used |
| `curl_cffi` | cURL-based HTTP client used to bypass bot detection; `httpx` covers all HTTP needs |
| `multitasking` | Thread-pool helper; `asyncio` is the concurrency model throughout |
| `annotated-doc` | Unknown documentation annotation package; not imported |
| `pytokens` | Unknown token utility; not imported |

---

### Moved to `requirements-dev.txt`

**Packages moved:**
`black==26.3.1`, `isort==8.0.1`, `mypy==1.20.0`, `flake8==7.3.0` (+ `pycodestyle`, `pyflakes`, `mccabe` as flake8 deps), `pytest==9.0.2`, `requests==2.33.1` (used only in test files)

These are development and code-quality tools. Including them in the production image adds ~150 MB to the layer and installs compiler toolchains that increase the attack surface. The production `Dockerfile` installs only `requirements.txt`. Run `pip install -r requirements-dev.txt` locally or in CI.

---

### What Was Not Removed

`requests==2.33.1` is kept in `requirements-dev.txt` because all four integration test files (`tests/*.py`) use it as their HTTP client. It is not imported by any production code and is not installed in the Docker image.

`pymongo==4.5.0` is kept even though it is not directly imported — `motor` wraps it internally and requires it at the same version. Pinning it explicitly prevents `pip` from updating it independently and breaking motor compatibility.

---

*Built with Python 3.12 · FastAPI · MongoDB · Prometheus · Grafana LGTM · OpenTelemetry · React · TypeScript*
