"""Static checks for Grafana readiness visibility."""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
BROKER_DASHBOARD = ROOT / "grafana" / "dashboards" / "broker_health.json"


class ReadinessGrafanaStaticTests(unittest.TestCase):
    def test_broker_dashboard_surfaces_edge_readiness(self):
        dashboard = json.loads(BROKER_DASHBOARD.read_text(encoding="utf-8"))["dashboard"]
        panels = dashboard["panels"]
        panel_text = json.dumps(panels)
        expressions = {
            target["expr"]
            for panel in panels
            for target in panel.get("targets", [])
            if "expr" in target
        }

        self.assertIn("Edge Readiness Checks", panel_text)
        self.assertIn("state-timeline", panel_text)
        self.assertIn("edge_readiness_status", expressions)
        self.assertIn("edge_readiness_check_status", expressions)
        self.assertIn("{{check}}", panel_text)


if __name__ == "__main__":
    unittest.main()
