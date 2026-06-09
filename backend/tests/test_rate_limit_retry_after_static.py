"""Static checks for helpful API rate-limit retry responses."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"


class RateLimitRetryAfterStaticTests(unittest.TestCase):
    def test_rate_limit_429_includes_retry_after_header(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("retry_after_seconds", text)
        self.assertIn('"Retry-After": str(retry_after_seconds)', text)
        self.assertIn("headers={", text)
        self.assertIn("status_code=429", text)

    def test_rate_limit_429_includes_budget_headers(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn('"RateLimit-Limit": str(_RATE_LIMIT_MAX_REQUESTS)', text)
        self.assertIn('"RateLimit-Remaining": "0"', text)
        self.assertIn('"RateLimit-Reset": str(retry_after_seconds)', text)
        self.assertIn('"X-RateLimit-Limit": str(_RATE_LIMIT_MAX_REQUESTS)', text)
        self.assertIn('"X-RateLimit-Remaining": "0"', text)
        self.assertIn('"X-RateLimit-Reset": str(retry_after_seconds)', text)

    def test_retry_after_is_derived_from_fixed_window_reset(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("recent[0] + _RATE_LIMIT_WINDOW_SECONDS - now", text)
        self.assertIn("max(1,", text)
        self.assertIn("min(_RATE_LIMIT_WINDOW_SECONDS,", text)


if __name__ == "__main__":
    unittest.main()
