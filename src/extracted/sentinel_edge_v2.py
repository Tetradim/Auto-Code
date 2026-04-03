import os
import asyncio
import logging
import httpx
import pandas as pd
from datetime import datetime, time, timezone
from typing import Dict, List, Optional, Set
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import yfinance as yf
from zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("Sentinel-Edge")

# Prometheus Metrics
BALANCE = Gauge("trading_bot_balance", "Current account balance")
TOTAL_PNL = Gauge("trading_bot_total_pnl", "Total profit and loss")
ACTIVE_POSITIONS = Gauge("trading_bot_active_positions", "Number of open positions")
ORB_BREAKOUT = Counter("trading_bot_orb_breakout_total", "Total O.R.B. breakouts detected", ["symbol", "direction", "timeframe"])
TRADE_COUNT = Gauge("trading_bot_trade_count_total", "Total number of trades executed")
CURRENT_PRICE = Gauge("trading_bot_current_price", "Current price of tracked tickers", ["symbol"])
ORB_HIGH = Gauge("trading_bot_orb_high", "Opening Range High", ["symbol", "timeframe"])
ORB_LOW = Gauge("trading_bot_orb_low", "Opening Range Low", ["symbol", "timeframe"])
VOLATILITY_ATR = Gauge("trading_bot_atr", "Average True Range (volatility)", ["symbol"])
TRAILING_STOP_PERCENT = Gauge("trading_bot_trailing_stop_pct", "Active dynamic trailing stop percentage", ["symbol"])

# Configuration
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongodb:27017")
DB_NAME = os.environ.get("DB_NAME", "bracket_bot")
METRICS_PORT = int(os.environ.get("METRICS_PORT", 8002))
ORB_TIMEFRAMES = [5, 15, 30] # Minutes for ORB
PULSE_API_URL = os.environ.get("PULSE_API_URL", "http://sentinel-pulse:8001")
PULSE_API_KEY = os.environ.get("PULSE_API_KEY", "") # If needed
ET = ZoneInfo("America/New_York")

class PulseClient:
    """Client to interact with Sentinel Pulse API."""
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url
        self.headers = {"X-API-KEY": api_key} if api_key else {}
        self.client = httpx.AsyncClient(timeout=10.0)

    async def update_ticker(self, symbol: str, data: dict):
        try:
            url = f"{self.base_url}/api/tickers/{symbol}"
            response = await self.client.put(url, json=data, headers=self.headers)
            if response.status_code == 200:
                logger.info(f"Successfully updated ticker {symbol} in Pulse: {data}")
            else:
                logger.error(f"Failed to update ticker {symbol} in Pulse: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error calling Pulse API for {symbol}: {e}")

    async def emergency_stop(self):
        try:
            url = f"{self.base_url}/api/bot/stop"
            await self.client.post(url, headers=self.headers)
            logger.warning("SENTINEL EDGE: EMERGENCY STOP TRIGGERED FOR PULSE!")
        except Exception as e:
            logger.error(f"Error triggering emergency stop: {e}")

