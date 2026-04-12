import os
import asyncio
import logging
from datetime import datetime, time, timezone
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import start_http_server, Gauge, Counter
import yfinance as yf
from zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ORB-Analyzer")

# Prometheus Metrics
BALANCE = Gauge("trading_bot_balance", "Current account balance")
TOTAL_PNL = Gauge("trading_bot_total_pnl", "Total profit and loss")
ACTIVE_POSITIONS = Gauge("trading_bot_active_positions", "Number of open positions")
ORB_BREAKOUT = Counter("trading_bot_orb_breakout_total", "Total O.R.B. breakouts detected", ["symbol", "direction"])
TRADE_COUNT = Gauge("trading_bot_trade_count_total", "Total number of trades executed")
CURRENT_PRICE = Gauge("trading_bot_current_price", "Current price of tracked tickers", ["symbol"])
ORB_HIGH = Gauge("trading_bot_orb_high", "Opening Range High", ["symbol"])
ORB_LOW = Gauge("trading_bot_orb_low", "Opening Range Low", ["symbol"])

# Configuration
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongodb:27017")
DB_NAME = os.environ.get("DB_NAME", "bracket_bot")
METRICS_PORT = int(os.environ.get("METRICS_PORT", 8002))
ORB_MINUTES = int(os.environ.get("ORB_MINUTES", 15))
ET = ZoneInfo("America/New_York")

class ORBAnalyzer:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.orb_ranges = {}  # symbol -> {"high": float, "low": float, "date": str}
        self.breakouts_seen = set() # (symbol, date, direction)

    async def update_trading_metrics(self):
        """Fetch general trading metrics from MongoDB."""
        try:
            # Balance
            balance_doc = await self.db.settings.find_one({"key": "account_balance"})
            if balance_doc:
                BALANCE.set(balance_doc.get("value", 0))

            # PnL and Trade Count
            profits = await self.db.profits.find().to_list(1000)
            total_pnl = sum(p.get("total_pnl", 0) for p in profits)
            total_trades = sum(p.get("trade_count", 0) for p in profits)
            TOTAL_PNL.set(total_pnl)
            TRADE_COUNT.set(total_trades)

            # Active Positions
            # In Set-Trader, positions are often stored in the engine state or a dedicated collection
            # For this sidecar, we'll check the 'tickers' collection for active trades if possible
            # or assume the engine exposes it. Based on server.py, it's in deps.engine.positions.
            # Since we are a sidecar, we'll look at the database state.
            active_tickers = await self.db.tickers.find({"active": True}).to_list(100)
            ACTIVE_POSITIONS.set(len(active_tickers))

        except Exception as e:
            logger.error(f"Error updating trading metrics: {e}")

    def is_market_open(self):
        now = datetime.now(ET)
        if now.weekday() >= 5:
            return False
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= now <= market_close

    async def analyze_orb(self):
        """Analyze O.R.B. for all active tickers."""
        if not self.is_market_open():
            return

        now = datetime.now(ET)
        today_str = now.strftime("%Y-%m-%d")
        
        # Get active tickers from DB
        tickers = await self.db.tickers.find({"active": True}).to_list(100)
        symbols = [t["symbol"] for t in tickers]

        for symbol in symbols:
            try:
                # 1. Get Opening Range (first ORB_MINUTES)
                if symbol not in self.orb_ranges or self.orb_ranges[symbol]["date"] != today_str:
                    # Fetch morning data
                    start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
                    end_time = start_time + asyncio.to_thread(lambda: None) # placeholder
                    
                    # Use yfinance to get the opening range bars
                    ticker_data = yf.Ticker(symbol)
                    hist = ticker_data.history(start=today_str, interval="1m")
                    
                    if not hist.empty:
                        opening_period = hist.between_time("09:30", (datetime.combine(now.date(), time(9, 30)) + (datetime.min.time().replace(minute=ORB_MINUTES) - datetime.min.time())).time().strftime("%H:%M"))
                        if not opening_period.empty:
                            orb_high = opening_period["High"].max()
                            orb_low = opening_period["Low"].min()
                            self.orb_ranges[symbol] = {"high": orb_high, "low": orb_low, "date": today_str}
                            ORB_HIGH.labels(symbol=symbol).set(orb_high)
                            ORB_LOW.labels(symbol=symbol).set(orb_low)
                            logger.info(f"Set ORB for {symbol}: {orb_low} - {orb_high}")

                # 2. Check for Breakouts
                if symbol in self.orb_ranges:
                    current_data = yf.Ticker(symbol).history(period="1d", interval="1m").iloc[-1]
                    price = current_data["Close"]
                    CURRENT_PRICE.labels(symbol=symbol).set(price)
                    
                    orb_high = self.orb_ranges[symbol]["high"]
                    orb_low = self.orb_ranges[symbol]["low"]

                    # Breakout Up
                    if price > orb_high and (symbol, today_str, "UP") not in self.breakouts_seen:
                        ORB_BREAKOUT.labels(symbol=symbol, direction="UP").inc()
                        self.breakouts_seen.add((symbol, today_str, "UP"))
                        logger.info(f"ORB BREAKOUT UP: {symbol} at {price}")

                    # Breakout Down
                    elif price < orb_low and (symbol, today_str, "DOWN") not in self.breakouts_seen:
                        ORB_BREAKOUT.labels(symbol=symbol, direction="DOWN").inc()
                        self.breakouts_seen.add((symbol, today_str, "DOWN"))
                        logger.info(f"ORB BREAKOUT DOWN: {symbol} at {price}")

            except Exception as e:
                logger.error(f"Error analyzing ORB for {symbol}: {e}")

    async def run(self):
        logger.info(f"Starting Prometheus metrics server on port {METRICS_PORT}")
        start_http_server(METRICS_PORT)
        
        while True:
            await self.update_trading_metrics()
            await self.analyze_orb()
            await asyncio.sleep(60) # Check every minute

if __name__ == "__main__":
    analyzer = ORBAnalyzer()
    asyncio.run(analyzer.run())
