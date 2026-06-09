"""Static checks for frontend RUM freshness metrics."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class FrontendRumFreshnessStaticTests(unittest.TestCase):
    def test_backend_exports_freshness_and_route_count_gauges(self):
        metrics = read("backend/metrics.py")
        server = read("backend/server.py")

        self.assertIn("edge_frontend_rum_last_received_timestamp_seconds", metrics)
        self.assertIn("edge_frontend_rum_active_routes", metrics)
        self.assertIn("edge_frontend_rum_last_received_timestamp_seconds.set", server)
        self.assertIn("edge_frontend_rum_active_routes.set", server)

    def test_alerts_and_dashboard_use_timestamp_freshness(self):
        alerts = read("prometheus/alerts/sentinel_edge_rules.yml")
        dashboard = read("grafana/dashboards/frontend-experience.json")
        rules = read("prometheus/rules.yml")

        self.assertIn("time() - edge_frontend_rum_last_received_timestamp_seconds", rules)
        self.assertIn("edge_frontend_rum:freshness_seconds", alerts)
        self.assertIn("edge_frontend_rum:freshness_seconds", dashboard)


if __name__ == "__main__":
    unittest.main()
