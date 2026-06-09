"""Static contract checks for frontend RUM Prometheus alerts."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
RUM_RUNBOOK = ROOT / "docs" / "runbooks" / "frontend-rum-ingest-missing.md"
WEB_VITALS_RUNBOOK = ROOT / "docs" / "runbooks" / "frontend-core-web-vitals.md"


class FrontendRumAlertRulesStaticTests(unittest.TestCase):
    def test_frontend_rum_alerts_cover_ingest_and_core_vitals(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("FrontendRumIngestMissing", text)
        self.assertIn("absent_over_time(edge_frontend_rum_samples_total[30m])", text)
        self.assertIn("FrontendINPPoor", text)
        self.assertIn('edge_frontend_web_vital_value{metric="inp"} > 500', text)
        self.assertIn("FrontendLCPPoor", text)
        self.assertIn('edge_frontend_web_vital_value{metric="lcp"} > 4000', text)
        self.assertIn("FrontendCLSPoor", text)
        self.assertIn('edge_frontend_web_vital_value{metric="cls"} > 0.25', text)

    def test_frontend_rum_alerts_cover_histogram_p95(self):
        text = ALERTS.read_text(encoding="utf-8")
        rules = (ROOT / "prometheus" / "rules.yml").read_text(encoding="utf-8")

        self.assertIn("FrontendSlowInteractionP95High", text)
        self.assertIn("edge_frontend_slow_interaction:p95_ms > 500", text)
        self.assertIn("histogram_quantile(0.95", rules)
        self.assertIn("edge_frontend_slow_interaction_duration_ms_bucket", rules)
        self.assertIn("component: frontend", text)

    def test_core_web_vitals_alerts_link_shared_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertEqual(text.count('runbook_url: "docs/runbooks/frontend-core-web-vitals.md"'), 4)
        self.assertTrue(WEB_VITALS_RUNBOOK.exists(), "frontend Core Web Vitals runbook is missing")

        runbook = WEB_VITALS_RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("FrontendINPPoor", runbook)
        self.assertIn("FrontendLCPPoor", runbook)
        self.assertIn("FrontendCLSPoor", runbook)
        self.assertIn("FrontendSlowInteractionP95High", runbook)
        self.assertIn("frontend/src/lib/webVitals.ts", runbook)
        self.assertIn("grafana/dashboards/frontend-experience.json", runbook)

    def test_frontend_rum_ingest_alert_links_actionable_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn('runbook_url: "docs/runbooks/frontend-rum-ingest-missing.md"', text)
        self.assertTrue(RUM_RUNBOOK.exists(), "frontend RUM ingest runbook is missing")

        runbook = RUM_RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("FrontendRumIngestMissing", runbook)
        self.assertIn("/api/frontend/rum/status", runbook)
        self.assertIn("edge_frontend_rum:freshness_seconds", runbook)
        self.assertIn("edge_frontend_rum_dropped_metrics_total", runbook)


if __name__ == "__main__":
    unittest.main()
