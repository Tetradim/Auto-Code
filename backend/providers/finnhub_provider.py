"""Finnhub Provider - Full implementation (Phase 6)"""
import logging
import os
import time
from typing import Optional, Tuple
import pandas as pd
import httpx


from .base import BasePriceProvider
from metrics import price_fetch_latency, price_fetch_failures_total


logger = logging.getLogger(__name__)


class FinnhubProvider(BasePriceProvider):
    """Finnhub price data provider."""
    
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY")
        self.base_url = "https://finnhub.io/api/v1"
        logger.info(
            "FinnhubProvider initialized" + 
            (" (ready)" if self.api_key else " (no key)")
        )

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/quote",
                    params={"symbol": symbol, "token": self.api_key},
                    timeout=5.0
                )
                resp.raise_for_status()
                data = resp.json()
                # c = current price
                return float(data["c"]) if data.get("c") else None
                
        except Exception as e:
            price_fetch_failures_total.labels(symbol=symbol, source="finnhub").inc()
            logger.debug(f"Finnhub price failed: {e}")
            return None

    async def get_price_with_volume(self, symbol: str) -> Optional[Tuple[float, float]]:
        """Get current price with volume."""
        price = await self.get_current_price(symbol)
        return (price, 0.0) if price else None

    async def get_ohlcv(
        self, 
        symbol: str, 
        period: str = "1d", 
        interval: str = "1m"
    ) -> Optional[pd.DataFrame]:
        """Get OHLCV data using Finnhub candle endpoint."""
        if not self.api_key:
            return None
        
        try:
            # Map interval to finnhub resolution
            resolution = "1" if interval == "1m" else "5"
            
            # Calculate from/to timestamps (last 5 days)
            to_ts = int(time.time())
            from_ts = to_ts - (86400 * 5)
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/stock/candle",
                    params={
                        "symbol": symbol,
                        "resolution": resolution,
                        "from": from_ts,
                        "to": to_ts,
                        "token": self.api_key
                    },
                    timeout=10.0
                )
                data = resp.json()
                
                if data.get("s") != "ok":
                    return None
                    
                df = pd.DataFrame({
                    "Open": data["o"], 
                    "High": data["h"], 
                    "Low": data["l"],
                    "Close": data["c"], 
                    "Volume": data["v"]
                })
                
                # Create datetime index from timestamps
                df.index = pd.to_datetime(data["t"], unit="s")
                df.index.name = "timestamp"
                
                return df
                
        except Exception as e:
            logger.error(f"Finnhub OHLCV error: {e}")
            return None