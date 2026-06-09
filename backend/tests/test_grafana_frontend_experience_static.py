"""Static checks for the frontend experience Grafana dashboard."""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "grafana" / "dashboards" / "frontend-experience.json"


class FrontendExperienceGrafanaDashboardTests(unittest.TestCase):
    def test_dashboard_json_is_provisionable_and_uses_frontend_rum_metrics(self):
        dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
        rules = (ROOT / "prometheus" / "rules.yml").read_text(encoding="utf-8")
        self.assertEqual(dashboard["uid"], "se-frontend-experience")
        self.assertIn("frontend-experience", dashboard["tags"])

        panel_text = json.dumps(dashboard["panels"])
        self.assertIn("edge_frontend_rum_samples_total", panel_text)
        self.assertIn("edge_frontend_web_vital_value", panel_text)
        self.assertIn("edge_frontend_slow_interaction:p95_ms", panel_text)
        self.assertIn("edge_frontend_long_task:p95_ms", panel_text)
        self.assertIn("edge_frontend_slow_interaction_duration_ms_bucket", rules)
        self.assertIn("edge_frontend_long_task_duration_ms_bucket", rules)
        self.assertIn("histogram_quantile(0.95", rules)

    def test_dashboard_has_route_filter_and_prometheus_datasource_variable(self):
        dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
        variables = dashboard["templating"]["list"]
        names = {variable["name"] for variable in variables}
        self.assertIn("DS_PROMETHEUS", names)
        self.assertIn("route", names)


if __name__ == "__main__":
    unittest.main()
