"""Static checks for Puzzle Key Strategy API integration."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"
REGISTRY = ROOT / "backend" / "strategies" / "registry.py"
SCHEDULER = ROOT / "backend" / "scheduler.py"


class PuzzleKeyApiStaticTests(unittest.TestCase):
    def test_backtest_request_exposes_puzzle_key_customization(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn('puzzle_key_mode: str = Field("combined"', text)
        self.assertIn('puzzle_key_night_session: str = "18:00-07:00"', text)
        self.assertIn('puzzle_key_day_session: str = "07:00-15:00"', text)
        self.assertIn("puzzle_key_atr_multiplier: float", text)
        self.assertIn("puzzle_key_trade_direction: str", text)
        self.assertIn("puzzle_key_no_new_entries_after: str", text)

    def test_backtest_run_passes_puzzle_key_params_to_registry(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn('elif request.strategy == "puzzle_key_strategy":', text)
        self.assertIn('"mode": request.puzzle_key_mode', text)
        self.assertIn('"night_session": request.puzzle_key_night_session', text)
        self.assertIn('"day_session": request.puzzle_key_day_session', text)
        self.assertIn('"trade_direction": request.puzzle_key_trade_direction', text)

    def test_registry_describes_puzzle_key_as_stock_etf_strategy(self):
        text = REGISTRY.read_text(encoding="utf-8")

        self.assertIn("class PuzzleKeyStrategy", text)
        self.assertIn('"puzzle_key_strategy"', text)
        self.assertIn("customizable session reversal and trend-pullback day trading package", text)
        self.assertIn("night_bar_minutes", text)
        self.assertIn("day_bar_minutes", text)

    def test_plugin_signals_can_use_existing_automation_handoff(self):
        text = SCHEDULER.read_text(encoding="utf-8")

        self.assertIn('plugin_signal.metadata.get("plugin") == "puzzle_key_strategy"', text)
        self.assertIn("Puzzle Key Strategy plugin signal", text)
        self.assertIn("AutomationAction.BUY", text)
        self.assertIn("AutomationAction.STOP_BUYING", text)


if __name__ == "__main__":
    unittest.main()
