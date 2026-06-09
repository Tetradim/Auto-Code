"""Static checks for automation handoff failure alerting."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "automation-handoff-failures.md"


class AutomationHandoffAlertsStaticTests(unittest.TestCase):
    def test_failed_handoffs_have_actionable_alert(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("EdgeAutomationHandoffFailures", text)
        self.assertIn('edge_automation_handoffs:rate5m{result="failed"} > 0', text)
        self.assertIn("for: 2m", text)
        self.assertIn("component: automation", text)
        self.assertIn("{{ $labels.action }}", text)
        self.assertIn("{{ $labels.mode }}", text)
        self.assertIn("{{ $labels.reason }}", text)
        self.assertIn('runbook_url: "docs/runbooks/automation-handoff-failures.md"', text)

    def test_runbook_has_triage_steps_for_failed_handoffs(self):
        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("Automation Handoff Failures", text)
        self.assertIn('edge_automation_handoffs:rate5m{result="failed"}', text)
        self.assertIn("/api/automation", text)
        self.assertIn("/api/pulse/health", text)
        self.assertIn("Pause autonomous handoff", text)


if __name__ == "__main__":
    unittest.main()
