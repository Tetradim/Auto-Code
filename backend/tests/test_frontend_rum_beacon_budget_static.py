"""Static checks for browser-safe frontend RUM beacon payloads."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "frontend" / "src" / "lib" / "api.ts"


class FrontendRumBeaconBudgetStaticTests(unittest.TestCase):
    def test_beacon_payload_has_conservative_byte_budget(self):
        text = API.read_text(encoding="utf-8")

        self.assertIn("FRONTEND_RUM_BEACON_MAX_BYTES", text)
        self.assertIn("60 * 1024", text)
        self.assertIn("TextEncoder", text)
        self.assertIn("rumBodyByteLength", text)

    def test_beacon_payload_compacts_large_snapshots(self):
        text = API.read_text(encoding="utf-8")

        self.assertIn("toFrontendRumBeaconBody", text)
        self.assertIn("compactFrontendRumSnapshot", text)
        self.assertIn("slowInteractions.slice(0, FRONTEND_RUM_BEACON_LIST_LIMIT)", text)
        self.assertIn("longTasks.slice(0, FRONTEND_RUM_BEACON_LIST_LIMIT)", text)
        self.assertIn("const body = toFrontendRumBeaconBody(snapshot)", text)
        self.assertNotIn("const body = JSON.stringify(snapshot)", text)


if __name__ == "__main__":
    unittest.main()
