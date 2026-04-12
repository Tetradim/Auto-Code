"""Sentinel Pulse API Client — circuit-breaker HTTP client.

All outbound calls to Sentinel Pulse go through this module.
The circuit breaker opens after FAILURE_THRESHOLD consecutive failures and
stays open for CIRCUIT_OPEN_DURATION seconds before allowing a test request.

A single persistent AsyncClient is reused across all calls (connection pooling).
Call `await pulse.aclose()` during application shutdown.
"""
import logging
import time
from enum import Enum
from typing import Any, Dict, Optional

import httpx

from metrics import (
    broker_circuit_state,
    broker_failure_rate,
    edge_api_calls_total,
    edge_api_latency,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED    = 0   # normal operation
    HALF_OPEN = 1   # testing recovery
    OPEN      = 2   # Pulse unreachable; requests blocked


class PulseClient:
    """HTTP client for Sentinel Pulse with a circuit-breaker guard."""

    FAILURE_THRESHOLD    = 5
    SUCCESS_THRESHOLD    = 2
    TIMEOUT_SECONDS      = 5.0
    CIRCUIT_OPEN_DURATION = 60  # seconds before attempting HALF_OPEN

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        api_key: Optional[str] = None,
    ):
        self.base_url  = base_url.rstrip("/")
        self.api_key   = api_key
        self.broker_id = "pulse"

        # Circuit breaker state
        self.state            = CircuitState.CLOSED
        self.failure_count    = 0
        self.success_count    = 0
        self.last_failure_time = 0.0

        # Persistent connection pool — avoids TCP handshake overhead per call
        self._client = httpx.AsyncClient(
            timeout=self.TIMEOUT_SECONDS,
            headers=self._build_headers(),
        )

        broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
        broker_failure_rate.labels(broker_id=self.broker_id).set(0.0)
        logger.info("PulseClient → %s", self.base_url)

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-API-KEY"] = self.api_key
        return h

    def _should_allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.CIRCUIT_OPEN_DURATION:
                logger.info("Circuit breaker → HALF_OPEN (testing recovery)")
                self.state = CircuitState.HALF_OPEN
                broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
                return True
            return False
        return True  # HALF_OPEN — allow the test request

    def _record_success(self):
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.SUCCESS_THRESHOLD:
                logger.info("Circuit breaker → CLOSED after %d successes", self.success_count)
                self.state         = CircuitState.CLOSED
                self.success_count = 0
                broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)

    def _record_failure(self):
        self.failure_count    += 1
        self.last_failure_time = time.time()
        self.success_count     = 0
        if self.failure_count >= self.FAILURE_THRESHOLD:
            logger.error("Circuit breaker → OPEN after %d failures", self.failure_count)
            self.state = CircuitState.OPEN
            broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
        total = max(self.failure_count, 1)
        broker_failure_rate.labels(broker_id=self.broker_id).set(
            (self.failure_count / total) * 100
        )

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> bool:
        """POST with circuit-breaker guard. Returns True on 2xx."""
        if not self._should_allow_request():
            logger.warning("Circuit %s — POST %s blocked", self.state.name, endpoint)
            return False

        url   = f"{self.base_url}{endpoint}"
        start = time.time()
        try:
            response = await self._client.post(url, json=payload)
            edge_api_latency.labels(endpoint=endpoint).observe(time.time() - start)
            if response.status_code in (200, 201, 204):
                edge_api_calls_total.labels(endpoint=endpoint, status="success").inc()
                self._record_success()
                return True
            edge_api_calls_total.labels(endpoint=endpoint, status="failure").inc()
            self._record_failure()
            logger.error("Pulse %s → HTTP %d", endpoint, response.status_code)
            return False
        except httpx.TimeoutException:
            edge_api_calls_total.labels(endpoint=endpoint, status="timeout").inc()
            self._record_failure()
            logger.error("Pulse %s timed out", endpoint)
            return False
        except Exception as exc:
            edge_api_calls_total.labels(endpoint=endpoint, status="error").inc()
            self._record_failure()
            logger.error("Pulse %s error: %s", endpoint, exc)
            return False

    async def _get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """GET with circuit-breaker guard. Returns parsed JSON or None."""
        if not self._should_allow_request():
            logger.debug("Circuit %s — GET %s blocked", self.state.name, endpoint)
            return None

        url   = f"{self.base_url}{endpoint}"
        start = time.time()
        try:
            response = await self._client.get(url)
            edge_api_latency.labels(endpoint=endpoint).observe(time.time() - start)
            if response.status_code == 200:
                edge_api_calls_total.labels(endpoint=endpoint, status="success").inc()
                self._record_success()
                return response.json()
            if response.status_code == 404:
                # Not an error — symbol has no open position
                self._record_success()
                return None
            edge_api_calls_total.labels(endpoint=endpoint, status="failure").inc()
            self._record_failure()
            logger.warning("Pulse GET %s → HTTP %d", endpoint, response.status_code)
            return None
        except httpx.TimeoutException:
            edge_api_calls_total.labels(endpoint=endpoint, status="timeout").inc()
            self._record_failure()
            logger.error("Pulse GET %s timed out", endpoint)
            return None
        except Exception as exc:
            edge_api_calls_total.labels(endpoint=endpoint, status="error").inc()
            self._record_failure()
            logger.error("Pulse GET %s error: %s", endpoint, exc)
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Position query
    # ─────────────────────────────────────────────────────────────────────────

    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch live position state for *symbol* from Pulse.

        Expected Pulse response shape
        ──────────────────────────────
        {
          "symbol":           "SPY",
          "has_position":     true,
          "pnl":              125.50,        // absolute P&L in dollars
          "pnl_pct":          1.20,          // P&L as percentage of entry value
          "trailing_enabled": false,
          "trailing_percent": null,
          "entry_price":      440.00,
          "current_price":    445.28,
          "drawdown_pct":     0.0            // optional; computed locally if absent
        }

        Returns None when:
          - circuit is open (Pulse unreachable)
          - 404 (symbol has no open position)
          - any network / parsing error

        Callers should fall back to their local cached state on None.
        """
        data = await self._get(f"/api/positions/{symbol}")
        if data is None:
            return None

        # Normalise — Pulse API versions may use different key names
        return {
            "has_position":     bool(data.get("has_position", data.get("active", False))),
            "pnl":              float(data.get("pnl", data.get("unrealized_pnl", 0.0))),
            "pnl_pct":          float(data.get("pnl_pct", data.get("unrealized_pnl_pct", 0.0))),
            "trailing_enabled": bool(data.get("trailing_enabled", data.get("trailing_stop_enabled", False))),
            "trailing_percent": data.get("trailing_percent"),
            "entry_price":      data.get("entry_price"),
            "drawdown_pct":     float(data.get("drawdown_pct", 0.0)),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Trade commands
    # ─────────────────────────────────────────────────────────────────────────

    async def send_decision(self, symbol: str, decision: str, **kwargs) -> bool:
        """Forward a trading decision to Pulse."""
        return await self._post(
            f"/api/tickers/{symbol}/decision",
            {"symbol": symbol, "decision": decision, **kwargs},
        )

    async def enable_trailing_stop(self, symbol: str, trailing_percent: float) -> bool:
        return await self.send_decision(
            symbol, "enable_trailing_stop", trailing_percent=trailing_percent
        )

    async def stop_buying(self, symbol: str) -> bool:
        return await self.send_decision(symbol, "stop_buying")

    async def emergency_stop(self, symbol: str) -> bool:
        return await self.send_decision(symbol, "emergency_stop")

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    async def get_tickers(self) -> list:
        """List tickers tracked by Pulse."""
        data = await self._get("/api/tickers")
        return data if isinstance(data, list) else []

    async def aclose(self):
        """Release the underlying connection pool. Call during app shutdown."""
        await self._client.aclose()
