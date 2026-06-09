"""Static checks for auto-stop / emergency-exit alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "auto-stop-triggered.md"


class AutoStopRunbookStaticTests(unittest.TestCase):
    def test_auto_stop_alert_links_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("AutoStopTriggered", text)
        self.assertIn('increase(edge_decision_total{decision="emergency_exit"}[5m]) > 0', text)
        self.assertIn('runbook_url: "docs/runbooks/auto-stop-triggered.md"', text)

    def test_auto_stop_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "auto-stop runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("AutoStopTriggered", text)
        self.assertIn("edge_decision_total", text)
        self.assertIn("/api/automation", text)
        self.assertIn("/api/control/pause", text)
        self.assertIn("/api/pulse/health", text)
        self.assertIn("EMERGENCY_EXIT", text)
        self.assertIn("Pause automation", text)


if __name__ == "__main__":
    unittest.main()
