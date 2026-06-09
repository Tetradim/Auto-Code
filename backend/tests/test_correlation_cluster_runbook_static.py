"""Static checks for correlation cluster alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "correlation-cluster.md"


class CorrelationClusterRunbookStaticTests(unittest.TestCase):
    def test_correlation_bearish_cluster_alert_links_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("CorrelationBearishCluster", text)
        self.assertIn("StrongCorrelationCluster", text)
        self.assertIn("BearishClusterOverride", text)
        self.assertIn('increase(analyst_correlation_clusters_total{direction="bearish"}[5m]) > 0', text)
        self.assertIn('analyst_correlation_clusters_total{strength="high"} > 1', text)
        self.assertIn('increase(analyst_correlation_clusters_total{direction="bearish",strength="high"}[5m]) > 0', text)
        self.assertEqual(text.count('runbook_url: "docs/runbooks/correlation-cluster.md"'), 3)

    def test_correlation_cluster_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "correlation cluster runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("CorrelationBearishCluster", text)
        self.assertIn("StrongCorrelationCluster", text)
        self.assertIn("BearishClusterOverride", text)
        self.assertIn("analyst_correlation_clusters_total", text)
        self.assertIn("/api/correlation", text)
        self.assertIn("/api/automation", text)
        self.assertIn("/api/control/pause", text)
        self.assertIn("CorrelationEngine", text)
        self.assertIn("backend/analyst/correlation/engine.py", text)
        self.assertIn("Pulse override", text)
        self.assertIn("Pause automation", text)


if __name__ == "__main__":
    unittest.main()
