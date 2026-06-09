"""Static checks for consecutive-loss alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PRIMARY_ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
LEGACY_ALERTS = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "consecutive-losses.md"


class ConsecutiveLossesRunbookStaticTests(unittest.TestCase):
    def test_consecutive_loss_alerts_link_runbook(self):
        primary = PRIMARY_ALERTS.read_text(encoding="utf-8")
        legacy = LEGACY_ALERTS.read_text(encoding="utf-8")

        self.assertIn("ConsecutiveLossesWarning", primary)
        self.assertIn("ConsecutiveLossesCritical", primary)
        self.assertIn("HighConsecutiveLosses", legacy)
        self.assertIn("edge_consecutive_losses >= 3", primary)
        self.assertIn("edge_consecutive_losses >= 5", primary)
        self.assertIn("edge_consecutive_losses > 3", legacy)
        self.assertEqual(primary.count('runbook_url: "docs/runbooks/consecutive-losses.md"'), 2)
        self.assertIn('runbook_url: "docs/runbooks/consecutive-losses.md"', legacy)

    def test_consecutive_loss_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "consecutive losses runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("ConsecutiveLossesWarning", text)
        self.assertIn("ConsecutiveLossesCritical", text)
        self.assertIn("HighConsecutiveLosses", text)
        self.assertIn("edge_consecutive_losses", text)
        self.assertIn("/api/automation", text)
        self.assertIn("/api/control/pause", text)
        self.assertIn("max_consecutive_losses", text)
        self.assertIn("TickerConfigModal", text)
        self.assertIn("Pause automation", text)


if __name__ == "__main__":
    unittest.main()
