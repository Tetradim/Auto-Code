"""Static checks for bfcache-friendly frontend RUM final flush."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "frontend" / "src" / "lib" / "api.ts"
EXPERIENCE_DASHBOARD = ROOT / "frontend" / "src" / "components" / "dashboards" / "ExperienceDashboard.tsx"


class FrontendRumBeaconStaticTests(unittest.TestCase):
    def test_api_exposes_beacon_first_rum_flush(self):
        text = API.read_text(encoding="utf-8")

        self.assertIn("sendFrontendRumBeacon", text)
        self.assertIn("navigator.sendBeacon", text)
        self.assertIn("keepalive: true", text)
        self.assertIn("application/json", text)
        self.assertIn("/api/frontend/rum", text)

    def test_final_flush_uses_pagehide_without_unload_handlers(self):
        text = EXPERIENCE_DASHBOARD.read_text(encoding="utf-8")

        self.assertIn("pagehide", text)
        self.assertIn("sendFrontendRumBeacon", text)
        self.assertNotIn("'unload'", text)
        self.assertNotIn('"unload"', text)
        self.assertNotIn("beforeunload", text)


if __name__ == "__main__":
    unittest.main()