class SentinelEdge:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.pulse = PulseClient(PULSE_API_URL, PULSE_API_KEY)
        self.orb_ranges = {}  # (symbol, timeframe) -> {"high": float, "low": float, "avg_vol": float, "date": str}
        self.breakouts_seen = set() # (symbol, date, direction, timeframe)
        self.active_tickers = []
        self.cooldowns = {} # symbol -> datetime

    async def update_trading_metrics(self):
        """Fetch general trading metrics from MongoDB."""
        try:
            balance_doc = await self.db.settings.find_one({"key": "account_balance"})
            if balance_doc:
                BALANCE.set(balance_doc.get("value", 0))

            profits = await self.db.profits.find().to_list(1000)
            total_pnl = sum(p.get("total_pnl", 0) for p in profits)
            total_trades = sum(p.get("trade_count", 0) for p in profits)
            TOTAL_PNL.set(total_pnl)
            TRADE_COUNT.set(total_trades)

            # Active tickers for monitoring
            self.active_tickers = await self.db.tickers.find({"enabled": True}).to_list(100)
            ACTIVE_POSITIONS.set(len(self.active_tickers))

        except Exception as e:
            logger.error(f"Error updating trading metrics: {e}")

    def is_market_open(self):
        now = datetime.now(ET)
        if now.weekday() >= 5: return False
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= now <= market_close

    async def get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch robust price and volume data using yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            # Fetch last 2 days to have enough data for ATR
            df = ticker.history(period="2d", interval="1m")
            if df.empty: return None
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range for volatility-aware stops."""
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        return float(atr)

    async def analyze_orb_and_control(self):
        """Analyze O.R.B. and take control actions."""
        if not self.is_market_open():
            return

        now = datetime.now(ET)
        today_str = now.strftime("%Y-%m-%d")
        
        for ticker in self.active_tickers:
            symbol = ticker["symbol"]
            df = await self.get_market_data(symbol)
            if df is None: continue

            # Current price and ATR
            current_price = df["Close"].iloc[-1]
            current_vol = df["Volume"].iloc[-1]
            atr = self.calculate_atr(df)
            
            CURRENT_PRICE.labels(symbol=symbol).set(current_price)
            VOLATILITY_ATR.labels(symbol=symbol).set(atr)

            # Analyze each timeframe
            for tf in ORB_TIMEFRAMES:
                try:
                    # 1. Establish ORB Range
                    key = (symbol, tf)
                    if key not in self.orb_ranges or self.orb_ranges[key]["date"] != today_str:
                        start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
                        cutoff_time = start_time + pd.Timedelta(minutes=tf)
                        
                        # Only calc if we are past the timeframe window
                        if now >= cutoff_time:
                            orb_data = df.between_time("09:30", cutoff_time.time().strftime("%H:%M"))
                            if not orb_data.empty:
                                orb_high = orb_data["High"].max()
                                orb_low = orb_data["Low"].min()
                                avg_vol = orb_data["Volume"].mean()
                                
                                self.orb_ranges[key] = {
                                    "high": orb_high, 
                                    "low": orb_low, 
                                    "avg_vol": avg_vol,
                                    "date": today_str
                                }
                                ORB_HIGH.labels(symbol=symbol, timeframe=tf).set(orb_high)
                                ORB_LOW.labels(symbol=symbol, timeframe=tf).set(orb_low)
                                logger.info(f"ESTABLISHED {tf}m ORB for {symbol}: {orb_low:.2f} - {orb_high:.2f} (Avg Vol: {avg_vol:.0f})")

                    # 2. Breakout Detection & Pulse Control
                    if key in self.orb_ranges:
                        orb = self.orb_ranges[key]
                        
                        # Cooldown check
                        if symbol in self.cooldowns and now < self.cooldowns[symbol]:
                            continue

                        # Breakout UP (Breakout through ORB High)
                        if current_price > orb["high"] and (symbol, today_str, "UP", tf) not in self.breakouts_seen:
                            # Volume confirmation (e.g., 1.5x average ORB volume)
                            if current_vol > orb["avg_vol"] * 1.5:
                                logger.warning(f"SENTINEL EDGE: {tf}m BREAKOUT UP CONFIRMED FOR {symbol} at {current_price:.2f}")
                                ORB_BREAKOUT.labels(symbol=symbol, direction="UP", timeframe=tf).inc()
                                self.breakouts_seen.add((symbol, today_str, "UP", tf))
                                
                                # CONTROL ACTION: Tighten stops and enable trailing
                                dynamic_trail = (atr * 2.5 / current_price) * 100 # ATR-based trailing pct
                                await self.pulse.update_ticker(symbol, {
                                    "trailing_enabled": True,
                                    "trailing_percent": dynamic_trail,
                                    "stop_percent": True,
                                    "stop_offset": 5.0 # Wider stop as it breaks out
                                })
                                TRAILING_STOP_PERCENT.labels(symbol=symbol).set(dynamic_trail)

                        # Breakout DOWN (Breakout through ORB Low)
                        elif current_price < orb["low"] and (symbol, today_str, "DOWN", tf) not in self.breakouts_seen:
                            if current_vol > orb["avg_vol"] * 1.2: # Lower threshold for down moves
                                logger.warning(f"SENTINEL EDGE: {tf}m BREAKOUT DOWN DETECTED FOR {symbol} at {current_price:.2f}")
                                ORB_BREAKOUT.labels(symbol=symbol, direction="DOWN", timeframe=tf).inc()
                                self.breakouts_seen.add((symbol, today_str, "DOWN", tf))
                                
                                # CONTROL ACTION: Stop buying, exit fast
                                await self.pulse.update_ticker(symbol, {
                                    "enabled": False, # Stop the bot for this ticker
                                    "trailing_enabled": True,
                                    "trailing_percent": 0.5 # Very tight exit
                                })
                                self.cooldowns[symbol] = now + pd.Timedelta(minutes=30)

                except Exception as e:
                    logger.error(f"Error analyzing {tf}m ORB for {symbol}: {e}")

    async def run(self):
        logger.info(f"Starting Prometheus metrics server on port {METRICS_PORT}")
        start_http_server(METRICS_PORT)
        
        while True:
            await self.update_trading_metrics()
            await self.analyze_orb_and_control()
            # Loop faster than before (every 30s) for more responsiveness
            await asyncio.sleep(30)

if __name__ == "__main__":
    edge = SentinelEdge()
    asyncio.run(edge.run())
