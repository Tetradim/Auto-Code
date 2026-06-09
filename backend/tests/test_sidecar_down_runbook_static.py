"""Static checks for Sentinel Edge sidecar availability runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "sidecar-down.md"


class SidecarDownRunbookStaticTests(unittest.TestCase):
    def test_sidecar_down_alert_links_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("SidecarDown", text)
        self.assertIn('up{job="sentinel-edge"} == 0', text)
        self.assertIn('runbook_url: "docs/runbooks/sidecar-down.md"', text)

    def test_sidecar_down_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "SidecarDown runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("SidecarDown", text)
        self.assertIn("/api/live", text)
        self.assertIn("/api/ready", text)
        self.assertIn("up{job=\"sentinel-edge\"}", text)
        self.assertIn("docker compose ps", text)
        self.assertIn("prometheus/prometheus.yml", text)


if __name__ == "__main__":
    unittest.main()
