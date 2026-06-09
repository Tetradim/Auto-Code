"""Static checks for structured frontend API error handling."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "frontend" / "src" / "lib" / "api.ts"


class FrontendApiErrorStaticTests(unittest.TestCase):
    def test_fetch_json_throws_structured_api_error(self):
        text = API.read_text(encoding="utf-8")

        self.assertIn("export class ApiError extends Error", text)
        self.assertIn("status: number", text)
        self.assertIn("retryAfterSeconds?: number", text)
        self.assertIn("rateLimitLimit?: number", text)
        self.assertIn("rateLimitRemaining?: number", text)
        self.assertIn("rateLimitResetSeconds?: number", text)
        self.assertIn("throw new ApiError", text)
        self.assertNotIn("throw new Error(`HTTP ${res.status}: ${res.statusText}`)", text)

    def test_retry_after_is_preserved_from_header_or_body(self):
        text = API.read_text(encoding="utf-8")

        self.assertIn("parseRetryAfterSeconds", text)
        self.assertIn("res.headers.get('Retry-After')", text)
        self.assertIn("payload?.detail?.retry_after_seconds", text)
        self.assertIn("Number.isFinite", text)

    def test_rate_limit_budget_headers_are_preserved(self):
        text = API.read_text(encoding="utf-8")

        self.assertIn("parseRateLimitHeaders(res.headers)", text)
        self.assertIn("headers.get('RateLimit-Limit') ?? headers.get('X-RateLimit-Limit')", text)
        self.assertIn("headers.get('RateLimit-Remaining') ?? headers.get('X-RateLimit-Remaining')", text)
        self.assertIn("headers.get('RateLimit-Reset') ?? headers.get('X-RateLimit-Reset')", text)
        self.assertIn("rateLimitResetSeconds: parseRetryAfterSeconds", text)


if __name__ == "__main__":
    unittest.main()
