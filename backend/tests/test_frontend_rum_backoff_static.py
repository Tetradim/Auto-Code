"""Static checks for frontend RUM backoff after API rate limits."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
EXPERIENCE_DASHBOARD = ROOT / "frontend" / "src" / "components" / "dashboards" / "ExperienceDashboard.tsx"


class FrontendRumBackoffStaticTests(unittest.TestCase):
    def test_rum_ingest_respects_retry_after_from_api_error(self):
        text = EXPERIENCE_DASHBOARD.read_text(encoding="utf-8")

        self.assertIn("ApiError", text)
        self.assertIn("nextRumPostAfter", text)
        self.assertIn("error instanceof ApiError", text)
        self.assertIn("error.status === 429", text)
        self.assertIn("error.retryAfterSeconds", text)
        self.assertIn("Date.now() + error.retryAfterSeconds * 1000", text)

    def test_rate_limited_state_is_visible_in_ingest_status(self):
        text = EXPERIENCE_DASHBOARD.read_text(encoding="utf-8")

        self.assertIn("'rate-limited'", text)
        self.assertIn("setRetryAfterSeconds", text)
        self.assertIn("formatIngestStatus(ingestStatus, retryAfterSeconds)", text)


if __name__ == "__main__":
    unittest.main()
