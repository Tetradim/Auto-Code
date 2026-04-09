# Sentinel Edge

**Production-Ready Trading Analyst Sidecar for Sentinel Pulse**

Sentinel Edge is a comprehensive trading analysis system that monitors Opening Range Breakouts (ORB), calculates ATR-based volatility, generates bullish/bearish signals, makes intelligent trading decisions, and exposes full observability via the Grafana LGTM stack.

---

## Architecture & Communication

**Sentinel Edge** acts as the **Intelligence & Risk Layer** for **Sentinel Pulse**.

### Communication Channels (Robust & Redundant)

| Channel | Purpose | Latency | Use Case |
|---|---|---|---|
| WebSocket | Real-time signals & confirmations | <100 ms | Primary |
| Mongo Change Streams | Persistent state & commands | ~200 ms | Reliable fallback |
| REST (circuit breaker) | One-off overrides & admin actions | 300–800 ms | Fallback |
| Prometheus | Observability only | — | Metrics |
| OpenTelemetry (gRPC) | Distributed tracing → Tempo | — | Debugging |

### System Diagram

```
  ┌──────────────────────────────────────────────────────┐
  │                   Sentinel Edge                       │
  │                                                      │
  │  ┌─────────────┐   ┌──────────────────────────────┐  │
  │  │  analyst/   │   │  EvaluationScheduler          │  │
  │  │  core.py    │◄──│  (ORB + ATR + Signal + Eng)  │  │
  │  │  SentinelEdge    └──────────────────────────────┘  │
  │  └──────┬──────┘                                     │
  │         │ WebSocket / REST / Change Streams           │
  │  ┌──────▼─────────────────────────────────────────┐  │
  │  │       analyst/correlation/engine.py             │  │
  │  │       CorrelationEngine  (120 s window)         │  │
  │  │       ≥3 symbols same direction → cluster       │  │
  │  │       BEARISH + strength>0.65 → Pulse override  │  │
  │  └─────────────────────────────────────────────────┘  │
  │                                                      │
  │  Prometheus /metrics (:8001)  OTel gRPC (:4317)     │
  └──────────────────────────────────────────────────────┘
                          │  REST/WS
              ┌───────────▼───────────┐
              │     Sentinel Pulse    │
              │   (execution engine)  │
              └───────────────────────┘
```

---

## Key Features

### Backend (Python FastAPI)
- **Multi-timeframe ORB Detection** — 5 m, 15 m, 30 m
- **ATR Calculation** — dynamic trailing stop sizing
- **Signal Analysis** — volume confirmation, price momentum, volatility adjustment
- **Decision Engine** — BUY / STOP / TRAILING / TIGHTEN / EXIT with risk guards
- **Circuit Breaker Pattern** — Pulse API resilience
- **Market Hours Tracking** — 7 global exchanges
- **40+ Prometheus Metrics** at `/metrics`
- **MongoDB State Persistence** — ORB levels survive restarts
- **Correlation Detection** — 2-min rolling window, cluster alerts, auto Pulse override
- **Decision Feed** — last 50 non-HOLD decisions exposed at `/api/decisions`

### analyst/ Package
| Module | Role |
|---|---|
| `analyst/core.py` | `SentinelEdge` orchestrator — OTel + WS + change stream |
| `analyst/correlation/engine.py` | Full correlation engine (canonical) |
| `analyst/signals/base.py` | `Signal` dataclass, `BaseSignal` ABC, `SignalConfig` |
| `analyst/signals/custom/` | Drop-in strategy plugins |
| `analyst/exporters/prometheus.py` | Pluggable Prometheus exporter |
| `analyst/observability/otel.py` | gRPC OTLP, HTTPXClientInstrumentor, AsyncioInstrumentor |

### Frontend (TypeScript + React + Vite)
- **4 Dashboards:** Trading Overview · Broker Health · P&L Tracking · Market Coverage
- **Decision Feed** — live log of BUY / STOP / EXIT decisions
- **Market Breadth panel** — bull/bear % bar + correlation cluster card
- **Add / Remove Tickers** — live ticker management
- **Mock Data Mode** — simulated drifting prices for demo/dev

### Observability (LGTM Stack)
| Component | Port | Purpose |
|---|---|---|
| Prometheus | 9090 | Metrics collection |
| Grafana | 3001 | Dashboards + alerts |
| Loki | 3100 | Log aggregation |
| Tempo | 3200 / 4317 | Distributed traces |
| Promtail | — | Log shipper |
| AlertManager | 9093 | Alert routing |

---

## Grafana Dashboards (Auto-Provisioned)

