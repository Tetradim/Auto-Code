"""Static checks for the Puzzle Key Strategy status endpoint."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"


class PuzzleKeyStatusStaticTests(unittest.TestCase):
    def test_status_endpoint_reports_feature_flag_and_env_config(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn('@api_router.get("/strategies/puzzle-key/status")', text)
        self.assertIn("def get_puzzle_key_status", text)
        self.assertIn("EDGE_PUZZLE_KEY_ENABLED", text)
        self.assertIn("EDGE_PUZZLE_KEY_MODE", text)
        self.assertIn("EDGE_PUZZLE_KEY_NIGHT_SESSION", text)
        self.assertIn("EDGE_PUZZLE_KEY_DAY_SESSION", text)
        self.assertIn("puzzle_key_strategy", text)
        self.assertIn("automation", text)


if __name__ == "__main__":
    unittest.main()
