"""Static checks for EdgeEnginePaused alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "engine-paused.md"


class EdgeEnginePausedRunbookStaticTests(unittest.TestCase):
    def test_edge_engine_paused_alert_links_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("EdgeEnginePaused", text)
        self.assertIn("edge_engine_paused == 1", text)
        self.assertIn('runbook_url: "docs/runbooks/engine-paused.md"', text)

    def test_engine_paused_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "engine-paused runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("EdgeEnginePaused", text)
        self.assertIn("edge_engine_paused", text)
        self.assertIn("/api/stats", text)
        self.assertIn("/api/automation", text)
        self.assertIn("/api/control/resume", text)
        self.assertIn("backend/scheduler.py", text)
        self.assertIn("intentional", text)


if __name__ == "__main__":
    unittest.main()
