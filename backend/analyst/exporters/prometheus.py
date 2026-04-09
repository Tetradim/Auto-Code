"""Pluggable Prometheus exporter for Sentinel Edge signals."""
import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from analyst.signals.base import Signal


class PrometheusExporter:
    """
    Thin adapter that maps analyst Signal objects onto the existing
    Prometheus gauges already defined in metrics.py.

    Subclass and override ``record_signal`` to add custom collectors
    without touching the core evaluation loop.
    """

    def record_signal(self, symbol: str, signal: "Signal") -> None:
        """Push signal data into existing Prometheus metrics."""
        try:
            from metrics import edge_signal_strength, edge_trend_direction
            if signal.signal_strength:
                edge_signal_strength.labels(symbol=symbol).set(signal.signal_strength)
        except Exception as exc:
            logger.debug("PrometheusExporter.record_signal error: %s", exc)

    def record_evaluation(self, symbol: str, duration_seconds: float) -> None:
        """Record evaluation timing."""
        try:
            from metrics import edge_eval_duration
            edge_eval_duration.labels(symbol=symbol).observe(duration_seconds)
        except Exception as exc:
            logger.debug("PrometheusExporter.record_evaluation error: %s", exc)

    def record_cluster(self, direction: str, strength: str) -> None:
        """Record a correlation cluster detection."""
        try:
            from metrics import correlation_clusters_total
            correlation_clusters_total.labels(
                direction=direction.lower(), strength=strength
            ).inc()
        except Exception as exc:
            logger.debug("PrometheusExporter.record_cluster error: %s", exc)