| Dashboard | UID | Panels |
|---|---|---|
| Analyst Overview | `se-analyst-overview` | 16 — engine state, ORB rate, ATR heatmap, signal strength, ticker table, latency |
| Correlation Breadth | `se-correlation-breadth` | 8 — cluster table, bull/bear pie, detection rate, breadth timeseries |
| Trading Overview | `trading-overview` | Existing 8-panel ORB + signal overview |
| Broker Health | `broker-health` | Circuit breaker metrics |
| P&L Tracking | `pnl-tracking` | Realized / unrealized P&L |
| Market Coverage | `market-coverage` | Global market hours |

---

## Prometheus Alert Rules

| Alert | Severity | Condition |
|---|---|---|
| `EdgeEngineDown` | critical | engine not running > 1 m |
| `EdgeEnginePaused` | warning | engine paused > 10 m |
| `HighConsecutiveLosses` | warning | consecutive losses > 3 |
| `LowWinRate` | warning | win rate < 40 % for 30 m |
| `SlowEvaluation` | warning | eval p99 > 1 s for 3 m |
| `PriceFetchFailures` | warning | fetch failures > 0.5/s |
| `CorrelationBearishCluster` | warning | bearish cluster detected |
| `HighDrawdown` | critical | drawdown > 8 % |
| `StrongCorrelationCluster` | warning | high-strength clusters > 1 |
| `BearishClusterOverride` | critical | high-strength bearish cluster (Pulse override sent) |
| `HighPulseOverrideRate` | warning | override rate > 0.5/s |

---

## API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/tickers` | Enriched live ticker data |
| POST | `/api/tickers/{symbol}` | Add ticker |
| DELETE | `/api/tickers/{symbol}` | Remove ticker |
| GET/PUT | `/api/tickers/{symbol}/config` | Prometheus metric toggles |
| GET | `/api/stats` | System stats |
| GET | `/api/orb/{symbol}` | ORB levels for symbol |
| GET | `/api/correlation` | Correlation clusters + breadth + latest |
| GET | `/api/decisions` | Last 50 non-HOLD decisions |
| GET | `/api/markets` | Global market open/closed status |
| POST | `/api/control/pause` | Pause scheduler |
| POST | `/api/control/resume` | Resume scheduler |
| GET | `/metrics` | Prometheus scrape endpoint |

---

## Pluggable Signal Strategies

Drop a subclass of `BaseSignal` into `analyst/signals/custom/` and it will be auto-discovered:

```python
# analyst/signals/custom/vwap_breakout.py
from analyst.signals.base import BaseSignal, Signal
from typing import Dict, Any, Optional

class VWAPBreakout(BaseSignal):
    name = "vwap_breakout"
    description = "VWAP cross with volume confirmation"
    tags = ["vwap", "intraday", "momentum"]

    async def generate(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Signal]:
        price = market_data.get("price", 0)
        vwap  = market_data.get("vwap", 0)
        vol   = market_data.get("volume_ratio", 1.0)

        if price > vwap * 1.005 and vol > 1.5:
            return Signal.buy(symbol, confidence=0.8,
                              reason="Price above VWAP with high volume",
                              timeframe="5m", price=price)
        return None
```

---

## MongoDB Change Streams — Command Bus

Insert a document into the `analyst_commands` collection to send commands without a REST call:

```js
// Pause the scheduler
db.analyst_commands.insertOne({ command: "pause", source: "dashboard" })

// Resume
db.analyst_commands.insertOne({ command: "resume" })

// Add ticker
db.analyst_commands.insertOne({ command: "add_ticker", symbol: "TSLA" })

// Manual Pulse override
db.analyst_commands.insertOne({ command: "override", action: "tighten_trailing_global" })
```

> **Note:** Requires MongoDB replica set (`--replSet rs0`).  
> The `mongodb-init` service in `docker-compose.yml` handles this automatically.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MONGO_URL` | required | MongoDB connection string |
| `DB_NAME` | required | MongoDB database name |
| `PULSE_API_URL` | `http://localhost:8002` | Pulse service URL |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://tempo:4317` | Tempo gRPC endpoint |
| `OTEL_SERVICE_NAME` | `sentinel-edge` | OTel service name |
| `ANALYST_START_METRICS_SERVER` | `false` | Expose dedicated `:8002/metrics` |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

---

## Quick Start (Docker)

```bash
git clone https://github.com/your-org/sentinel-edge
cd sentinel-edge
docker compose up -d

# Services
open http://localhost:3001   # Grafana  (admin / sentinel123)
open http://localhost:9090   # Prometheus
open http://localhost:3200   # Tempo UI
```
