"""Sentinel Edge - Main FastAPI Server"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import REGISTRY, generate_latest
from starlette.middleware.cors import CORSMiddleware

# Import our modules
from atr import ATRCalculator
from engine import DecisionEngine
from market_hours import MarketHours
from orb import ORBTracker
from price_fetcher import PriceFetcher
from pulse_client import PulseClient
from scheduler import EvaluationScheduler
from signals import SignalEngine

# Setup
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Global scheduler instance
scheduler: EvaluationScheduler = None
scheduler_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    global scheduler, scheduler_task
    
    logger.info("🚀 Starting Sentinel Edge...")
    
    # Initialize components
    pulse_client = PulseClient(
        base_url=os.getenv("PULSE_API_URL", "http://localhost:8002"),
        api_key=os.getenv("PULSE_API_KEY")
    )
    
    price_fetcher = PriceFetcher()
    orb_tracker = ORBTracker()
    atr_calculator = ATRCalculator(period=14)
    signal_engine = SignalEngine()
    decision_engine = DecisionEngine()
    market_hours = MarketHours()
    
    # Initialize scheduler
    scheduler = EvaluationScheduler(
        pulse_client=pulse_client,
        price_fetcher=price_fetcher,
        orb_tracker=orb_tracker,
        atr_calculator=atr_calculator,
        signal_engine=signal_engine,
        decision_engine=decision_engine,
        market_hours=market_hours
    )
    
    # Start scheduler in background
    scheduler_task = asyncio.create_task(scheduler.run())
    
    logger.info("✅ Sentinel Edge started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Sentinel Edge...")
    if scheduler:
        scheduler.stop()
    if scheduler_task:
        await scheduler_task
    client.close()
    logger.info("👋 Sentinel Edge stopped")


# Create app
app = FastAPI(
    title="Sentinel Edge",
    description="Trading analyst sidecar for Sentinel Pulse",
    version="1.0.0",
    lifespan=lifespan
)

# Create router with /api prefix
api_router = APIRouter(prefix="/api")


# ═══════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@api_router.get("/")
async def root():
    """API root"""
    return {
        "name": "Sentinel Edge",
        "version": "1.0.0",
        "status": "running" if scheduler and scheduler.running else "stopped"
    }


@api_router.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "running": scheduler.running if scheduler else False,
        "paused": scheduler.paused if scheduler else False,
        "active_tickers": len(scheduler.active_tickers) if scheduler else 0
    }


@api_router.get("/tickers")
async def get_tickers():
    """Get active tickers"""
    if not scheduler:
        return {"tickers": []}
    
    return {
        "tickers": scheduler.active_tickers,
        "count": len(scheduler.active_tickers)
    }


@api_router.post("/tickers/{symbol}")
async def add_ticker(symbol: str):
    """Add ticker to watch list"""
    if scheduler:
        scheduler.add_ticker(symbol.upper())
    return {"message": f"Added {symbol.upper()} to watch list"}


@api_router.delete("/tickers/{symbol}")
async def remove_ticker(symbol: str):
    """Remove ticker from watch list"""
    if scheduler:
        scheduler.remove_ticker(symbol.upper())
    return {"message": f"Removed {symbol.upper()} from watch list"}


@api_router.put("/tickers/{symbol}/config")
async def update_ticker_config(symbol: str, config: dict):
    """Update ticker metric configuration"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}
    
    symbol = symbol.upper()
    
    # Store config in MongoDB
    try:
        result = await db.ticker_configs.update_one(
            {"symbol": symbol},
            {"$set": {
                "symbol": symbol,
                "metrics": config.get("metrics", {}),
                "updated_at": datetime.now()
            }},
            upsert=True
        )
        
        # Update scheduler's metric tracking
        if hasattr(scheduler, 'ticker_configs'):
            scheduler.ticker_configs[symbol] = config.get("metrics", {})
        else:
            scheduler.ticker_configs = {symbol: config.get("metrics", {})}
        
        return {
            "message": f"Updated config for {symbol}",
            "config": config,
            "modified": result.modified_count > 0
        }
    except Exception as e:
        logger.error(f"Failed to update ticker config: {e}")
        return {"error": str(e)}


@api_router.get("/tickers/{symbol}/config")
async def get_ticker_config(symbol: str):
    """Get ticker metric configuration"""
    symbol = symbol.upper()
    
    try:
        config = await db.ticker_configs.find_one({"symbol": symbol})
        if config:
            return {
                "symbol": symbol,
                "metrics": config.get("metrics", {}),
                "updated_at": config.get("updated_at")
            }
        else:
            # Return default config
            return {
                "symbol": symbol,
                "metrics": {
                    "orb": True,
                    "atr": True,
                    "signal": True,
                    "volume": True,
                    "price": True,
                    "breakouts": True
                }
            }
    except Exception as e:
        logger.error(f"Failed to get ticker config: {e}")
        return {"error": str(e)}


@api_router.post("/control/pause")
async def pause_scheduler():
    """Pause scheduler"""
    if scheduler:
        scheduler.pause()
    return {"message": "Scheduler paused"}


@api_router.post("/control/resume")
async def resume_scheduler():
    """Resume scheduler"""
    if scheduler:
        scheduler.resume()
    return {"message": "Scheduler resumed"}


@api_router.get("/orb/{symbol}")
async def get_orb_levels(symbol: str):
    """Get ORB levels for a symbol"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}
    
    levels = scheduler.orb.get_levels(symbol.upper())
    if not levels:
        return {"error": f"No ORB data for {symbol}"}
    
    result = {}
    for timeframe, level in levels.items():
        result[f"{timeframe}m"] = {
            "high": level.high,
            "low": level.low,
            "locked": level.locked,
            "range_width": level.range_width,
            "is_valid": level.is_valid
        }
    
    return result


@api_router.get("/markets")
async def get_market_status():
    """Get status of all markets"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}
    
    return scheduler.market_hours.get_all_status()


@api_router.get("/stats")
async def get_stats():
    """Get system statistics"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}
    
    stats = {
        "active_tickers": scheduler.active_tickers,
        "running": scheduler.running,
        "paused": scheduler.paused,
        "orb_levels_count": len(scheduler.orb.get_all_levels()),
        "pulse_circuit_state": scheduler.pulse.state.name,
        "pulse_failures": scheduler.pulse.failure_count
    }
    
    return stats


# ═══════════════════════════════════════════════════════════════════════════
# PROMETHEUS METRICS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(REGISTRY).decode('utf-8')


# Include API router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
