"""Static checks for API rate-limit bucket pressure alerting."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
RULES = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "api-rate-limit-bucket-pressure.md"


class RateLimitBucketPressureAlertStaticTests(unittest.TestCase):
    def test_bucket_pressure_has_recording_rule(self):
        text = RULES.read_text(encoding="utf-8")

        self.assertIn("api_observability_rules", text)
        self.assertIn("edge_rate_limit_tracked_clients:max5m", text)
        self.assertIn("max_over_time(edge_rate_limit_tracked_clients[5m])", text)

    def test_bucket_pressure_has_warning_alert(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("ApiRateLimitBucketPressure", text)
        self.assertIn("edge_rate_limit_tracked_clients:max5m > 500", text)
        self.assertIn("for: 5m", text)
        self.assertIn("component: api", text)
        self.assertIn("severity: warning", text)
        self.assertIn("Tracked API rate-limit buckets", text)
        self.assertIn('runbook_url: "docs/runbooks/api-rate-limit-bucket-pressure.md"', text)

    def test_bucket_pressure_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "API rate-limit bucket pressure runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("ApiRateLimitBucketPressure", text)
        self.assertIn("edge_rate_limit_tracked_clients:max5m", text)
        self.assertIn("/api/rate-limit/status", text)
        self.assertIn("backend/rate_limit.py", text)
        self.assertIn("scan traffic", text)


if __name__ == "__main__":
    unittest.main()
