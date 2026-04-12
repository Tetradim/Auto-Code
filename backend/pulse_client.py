"""Sentinel Pulse API Client — circuit-breaker HTTP client.

Pulse independence
──────────────────
Sentinel Edge is designed to run fully independently of Sentinel Pulse.
On startup, check_pulse() probes Pulse's /api/health endpoint once.
If Pulse is unreachable, pulse_available is set to False and all outbound
decision/override calls are silently suppressed (logged but not sent).
The circuit breaker then handles transient failures during normal operation.

The evaluation loop (ORB detection, signal scoring, risk management) runs
regardless of Pulse availability. Decisions are computed and logged; they
are only sent when Pulse is reachable.

Standalone mode
───────────────
  pulse_available = False → all send_* methods return False immediately
  pulse_available = True  → normal circuit-breaker behaviour

Pulse availability is re-checked automatically whenever the circuit breaker
transitions from OPEN to HALF_OPEN, so a later Pulse start is detected
without needing a restart.

Connection pooling
──────────────────
A single persistent AsyncClient is reused across all calls (keep-alive,
connection pooling). Call await pulse.aclose() during application shutdown.
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

HEALTH_PROBE_TIMEOUT = 3.0   # seconds — startup health check


class CircuitState(Enum):
    CLOSED    = 0   # normal operation
    HALF_OPEN = 1   # testing if Pulse recovered
    OPEN      = 2   # Pulse unreachable; requests suppressed


class PulseClient:
    """HTTP client for Sentinel Pulse with a circuit-breaker guard
    and an explicit pulse_available flag for standalone operation."""

    FAILURE_THRESHOLD     = 5
    SUCCESS_THRESHOLD     = 2
    TIMEOUT_SECONDS       = 5.0
    CIRCUIT_OPEN_DURATION = 60  # seconds before HALF_OPEN probe

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        api_key:  Optional[str] = None,
    ):
        self.base_url  = base_url.rstrip("/")
        self.api_key   = api_key
        self.broker_id = "pulse"

        # Availability flag — set by check_pulse() on startup
        # and re-evaluated when circuit moves to HALF_OPEN
        self.pulse_available: bool = False

        # Circuit breaker state
        self.state             = CircuitState.CLOSED
        self.failure_count     = 0
        self.success_count     = 0
        self.last_failure_time = 0.0

        # Persistent connection pool
        self._client = httpx.AsyncClient(
            timeout=self.TIMEOUT_SECONDS,
            headers=self._build_headers(),
        )

        broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
        broker_failure_rate.labels(broker_id=self.broker_id).set(0.0)
        logger.info("PulseClient initialised → %s (awaiting health probe)", self.base_url)

    # ─────────────────────────────────────────────────────────────────────────
    # Startup probe
    # ─────────────────────────────────────────────────────────────────────────

    async def check_pulse(self) -> bool:
        """Probe Pulse once. Safe to call at startup — never raises.

        Sets self.pulse_available and returns the same value.
        Called automatically by server.py lifespan before the scheduler starts.
        """
        url = f"{self.base_url}/api/health"
        try:
            async with httpx.AsyncClient(timeout=HEALTH_PROBE_TIMEOUT) as probe:
                resp = await probe.get(url)
            if resp.status_code == 200:
                self.pulse_available = True
                logger.info("✅ Pulse reachable @ %s — connected mode", self.base_url)
            else:
                self.pulse_available = False
                logger.warning(
                    "⚠️  Pulse returned HTTP %d — standalone mode", resp.status_code
                )
        except Exception as exc:
            self.pulse_available = False
            logger.warning(
                "⚠️  Pulse not reachable (%s) — Edge running in standalone mode. "
                "Signal analysis and ORB detection will run normally; "
                "decisions will be computed but not sent to Pulse.",
                exc,
            )
        return self.pulse_available

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-API-KEY"] = self.api_key
        return h

    def _should_allow_request(self) -> bool:
        """Gate: not available → False; circuit open → False; else True."""
        if not self.pulse_available:
            return False

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.CIRCUIT_OPEN_DURATION:
                logger.info("Circuit breaker → HALF_OPEN (re-probing Pulse)")
                self.state = CircuitState.HALF_OPEN
                broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
                return True
            return False

        return True   # HALF_OPEN

    def _record_success(self) -> None:
        self.failure_count = 0
        if not self.pulse_available:
            self.pulse_available = True
            logger.info("Pulse responded — switching to connected mode")
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.SUCCESS_THRESHOLD:
                logger.info("Circuit breaker → CLOSED after %d successes", self.success_count)
                self.state         = CircuitState.CLOSED
                self.success_count = 0
                broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)

    def _record_failure(self) -> None:
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
        if not self._should_allow_request():
            if self.pulse_available:
                logger.debug("Circuit %s — POST %s suppressed", self.state.name, endpoint)
            else:
                logger.debug("Standalone mode — POST %s suppressed", endpoint)
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
        if not self._should_allow_request():
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
                self._record_success()
                return None
            edge_api_calls_total.labels(endpoint=endpoint, status="failure").inc()
            self._record_failure()
            return None
        except httpx.TimeoutException:
            edge_api_calls_total.labels(endpoint=endpoint, status="timeout").inc()
            self._record_failure()
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

        Returns None when standalone, circuit open, Pulse 404, or any error.
        Callers should fall back to PositionTracker's self-sovereign state.
        """
        data = await self._get(f"/api/positions/{symbol}")
        if data is None:
            return None

        return {
            "has_position":     bool(data.get("has_position", data.get("active", False))),
            "pnl":              float(data.get("pnl",     data.get("unrealized_pnl",     0.0))),
            "pnl_pct":          float(data.get("pnl_pct", data.get("unrealized_pnl_pct", 0.0))),
            "trailing_enabled": bool(data.get("trailing_enabled", data.get("trailing_stop_enabled", False))),
            "trailing_percent": data.get("trailing_percent"),
            "entry_price":      data.get("entry_price"),
            "drawdown_pct":     float(data.get("drawdown_pct", 0.0)),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Trade commands — silently suppressed in standalone mode
    # ─────────────────────────────────────────────────────────────────────────

    async def send_decision(self, symbol: str, decision: str, **kwargs) -> bool:
        sent = await self._post(
            f"/api/tickers/{symbol}/decision",
            {"symbol": symbol, "decision": decision, **kwargs},
        )
        if not sent and not self.pulse_available:
            logger.info("STANDALONE: would have sent %s → %s", decision, symbol)
        return sent

    async def enable_trailing_stop(self, symbol: str, trailing_percent: float) -> bool:
        return await self.send_decision(
            symbol, "enable_trailing_stop", trailing_percent=trailing_percent
        )

    async def stop_buying(self, symbol: str) -> bool:
        return await self.send_decision(symbol, "stop_buying")

    async def emergency_stop(self, symbol: str) -> bool:
        return await self.send_decision(symbol, "emergency_stop")

    async def get_tickers(self) -> list:
        data = await self._get("/api/tickers")
        return data if isinstance(data, list) else []

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    async def aclose(self) -> None:
        """Release the connection pool. Call during app shutdown."""
        await self._client.aclose()
