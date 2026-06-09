"""Static checks for aggregate API rate-limit status endpoint."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"


class RateLimitStatusEndpointStaticTests(unittest.TestCase):
    def test_status_endpoint_exposes_aggregate_limiter_state(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn('@api_router.get("/rate-limit/status")', text)
        self.assertIn("async def get_rate_limit_status(request: Request):", text)
        self.assertIn("tracked_clients = len(_rate_limit_buckets)", text)
        self.assertIn('"tracked_clients": tracked_clients', text)
        self.assertIn('"window_seconds": _RATE_LIMIT_WINDOW_SECONDS', text)
        self.assertIn('"max_requests_per_window": _RATE_LIMIT_MAX_REQUESTS', text)
        self.assertIn('"bucket_pressure_warning_threshold": _RATE_LIMIT_BUCKET_PRESSURE_WARNING_THRESHOLD', text)
        self.assertIn('"pressure": _rate_limit_pressure(tracked_clients)', text)
        self.assertIn('"remaining_requests": _rate_limit_remaining(request)', text)
        self.assertIn('"reset_seconds": _rate_limit_reset_seconds(request, time.time())', text)

    def test_status_endpoint_classifies_bucket_pressure(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("_RATE_LIMIT_BUCKET_PRESSURE_WARNING_THRESHOLD = 500", text)
        self.assertIn("def _rate_limit_pressure(tracked_clients: int) -> str:", text)
        self.assertIn("tracked_clients >= _RATE_LIMIT_BUCKET_PRESSURE_WARNING_THRESHOLD", text)
        self.assertIn('return "warning"', text)
        self.assertIn('return "normal"', text)

    def test_status_endpoint_reports_current_caller_budget_without_identity(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("def _rate_limit_remaining(request: Request) -> int:", text)
        self.assertIn("def _rate_limit_reset_seconds(request: Request, now: float) -> int:", text)
        self.assertIn("max(0, _RATE_LIMIT_MAX_REQUESTS - len(recent))", text)
        self.assertIn("int(recent[0] + _RATE_LIMIT_WINDOW_SECONDS - now) + 1", text)

    def test_status_endpoint_does_not_return_client_identifiers(self):
        text = SERVER.read_text(encoding="utf-8")
        start = text.index('async def get_rate_limit_status(request: Request):')
        endpoint = text[start:text.index('@api_router.get("/stats")', start)]

        self.assertNotIn("request.client.host", endpoint)
        self.assertNotIn("_rate_limit_buckets.keys()", endpoint)
        self.assertNotIn("client_ip", endpoint)
        self.assertNotIn('"clients"', endpoint)


if __name__ == "__main__":
    unittest.main()
