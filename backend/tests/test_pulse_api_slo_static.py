"""Static checks for Pulse API SLO burn-rate observability."""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "prometheus" / "rules.yml"
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
BROKER_DASHBOARD = ROOT / "grafana" / "dashboards" / "broker_health.json"
RUNBOOK = ROOT / "docs" / "runbooks" / "pulse-api-slo-burn.md"


class PulseApiSloStaticTests(unittest.TestCase):
    def test_slo_recording_rules_calculate_error_budget_burn(self):
        text = RULES.read_text(encoding="utf-8")

        self.assertIn("api_slo_rules", text)
        self.assertIn("edge_api_availability:error_ratio5m", text)
        self.assertIn("edge_api_availability:error_ratio30m", text)
        self.assertIn("edge_api_availability:error_ratio1h", text)
        self.assertIn("edge_api_availability:error_ratio6h", text)
        self.assertIn('edge_api_calls_total{status!="success"}[5m]', text)
        self.assertIn("clamp_min(sum(increase(edge_api_calls_total[5m])), 1)", text)
        self.assertIn("edge_api_availability:burn_rate5m", text)
        self.assertIn("edge_api_availability:error_ratio5m / 0.01", text)

    def test_slo_alerts_use_multi_window_burn_rate_pairs(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("PulseApiSloFastBurn", text)
        self.assertIn(
            "edge_api_availability:burn_rate1h > 14.4 and edge_api_availability:burn_rate5m > 14.4",
            text,
        )
        self.assertIn("severity: critical", text)
        self.assertIn("PulseApiSloSlowBurn", text)
        self.assertIn(
            "edge_api_availability:burn_rate6h > 6 and edge_api_availability:burn_rate30m > 6",
            text,
        )
        self.assertIn("slo: pulse-api-availability", text)
        self.assertIn('runbook_url: "docs/runbooks/pulse-api-slo-burn.md"', text)

    def test_broker_dashboard_surfaces_slo_burn_rate(self):
        dashboard = json.loads(BROKER_DASHBOARD.read_text(encoding="utf-8"))["dashboard"]
        panel_text = json.dumps(dashboard["panels"])
        expressions = {
            target["expr"]
            for panel in dashboard["panels"]
            for target in panel.get("targets", [])
            if "expr" in target
        }

        self.assertIn("Pulse API SLO Burn Rate", panel_text)
        self.assertIn("edge_api_availability:burn_rate5m", expressions)
        self.assertIn("edge_api_availability:burn_rate30m", expressions)
        self.assertIn("edge_api_availability:burn_rate1h", expressions)
        self.assertIn("edge_api_availability:burn_rate6h", expressions)

    def test_slo_alert_runbook_has_actionable_triage_steps(self):
        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("Pulse API SLO Burn", text)
        self.assertIn("Broker Health", text)
        self.assertIn("sum by (endpoint, status) (increase(edge_api_calls_total[15m]))", text)
        self.assertIn('up{job=~"pulse|sentinel-edge"}', text)
        self.assertIn("Pause autonomous handoff", text)


if __name__ == "__main__":
    unittest.main()
