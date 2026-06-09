"""Static checks for dependency-free Edge liveness endpoint."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"


class LivenessEndpointStaticTests(unittest.TestCase):
    def test_liveness_endpoint_is_dependency_free(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn('@api_router.get("/live")', text)
        self.assertIn("async def liveness", text)
        self.assertIn('"status": "alive"', text)
        self.assertIn('"uptime_seconds"', text)
        self.assertIn('"pid"', text)

        route_start = text.index('@api_router.get("/live")')
        route_end = text.index('@api_router.get("/health")')
        route_text = text[route_start:route_end]
        self.assertNotIn("_require_scheduler", route_text)
        self.assertNotIn("_readiness_checks", route_text)
        self.assertNotIn("price_fetcher", route_text)
        self.assertNotIn("db is not None", route_text)


if __name__ == "__main__":
    unittest.main()
