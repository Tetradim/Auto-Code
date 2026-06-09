"""Static checks for low win-rate alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "low-win-rate.md"


class LowWinRateRunbookStaticTests(unittest.TestCase):
    def test_low_win_rate_alert_links_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("LowWinRate", text)
        self.assertIn("edge_win_rate < 40", text)
        self.assertIn('runbook_url: "docs/runbooks/low-win-rate.md"', text)

    def test_low_win_rate_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "low win-rate runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("LowWinRate", text)
        self.assertIn("edge_win_rate", text)
        self.assertIn("/api/automation", text)
        self.assertIn("BacktestResultsChart", text)
        self.assertIn("Monte Carlo", text)
        self.assertIn("profit factor", text)
        self.assertIn("Pause automation", text)


if __name__ == "__main__":
    unittest.main()
