"""Static checks for in-memory rate-limit state observability."""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"
METRICS = ROOT / "backend" / "metrics.py"
BROKER_DASHBOARD = ROOT / "grafana" / "dashboards" / "broker_health.json"


class RateLimitStateMetricsStaticTests(unittest.TestCase):
    def test_rate_limit_state_metrics_are_defined_without_client_labels(self):
        text = METRICS.read_text(encoding="utf-8")

        self.assertIn("edge_rate_limit_tracked_clients", text)
        self.assertIn("edge_rate_limit_pruned_clients_total", text)
        self.assertNotIn('["client"]', text)
        self.assertNotIn('["ip"]', text)

    def test_rate_limit_pruning_updates_metrics(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("edge_rate_limit_pruned_clients_total.inc(len(stale_clients))", text)
        self.assertIn("edge_rate_limit_tracked_clients.set(len(_rate_limit_buckets))", text)

    def test_broker_dashboard_surfaces_limiter_state(self):
        dashboard = json.loads(BROKER_DASHBOARD.read_text(encoding="utf-8"))["dashboard"]
        panel_text = json.dumps(dashboard["panels"])
        expressions = {
            target["expr"]
            for panel in dashboard["panels"]
            for target in panel.get("targets", [])
            if "expr" in target
        }

        self.assertIn("API Rate Limiter State", panel_text)
        self.assertIn("edge_rate_limit_tracked_clients", expressions)
        self.assertIn("increase(edge_rate_limit_pruned_clients_total[$__range])", expressions)


if __name__ == "__main__":
    unittest.main()
