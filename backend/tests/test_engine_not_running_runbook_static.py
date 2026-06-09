"""Static checks for EngineNotRunning alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "engine-not-running.md"


class EngineNotRunningRunbookStaticTests(unittest.TestCase):
    def test_engine_not_running_alert_links_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("EngineNotRunning", text)
        self.assertIn("edge_engine_running == 0", text)
        self.assertIn('runbook_url: "docs/runbooks/engine-not-running.md"', text)

    def test_engine_not_running_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "EngineNotRunning runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("EngineNotRunning", text)
        self.assertIn("edge_engine_running", text)
        self.assertIn("/api/stats", text)
        self.assertIn("/api/ready", text)
        self.assertIn("/api/control/resume", text)
        self.assertIn("backend/scheduler.py", text)


if __name__ == "__main__":
    unittest.main()
