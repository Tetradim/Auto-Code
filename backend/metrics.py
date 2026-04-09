"""Prometheus Metrics Definitions for Sentinel Edge"""
from prometheus_client import Counter, Gauge, Histogram, Info

# ═══════════════════════════════════════════════════════════
# ORB METRICS
# ═══════════════════════════════════════════════════════════

edge_orb_breakouts_total = Counter(
    "edge_orb_breakouts_total",
    "Total ORB breakouts detected",
    ["symbol", "direction", "timeframe"]
)

edge_orb_high = Gauge(
    "edge_orb_high",
    "ORB high level for symbol",
    ["symbol", "timeframe"]
)

edge_orb_low = Gauge(
    "edge_orb_low",
    "ORB low level for symbol",
    ["symbol", "timeframe"]
)

edge_orb_range_width = Gauge(
    "edge_orb_range_width",
    "ORB range width (high - low)",
    ["symbol", "timeframe"]
)

# ═══════════════════════════════════════════════════════════
# SIGNAL METRICS
# ═══════════════════════════════════════════════════════════

edge_signal_strength = Gauge(
    "edge_signal_strength",
    "Bullish/Bearish strength score (-10 to +10)",
    ["symbol"]
)

edge_trend_direction = Gauge(
    "edge_trend_direction",
    "Trend direction: 1=bullish, -1=bearish, 0=neutral",
    ["symbol"]
)

edge_volume_ratio = Gauge(
    "edge_volume_ratio",
    "Current volume vs average volume ratio",
    ["symbol"]
)

edge_atr_value = Gauge(
    "edge_atr_value",
    "Average True Range (ATR) value",
    ["symbol", "period"]
)

edge_volatility_percentile = Gauge(
    "edge_volatility_percentile",
    "Volatility percentile (0-100)",
    ["symbol"]
)

# ═══════════════════════════════════════════════════════════
# DECISION METRICS
# ═══════════════════════════════════════════════════════════

edge_decision_total = Counter(
    "edge_decision_total",
    "Total decisions made by type",
    ["symbol", "decision"]
)

edge_active_positions = Gauge(
    "edge_active_positions",
    "Number of active positions",
    ["symbol"]
)

edge_consecutive_losses = Gauge(
    "edge_consecutive_losses",
    "Consecutive loss streak per ticker",
    ["symbol"]
)

edge_win_rate = Gauge(
    "edge_win_rate",
    "Win rate percentage per ticker",
    ["symbol"]
)

# ═══════════════════════════════════════════════════════════
# PULSE API METRICS
# ═══════════════════════════════════════════════════════════

edge_api_calls_total = Counter(
    "edge_api_calls_total",
    "Total API calls to Pulse",
    ["endpoint", "status"]
)

edge_api_latency = Histogram(
    "edge_api_latency_seconds",
    "API call latency to Pulse",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

broker_circuit_state = Gauge(
    "broker_circuit_state",
    "Circuit breaker state: 0=CLOSED, 1=HALF_OPEN, 2=OPEN",
    ["broker_id"]
)

broker_failure_rate = Gauge(
    "broker_failure_rate",
    "API failure rate percentage",
    ["broker_id"]
)

# ═══════════════════════════════════════════════════════════
# P&L METRICS
# ═══════════════════════════════════════════════════════════

ticker_realized_pnl_total = Gauge(
    "ticker_realized_pnl_total",
    "Realized P&L per ticker",
    ["symbol"]
)

ticker_unrealized_pnl = Gauge(
    "ticker_unrealized_pnl",
    "Unrealized P&L per ticker",
    ["symbol"]
)

ticker_drawdown_percent = Gauge(
    "ticker_drawdown_percent",
    "Current drawdown percentage from peak",
    ["symbol"]
)

ticker_max_drawdown_percent = Gauge(
    "ticker_max_drawdown_percent",
    "Maximum drawdown percentage",
    ["symbol"]
)

total_portfolio_value = Gauge(
    "total_portfolio_value",
    "Total portfolio value"
)

# ═══════════════════════════════════════════════════════════
# ENGINE METRICS
# ═══════════════════════════════════════════════════════════

edge_eval_duration = Histogram(
    "edge_eval_duration_seconds",
    "Evaluation duration per ticker",
    ["symbol"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

edge_engine_running = Gauge(
    "edge_engine_running",
    "Engine running status: 0=stopped, 1=running"
)

edge_engine_paused = Gauge(
    "edge_engine_paused",
    "Engine paused status: 0=active, 1=paused"
)

ticker_evaluation_total = Counter(
    "ticker_evaluation_total",
    "Total ticker evaluations",
    ["symbol"]
)

ticker_active_count = Gauge(
    "ticker_active_count",
    "Number of active tickers being tracked"
)

# ═══════════════════════════════════════════════════════════
# PRICE FEED METRICS
# ═══════════════════════════════════════════════════════════

price_fetch_latency = Histogram(
    "price_fetch_latency_seconds",
    "Price data fetch latency",
    ["source"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

price_fetch_failures_total = Counter(
    "price_fetch_failures_total",
    "Total price fetch failures",
    ["symbol", "source"]
)

current_price = Gauge(
    "current_price",
    "Current price per ticker",
    ["symbol"]
)

# ═══════════════════════════════════════════════════════════
# MARKET COVERAGE METRICS
# ═══════════════════════════════════════════════════════════

market_open_status = Gauge(
    "market_open_status",
    "Market open status: 0=closed, 1=open",
    ["market"]
)

market_lunch_break = Gauge(
    "market_lunch_break",
    "Market in lunch break: 0=no, 1=yes",
    ["market"]
)

market_minutes_to_close = Gauge(
    "market_minutes_to_close",
    "Minutes remaining until market close",
    ["market"]
)

# ═══════════════════════════════════════════════════════════
# CORRELATION METRICS
# ═══════════════════════════════════════════════════════════

correlation_clusters_total = Counter(
    "analyst_correlation_clusters_total",
    "Detected correlation clusters",
    ["direction", "strength"]
)

# ═══════════════════════════════════════════════════════════
# SYSTEM INFO
# ═══════════════════════════════════════════════════════════

edge_info = Info(
    "edge_info",
    "Sentinel Edge system information"
)

# Initialize system info
edge_info.info({
    'version': '1.0.0',
    'name': 'Sentinel Edge',
    'description': 'Trading analyst sidecar for Sentinel Pulse'
})
