"""Alpha Vantage market-data provider."""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

import httpx
import pandas as pd

from .base import BasePriceProvider
from metrics import price_fetch_failures_total, price_fetch_latency


logger = logging.getLogger(__name__)


class AlphaVantageProvider(BasePriceProvider):
    """Alpha Vantage free/freemium API provider.

    The free tier is rate-limited, so this provider is intentionally optional
    and should sit behind yfinance or other configured providers unless the user
    explicitly changes MARKET_DATA_PROVIDER_ORDER.
    """

    name = "alpha_vantage"
    base_url = "https://www.alphavantage.co/query"

    def __init__(self) -> None:
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        logger.info("AlphaVantageProvider initialized%s", " (ready)" if self.api_key else " (no key)")

    def _rate_limited(self, data: dict) -> bool:
        return any(key in data for key in ("Note", "Information"))

    async def _get(self, params: dict) -> Optional[dict]:
        if not self.api_key:
            return None
        safe_params = {**params, "apikey": self.api_key}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.base_url, params=safe_params, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
            if self._rate_limited(data):
                logger.info("Alpha Vantage rate limit/info response received; backing off")
                return None
            return data
        except Exception as exc:
            logger.debug("Alpha Vantage request failed: %s", exc)
            return None

    async def get_current_price(self, symbol: str) -> Optional[float]:
        data = await self._get({"function": "GLOBAL_QUOTE", "symbol": symbol})
        if not data:
            return None
        quote = data.get("Global Quote", {})
        price = quote.get("05. price")
        if not price:
            price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
            return None
        return float(price)

    async def get_price_with_volume(self, symbol: str) -> Optional[Tuple[float, float]]:
        data = await self._get({"function": "GLOBAL_QUOTE", "symbol": symbol})
        if not data:
            return None
        quote = data.get("Global Quote", {})
        price = quote.get("05. price")
        volume = quote.get("06. volume", 0)
        if not price:
            price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
            return None
        return float(price), float(volume or 0)

    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "2d",
        interval: str = "1m",
    ) -> Optional[pd.DataFrame]:
        import time
        start = time.monotonic()
        function = "TIME_SERIES_INTRADAY" if interval.endswith("m") else "TIME_SERIES_DAILY_ADJUSTED"
        params = {"function": function, "symbol": symbol, "outputsize": "compact"}
        if function == "TIME_SERIES_INTRADAY":
            params["interval"] = interval

        data = await self._get(params)
        if not data:
            price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
            return None

        series_key = next((key for key in data if key.startswith("Time Series")), None)
        if not series_key:
            price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
            return None

        rows = []
        for timestamp, values in data[series_key].items():
            rows.append(
                {
                    "timestamp": timestamp,
                    "Open": float(values.get("1. open", 0)),
                    "High": float(values.get("2. high", 0)),
                    "Low": float(values.get("3. low", 0)),
                    "Close": float(values.get("4. close", 0)),
                    "Volume": float(values.get("5. volume", values.get("6. volume", 0)) or 0),
                }
            )

        if not rows:
            price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
            return None

        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").set_index("timestamp")
        price_fetch_latency.labels(source=self.name).observe(time.monotonic() - start)
        return df
