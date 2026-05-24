"""Stooq no-key daily OHLCV provider."""
from __future__ import annotations

import logging
from io import StringIO
from typing import Optional, Tuple

import httpx
import pandas as pd

from .base import BasePriceProvider
from metrics import price_fetch_failures_total, price_fetch_latency


logger = logging.getLogger(__name__)


class StooqProvider(BasePriceProvider):
    """Public Stooq CSV provider.

    Stooq is useful as a no-key historical daily fallback. It should not be the
    primary intraday scheduler feed because this public CSV endpoint does not
    provide 1-minute bars. When callers ask for intraday data, we return None
    instead of pretending daily candles are real-time.
    """

    name = "stooq"
    base_url = "https://stooq.com/q/d/l/"

    def _symbol(self, symbol: str) -> str:
        # Stooq US equities generally use lowercase + .us, e.g. aapl.us.
        normalized = symbol.strip().lower().replace("-", ".")
        if "." not in normalized:
            normalized = f"{normalized}.us"
        return normalized

    async def get_current_price(self, symbol: str) -> Optional[float]:
        df = await self.get_ohlcv(symbol, period="1y", interval="1d")
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[-1])

    async def get_price_with_volume(self, symbol: str) -> Optional[Tuple[float, float]]:
        df = await self.get_ohlcv(symbol, period="1y", interval="1d")
        if df is None or df.empty:
            return None
        last = df.iloc[-1]
        return float(last["Close"]), float(last.get("Volume", 0.0))

    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> Optional[pd.DataFrame]:
        if interval != "1d":
            logger.debug("Stooq public CSV is daily-only; skipping %s request", interval)
            return None

        import time
        start = time.monotonic()
        stooq_symbol = self._symbol(symbol)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.base_url,
                    params={"s": stooq_symbol, "i": "d"},
                    timeout=8.0,
                    headers={"User-Agent": "SentinelEdge/market-data"},
                )
                resp.raise_for_status()

            if not resp.text or resp.text.lower().startswith("no data"):
                price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
                return None

            df = pd.read_csv(StringIO(resp.text))
            if df.empty or "Close" not in df.columns:
                price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
                return None

            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
            df.index.name = "timestamp"
            price_fetch_latency.labels(source=self.name).observe(time.monotonic() - start)
            return df
        except Exception as exc:
            price_fetch_failures_total.labels(symbol=symbol, source=self.name).inc()
            logger.debug("Stooq OHLCV failed for %s: %s", symbol, exc)
            return None
