"""Unit tests for frontend RUM ingestion status tracking."""
from datetime import datetime, timezone
import unittest

from backend.frontend_rum import FrontendRumRegistry


class FrontendRumStatusTests(unittest.TestCase):
    def test_registry_tracks_latest_snapshot_by_normalised_route(self):
        registry = FrontendRumRegistry(max_routes=3)
        now = datetime(2026, 6, 8, 8, 59, tzinfo=timezone.utc)

        registry.record(
            "/orders/123",
            metrics=4,
            slow_interactions=1,
            long_tasks=2,
            received_at=now,
        )
        registry.record(
            "/orders/456",
            metrics=2,
            slow_interactions=0,
            long_tasks=0,
            received_at=now,
        )

        status = registry.status(now=now)
        self.assertEqual(status["route_count"], 1)
        self.assertEqual(status["sample_count"], 2)
        self.assertEqual(status["last_route"], "/orders/:id")
        self.assertEqual(status["routes"][0]["samples"], 2)
        self.assertEqual(status["routes"][0]["metrics"], 2)
        self.assertEqual(status["routes"][0]["slow_interactions"], 0)

    def test_registry_bounds_route_count(self):
        registry = FrontendRumRegistry(max_routes=2)
        now = datetime(2026, 6, 8, 8, 59, tzinfo=timezone.utc)

        registry.record("/settings", metrics=1, received_at=now)
        registry.record("/positions/AAPL", metrics=1, received_at=now)
        registry.record("/orders/123", metrics=1, received_at=now)

        status = registry.status(now=now)
        self.assertEqual(status["route_count"], 2)
        self.assertEqual([route["route"] for route in status["routes"]], ["/orders/:id", "/positions/:symbol"])


if __name__ == "__main__":
    unittest.main()
