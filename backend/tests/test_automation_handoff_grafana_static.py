"""Static checks for automation handoff visibility in Grafana."""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
BROKER_DASHBOARD = ROOT / "grafana" / "dashboards" / "broker_health.json"


class AutomationHandoffGrafanaStaticTests(unittest.TestCase):
    def test_broker_dashboard_surfaces_handoff_outcomes(self):
        dashboard = json.loads(BROKER_DASHBOARD.read_text(encoding="utf-8"))["dashboard"]
        panel_text = json.dumps(dashboard["panels"])
        expressions = {
            target["expr"]
            for panel in dashboard["panels"]
            for target in panel.get("targets", [])
            if "expr" in target
        }

        self.assertIn("Automation Handoff Outcomes", panel_text)
        self.assertIn("sent, failed, and suppressed Edge-to-Pulse handoff outcomes", panel_text)
        self.assertIn("edge_automation_handoffs:rate5m", expressions)
        self.assertIn("edge_automation_handoffs_total", panel_text)
        self.assertIn("{{result}} / {{reason}}", panel_text)


if __name__ == "__main__":
    unittest.main()
