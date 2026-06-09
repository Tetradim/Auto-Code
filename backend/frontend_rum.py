"""Helpers for frontend real-user monitoring ingestion."""
from datetime import datetime, timezone
from collections import OrderedDict
from urllib.parse import urlparse
import re


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_LONG_ID_RE = re.compile(r"^(?:[0-9]+|[a-z0-9_-]{16,})$", re.IGNORECASE)
_SYMBOL_SEGMENT_RE = re.compile(r"^[A-Z]{1,6}(?:[.-][A-Z]{1,2})?$")
_SYMBOL_PARENT_SEGMENTS = {"positions", "tickers", "ticker", "symbol", "symbols"}


class FrontendRumRegistry:
    """Small in-memory status registry for recent frontend RUM ingestion."""

    def __init__(self, max_routes: int = 25):
        self.max_routes = max(1, max_routes)
        self._routes: OrderedDict[str, dict] = OrderedDict()
        self._sample_count = 0
        self._last_received_at: datetime | None = None
        self._last_route = "/"

    def record(
        self,
        route: str,
        metrics: int = 0,
        slow_interactions: int = 0,
        long_tasks: int = 0,
        received_at: datetime | None = None,
    ) -> str:
        normalised_route = normalise_rum_route(route)
        now = received_at or datetime.now(timezone.utc)
        previous = self._routes.pop(normalised_route, None)
        samples = int(previous["samples"]) + 1 if previous else 1

        self._routes[normalised_route] = {
            "route": normalised_route,
            "samples": samples,
            "metrics": int(metrics),
            "slow_interactions": int(slow_interactions),
            "long_tasks": int(long_tasks),
            "last_received_at": _iso(now),
        }
        while len(self._routes) > self.max_routes:
            self._routes.popitem(last=False)

        self._sample_count += 1
        self._last_received_at = now
        self._last_route = normalised_route
        return normalised_route

    def status(self, now: datetime | None = None) -> dict:
        current = now or datetime.now(timezone.utc)
        age = None
        if self._last_received_at is not None:
            age = max(0.0, (current - self._last_received_at).total_seconds())

        return {
            "status": "receiving" if self._last_received_at is not None else "waiting",
            "sample_count": self._sample_count,
            "route_count": len(self._routes),
            "last_route": self._last_route if self._last_received_at is not None else None,
            "last_received_at": _iso(self._last_received_at) if self._last_received_at else None,
            "seconds_since_last": age,
            "routes": list(reversed(self._routes.values())),
        }


def normalise_rum_route(raw_route: str, limit: int = 80) -> str:
    """Return a bounded, low-cardinality route label for RUM metrics."""
    parsed = urlparse(str(raw_route or "/"))
    path = parsed.path or "/"
    parts = [part for part in path.split("/") if part]
    normalised: list[str] = []

    for index, part in enumerate(parts):
        previous = normalised[index - 1].lower() if index > 0 else ""
        if _is_dynamic_segment(part, previous):
            normalised.append(":symbol" if previous in _SYMBOL_PARENT_SEGMENTS and _SYMBOL_SEGMENT_RE.match(part) else ":id")
        else:
            normalised.append(_clean_segment(part))

    route = "/" + "/".join(part for part in normalised if part)
    route = route[:limit].rstrip("/")
    return route or "/"


def metric_label(value: str, fallback: str = "unknown", limit: int = 80) -> str:
    """Bound and sanitize generic Prometheus labels."""
    cleaned = re.sub(r"[^A-Za-z0-9_./:-]+", "_", str(value or "").strip())
    return (cleaned[:limit] or fallback).lower()


def _is_dynamic_segment(part: str, previous: str) -> bool:
    if _UUID_RE.match(part) or _LONG_ID_RE.match(part):
        return True
    if previous in _SYMBOL_PARENT_SEGMENTS and _SYMBOL_SEGMENT_RE.match(part):
        return True
    return False


def _clean_segment(part: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", part).lower()[:40]


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
