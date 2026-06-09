"""Static checks for drawdown alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "drawdown-risk.md"


class DrawdownRunbookStaticTests(unittest.TestCase):
    def test_drawdown_alerts_link_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("DrawdownWarning", text)
        self.assertIn("DrawdownCritical", text)
        self.assertIn("ticker_drawdown_percent > 5", text)
        self.assertIn("ticker_drawdown_percent > 10", text)
        self.assertEqual(text.count('runbook_url: "docs/runbooks/drawdown-risk.md"'), 2)

    def test_drawdown_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "drawdown risk runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("DrawdownWarning", text)
        self.assertIn("DrawdownCritical", text)
        self.assertIn("ticker_drawdown_percent", text)
        self.assertIn("/api/automation", text)
        self.assertIn("max_drawdown_pct", text)
        self.assertIn("TickerConfigModal", text)
        self.assertIn("Pause automation", text)


if __name__ == "__main__":
    unittest.main()
