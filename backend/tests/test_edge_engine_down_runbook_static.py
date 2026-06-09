"""Static checks for legacy EdgeEngineDown alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "engine-not-running.md"


class EdgeEngineDownRunbookStaticTests(unittest.TestCase):
    def test_edge_engine_down_alert_links_existing_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("EdgeEngineDown", text)
        self.assertIn("edge_engine_running == 0", text)
        self.assertIn('runbook_url: "docs/runbooks/engine-not-running.md"', text)

    def test_engine_not_running_runbook_covers_edge_engine_down_symptom(self):
        self.assertTrue(RUNBOOK.exists(), "engine-not-running runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("EngineNotRunning", text)
        self.assertIn("edge_engine_running", text)
        self.assertIn("/api/stats", text)
        self.assertIn("/api/ready", text)
        self.assertIn("/api/control/resume", text)
        self.assertIn("backend/scheduler.py", text)


if __name__ == "__main__":
    unittest.main()
