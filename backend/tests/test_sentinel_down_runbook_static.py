"""Static checks for legacy SentinelDown alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "sidecar-down.md"


class SentinelDownRunbookStaticTests(unittest.TestCase):
    def test_sentinel_down_alert_links_existing_sidecar_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("SentinelDown", text)
        self.assertIn('up{job="sentinel-edge"} == 0', text)
        self.assertIn('runbook_url: "docs/runbooks/sidecar-down.md"', text)

    def test_sidecar_down_runbook_covers_sentinel_down_symptom(self):
        self.assertTrue(RUNBOOK.exists(), "sidecar-down runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("SidecarDown", text)
        self.assertIn('up{job="sentinel-edge"} == 0', text)
        self.assertIn("/api/live", text)
        self.assertIn("/api/ready", text)
        self.assertIn("docker compose ps", text)
        self.assertIn("prometheus/prometheus.yml", text)


if __name__ == "__main__":
    unittest.main()
