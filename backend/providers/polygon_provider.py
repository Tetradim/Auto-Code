"""Polygon.io Provider - Full implementation (Phase 6)"""
import logging
import os
import time
from typing import Optional, Tuple, Any
from datetime import datetime, timedelta
import pandas as pd
import httpx


from .base import BasePriceProvider
from metrics import price_fetch_latency, price_fetch_failures_total, current_price


logger = logging.getLogger(__name__)


class PolygonProvider(BasePriceProvider):
    """Polygon.io price data provider."""
    
    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY")
        self.base_url = "https://api.polygon.io"
        self.cache = {}
        self.cache_duration = timedelta(seconds=3)
        logger.info(
            "PolygonProvider initialized" + 
            (" (ready)" if self.api_key else " (no key)")
        )

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        if not self.api_key:
            return None
        
        # Check cache
        if symbol in self.cache:
            cached_price, cached_time = self.cache[symbol]
            if datetime.now() - cached_time < self.cache_duration:
                return cached_price
        
        start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/v2/last/trade/{symbol}",
                    params={"apiKey": self.api_key},
                    timeout=5.0
                )
                resp.raise_for_status()
                data = resp.json()
                price = float(data["results"]["price"])

            duration = time.time() - start
            price_fetch_latency.labels(source="polygon").observe(duration)
            self.cache[symbol] = (price, datetime.now())
            current_price.labels(symbol=symbol).set(price)
            return price

        except Exception as e:
            price_fetch_failures_total.labels(symbol=symbol, source="polygon").inc()
            logger.debug(f"Polygon price failed for {symbol}: {e}")
            return None

    async def get_price_with_volume(self, symbol: str) -> Optional[Tuple[float, float]]:
        """Get current price with volume."""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers",
                    params={"ticker": symbol, "apiKey": self.api_key},
                    timeout=5.0
                )
                data = resp.json()
                if data.get("tick") and len(data["tick"]) > 0:
                    ticker = data["tick"][0]
                    price = float(ticker.get("lastTrade", {}).get("p", 0))
                    volume = float(ticker.get("day", {}).get("v", 0))
                    return price, volume
                return None
        except Exception:
            return None

    async def get_ohlcv(
        self, 
        symbol: str, 
        period: str = "1d", 
        interval: str = "1m"
    ) -> Optional[pd.DataFrame]:
        """Get OHLCV data."""
        if not self.api_key:
            return None
        
        try:
            # Map interval to polygon params
            multiplier, timespan = (1, "minute") if interval == "1m" else (5, "minute")
            
            to_date = datetime.utcnow().date()
            days = 5 if period in ("1d", "2d", "5d") else 30
            from_date = to_date - timedelta(days=days)

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}",
                    params={"apiKey": self.api_key, "adjusted": "true", "sort": "asc"},
                    timeout=10.0
                )
                resp.raise_for_status()
                data = resp.json()
                
                if not data.get("results"):
                    return None
                    
                df = pd.DataFrame(data["results"])
                df = df.rename(columns={
                    "o": "Open", "h": "High", "l": "Low", 
                    "c": "Close", "v": "Volume", "t": "timestamp"
                })
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df = df.set_index("timestamp")
                return df
                
        except Exception as e:
            logger.error(f"Polygon OHLCV error: {e}")
            return None
