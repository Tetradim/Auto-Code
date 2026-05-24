"""Sentinel Edge — Main FastAPI Server"""
import asyncio
import logging
import os
import re
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import REGISTRY, generate_latest
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

# Local modules
from atr import ATRCalculator
from engine import DecisionEngine
from market_hours import MarketHours
from orb import ORBTracker
from price_fetcher import PriceFetcher
from pulse_client import PulseClient
from scheduler import EvaluationScheduler
from signals import SignalEngine
from alert_handler import router as alert_handler_router, shutdown as alert_handler_shutdown

# NEW: Resilience & persistence modules
from state_persistence import StatePersistence, IdempotencyManager
from rate_limit import RateLimiter, CCTXRateLimiter
from json_logging import setup_json_logging, get_logger
from audit import AuditTrail
from config_audit import ConfigValidator, ConfigHasher
from drift_detection import DriftDetector
from export_api import router as export_router

# Sentinel Edge analyst package
from analyst.core import SentinelEdge
from analyst.observability.otel import instrument_fastapi
from analyst.webhook import webhook_router
import analyst.core as _analyst_core

# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Demo mode - runs without external dependencies
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() in ("true", "1", "yes")

# MongoDB — client created once; motor handles pooling internally.
# In demo/standalone mode, avoid creating a lazy Motor client for an absent
# localhost MongoDB. That prevents noisy background ServerSelectionTimeout
# futures while still allowing full analysis to run without persistence.
mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
if DEMO_MODE:
    logger.info("DEMO_MODE enabled: MongoDB disabled; using in-memory/self-sovereign state")
    db = None
    _mongo_client = None
else:
    try:
        _mongo_client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        # Test connection
        _mongo_client.server_info()
        db = _mongo_client[os.environ.get("DB_NAME", "sentinel_edge")]
        logger.info(f"MongoDB connected to {mongo_url}")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise

# Global singletons populated during lifespan
scheduler: EvaluationScheduler = None
scheduler_task = None
edge: SentinelEdge = None

# NEW: Resilience module singletons (initialized in lifespan)
state_persistence: StatePersistence = None
idempotency_manager: IdempotencyManager = None
audit_trail: AuditTrail = None
drift_detector: DriftDetector = None
config_hasher: ConfigHasher = None

# ─────────────────────────────────────────────────────────────────────────────
# Request / response models
# ─────────────────────────────────────────────────────────────────────────────

_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-]{1,10}$")
_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 120
_rate_limit_buckets: Dict[str, list[float]] = {}


def _symbol(raw: str) -> str:
    """Uppercase and validate a ticker symbol.

    Accepts standard US equity formats (SPY, BRK.B, BF-B) up to 10 chars.
    Raises HTTP 422 on invalid input so the error surfaces in FastAPI's
    validation response rather than propagating as a silent 200.
    """
    s = raw.upper().strip()
    if not _SYMBOL_RE.match(s):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid symbol '{raw}'. Expected 1-10 characters: letters, digits, dot, or hyphen.",
        )
    return s


def _require_scheduler() -> EvaluationScheduler:
    """Return the running scheduler or raise HTTP 503."""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialised")
    return scheduler


def _require_price_fetcher() -> PriceFetcher:
    """Return the price fetcher or raise HTTP 503."""
    if price_fetcher is None:
        raise HTTPException(status_code=503, detail="PriceFetcher not initialised")
    return price_fetcher


def _enforce_rate_limit(request: Request) -> None:
    """Simple fixed-window in-memory rate limiter (per client IP)."""
    client = request.client.host if request.client else "unknown"
    now = time.time()
    recent = _rate_limit_buckets.setdefault(client, [])
    cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
    while recent and recent[0] < cutoff:
        recent.pop(0)
    if len(recent) >= _RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    recent.append(now)


class MetricToggles(BaseModel):
    """Per-ticker Prometheus metric enable/disable flags."""
    orb:       bool = Field(True,  description="ORB high/low/range metrics")
    atr:       bool = Field(True,  description="ATR value and volatility percentile")
    signal:    bool = Field(True,  description="Signal strength and trend direction")
    volume:    bool = Field(True,  description="Volume ratio and z-score")
    price:     bool = Field(True,  description="Current price gauge")
    breakouts: bool = Field(True,  description="ORB breakout counter")


class RiskConfig(BaseModel):
    """Per-ticker decision-risk thresholds."""
    max_consecutive_losses: int = Field(3, ge=1, le=20)
    max_drawdown_pct: float = Field(10.0, ge=0.1, le=100.0)
    trailing_stop_profit_threshold: float = Field(2.0, ge=0.1, le=50.0)


class TickerConfigBody(BaseModel):
    """Request body for PUT /api/tickers/{symbol}/config."""
    metrics: MetricToggles = Field(default_factory=MetricToggles)
    risk: RiskConfig = Field(default_factory=RiskConfig)


class BacktestRequest(BaseModel):
    """Request body for POST /api/backtest."""
    symbol: str
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    initial_capital: float = 10000.0
    slippage_pct: float = 0.05
    commission_pct: float = 0.1
    num_simulations: int = 1000
    volatility_multiplier: float = 1.0
    dry_run: bool = True


