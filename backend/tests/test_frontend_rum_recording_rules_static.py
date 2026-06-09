"""Static checks for frontend RUM Prometheus recording rules."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class FrontendRumRecordingRulesStaticTests(unittest.TestCase):
    def test_rum_recording_rules_precompute_common_queries(self):
        rules = read("prometheus/rules.yml")

        self.assertIn("edge_frontend_rum:freshness_seconds", rules)
        self.assertIn("edge_frontend_rum:ingest_rate_per_minute", rules)
        self.assertIn("edge_frontend_slow_interaction:p95_ms", rules)
        self.assertIn("edge_frontend_long_task:p95_ms", rules)
        self.assertIn("histogram_quantile(0.95", rules)

    def test_dashboard_and_alerts_use_recorded_rum_series(self):
        dashboard = read("grafana/dashboards/frontend-experience.json")
        alerts = read("prometheus/alerts/sentinel_edge_rules.yml")

        self.assertIn("edge_frontend_rum:freshness_seconds", dashboard)
        self.assertIn("edge_frontend_rum:ingest_rate_per_minute", dashboard)
        self.assertIn("edge_frontend_slow_interaction:p95_ms", dashboard)
        self.assertIn("edge_frontend_long_task:p95_ms", dashboard)
        self.assertIn("edge_frontend_rum:freshness_seconds > 1800", alerts)
        self.assertIn("edge_frontend_slow_interaction:p95_ms > 500", alerts)


if __name__ == "__main__":
    unittest.main()
