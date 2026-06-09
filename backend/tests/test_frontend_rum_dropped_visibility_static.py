"""Static checks for visibility into dropped frontend RUM samples."""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
DASHBOARD = ROOT / "grafana" / "dashboards" / "frontend-experience.json"
DROPPED_RUNBOOK = ROOT / "docs" / "runbooks" / "frontend-rum-dropped-metrics.md"


class FrontendRumDroppedVisibilityStaticTests(unittest.TestCase):
    def test_alert_fires_when_rum_metrics_are_dropped(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("FrontendRumDroppedMetrics", text)
        self.assertIn('increase(edge_frontend_rum_dropped_metrics_total{reason="unknown_metric"}[15m]) > 0', text)
        self.assertIn("component: frontend", text)
        self.assertIn("severity: warning", text)
        self.assertIn('runbook_url: "docs/runbooks/frontend-rum-dropped-metrics.md"', text)

    def test_dashboard_surfaces_dropped_rum_metrics(self):
        dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
        panel_text = json.dumps(dashboard["panels"])

        self.assertIn("Dropped RUM Metrics", panel_text)
        self.assertIn("edge_frontend_rum_dropped_metrics_total", panel_text)
        self.assertIn("sum by (reason)", panel_text)

    def test_dropped_rum_alert_has_actionable_runbook(self):
        self.assertTrue(DROPPED_RUNBOOK.exists(), "dropped RUM metrics runbook is missing")

        text = DROPPED_RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("FrontendRumDroppedMetrics", text)
        self.assertIn("edge_frontend_rum_dropped_metrics_total", text)
        self.assertIn("frontend/src/lib/webVitals.ts", text)
        self.assertIn("backend/frontend_rum.py", text)
        self.assertIn("unknown_metric", text)


if __name__ == "__main__":
    unittest.main()
