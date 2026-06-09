"""Static checks for price-fetch failure alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "price-fetch-failures.md"


class PriceFetchFailuresRunbookStaticTests(unittest.TestCase):
    def test_price_fetch_failure_alert_links_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("PriceFetchFailures", text)
        self.assertIn("rate(price_fetch_failures_total[5m]) > 0.5", text)
        self.assertIn('runbook_url: "docs/runbooks/price-fetch-failures.md"', text)

    def test_price_fetch_failure_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "price-fetch failures runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("PriceFetchFailures", text)
        self.assertIn("price_fetch_failures_total", text)
        self.assertIn("source", text)
        self.assertIn("symbol", text)
        self.assertIn("/api/automation", text)
        self.assertIn("/api/control/pause", text)
        self.assertIn("price_fetcher.py", text)
        self.assertIn("scheduler.py", text)
        self.assertIn("Pause automation", text)


if __name__ == "__main__":
    unittest.main()
