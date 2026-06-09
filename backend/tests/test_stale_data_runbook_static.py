"""Static checks for stale data alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "stale-data.md"


class StaleDataRunbookStaticTests(unittest.TestCase):
    def test_stale_data_alert_links_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("StaleData", text)
        self.assertIn("time() - sentinel_last_tick > 30", text)
        self.assertIn('runbook_url: "docs/runbooks/stale-data.md"', text)

    def test_stale_data_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "stale data runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("StaleData", text)
        self.assertIn("sentinel_last_tick", text)
        self.assertIn("time() - sentinel_last_tick", text)
        self.assertIn("/api/automation", text)
        self.assertIn("/api/control/pause", text)
        self.assertIn("price_fetcher.py", text)
        self.assertIn("scheduler.py", text)
        self.assertIn("Pause automation", text)
        self.assertIn("market hours", text)


if __name__ == "__main__":
    unittest.main()
