# Sentinel Edge

**Production-Ready Trading Analyst Sidecar for Sentinel Pulse**

Sentinel Edge is a comprehensive trading analysis system that monitors Opening Range Breakouts (ORB), calculates ATR-based volatility, generates bullish/bearish signals, and makes intelligent trading decisions. It exposes 30+ Prometheus metrics and includes 4 auto-provisioned Grafana dashboards.

## 🌟 Features

### Backend (Python FastAPI)
- **Multi-timeframe ORB Detection** (5m, 15m, 30m)
- **ATR Calculation** for dynamic trailing stops
- **Signal Analysis** with volume confirmation
- **Decision Engine** with risk management
- **Circuit Breaker Pattern** for API resilience
- **Market Hours Tracking** for 7 global exchanges
- **30+ Prometheus Metrics** exposed at `/metrics`
- **Real-time Price Data** via yfinance
- **MongoDB State Persistence**

### Frontend (TypeScript + React)
- **4 Comprehensive Dashboards:**
  1. Trading Overview - Ticker cards with ORB, signals, ATR
  2. Broker Health - Circuit breaker monitoring
  3. P&L Tracking - Realized/unrealized P&L analysis
  4. Market Coverage - Global market status
- **Card-based Layouts** with glassmorphism design
- **Real-time Data** refresh every 5 seconds
- **Beautiful Charts** using Recharts
- **Framer Motion** animations

### Infrastructure
- **Docker Compose** for full stack orchestration
- **Prometheus** for metrics collection
- **Grafana** with 4 auto-provisioned dashboards
- **12 Alert Rules** for critical events
- **Alertmanager** for notification routing

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd sentinel-edge

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f sentinel-edge
```

**Services will be available at:**
- Sentinel Edge Backend: http://localhost:8001
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/sentinel123)
- Alertmanager: http://localhost:9093

### Manual Setup

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001
```

#### Frontend
```bash
cd frontend
yarn install
yarn start
```

## 📊 Dashboards

### 1. Trading Overview
- Engine state and active ticker count
- ORB breakout activity charts
- Signal strength by ticker
- Ticker summary table with live prices
- Consecutive loss streak monitoring

### 2. Broker Health
- Circuit breaker state (CLOSED/HALF_OPEN/OPEN)
- API failure rate gauges
- Success vs failure rate charts
- API latency heatmaps and percentiles (p50, p95, p99)

### 3. P&L Tracking
- Total realized and unrealized P&L
- Drawdown monitoring (current and max)
- P&L charts per ticker
- Bar gauges showing individual ticker performance

### 4. Market Coverage
- Status for 7 global markets (NYSE, NASDAQ, LSE, TSE, HKEX, SSE, BSE)
- Lunch break indicators for Asian markets
- Minutes-to-close countdown
- 24-hour market session timeline

## 🔔 Alert Rules

Sentinel Edge includes 12 pre-configured alert rules:

1. **CircuitBreakerOpen** - Critical when circuit breaker opens
2. **CircuitBreakerHalfOpen** - Warning during recovery testing
3. **AutoStopTriggered** - Critical when emergency exit is triggered
4. **ConsecutiveLossesWarning** - Warning at 3 consecutive losses
5. **ConsecutiveLossesCritical** - Critical at 5 consecutive losses
6. **BrokerHighFailureRate** - Warning at >20% failure rate
7. **BrokerCriticalFailureRate** - Critical at >50% failure rate
8. **EngineNotRunning** - Critical when scheduler stops
9. **DrawdownWarning** - Warning at >5% drawdown
10. **DrawdownCritical** - Critical at >10% drawdown
11. **OrbBreakoutDetected** - Info alert for all breakouts
12. **SidecarDown** - Critical when service is unavailable

## 🎯 API Endpoints

### Health & Status
- `GET /api/health` - Health check
- `GET /api/stats` - System statistics
- `GET /metrics` - Prometheus metrics

### Tickers
- `GET /api/tickers` - List active tickers
- `POST /api/tickers/{symbol}` - Add ticker
- `DELETE /api/tickers/{symbol}` - Remove ticker

### ORB Data
- `GET /api/orb/{symbol}` - Get ORB levels for symbol

### Markets
- `GET /api/markets` - Global market status

### Control
- `POST /api/control/pause` - Pause scheduler
- `POST /api/control/resume` - Resume scheduler

## 📈 Key Metrics

### ORB Metrics
- `edge_orb_breakouts_total` - Total breakouts by symbol/direction/timeframe
- `edge_orb_high` / `edge_orb_low` - ORB levels
- `edge_orb_range_width` - ORB range width

### Signal Metrics
- `edge_signal_strength` - Bullish/bearish strength (-10 to +10)
- `edge_trend_direction` - 1=bullish, -1=bearish, 0=neutral
- `edge_volume_ratio` - Current vs average volume
- `edge_atr_value` - Average True Range

### Decision Metrics
- `edge_decision_total` - Decisions by type
- `edge_consecutive_losses` - Loss streaks
- `edge_win_rate` - Win rate percentage

### Broker Metrics
- `broker_circuit_state` - Circuit breaker state
- `broker_failure_rate` - API failure percentage
- `edge_api_calls_total` - API calls by status
- `edge_api_latency_seconds` - API latency histogram

### Market Metrics
- `market_open_status` - Market open/closed status
- `market_lunch_break` - Lunch break flag
- `market_minutes_to_close` - Time until close

## 🔧 Configuration

### Environment Variables

**Backend (.env):**
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=sentinel_edge
PULSE_API_URL=http://localhost:8002
PULSE_API_KEY=your_api_key
CORS_ORIGINS=*
```

**Frontend (.env):**
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

## 🏗️ Architecture

```
┌─────────────────────┐
│  Set-Trader Bot     │
│  (Pulse)            │
└──────────┬──────────┘
           │ REST API
           ▼
┌─────────────────────┐
│  Sentinel Edge      │
│  (FastAPI Backend)  │
├─────────────────────┤
│ • ORB Tracker       │
│ • ATR Calculator    │
│ • Signal Engine     │
│ • Decision Engine   │
│ • Metrics Exporter  │
└──────────┬──────────┘
           │ /metrics
           ▼
┌─────────────────────┐      ┌──────────────────┐
│   Prometheus        │──────│    Grafana       │
│  (Metrics Storage)  │      │  (Dashboards)    │
└─────────────────────┘      └──────────────────┘
```

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

## 📧 Support

For issues or questions, please open a GitHub issue.
