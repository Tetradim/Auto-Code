"""Sentinel Edge — Main orchestrator (analyst/core.py)

SentinelEdge wraps the existing EvaluationScheduler and adds:
  - OpenTelemetry distributed tracing
  - Bidirectional WebSocket connection to Pulse
  - MongoDB Change Streams for cross-service commands
  - Pluggable PrometheusExporter
  - Graceful degradation when ancillary services are unavailable
"""
import asyncio
import json
import logging
import os
from typing import Optional, Any

import httpx

from analyst.correlation.engine import CorrelationEngine
from analyst.exporters.prometheus import PrometheusExporter
from analyst.observability.otel import setup_otel, get_tracer

logger = logging.getLogger(__name__)


class SentinelEdge:
    """
    Top-level orchestrator for Sentinel Edge.

    Usage in server.py lifespan
    ────────────────────────────
        edge = SentinelEdge(db=db, pulse_url=os.getenv("PULSE_API_URL", "..."))
        edge.set_scheduler(scheduler)          # wire the evaluation scheduler
        await edge.start_background_tasks()    # WebSocket + change stream
        yield
        edge.stop()
    """

    def __init__(
        self,
        db=None,
        pulse_url: str = "http://pulse:8001",
        window_sec: int = 120,
        min_symbols: int = 3,
        cooldown_sec: int = 300,
    ):
        self.db = db
        self.pulse_url = pulse_url

        # OpenTelemetry (no-op shim when packages absent / OTLP not configured)
        setup_otel("sentinel-edge")
        self.tracer = get_tracer("sentinel.edge")

        # Pluggable Prometheus exporter
        # Set ANALYST_START_METRICS_SERVER=true to expose :8002/metrics separately
        start_server = os.getenv("ANALYST_START_METRICS_SERVER", "false").lower() == "true"
        self.prom_exporter = PrometheusExporter(start_server=start_server, port=8002)

        # Correlation engine (shared with scheduler via set_scheduler)
        self.correlation = CorrelationEngine(
            db=db,
            pulse_base_url=pulse_url,
            window_sec=window_sec,
            min_symbols=min_symbols,
            cooldown_sec=cooldown_sec,
        )

        self._running = False
        self._scheduler: Optional[Any] = None
        self._bg_tasks: list = []

    # ── Wiring ───────────────────────────────────────────────────────────

    def set_scheduler(self, scheduler: Any) -> None:
        """Wire the existing EvaluationScheduler.
        Replaces the scheduler's own CorrelationEngine with this one so both
        the main loop and SentinelEdge share a single event window.
        """
        self._scheduler = scheduler
        scheduler.correlation = self.correlation
        logger.info("SentinelEdge wired to EvaluationScheduler")

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def start_background_tasks(self) -> None:
        """Launch ancillary async tasks without blocking the caller."""
        self._running = True
        self._bg_tasks = [
            asyncio.create_task(self._connect_pulse_ws(),   name="edge-pulse-ws"),
            asyncio.create_task(self._watch_mongo_commands(), name="edge-mongo-stream"),
        ]
        logger.info("SentinelEdge background tasks started (WS + change stream)")

    def stop(self) -> None:
        self._running = False
        for task in self._bg_tasks:
            task.cancel()
        self._bg_tasks.clear()
        logger.info("SentinelEdge stopped")

    # ── Pulse WebSocket (bidirectional) ──────────────────────────────────

    async def _connect_pulse_ws(self) -> None:
        while self._running:
            ws_url = (
                self.pulse_url
                .replace("https://", "wss://")
                .replace("http://", "ws://")
            ) + "/ws/analyst"
            try:
                import websockets  # optional dependency
                async with websockets.connect(
                    ws_url,
                    open_timeout=5,
                    ping_interval=20,
                    ping_timeout=20,
                ) as ws:
                    logger.info("✅ WebSocket connected to Pulse @ %s", ws_url)
                    while self._running:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=30)
                            await self._handle_pulse_message(json.loads(raw))
                        except asyncio.TimeoutError:
                            continue
            except ImportError:
                logger.warning("websockets not installed — Pulse WS disabled")
                return
            except Exception as exc:
                logger.debug("Pulse WS unavailable (%s) — retry in 10 s", exc)
                await asyncio.sleep(10)

    async def _handle_pulse_message(self, data: dict) -> None:
        msg_type = data.get("type", "")
        symbol = data.get("symbol", "")

        with self.tracer.start_as_current_span("edge.handle_pulse_message"):
            if msg_type == "ORDER_FILLED" and symbol:
                action = "BUY" if data.get("side") == "buy" else "SELL"
                await self.correlation.record_signal(symbol, action, confidence=0.8)

            elif msg_type == "SIGNAL_UPDATE" and symbol:
                action = data.get("action", "BUY")
                confidence = float(data.get("confidence", 1.0))
                await self.correlation.record_signal(symbol, action, confidence)

            elif msg_type == "OVERRIDE_ACK":
                logger.info("Pulse acknowledged override: %s", data)

    # ── MongoDB Change Streams (command bus) ─────────────────────────────

    async def _watch_mongo_commands(self) -> None:
        """Watch `analyst_commands` collection for cross-service messages.
        Pulse (or any service) can insert a document here to trigger actions
        without a direct API call — a lightweight command bus pattern.
        """
        if self.db is None:
            return
        while self._running:
            try:
                pipeline = [{"$match": {"operationType": "insert"}}]
                async with self.db.analyst_commands.watch(pipeline) as stream:
                    logger.info("MongoDB change stream watching 'analyst_commands'")
                    async for change in stream:
                        doc = change.get("fullDocument", {})
                        await self._handle_db_command(doc)
            except Exception as exc:
                logger.debug("Change stream error (%s) — retry in 15 s", exc)
                await asyncio.sleep(15)

    async def _handle_db_command(self, doc: dict) -> None:
        cmd = doc.get("command", "")
        logger.info("DB command received: %s", cmd)

        if cmd == "pause" and self._scheduler:
            self._scheduler.pause()
        elif cmd == "resume" and self._scheduler:
            self._scheduler.resume()
        elif cmd == "add_ticker" and self._scheduler:
            symbol = doc.get("symbol", "").upper()
            if symbol:
                self._scheduler.add_ticker(symbol)
        elif cmd == "remove_ticker" and self._scheduler:
            symbol = doc.get("symbol", "").upper()
            if symbol:
                self._scheduler.remove_ticker(symbol)
        elif cmd == "override":
            await self.send_override(doc.get("action", ""), doc)

    # ── Pulse REST override (fallback / manual) ───────────────────────────

    async def send_override(self, action: str, payload: dict) -> None:
        """Send a command to Pulse over REST. Used as fallback or for
        manual overrides triggered from the dashboard command bus."""
        with self.tracer.start_as_current_span("edge.send_override"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        f"{self.pulse_url}/control/override",
                        json={"source": "sentinel-edge", "action": action, **payload},
                    )
            except Exception as exc:
                logger.error("Pulse REST override failed: %s", exc)
