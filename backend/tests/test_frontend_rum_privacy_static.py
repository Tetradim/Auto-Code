"""Static checks for privacy-safe frontend RUM collection."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WEB_VITALS = ROOT / "frontend" / "src" / "lib" / "webVitals.ts"


class FrontendRumPrivacyStaticTests(unittest.TestCase):
    def test_slow_interaction_targets_do_not_capture_visible_text(self):
        text = WEB_VITALS.read_text(encoding="utf-8")

        self.assertNotIn("textContent", text)
        self.assertIn("describeTarget", text)
        self.assertIn("data-testid", text)
        self.assertIn("role", text)

    def test_manual_prometheus_export_does_not_emit_target_label(self):
        text = WEB_VITALS.read_text(encoding="utf-8")

        self.assertIn("sentinel_edge_frontend_slow_interaction_duration_ms", text)
        self.assertNotIn('target="${escapeLabel(item.target)}"', text)


if __name__ == "__main__":
    unittest.main()
