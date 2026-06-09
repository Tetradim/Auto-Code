"""Static checks for browser-visible rate-limit response headers."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"


class RateLimitCorsHeadersStaticTests(unittest.TestCase):
    def test_cors_exposes_rate_limit_headers_to_browser_clients(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("expose_headers=[", text)
        self.assertIn('"Retry-After"', text)
        self.assertIn('"RateLimit-Limit"', text)
        self.assertIn('"RateLimit-Remaining"', text)
        self.assertIn('"RateLimit-Reset"', text)
        self.assertIn('"X-RateLimit-Limit"', text)
        self.assertIn('"X-RateLimit-Remaining"', text)
        self.assertIn('"X-RateLimit-Reset"', text)


if __name__ == "__main__":
    unittest.main()
