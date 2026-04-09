"""OpenTelemetry setup for Sentinel Edge.

Uses the gRPC OTLP exporter (port 4317) which Grafana Tempo expects.
Falls back gracefully when packages are absent or Tempo is unreachable.
"""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def setup_otel(service_name: str = "sentinel-edge") -> None:
    """Configure the global TracerProvider with gRPC OTLP exporter.

    Auto-instruments httpx and asyncio when the instrumentation packages
    are present.  All steps are wrapped in try/except so a missing package
    or unavailable Tempo never prevents the application from starting.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {SERVICE_NAME: service_name, "service.version": "1.0.0"}
        )
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # gRPC OTLP → Tempo (port 4317)
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317")
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTel gRPC OTLP exporter → %s", otlp_endpoint)
        except ImportError:
            logger.warning("gRPC OTLP exporter unavailable; traces not exported")

        # Auto-instrument httpx outbound requests
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
            logger.debug("HTTPXClientInstrumentor active")
        except ImportError:
            pass

        # Auto-instrument asyncio tasks
        try:
            from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
            AsyncioInstrumentor().instrument()
            logger.debug("AsyncioInstrumentor active")
        except ImportError:
            pass

        logger.info("✅ OpenTelemetry initialized for '%s'", service_name)

    except ImportError:
        logger.warning("opentelemetry not installed; tracing disabled")


def instrument_fastapi(app: Any) -> None:
    """Attach FastAPI request-span instrumentation."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI OTel instrumentation enabled")
    except ImportError:
        pass


def get_tracer(name: str = "sentinel.edge") -> Any:
    """Return a live OTel tracer or a no-op shim."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return _NoOpTracer()


class _NoOpTracer:
    class _ctx:
        def __enter__(self): return self
        def __exit__(self, *_): pass

    def start_as_current_span(self, name: str, **kwargs):
        return self._ctx()
