"""Rich Prometheus exporter with pluggable collectors — Sentinel Edge"""
import logging
from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram, start_http_server as _start_http_server

if TYPE_CHECKING:
    from analyst.signals.base import Signal

logger = logging.getLogger(__name__)

# ── Analyst-specific metrics ──────────────────────────────────────────────────
# These live on the default REGISTRY so they are exposed by the existing
# FastAPI /metrics endpoint (port 8001).  When running as a standalone service,
# call PrometheusExporter(start_server=True) to spin up a dedicated port 8002.

orb_breakouts = Counter(
    "analyst_orb_breakouts_total",
    "ORB breakouts detected by the analyst",
    ["timeframe", "direction", "symbol"],
)

atr_gauge = Gauge(
    "analyst_atr_value",
    "ATR value per symbol as seen by the analyst",
    ["symbol"],
)

pulse_overrides = Counter(
    "analyst_pulse_overrides_total",
    "Override commands sent to Pulse",
    ["action"],
)

signal_latency = Histogram(
    "analyst_signal_latency_seconds",
    "Time taken to generate a signal",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)


class PrometheusExporter:
    """
    Pluggable Prometheus exporter.

    In the integrated FastAPI setup (default) the metrics surface at /metrics
    on the existing port 8001 — no extra server is started.

    For standalone / Docker deployments pass start_server=True to bind a
    dedicated Prometheus scrape endpoint on `port` (default 8002).
    """

    def __init__(self, start_server: bool = False, port: int = 8002):
        if start_server:
            try:
                _start_http_server(port)
                logger.info("📊 Prometheus exporter started on :%d/metrics", port)
            except OSError as exc:
                logger.warning(
                    "Could not start metrics server on :%d (%s) — "
                    "metrics available via existing /metrics endpoint",
                    port, exc,
                )

    # ── Record helpers ────────────────────────────────────────────────────

    def record_signal(self, symbol: str, signal: "Signal") -> None:
        """Push a Signal into Prometheus counters / gauges."""
        try:
            orb_breakouts.labels(
                timeframe=signal.timeframe,
                direction=signal.action.lower(),
                symbol=symbol,
            ).inc()
            if signal.atr > 0:
                atr_gauge.labels(symbol=symbol).set(signal.atr)
        except Exception as exc:
            logger.debug("record_signal error: %s", exc)

    def record_override(self, action: str) -> None:
        try:
            pulse_overrides.labels(action=action).inc()
        except Exception as exc:
            logger.debug("record_override error: %s", exc)

    def record_evaluation(self, symbol: str, duration_seconds: float) -> None:
        """Delegate eval timing to the existing edge_eval_duration histogram."""
        try:
            from metrics import edge_eval_duration
            edge_eval_duration.labels(symbol=symbol).observe(duration_seconds)
        except Exception as exc:
            logger.debug("record_evaluation error: %s", exc)
