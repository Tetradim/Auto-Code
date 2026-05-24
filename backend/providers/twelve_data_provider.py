"""Twelve Data market-data provider."""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

import httpx
import pandas as pd

from .base import BasePriceProvider
from metrics import price_fetch_failures_total, price_fetch_latency


logger = logging.getLogger(__name__)


class TwelveDataProvider(BasePriceProvider):
    """Twelve Data free/freemium API provider.

    Requires TWELVE_DATA_API_KEY. The free tier is credit/rate limited, so this
    provider is optional and only used when the user places it in
    MARKET_DATA_PROVIDER_ORDER.
    """

    name = "twelve_data"
    base_url = "https://api.twelvedata.com"

    def __init__(self) -> None:
        self.api_key = os.getenv("TWELVE_DATA_API_KEY")
        logger.info("TwelveDataProvider initialized%s", " (ready)" if self.api_key else " (no key)")

    async def _get(self, endpoint: str, params: dict) -> Optional[dict]:
        if not self.api_key:
            return None
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/{endpoint}",
                    params={**params, "apikey": self.api_key},
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
            if data.get("status") == "error" or "message" in data:
                logger.info("Twelve Data returned non-data response for %s", endpoint)
                return None
            return data
        except Exception as exc:
            logger.debug("Twelve Data request failed for %s: %s", endpoint, exc)
            return None

    async def get_current_price(self, symbol: str) -> Optional[float]:
        data = await self._get("price", {"symbol": symbol})
        if not data or not data.get("price"):
            price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
            return None
        return float(data["price"])

    async def get_price_with_volume(self, symbol: str) -> Optional[Tuple[float, float]]:
        quote = await self._get("quote", {"symbol": symbol})
        if quote and quote.get("close"):
            volume = quote.get("volume") or quote.get("average_volume") or 0
            return float(quote["close"]), float(volume or 0)

        price = await self.get_current_price(symbol)
        return (price, 0.0) if price is not None else None

    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "2d",
        interval: str = "1min",
    ) -> Optional[pd.DataFrame]:
        import time
        start = time.monotonic()
        td_interval = "1min" if interval in ("1m", "1min") else interval
        data = await self._get(
            "time_series",
            {"symbol": symbol, "interval": td_interval, "outputsize": 500},
        )
        values = data.get("values") if data else None
        if not values:
            price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
            return None

        rows = []
        for item in values:
            rows.append(
                {
                    "timestamp": item.get("datetime"),
                    "Open": float(item.get("open", 0)),
                    "High": float(item.get("high", 0)),
                    "Low": float(item.get("low", 0)),
                    "Close": float(item.get("close", 0)),
                    "Volume": float(item.get("volume") or 0),
                }
            )

        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").set_index("timestamp")
        price_fetch_latency.labels(source=self.name).observe(time.monotonic() - start)
        return df
