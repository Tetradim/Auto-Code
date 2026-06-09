"""Static checks for slow evaluation alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "slow-evaluation.md"


class SlowEvaluationRunbookStaticTests(unittest.TestCase):
    def test_slow_evaluation_alert_links_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("SlowEvaluation", text)
        self.assertIn("histogram_quantile(0.99, rate(edge_eval_duration_seconds_bucket[5m])) > 1.0", text)
        self.assertIn('runbook_url: "docs/runbooks/slow-evaluation.md"', text)

    def test_slow_evaluation_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "slow evaluation runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("SlowEvaluation", text)
        self.assertIn("edge_eval_duration_seconds_bucket", text)
        self.assertIn("histogram_quantile", text)
        self.assertIn("scheduler.py", text)
        self.assertIn("analyst/exporters/prometheus.py", text)
        self.assertIn("/api/automation", text)
        self.assertIn("Pause automation", text)
        self.assertIn("symbol-specific", text)


if __name__ == "__main__":
    unittest.main()
