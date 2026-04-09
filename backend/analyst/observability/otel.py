"""OpenTelemetry setup for Sentinel Edge.

Gracefully degrades to no-op spans if OTel packages are unavailable
or OTEL_EXPORTER_OTLP_ENDPOINT is not set.
"""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def setup_otel(service_name: str = "sentinel-edge") -> None:
    """Configure the global TracerProvider.  Call once at startup."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {SERVICE_NAME: service_name, "service.version": "1.0.0"}
        )
        provider = TracerProvider(resource=resource)

        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
                exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("OTel OTLP exporter → %s", otlp_endpoint)
            except ImportError:
                logger.warning("OTLP exporter unavailable; traces not exported")

        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry tracing initialised for '%s'", service_name)

    except ImportError:
        logger.warning("opentelemetry not installed; tracing disabled")


def instrument_fastapi(app: Any) -> None:
    """Attach FastAPI auto-instrumentation (request spans)."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI OTel instrumentation enabled")
    except ImportError:
        pass


def get_tracer(name: str = "sentinel.edge") -> Any:
    """Return a live tracer or a no-op shim."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return _NoOpTracer()


class _NoOpTracer:
    """Silent stand-in when opentelemetry is absent."""

    class _ctx:
        def __enter__(self): return self
        def __exit__(self, *_): pass

    def start_as_current_span(self, name: str, **kwargs):
        return self._ctx()
