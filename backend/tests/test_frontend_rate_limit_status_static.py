"""Static checks for frontend API rate-limit status visibility."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "frontend" / "src" / "lib" / "api.ts"
EXPERIENCE_DASHBOARD = ROOT / "frontend" / "src" / "components" / "dashboards" / "ExperienceDashboard.tsx"


class FrontendRateLimitStatusStaticTests(unittest.TestCase):
    def test_api_client_exposes_rate_limit_status(self):
        text = API.read_text(encoding="utf-8")

        self.assertIn("export interface RateLimitStatus", text)
        self.assertIn("tracked_clients: number", text)
        self.assertIn("remaining_requests: number", text)
        self.assertIn("reset_seconds: number", text)
        self.assertIn("pressure: 'normal' | 'warning'", text)
        self.assertIn("async getRateLimitStatus()", text)
        self.assertIn("'/api/rate-limit/status'", text)

    def test_experience_dashboard_surfaces_rate_limit_status(self):
        text = EXPERIENCE_DASHBOARD.read_text(encoding="utf-8")

        self.assertIn("const [rateLimitStatus, setRateLimitStatus]", text)
        self.assertIn("api.getRateLimitStatus()", text)
        self.assertIn("API Limiter", text)
        self.assertIn("Pressure", text)
        self.assertIn("rateLimitStatus?.tracked_clients", text)
        self.assertIn("rateLimitStatus?.remaining_requests", text)
        self.assertIn("rateLimitStatus ? `${rateLimitStatus.reset_seconds}s`", text)
        self.assertIn("formatRateLimitPressure", text)


if __name__ == "__main__":
    unittest.main()
