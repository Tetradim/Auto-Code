"""Price Data Fetcher — one yfinance call per symbol per cache window.

Problem with the previous design
──────────────────────────────────
The scheduler called get_price_with_volume() and get_ohlcv() separately on
every evaluation tick. Both made their own ticker.history() HTTP request, so
each ticker cost two blocking network calls per second. For N tickers:

    previous: 2 × N yfinance calls/s  →  blocked event loop × 2N/s
    fixed:    1 yfinance call / (symbol × OHLCV_CACHE_TTL seconds)

Single cache design
────────────────────
_get_ohlcv_cached() is the only place a yfinance request is made.
get_price_with_volume(), get_ohlcv(), and get_current_price() all derive their
return values from the same cached DataFrame — no extra network calls.

Thread executor
────────────────
yfinance.Ticker.history() is a synchronous blocking HTTP call. Calling it
directly inside an async function stalls the entire event loop for the
duration of the request (~200–800 ms). It is offloaded to a thread via
asyncio.get_running_loop().run_in_executor() so all tickers can be fetched
concurrently without blocking each other or the scheduler.

Stampede guard
────────────────
A per-symbol asyncio.Lock prevents multiple coroutines from all fetching the
same symbol simultaneously on a cache miss (the "thundering herd" problem).
Waiters re-check the cache after acquiring the lock; if another coroutine
already fetched, they return the cached result without making a network call.

Cache TTL
──────────
OHLCV_CACHE_TTL defaults to 30 s. yfinance 1-minute bars are themselves
delayed ~15 s on the free feed, so refreshing faster than 30 s would fetch
stale data twice as often for no accuracy gain. Adjust downward if you switch
to a real-time data provider.

Staleness on failure
─────────────────────
On a transient fetch failure the most recently cached DataFrame is returned
rather than None. This keeps the ATR calculator, signal engine, and ORB
plugin running on slightly stale data rather than crashing the evaluation for
that ticker. Prometheus counters record every failure for alerting.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Tuple

import pandas as pd
import yfinance as yf

from metrics import current_price, price_fetch_failures_total, price_fetch_latency
from providers.health import ProviderHealth

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level fetch function
# Must be module-level (not a lambda or method) so it can be sent to the
# ThreadPoolExecutor without pickling issues on some platforms.
# ─────────────────────────────────────────────────────────────────────────────

def _yf_fetch(symbol: str) -> pd.DataFrame:
    """Synchronous yfinance call — always run via run_in_executor, never directly."""
    # period="2d" ensures enough bars for ATR seeding even when the bot starts
    # during the session (1d gives too few bars early in the morning).
    return yf.Ticker(symbol).history(period="2d", interval="1m")


# ─────────────────────────────────────────────────────────────────────────────
# PriceFetcher
# ─────────────────────────────────────────────────────────────────────────────

class PriceFetcher:
    """Unified OHLCV cache — all callers share one DataFrame per symbol."""

    OHLCV_CACHE_TTL: int = 30  # seconds

    def __init__(self) -> None:
        # symbol → (DataFrame, monotonic_fetch_time)
        self._cache: Dict[str, Tuple[pd.DataFrame, float]] = {}
        # Per-symbol locks — created lazily inside async context
        self._locks: Dict[str, asyncio.Lock] = {}
        # Live price from WebSocket (symbol → (price, volume, timestamp))
        self._live_prices: Dict[str, Tuple[float, float, float]] = {}
        # WebSocket manager reference
        self._ws_manager = None
        # Provider health monitoring
        self.health = ProviderHealth()
        logger.info(
            "PriceFetcher initialised (yfinance, cache TTL=%ds)", self.OHLCV_CACHE_TTL
        )

    # ─────────────────────────────────────────────────────────────────────────
    # WebSocket integration
    # ─────────────────────────────────────────────────────────────────────────

    def set_ws_manager(self, ws_manager):
        """Set the WebSocket manager for live price updates."""
        self._ws_manager = ws_manager
        logger.info("WebSocketManager wired into PriceFetcher")

    def update_live_price(self, symbol: str, price: float, volume: float = 0):
        """Called by WebSocket when live price arrives."""
        import time as time_module
        self._live_prices[symbol] = (price, volume, time_module.time())
        logger.debug(f"Live price updated: {symbol} = ${price}")

    def get_live_price(self, symbol: str) -> Optional[Tuple[float, float]]:
        """Get recent live price from WebSocket if available."""
        if symbol in self._live_prices:
            price, volume, timestamp = self._live_prices[symbol]
            # Only use live price if recent (within 5 seconds)
            import time as time_module
            if time_module.time() - timestamp < 5:
                return (price, volume)
        return None

    def get_provider_health(self) -> dict:
        """Get health status for all providers."""
        return self.health.get_health()

    # ─────────────────────────────────────────────────────────────────────────
    # Core — single network call shared by all public methods
    # ─────────────────────────────────────────────────────────────────────────

    async def _get_ohlcv_cached(self, symbol: str) -> Optional[pd.DataFrame]:
        """Return a fresh-or-cached 2d/1m OHLCV DataFrame for *symbol*.

        Call graph
        ──────────
        1. Fast path — return cache hit immediately (no lock, no allocation).
        2. Acquire per-symbol lock.
        3. Double-check cache (another coroutine may have fetched while we queued).
        4. Run _yf_fetch in a thread — does not block the event loop.
        5. Cache result, update Prometheus price gauge, return DataFrame.
        6. On any error return the stale cached DataFrame if one exists.
        """
        now = time.monotonic()

        # ── 1. Fast path ──────────────────────────────────────────────────────
        entry = self._cache.get(symbol)
        if entry and now - entry[1] < self.OHLCV_CACHE_TTL:
            return entry[0]

        # ── 2. Acquire per-symbol lock ────────────────────────────────────────
        if symbol not in self._locks:
            self._locks[symbol] = asyncio.Lock()

        async with self._locks[symbol]:

            # ── 3. Double-check after lock ────────────────────────────────────
            entry = self._cache.get(symbol)
            if entry and now - entry[1] < self.OHLCV_CACHE_TTL:
                return entry[0]

            # ── 4. Fetch in thread ────────────────────────────────────────────
            t0 = time.monotonic()
            try:
                loop = asyncio.get_running_loop()
                df: pd.DataFrame = await loop.run_in_executor(None, _yf_fetch, symbol)

                price_fetch_latency.labels(source="yfinance").observe(
                    time.monotonic() - t0
                )

                if df is None or df.empty:
                    price_fetch_failures_total.labels(
                        symbol=symbol, source="yfinance"
                    ).inc()
                    logger.warning("No OHLCV data returned for %s", symbol)
                    # Return stale data rather than None
                    self.health.record_failure("yfinance")
                    return self._cache[symbol][0] if symbol in self._cache else None

                # ── 5. Cache + metrics ────────────────────────────────────────
                self._cache[symbol] = (df, time.monotonic())
                self.health.record_success("yfinance")
                last_close = float(df["Close"].iloc[-1])
                current_price.labels(symbol=symbol).set(last_close)
                logger.debug(
                    "Fetched %s — %d bars, last=$%.2f (%.2fs)",
                    symbol, len(df), last_close, time.monotonic() - t0,
                )
                return df

            except Exception as exc:
                # ── 6. Error — return stale rather than crashing ──────────────
                price_fetch_failures_total.labels(
                    symbol=symbol, source="yfinance"
                ).inc()
                self.health.record_failure("yfinance")
                logger.error("yfinance fetch error for %s: %s", symbol, exc)
                return self._cache[symbol][0] if symbol in self._cache else None

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def get_price_with_volume(self, symbol: str) -> Optional[Tuple[float, float]]:
        """Return ``(close, volume)`` for the most recent 1m bar.

        This is the primary method called by the scheduler every evaluation
        cycle. It attempts to use live WebSocket prices if available,
        otherwise falls back to cached yfinance data.
        """
        # First check for live WebSocket price
        live = self.get_live_price(symbol)
        if live:
            return live

        df = await self._get_ohlcv_cached(symbol)
        if df is None or df.empty:
            return None
        last = df.iloc[-1]
        return float(last["Close"]), float(last["Volume"])

    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "2d",
        interval: str = "1m",
    ) -> Optional[pd.DataFrame]:
        """Return the full OHLCV DataFrame for *symbol*.

        Used by the ATR calculator, ORB level seeding on restart, and
        BaseSignal plugins. Always returns 2d/1m data from the shared cache.

        The *period* and *interval* arguments are accepted for API
        compatibility but are intentionally ignored — the cache stores 2d/1m
        which is a superset of 1d/1m. Non-standard combinations log a warning.
        """
        if interval != "1m" or period not in ("1d", "2d", "5d"):
            logger.warning(
                "get_ohlcv(%s, period=%r, interval=%r) — "
                "only 1m interval is cached; returning 2d/1m",
                symbol, period, interval,
            )
        return await self._get_ohlcv_cached(symbol)

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Return the most recent close price."""
        result = await self.get_price_with_volume(symbol)
        return result[0] if result else None

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics
    # ─────────────────────────────────────────────────────────────────────────

    def cache_ages(self) -> Dict[str, float]:
        """Return seconds since last successful fetch per symbol (for /api/stats)."""
        now = time.monotonic()
        return {
            sym: round(now - fetched_at, 1)
            for sym, (_, fetched_at) in self._cache.items()
        }
