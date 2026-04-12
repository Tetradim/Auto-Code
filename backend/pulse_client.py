"""Sentinel Pulse API Client — circuit-breaker HTTP client."""

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
from retry_queue import DecisionQueue

logger = logging.getLogger(__name__)

HEALTH_PROBE_TIMEOUT = 3.0


class CircuitState(Enum):
    CLOSED = 0
    HALF_OPEN = 1
    OPEN = 2


class PulseClient:
    """HTTP client for Sentinel Pulse with circuit breaker and retry queue."""

    FAILURE_THRESHOLD = 5
    SUCCESS_THRESHOLD = 2
    TIMEOUT_SECONDS = 5.0
    CIRCUIT_OPEN_DURATION = 60
    DEFAULT_RETRY_TTL_SECONDS = 60.0
    EMERGENCY_EXIT_RETRY_TTL_SECONDS = 300.0

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        api_key: Optional[str] = None,
        retry_queue_log_dir: str = "/app/logs",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.broker_id = "pulse"

        self.pulse_available: bool = False
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0

        self._client = httpx.AsyncClient(
            timeout=self.TIMEOUT_SECONDS,
            headers=self._build_headers(),
        )
        self.retry_queue = DecisionQueue(
            log_dir=retry_queue_log_dir,
            default_ttl_seconds=self.DEFAULT_RETRY_TTL_SECONDS,
            emergency_ttl_seconds=self.EMERGENCY_EXIT_RETRY_TTL_SECONDS,
        )

        broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
        broker_failure_rate.labels(broker_id=self.broker_id).set(0.0)
        logger.info("PulseClient initialised → %s (awaiting health probe)", self.base_url)

    async def check_pulse(self) -> bool:
        url = f"{self.base_url}/api/health"
        try:
            async with httpx.AsyncClient(timeout=HEALTH_PROBE_TIMEOUT) as probe:
                resp = await probe.get(url)
            if resp.status_code == 200:
                self.pulse_available = True
                logger.info("pulse_health_check ok base_url=%s", self.base_url)
            else:
                self.pulse_available = False
                logger.warning(
                    "pulse_health_check non_200 status=%d base_url=%s",
                    resp.status_code,
                    self.base_url,
                )
        except Exception as exc:
            self.pulse_available = False
            logger.warning(
                "pulse_health_check error=%s mode=standalone",
                exc,
            )
        return self.pulse_available

    def start_retry_drain_loop(self) -> None:
        self.retry_queue.start(
            can_send=lambda: self.state == CircuitState.CLOSED and self.pulse_available,
            send_func=self._post,
        )

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        return headers

    def _should_allow_request(self) -> bool:
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

        return True

    def _record_success(self) -> None:
        self.failure_count = 0
        if not self.pulse_available:
            self.pulse_available = True
            logger.info("Pulse responded — switching to connected mode")

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.SUCCESS_THRESHOLD:
                logger.info("Circuit breaker → CLOSED after %d successes", self.success_count)
                self.state = CircuitState.CLOSED
                self.success_count = 0
                broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
                self.retry_queue.notify_circuit_closed()

    def _record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        if self.failure_count >= self.FAILURE_THRESHOLD:
            logger.error("Circuit breaker → OPEN after %d failures", self.failure_count)
            self.state = CircuitState.OPEN
            broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)

        total = max(self.failure_count, 1)
        broker_failure_rate.labels(broker_id=self.broker_id).set((self.failure_count / total) * 100)

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> bool:
        if not self._should_allow_request():
            if self.pulse_available:
                logger.debug("Circuit %s — POST %s suppressed", self.state.name, endpoint)
            else:
                logger.debug("Standalone mode — POST %s suppressed", endpoint)
            return False

        url = f"{self.base_url}{endpoint}"
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

        url = f"{self.base_url}{endpoint}"
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

    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        data = await self._get(f"/api/positions/{symbol}")
        if data is None:
            return None

        return {
            "has_position": bool(data.get("has_position", data.get("active", False))),
            "pnl": float(data.get("pnl", data.get("unrealized_pnl", 0.0))),
            "pnl_pct": float(data.get("pnl_pct", data.get("unrealized_pnl_pct", 0.0))),
            "trailing_enabled": bool(data.get("trailing_enabled", data.get("trailing_stop_enabled", False))),
            "trailing_percent": data.get("trailing_percent"),
            "entry_price": data.get("entry_price"),
            "drawdown_pct": float(data.get("drawdown_pct", 0.0)),
        }

    async def send_decision(self, symbol: str, decision: str, **kwargs) -> bool:
        endpoint = f"/api/tickers/{symbol}/decision"
        payload = {"symbol": symbol, "decision": decision, **kwargs}
        sent = await self._post(endpoint, payload)
        if (not sent) and self.pulse_available and self.state == CircuitState.OPEN:
            await self.retry_queue.enqueue(symbol, decision, endpoint, payload)
        if not sent and not self.pulse_available:
            logger.info("STANDALONE: would have sent %s → %s", decision, symbol)
        return sent

    async def enable_trailing_stop(self, symbol: str, trailing_percent: float) -> bool:
        return await self.send_decision(symbol, "enable_trailing_stop", trailing_percent=trailing_percent)

    async def stop_buying(self, symbol: str) -> bool:
        return await self.send_decision(symbol, "stop_buying")

    async def emergency_stop(self, symbol: str) -> bool:
        return await self.send_decision(symbol, "emergency_stop")

    async def get_tickers(self) -> list:
        data = await self._get("/api/tickers")
        return data if isinstance(data, list) else []

    def queue_stats(self) -> Dict[str, Any]:
        return self.retry_queue.stats()

    async def queue_snapshot(self, limit: int = 100) -> list[Dict[str, Any]]:
        return await self.retry_queue.snapshot(limit=limit)

    async def aclose(self) -> None:
        await self.retry_queue.flush_to_file()
        await self.retry_queue.stop()
        await self._client.aclose()
