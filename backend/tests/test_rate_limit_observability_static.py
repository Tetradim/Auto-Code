"""Static checks for API rate-limit rejection observability."""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"
METRICS = ROOT / "backend" / "metrics.py"
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
BROKER_DASHBOARD = ROOT / "grafana" / "dashboards" / "broker_health.json"
RULES = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "api-rate-limit-rejections.md"


class RateLimitObservabilityStaticTests(unittest.TestCase):
    def test_rate_limit_rejections_increment_low_cardinality_counter(self):
        server = SERVER.read_text(encoding="utf-8")
        metrics = METRICS.read_text(encoding="utf-8")

        self.assertIn("edge_rate_limit_rejections_total", metrics)
        self.assertIn('"scope"', metrics)
        self.assertIn("edge_rate_limit_rejections_total.labels(scope=\"api\").inc()", server)
        self.assertNotIn("request.url.path", server)

    def test_rate_limit_rejections_have_warning_alert(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("ApiRateLimitRejections", text)
        self.assertIn('edge_rate_limit_rejections:rate5m{scope="api"} > 0', text)
        self.assertIn("component: api", text)
        self.assertIn("severity: warning", text)
        self.assertIn('runbook_url: "docs/runbooks/api-rate-limit-rejections.md"', text)

    def test_rate_limit_rejection_alert_has_actionable_runbook(self):
        self.assertTrue(RUNBOOK.exists(), "API rate-limit rejection runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("ApiRateLimitRejections", text)
        self.assertIn("edge_rate_limit_rejections:rate5m", text)
        self.assertIn("/api/rate-limit/status", text)
        self.assertIn("Retry-After", text)
        self.assertIn("frontend/src/lib/api.ts", text)

    def test_rate_limit_rejection_rate_has_recording_rule(self):
        text = RULES.read_text(encoding="utf-8")

        self.assertIn("api_observability_rules", text)
        self.assertIn("edge_rate_limit_rejections:rate5m", text)
        self.assertIn("sum by (scope) (rate(edge_rate_limit_rejections_total[5m]))", text)

    def test_broker_dashboard_surfaces_rate_limit_rejections(self):
        dashboard = json.loads(BROKER_DASHBOARD.read_text(encoding="utf-8"))["dashboard"]
        panel_text = json.dumps(dashboard["panels"])
        expressions = {
            target["expr"]
            for panel in dashboard["panels"]
            for target in panel.get("targets", [])
            if "expr" in target
        }

        self.assertIn("API Rate Limit Rejections", panel_text)
        self.assertIn('sum(increase(edge_rate_limit_rejections_total{scope="api"}[$__range]))', expressions)
        self.assertIn('edge_rate_limit_rejections:rate5m{scope="api"}', expressions)


if __name__ == "__main__":
    unittest.main()
