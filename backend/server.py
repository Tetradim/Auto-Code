"""Sentinel Edge — Main FastAPI Server"""
import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Body, HTTPException
from fastapi.responses import PlainTextResponse
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

# MongoDB — client created once; motor handles pooling internally
mongo_url = os.environ["MONGO_URL"]
_mongo_client = AsyncIOMotorClient(mongo_url)
db = _mongo_client[os.environ["DB_NAME"]]

# Global singletons populated during lifespan
scheduler: EvaluationScheduler = None
scheduler_task = None
edge: SentinelEdge = None

# ─────────────────────────────────────────────────────────────────────────────
# Request / response models
# ─────────────────────────────────────────────────────────────────────────────

_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-]{1,10}$")


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


class MetricToggles(BaseModel):
    """Per-ticker Prometheus metric enable/disable flags."""
    orb:       bool = Field(True,  description="ORB high/low/range metrics")
    atr:       bool = Field(True,  description="ATR value and volatility percentile")
    signal:    bool = Field(True,  description="Signal strength and trend direction")
    volume:    bool = Field(True,  description="Volume ratio and z-score")
    price:     bool = Field(True,  description="Current price gauge")
    breakouts: bool = Field(True,  description="ORB breakout counter")


class TickerConfigBody(BaseModel):
    """Request body for PUT /api/tickers/{symbol}/config."""
    metrics: MetricToggles = Field(default_factory=MetricToggles)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire all components, start background tasks, then tear down cleanly."""
    global scheduler, scheduler_task, edge

    logger.info("🚀 Starting Sentinel Edge...")

    pulse_url = os.getenv("PULSE_API_URL", "http://localhost:8002")

    pulse_client   = PulseClient(base_url=pulse_url, api_key=os.getenv("PULSE_API_KEY"))
    price_fetcher  = PriceFetcher()
    orb_tracker    = ORBTracker()
    atr_calculator = ATRCalculator(period=14)
    signal_engine  = SignalEngine()
    decision_engine = DecisionEngine()
    market_hours   = MarketHours()

    # SentinelEdge orchestrator — OTel tracing, WebSocket, MongoDB change stream
    edge = SentinelEdge(db=db, pulse_url=pulse_url)

    scheduler = EvaluationScheduler(
        pulse_client=pulse_client,
        price_fetcher=price_fetcher,
        orb_tracker=orb_tracker,
        atr_calculator=atr_calculator,
        signal_engine=signal_engine,
        decision_engine=decision_engine,
        market_hours=market_hours,
        db=db,
    )
    # Share the correlation engine and wire plugin discovery
    edge.set_scheduler(scheduler)

    # Expose live instance to the webhook alert handler
    _analyst_core.analyst_instance = edge

    scheduler_task = asyncio.create_task(scheduler.run())
    await edge.start_background_tasks()

    logger.info("✅ Sentinel Edge started successfully")
    yield

    # ── Graceful shutdown ──────────────────────────────────────────────────
    logger.info("🛑 Shutting down Sentinel Edge...")
    edge.stop()
    scheduler.stop()
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
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
        "status": "healthy",
        "running": sched.running,
        "paused": sched.paused,
        "active_tickers": len(sched.active_tickers),
    }


@api_router.get("/stats")
async def get_stats():
    sched = _require_scheduler()
    return {
        "active_tickers":    sched.active_tickers,
        "running":           sched.running,
        "paused":            sched.paused,
        "orb_levels_count":  len(sched.orb.get_all_levels()),
        "pulse_circuit_state": sched.pulse.state.name,
        "pulse_failures":    sched.pulse.failure_count,
    }


@api_router.get("/markets")
async def get_market_status():
    sched = _require_scheduler()
    return sched.market_hours.get_all_status()


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

    await db.ticker_configs.update_one(
        {"symbol": sym},
        {"$set": {"symbol": sym, "metrics": metrics_dict, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    sched.ticker_configs[sym] = metrics_dict

    return {"symbol": sym, "metrics": metrics_dict}


@api_router.get("/tickers/{symbol}/config")
async def get_ticker_config(symbol: str):
    """Return the metric configuration for a ticker, defaulting all flags to True."""
    sym = _symbol(symbol)

    # Exclude _id — ObjectId is not JSON-serialisable
    doc = await db.ticker_configs.find_one({"symbol": sym}, {"_id": 0})
    if doc:
        return {"symbol": sym, "metrics": doc.get("metrics", {}), "updated_at": doc.get("updated_at")}

    # Return defaults rather than 404 — callers can treat missing config as "all on"
    return {
        "symbol": sym,
        "metrics": MetricToggles().model_dump(),
        "updated_at": None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ORB levels
# ═══════════════════════════════════════════════════════════════════════════

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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