class BacktestRunRequest(BaseModel):
    """Enhanced request for POST /api/backtest/run - with strategy selection"""
    symbols: List[str] = Field(default_factory=lambda: ["AAPL"])
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    strategy: str = "sma"  # sma, rsi, breakout, rsi_with_patterns, sma_with_patterns
    initial_capital: float = 100000.0
    position_size_pct: float = 0.10
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.15
    trailing_stop: bool = True
    trailing_pct: float = 0.03
    # Strategy-specific params
    fast_period: Optional[int] = 10
    slow_period: Optional[int] = 30
    rsi_period: Optional[int] = 14
    rsi_oversold: Optional[int] = 30
    rsi_overbought: Optional[int] = 70
    breakout_lookback: Optional[int] = 20
    # Pattern mode (for pattern-enhanced strategies)
    pattern_mode: Optional[str] = "filter"


class BacktestReportRequest(BaseModel):
    """Request for GET /api/backtest/report/{run_id}"""
    run_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire all components, start background tasks, then tear down cleanly."""
    global scheduler, scheduler_task, edge
    global state_persistence, idempotency_manager, audit_trail, drift_detector, config_hasher, audit_logger

    logger.info("🚀 Starting Sentinel Edge...")
    
    if DEMO_MODE:
        logger.info("🎯 DEMO MODE enabled - will run without MongoDB")

    pulse_url = os.getenv("PULSE_API_URL", "http://localhost:8002")

    retry_queue_log_dir = os.getenv("RETRY_QUEUE_LOG_DIR", "/app/logs")
    pulse_client   = PulseClient(
        base_url=pulse_url,
        api_key=os.getenv("PULSE_API_KEY"),
        retry_queue_log_dir=retry_queue_log_dir,
    )
    price_fetcher  = PriceFetcher()
    orb_tracker    = ORBTracker()
    atr_calculator = ATRCalculator(period=14)
    signal_engine  = SignalEngine()
    decision_engine = DecisionEngine()
    market_hours   = MarketHours()

    # ── Startup Pulse probe ────────────────────────────────────────────────
    # Non-blocking: Edge starts regardless of the result. In demo mode,
    # avoid probing an expected-absent Pulse service unless explicitly enabled.
    if DEMO_MODE and os.getenv("PULSE_PROBE_IN_DEMO", "false").lower() not in ("true", "1", "yes"):
        pulse_available = False
        logger.info(
            "DEMO_MODE enabled: skipping Pulse health probe; running standalone analysis"
        )
    else:
        pulse_available = await pulse_client.check_pulse()
        if pulse_available:
            logger.info("🔗 Pulse connected — running in connected mode")
        else:
            logger.warning(
                "🔌 Pulse not available — running in standalone mode. "
                "All analysis runs normally. Decisions will be sent once Pulse comes online."
            )
    pulse_client.start_retry_drain_loop()

    # SentinelEdge orchestrator — OTel tracing, WebSocket, MongoDB change stream
    if db is not None:
        edge = SentinelEdge(db=db, pulse_url=pulse_url)
    else:
        logger.info("DEMO_MODE/no database: MongoDB change streams disabled")
        edge = SentinelEdge(db=None, pulse_url=pulse_url)

    scheduler = EvaluationScheduler(
        pulse_client=pulse_client,
        price_fetcher=price_fetcher,
        orb_tracker=orb_tracker,
        atr_calculator=atr_calculator,
        signal_engine=signal_engine,
        decision_engine=decision_engine,
        market_hours=market_hours,
        db=db,  # Can be None in demo mode
    )
    # Share the correlation engine and wire plugin discovery
    edge.set_scheduler(scheduler)

    # ── Initialize new resilience modules ─────────────────────────────────────
    global state_persistence, idempotency_manager, audit_trail, drift_detector, config_hasher
    
    # JSON structured logging for Loki
    setup_json_logging(json_output=os.getenv("LOG_JSON", "true").lower() == "true")
    audit_logger = get_logger("sentinel.audit")
    
    # State persistence (SQLite)
    state_persistence = StatePersistence()
    await state_persistence.init()
    
    # Idempotency manager for orders
    idempotency_manager = IdempotencyManager()
    await idempotency_manager.init()
    
    # Audit trail
    audit_trail = AuditTrail()
    await audit_trail.init()
    
    # Drift detection
    drift_detector = DriftDetector()
    await drift_detector.init()
    
    # Config validator (for validation endpoint)
    config_hasher = ConfigHasher()
    
    logger.info("✅ Resilience modules initialized (persistence, audit, drift detection)")

    # Expose live instance to the webhook alert handler
    _analyst_core.analyst_instance = edge

    scheduler_task = asyncio.create_task(scheduler.run())
    await edge.start_background_tasks()

    logger.info(
        "✅ Sentinel Edge started (Pulse: %s, position tracking: %s)",
        "connected" if pulse_available else "standalone",
        scheduler.position_tracker.mode_name,
    )
    yield

    # ── Graceful shutdown ──────────────────────────────────────────────────
    logger.info("🛑 Shutting down Sentinel Edge...")
    
    # Cleanup new resilience modules
    state_persistence.close()
    idempotency_manager.close()
    audit_trail.close()
    drift_detector.close()
    
    edge.stop()
    scheduler.stop()
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
    await alert_handler_shutdown()  # close alert handler HTTP session
    await pulse_client.aclose()   # release httpx connection pool
    if _mongo_client is not None:
        _mongo_client.close()
    logger.info("👋 Sentinel Edge stopped")


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Sentinel Edge",
    description="Trading analyst sidecar for Sentinel Pulse",
    version="1.0.0",
    lifespan=lifespan,
)

instrument_fastapi(app)          # OTel request spans

api_router = APIRouter(prefix="/api")


# ═══════════════════════════════════════════════════════════════════════════
# Status / health
# ═══════════════════════════════════════════════════════════════════════════

@api_router.get("/")
async def root():
    return {
        "name": "Sentinel Edge",
        "version": "1.0.0",
        "status": "running" if scheduler and scheduler.running else "stopped",
    }


@api_router.get("/health")
async def health():
    sched = _require_scheduler()
    return {
        "status":                 "healthy",
        "running":                sched.running,
        "paused":                 sched.paused,
        "active_tickers":         len(sched.active_tickers),
        "pulse_available":        sched.pulse.pulse_available,
        "position_tracking_mode": sched.position_tracker.mode_name,
    }


@api_router.get("/stats")
async def get_stats(request: Request):
    _enforce_rate_limit(request)
    sched = _require_scheduler()
    return {
        "active_tickers":      sched.active_tickers,
        "running":             sched.running,
        "paused":              sched.paused,
        "orb_levels_count":    len(sched.orb.get_all_levels()),
        "pulse_available":        sched.pulse.pulse_available,
        "pulse_circuit_state":    sched.pulse.state.name,
        "pulse_failures":         sched.pulse.failure_count,
        "retry_queue":            sched.pulse.queue_stats(),
        "position_tracking_mode": sched.position_tracker.mode_name,
        # Seconds since last successful yfinance fetch per symbol.
        # Values consistently > OHLCV_CACHE_TTL indicate stale data.
        "price_cache_age_s":      sched.prices.cache_ages(),
    }


@api_router.get("/markets")
async def get_market_status():
    sched = _require_scheduler()
    return sched.market_hours.get_all_status()


@api_router.get("/queue")
async def get_retry_queue(request: Request, limit: int = 100):
    _enforce_rate_limit(request)
    sched = _require_scheduler()
    return {
        "stats": sched.pulse.queue_stats(),
        "items": await sched.pulse.queue_snapshot(limit=limit),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Scheduler control
# ═══════════════════════════════════════════════════════════════════════════

@api_router.post("/control/pause")
async def pause_scheduler():
    _require_scheduler().pause()
    return {"message": "Scheduler paused"}


@api_router.post("/control/resume")
async def resume_scheduler():
    _require_scheduler().resume()
    return {"message": "Scheduler resumed"}


# ═══════════════════════════════════════════════════════════════════════════
# Tickers
# ═══════════════════════════════════════════════════════════════════════════

@api_router.get("/tickers")
async def get_tickers():
    """All active tickers with enriched live state."""
    sched = _require_scheduler()
    enriched = []
    for sym in sched.active_tickers:
        state = sched.ticker_state.get(sym) or {
            "symbol":        sym,
            "enabled":       True,
            "current_price": None,
            "orb_levels":    {},
            "signal_strength": 0.0,
            "trend":         "neutral",
            "atr":           None,
            "volume_ratio":  None,
            "last_decision": None,
            "confidence":    0.0,
            "last_updated":  None,
        }
        enriched.append(state)
    return {"tickers": enriched, "count": len(enriched)}


@api_router.post("/tickers/{symbol}", status_code=201)
async def add_ticker(symbol: str):
    """Add a ticker to the watch list."""
    sched = _require_scheduler()
    sym = _symbol(symbol)
    sched.add_ticker(sym)
    return {"message": f"Added {sym} to watch list"}


@api_router.delete("/tickers/{symbol}")
async def remove_ticker(symbol: str):
    """Remove a ticker from the watch list."""
    sched = _require_scheduler()
    sym = _symbol(symbol)
    if sym not in sched.active_tickers:
        raise HTTPException(status_code=404, detail=f"{sym} is not on the watch list")
    sched.remove_ticker(sym)
    return {"message": f"Removed {sym} from watch list"}


@api_router.put("/tickers/{symbol}/config")
async def update_ticker_config(symbol: str, body: TickerConfigBody = Body(...)):
    """
    Enable or disable individual Prometheus metrics for a ticker.

    The flags are persisted to MongoDB (ticker_configs collection) and applied
    immediately to the running scheduler — no restart required.
    """
    sched = _require_scheduler()
    sym = _symbol(symbol)

    metrics_dict = body.metrics.model_dump()
    risk_dict = body.risk.model_dump()

    await db.ticker_configs.update_one(
        {"symbol": sym},
        {
            "$set": {
                "symbol": sym,
                "metrics": metrics_dict,
                "risk": risk_dict,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )
    sched.ticker_configs[sym] = {"metrics": metrics_dict, "risk": risk_dict}

    return {"symbol": sym, "metrics": metrics_dict, "risk": risk_dict}


@api_router.get("/tickers/{symbol}/config")
async def get_ticker_config(symbol: str):
    """Return the metric configuration for a ticker, defaulting all flags to True."""
    sym = _symbol(symbol)

    # Exclude _id — ObjectId is not JSON-serialisable
    doc = await db.ticker_configs.find_one({"symbol": sym}, {"_id": 0})
    if doc:
        return {
            "symbol": sym,
            "metrics": doc.get("metrics", MetricToggles().model_dump()),
            "risk": doc.get("risk", RiskConfig().model_dump()),
            "updated_at": doc.get("updated_at"),
        }

    # Return defaults rather than 404 — callers can treat missing config as "all on"
    return {
        "symbol": sym,
        "metrics": MetricToggles().model_dump(),
        "risk": RiskConfig().model_dump(),
        "updated_at": None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ORB levels
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# Provider health
# ═══════════════════════════════════════════════════════════════════════════


@api_router.get("/providers/health")
async def get_providers_health(price_fetcher: PriceFetcher = Depends(_require_price_fetcher)):
    """Return health status for all price providers."""
    return price_fetcher.get_provider_health()


# ═══════════════════════════════════════════════════════════════════════════
# Backtest
# ═══════════════════════════════════════════════════════════════════════════


# Global backtest engine (initialized in lifespan)
_backtest_engine = None


def get_backtest_engine():
    """Dependency to get backtest engine."""
    return _backtest_engine


@api_router.post("/backtest")
async def run_backtest(
    request: BacktestRequest,
    price_fetcher: PriceFetcher = Depends(_require_price_fetcher),
):
    """Run historical backtest for a symbol."""
    # Lazy initialization of backtest engine
    global _backtest_engine
    if _backtest_engine is None:
        from backtest.engine import BacktestEngine
        from engine import DecisionEngine
        _backtest_engine = BacktestEngine(price_fetcher, DecisionEngine())
    
    result = await _backtest_engine.run_backtest(
        symbol=request.symbol,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        slippage_pct=request.slippage_pct,
        commission_pct=request.commission_pct,
        num_simulations=request.num_simulations,
        volatility_multiplier=request.volatility_multiplier
    )
    return result


@api_router.post("/backtest/run")
async def run_backtest_enhanced(
    request: BacktestRunRequest
):
    """Enhanced backtest with strategy selection and patterns.
    
    Use this endpoint for full backtesting with:
    - Strategy selection (sma, rsi, breakout, rsi_with_patterns, sma_with_patterns)
    - Configurable risk parameters (stop loss, take profit, trailing)
    - Pattern-enhanced strategies that filter/boost signals with chart patterns
    
    Returns run_id for fetching report later.
    """
    from backtest.engine import BacktestConfig, BacktestEngine
    from strategies.registry import create_strategy, StrategyRegistry
    
    # Create config
    config = BacktestConfig(
        symbols=request.symbols,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        position_size_pct=request.position_size_pct,
        stop_loss_pct=request.stop_loss_pct,
        take_profit_pct=request.take_profit_pct,
        trailing_stop=request.trailing_stop,
        trailing_pct=request.trailing_pct
    )
    
    # Create strategy based on selection
    strategy_params = {}
    if request.strategy == "sma":
        strategy_params = {"fast": request.fast_period, "slow": request.slow_period}
    elif request.strategy == "rsi":
        strategy_params = {
            "period": request.rsi_period,
            "oversold": request.rsi_oversold,
            "overbought": request.rsi_overbought
        }
    elif request.strategy == "breakout":
        strategy_params = {"lookback": request.breakout_lookback}
    elif request.strategy in ["rsi_with_patterns", "sma_with_patterns"]:
        strategy_params = {
            "period": request.rsi_period,
            "oversold": request.rsi_oversold,
            "overbought": request.rsi_overbought,
            "pattern_mode": request.pattern_mode
        }
    
    strategy = create_strategy(request.strategy, config, **strategy_params)
    
    # Run backtest
    engine = BacktestEngine(config, strategy)
    metrics = await engine.run()
    
    # Store result for later retrieval
    run_id = f"bt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    _backtest_runs[run_id] = {
        "config": request.dict(),
        "metrics": metrics.to_dict(),
        "trades": [
            {
                "entry": t.entry_date.isoformat() if t.entry_date else None,
                "exit": t.exit_date.isoformat() if t.exit_date else None,
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct
            } for t in metrics.trades
        ],
        "equity_curve": metrics.equity_curve,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "run_id": run_id,
        "status": "completed",
        "summary": {
            "total_return_pct": metrics.total_return_pct,
            "annualized_return": metrics.annualized_return,
            "sharpe_ratio": metrics.sharpe_ratio,
            "sortino_ratio": metrics.sortino_ratio,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "total_trades": metrics.total_trades,
            "win_rate": metrics.win_rate
        }
    }


@api_router.get("/backtest/runs")
async def list_backtest_runs():
    """List all backtest runs"""
    return {
        "runs": [
            {"run_id": k, "created_at": v.get("created_at")}
            for k, v in _backtest_runs.items()
        ]
    }


@api_router.get("/backtest/report/{run_id}")
async def get_backtest_report(run_id: str):
    """Get full backtest report with trades and equity curve"""
    run = _backtest_runs.get(run_id)
    if not run:
        return {"error": "Run not found"}
    
    return {
        "run_id": run_id,
        "config": run["config"],
        "metrics": run["metrics"],
        "trades": run["trades"],
        "equity_curve": run["equity_curve"][:100],  # Limit for display
        "created_at": run["created_at"]
    }


@api_router.get("/strategies")
async def list_strategies():
    """List all available strategies with their parameters"""
    from strategies.registry import StrategyRegistry
    return StrategyRegistry.list_strategies()


@api_router.get("/strategies/{strategy_name}")
async def get_strategy_info(strategy_name: str):
    """Get detailed info about a specific strategy"""
    from strategies.registry import StrategyRegistry
    info = StrategyRegistry.get_strategy_info(strategy_name)
    if not info:
        return {"error": "Strategy not found"}
    return info


# In-memory storage for backtest runs
_backtest_runs: Dict[str, Dict] = {}


@api_router.get("/dry-run/status")
async def get_dry_run_status():
    """Get current dry-run mode status."""
    import os
    return {"dry_run_enabled": os.getenv("DRY_RUN", "true").lower() == "true"}


# ─────────────────────────────────────────────────────────────────────────────
# Paper Trading API
# ─────────────────────────────────────────────────────────────────────────────

_paper_broker: Optional[Any] = None


def get_paper_broker() -> Any:
    """Get or create paper broker"""
    global _paper_broker
    if _paper_broker is None:
        from data_feeder import PaperBroker
        _paper_broker = PaperBroker(initial_cash=100000)
    return _paper_broker


@api_router.post("/paper/order")
async def submit_paper_order(request: Dict):
    """Submit a paper trading order"""
    broker = get_paper_broker()
    
    from data_feeder import OrderSide, OrderType
    side = OrderSide(request.get("side", "buy"))
    order_type = OrderType(request.get("order_type", "market"))
    
    order = await broker.submit_order(
        symbol=request["symbol"],
        side=side,
        quantity=request["quantity"],
        order_type=order_type,
        price=request.get("price"),
        stop_price=request.get("stop_price")
    )
    
    # Auto-execute for market orders
    if order_type == OrderType.MARKET:
        await broker.execute_order(order)
    
    return {
        "order_id": order.order_id,
        "status": order.status.value,
        "symbol": order.symbol,
        "side": order.side.value,
        "quantity": order.quantity,
        "filled_quantity": order.filled_quantity,
        "avg_fill_price": order.avg_fill_price
    }


@api_router.get("/paper/orders")
async def get_paper_orders():
    """Get all paper trading orders"""
    broker = get_paper_broker()
    orders = list(broker.orders.values())
    
    return {
        "orders": [
            {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "side": o.side.value,
                "quantity": o.quantity,
                "price": o.price,
                "status": o.status.value,
                "created_at": o.created_at.isoformat()
            }
            for o in orders
        ]
    }


@api_router.post("/paper/order/{order_id}/cancel")
async def cancel_paper_order(order_id: str):
    """Cancel a pending paper order"""
    broker = get_paper_broker()
    success = await broker.cancel_order(order_id)
    
    return {"success": success}


@api_router.get("/paper/account")
async def get_paper_account():
    """Get paper trading account state"""
    broker = get_paper_broker()
    state = await broker.get_account_state()
    
    return {
        "cash": state.cash,
        "equity": state.equity,
        "buying_power": state.buying_power,
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_cost": p.avg_cost,
                "market_value": p.market_value,
                "unrealized_pnl": p.unrealized_pnl,
                "realized_pnl": p.realized_pnl
            }
            for p in state.positions.values()
        ]
    }


@api_router.get("/paper/portfolio")
async def get_paper_portfolio():
    """Get portfolio analytics"""
    from data_feeder import PortfolioAnalytics
    
    broker = get_paper_broker()
    analytics = PortfolioAnalytics(broker)
    metrics = await analytics.calculate_metrics()
    
    return metrics


@api_router.post("/paper/price/{symbol}")
async def update_paper_price(symbol: str, price: float):
    """Update current price for a symbol (for simulation)"""
    broker = get_paper_broker()
    broker.update_price(symbol.upper(), price)
    
    return {"symbol": symbol.upper(), "price": price}


# ─────────────────────────────────────────────────────────────────────────────
# Strategy Optimization
# ─────────────────────────────────────────────────────────────────────────────


class OptimizeRequest(BaseModel):
    """Request body for POST /api/backtest/optimize."""
    symbol: str
    start_date: str
    end_date: str
    param_grid: Dict[str, List[float]]
    initial_capital: float = 10000.0


_optimizer = None


def get_strategy_optimizer():
    """Dependency to get strategy optimizer."""
    return _optimizer


@api_router.post("/backtest/optimize")
async def optimize_strategy(
    request: OptimizeRequest,
    price_fetcher: PriceFetcher = Depends(_require_price_fetcher),
):
    """Run grid search optimization over parameter combinations."""
    global _optimizer
    if _optimizer is None:
        from strategies.optimizer import StrategyOptimizer
        from engine import DecisionEngine
        _optimizer = StrategyOptimizer(
            BacktestEngine(price_fetcher, DecisionEngine())
        )
    
    result = await _optimizer.optimize(
        symbol=request.symbol,
        param_grid=request.param_grid,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
    )
    return result


@api_router.post("/emergency/kill-switch")
async def toggle_kill_switch(state: bool):
    """Toggle the global kill switch to instantly halt all trading."""
    import os
    os.environ["GLOBAL_KILL_SWITCH"] = str(state).lower()
    logger.warning(f"🚨 Kill switch set to {state}")
    return {"status": f"kill switch set to {state}", "kill_switch_active": state}


@api_router.post("/test/pulse-command")
async def test_pulse_command(command: dict):
    """For testing: simulate Pulse sending a command to Edge via MongoDB.
    
    This inserts a command into the shared `commands` collection, which
    Edge's change stream listener will pick up and process.
    
    Example curl:
        curl -X POST http://localhost:8000/api/test/pulse-command \
          -H "Content-Type: application/json" \
          -d '{
            "command_type": "ORDER_FILLED",
            "symbol": "NVDA",
            "order_id": "test_001",
            "fill_price": 142.35,
            "quantity": 50,
            "side": "BUY"
          }'
    """
    from datetime import datetime
    
    global db
    await db.commands.insert_one({
        **command,
        "timestamp": datetime.utcnow()
    })
    logger.info(f"📤 Test command inserted: {command.get('command_type')} | {command.get('symbol')}")
    return {"status": "sent", "type": command.get("command_type")}


# ====================== Pulse Integration Endpoints ======================

@api_router.get("/pulse/health")
async def get_pulse_health():
    """Get Pulse connection health status.
    
    Returns circuit breaker state, failure count, retry queue status.
    """
    sched = _require_scheduler()
    if hasattr(sched, 'pulse'):
        return await sched.pulse.health_check_detailed()
    return {"error": "Pulse not configured"}


@api_router.get("/pulse/status")
async def get_pulse_status():
    """Get Pulse availability and connection state."""
    sched = _require_scheduler()
    if hasattr(sched, 'pulse'):
        return {
            "available": sched.pulse.pulse_available,
            "circuit_state": sched.pulse.state.name,
            "base_url": sched.pulse.base_url,
        }
    return {"error": "Pulse not configured"}


@api_router.get("/pulse/positions")
async def get_pulse_positions():
    """Get all positions from DecisionEngine (synced from Pulse)."""
    sched = _require_scheduler()
    if hasattr(sched, 'decisions'):
        return sched.decisions.get_all_positions()
    return {}


@api_router.get("/pulse/positions/{symbol}")
async def get_pulse_position(symbol: str):
    """Get position for a specific symbol from DecisionEngine."""
    sched = _require_scheduler()
    if hasattr(sched, 'decisions'):
        position = sched.decisions.get_position(symbol)
        if position:
            return position
        return {"status": "no_position", "symbol": symbol}
    return {"error": "Decision engine not configured"}


@api_router.get("/pulse/queue")
async def get_pulse_queue():
    """Get retry queue status for failed decisions."""
    sched = _require_scheduler()
    if hasattr(sched, 'pulse'):
        return sched.pulse.queue_stats()
    return {"error": "Pulse not configured"}


@api_router.get("/pulse/account")
async def get_pulse_account():
    """Get account status from Pulse (buying power, equity, etc.)."""
    sched = _require_scheduler()
    if hasattr(sched, 'pulse'):
        account = await sched.pulse.get_account_status()
        if account:
            return account
        return {"status": "unavailable"}
    return {"error": "Pulse not configured"}


@api_router.post("/pulse/emergency-exit/{symbol}")
async def pulse_emergency_exit(symbol: str, reason: str = "Manual trigger"):
    """Trigger emergency exit for a symbol via Pulse."""
    sched = _require_scheduler()
    if hasattr(sched, 'pulse'):
        result = await sched.pulse.send_emergency_exit(symbol.upper(), reason)
        return {"status": "sent" if result else "failed", "symbol": symbol, "reason": reason}
    return {"error": "Pulse not configured"}


@api_router.post("/pulse/trailing-stop/{symbol}")
async def pulse_enable_trailing(symbol: str, percent: float = 1.5):
    """Enable trailing stop for a symbol via Pulse."""
    sched = _require_scheduler()
    if hasattr(sched, 'pulse'):
        result = await sched.pulse.enable_trailing_stop(symbol.upper(), percent)
        return {"status": "sent" if result else "failed", "symbol": symbol, "percent": percent}
    return {"error": "Pulse not configured"}


@api_router.get("/orb/{symbol}")
async def get_orb_levels(symbol: str):
    """
    Return ORB high/low/range for every tracked timeframe (5m, 15m, 30m).

    Fields per timeframe
    ────────────────────
    high        : locked opening range high
    low         : locked opening range low
    range_width : high − low
    locked      : True once the opening window has elapsed
    is_valid    : True when both high and low have been set
    date        : trading date the levels were established (YYYY-MM-DD)
    start_time  : datetime the tracker started collecting for this timeframe
    lock_time   : datetime the range was locked (null until locked)
    """
    sched = _require_scheduler()
    sym = _symbol(symbol)

    levels = sched.orb.get_levels(sym)
    if not levels:
        raise HTTPException(status_code=404, detail=f"No ORB data for {sym} — market may be closed or ticker not yet evaluated")

    result = {}
    for timeframe, level in levels.items():
        result[f"{timeframe}m"] = {
            "high":        level.high if level.is_valid else None,
            "low":         level.low  if level.is_valid else None,
            "range_width": level.range_width,
            "locked":      level.locked,
            "is_valid":    level.is_valid,
            "date":        level.date,
            "start_time":  level.start_time.isoformat() if level.start_time else None,
            "lock_time":   level.lock_time.isoformat()  if level.lock_time  else None,
        }

    return {"symbol": sym, "orb_levels": result}


# ═══════════════════════════════════════════════════════════════════════════
# Decisions & correlation
# ═══════════════════════════════════════════════════════════════════════════

@api_router.get("/decisions")
async def get_decisions():
    """Last 50 non-HOLD trading decisions (decision feed)."""
    sched = _require_scheduler()
    return {
        "decisions": sched.recent_decisions[:50],
        "count":     len(sched.recent_decisions),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Config validation
# ═══════════════════════════════════════════════════════════════════════════

@api_router.post("/config/validate")
async def validate_config(config: dict = Body(...)):
    """Validate trading config and return hash for audit."""
    validator = ConfigValidator()
    issues = validator.validate(config)
    
    # Generate config hash
    config_hash = config_hasher.hash_config(config) if config_hasher else None
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "config_hash": config_hash,
    }


@api_router.get("/config/hash")
async def get_config_hash():
    """Get current config hash for audit trail."""
    if not config_hasher:
        return {"error": "Config hasher not initialized"}
    
    # Get config from scheduler or edge
    try:
        current_config = getattr(scheduler, 'config', {})
        config_hash = config_hasher.hash_config(current_config)
        return {"config_hash": config_hash}
    except Exception as e:
        return {"error": str(e)}


@api_router.get("/correlation")
async def get_correlation():
    """Correlation cluster list, market breadth summary, and latest cluster."""
    sched = _require_scheduler()
    return {
        "clusters": sched.correlation.get_recent_clusters(),
        "breadth":  sched.correlation.get_current_breadth(),
        "latest":   sched.correlation.get_latest_cluster(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Command Bus Test Endpoints (for testing Pulse → Edge communication)
# ═══════════════════════════════════════════════════════════════════════════

@api_router.post("/test/send-command")
async def test_send_command(command: dict = Body(...)):
    """Send a command to Edge via the Command Bus.
    
    This endpoint allows Pulse (or you) to simulate sending commands
    that would normally come via MongoDB Change Stream.
    
    Example - send ORDER_FILLED:
    ```json
    {
      "command_type": "ORDER_FILLED",
      "symbol": "BTCUSDT",
      "order_id": "se-order-123",
      "fill_price": 42000.0,
      "quantity": 0.1,
      "side": "BUY",
      "pnl_realized": 50.0
    }
    ```
    
    Example - send POSITION_UPDATE:
    ```json
    {
      "command_type": "POSITION_UPDATE",
      "symbol": "BTCUSDT",
      "position_size": 0.5,
      "entry_price": 41900.0,
      "current_pnl_pct": 2.38,
      "current_pnl_dollar": 50.0
    }
    ```
    """
    from datetime import datetime, timezone
    from shared.commands import COMMANDS_COLLECTION
    
    # Add timestamp if not provided
    if "timestamp" not in command:
        command["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    # Insert into commands collection (triggers change stream)
    result = await db[COMMANDS_COLLECTION].insert_one(command)
    
    return {
        "status": "command sent to Edge via Change Stream",
        "command_type": command.get("command_type"),
        "symbol": command.get("symbol"),
        "inserted_id": str(result.inserted_id),
    }


@api_router.get("/test/commands")
async def list_commands(limit: int = 10):
    """List recent commands in the Command Bus."""
    from shared.commands import COMMANDS_COLLECTION
    
    commands = await db[COMMANDS_COLLECTION].find() \
        .sort("timestamp", -1) \
        .limit(limit) \
        .to_list(limit)
    
    return {
        "count": len(commands),
        "commands": commands,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Prometheus scrape endpoint (outside the /api prefix)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
async def metrics():
    """Prometheus text-format scrape endpoint."""
    return generate_latest(REGISTRY).decode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Router registration
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(api_router)

# Alertmanager webhook receiver — /api/webhook/alert, /api/webhook/health
app.include_router(webhook_router, prefix="/api")

# Prometheus Alertmanager webhook receiver — /alerts
app.include_router(alert_handler_router, prefix="")

# Trade export endpoints — /export/trades, /export/pnl
app.include_router(export_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Frontend Static Files
# ─────────────────────────────────────────────────────────────────────────────

# Get frontend build directories for source, installed, and PyInstaller layouts.
root_dir = Path(__file__).parent.parent
if not root_dir.exists():
    root_dir = Path.cwd()

exe_dir = Path(sys.executable).parent if getattr(sys, "executable", None) else root_dir
bundle_dir = Path(getattr(sys, "_MEIPASS", exe_dir))

frontend_dist = root_dir / "frontend" / "dist"
frontend_src = root_dir / "frontend" / "public"
backend_static = root_dir / "backend" / "static"
installed_static = exe_dir / "static"
bundled_static = bundle_dir / "static"

static_candidates = [
    backend_static,
    installed_static,
    bundled_static,
    frontend_dist,
    frontend_src,
]
actual_static = next((path for path in static_candidates if path.exists()), None)

print(f"Root dir: {root_dir}")
print(f"Exe dir: {exe_dir}")
print(f"Bundle dir: {bundle_dir}")
print(f"Frontend dist exists: {frontend_dist.exists()}")
print(f"Frontend src exists: {frontend_src.exists()}")
print(f"Backend static exists: {backend_static.exists()}")
print(f"Installed static exists: {installed_static.exists()}")
print(f"Bundled static exists: {bundled_static.exists()}")
print(f"Actual static path: {actual_static}")

frontend_mounted = False

if actual_static is not None:
    app.mount("/", StaticFiles(directory=str(actual_static), html=True), name="static")
    print(f"Frontend mounted from {actual_static}")
    frontend_mounted = True
else:
    print("WARNING: No frontend found - attempting to build automatically...")
    import subprocess
    import shutil
    import sys
    
    # Try to find npm - check PATH and common locations
    npm_cmd = None
    
    # First try shutil.which (works on Linux/Mac)
    npm_path = shutil.which("npm")
    if npm_path:
        npm_cmd = "npm"
    else:
        # On Windows, try npm.cmd or check common install locations
        if sys.platform == "win32":
            # Try npm.cmd
            npm_path = shutil.which("npm.cmd")
            if npm_path:
                npm_cmd = "npm.cmd"
            else:
                # Check Node.js common install paths
                node_paths = [
                    Path(os.environ.get("ProgramFiles", "C:\\Program Files") + "\\nodejs"),
                    Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)") + "\\nodejs"),
                    Path(os.environ.get("LOCALAPPDATA", "") + "\\Programs\\nodejs"),
                ]
                for node_path in node_paths:
                    if node_path.exists():
                        npm_candidate = node_path / "npm.cmd"
                        if npm_candidate.exists():
                            npm_cmd = str(npm_candidate)
                            break
    
    if npm_cmd:
        print(f"Found npm: {npm_cmd}")
        # Try to find frontend folder - check multiple locations
        frontend_dir = None
        possible_frontend_dirs = [
            root_dir / "frontend",
            exe_dir / "frontend",
            Path.cwd() / "frontend",
        ]
        for dir_check in possible_frontend_dirs:
            if dir_check.exists():
                pkg_check = dir_check / "package.json"
                if pkg_check.exists():
                    frontend_dir = dir_check
                    break
        
        if frontend_dir:
            try:
                print(f"Building frontend from {frontend_dir}")
                # Install dependencies using shell=True for Windows compatibility
                install_result = subprocess.run(
                    f'"{npm_cmd}" install',
                    cwd=str(frontend_dir),
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                print(f"npm install result: {install_result.returncode}")
                
                if install_result.returncode == 0:
                    # Build the frontend
                    build_result = subprocess.run(
                        f'"{npm_cmd}" run build',
                        cwd=str(frontend_dir),
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    print(f"npm build result: {build_result.returncode}")
                    
                    # Build outputs to frontend/dist - copy to exe folder
                    built_dist = frontend_dir / "dist"
                    if build_result.returncode == 0 and built_dist.exists():
                        # Copy to exe directory for persistence
                        exe_static = exe_dir / "static"
                        exe_static.mkdir(exist_ok=True)
                        import shutil as sh
                        # Copy files
                        for f in built_dist.iterdir():
                            dest = exe_static / f.name
                            if f.is_dir():
                                sh.copytree(f, dest, dirs_exist_ok=True)
                            else:
                                sh.copy2(f, dest)
                        app.mount("/", StaticFiles(directory=str(exe_static), html=True), name="frontend")
                        print(f"Frontend built and mounted from {exe_static}")
                        frontend_mounted = True
                    else:
                        print(f"Frontend build output: {build_result.stdout}")
                        print(f"Frontend build error: {build_result.stderr}")
                else:
                    print(f"npm install output: {install_result.stdout}")
                    print(f"npm install error: {install_result.stderr}")
            except Exception as e:
                print(f"Auto-build error: {e}")
    
    if not frontend_mounted:
        print("ERROR: No frontend found!")
        print("=" * 50)
        print("To fix this, either:")
        print("  1. Install Node.js from https://nodejs.org and restart Sentinel Edge")
        print("  2. OR copy frontend/dist to backend/static manually")
        print("  3. OR download the latest SentinelEdge-Setup.exe from GitHub releases")
        print("=" * 50)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
