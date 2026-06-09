"""Tests for the live Puzzle Key signal plugin."""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

analyst_pkg = types.ModuleType("analyst")
analyst_pkg.__path__ = [str(BACKEND / "analyst")]
signals_pkg = types.ModuleType("analyst.signals")
signals_pkg.__path__ = [str(BACKEND / "analyst" / "signals")]
custom_pkg = types.ModuleType("analyst.signals.custom")
custom_pkg.__path__ = [str(BACKEND / "analyst" / "signals" / "custom")]
sys.modules.setdefault("analyst", analyst_pkg)
sys.modules.setdefault("analyst.signals", signals_pkg)
sys.modules.setdefault("analyst.signals.custom", custom_pkg)

base_spec = importlib.util.spec_from_file_location(
    "analyst.signals.base",
    BACKEND / "analyst" / "signals" / "base.py",
)
base_module = importlib.util.module_from_spec(base_spec)
sys.modules["analyst.signals.base"] = base_module
base_spec.loader.exec_module(base_module)

from analyst.signals.custom.puzzle_key_strategy import PuzzleKeySignal


class PuzzleKeySignalPluginTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("EDGE_PUZZLE_KEY_ENABLED", None)
        os.environ.pop("EDGE_PUZZLE_KEY_ATR_PERIOD", None)
        os.environ.pop("EDGE_PUZZLE_KEY_REVERSAL_LOOKBACK", None)
        os.environ.pop("EDGE_PUZZLE_KEY_TRADE_DIRECTION", None)

    def test_plugin_is_explicitly_enabled_before_signaling(self):
        plugin = PuzzleKeySignal()
        signal = asyncio.run(plugin.generate("SPY", {"ohlcv": self._night_reversal_data(), "price": 96.0}))

        self.assertIsNone(signal)

    def test_enabled_plugin_emits_buy_signal_from_strategy(self):
        os.environ["EDGE_PUZZLE_KEY_ENABLED"] = "true"
        os.environ["EDGE_PUZZLE_KEY_ATR_PERIOD"] = "3"
        os.environ["EDGE_PUZZLE_KEY_REVERSAL_LOOKBACK"] = "3"
        os.environ["EDGE_PUZZLE_KEY_TRADE_DIRECTION"] = "long"
        plugin = PuzzleKeySignal()

        signal = asyncio.run(plugin.generate("SPY", {"ohlcv": self._night_reversal_data(), "price": 96.0, "atr": 2.0}))

        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, "BUY")
        self.assertEqual(signal.metadata["plugin"], "puzzle_key_strategy")
        self.assertIn("puzzle_key_night_reversal_buy", signal.reason)

    @staticmethod
    def _night_reversal_data():
        return pd.DataFrame(
            [
                {"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1000},
                {"Open": 99.0, "High": 100.0, "Low": 98.0, "Close": 99.0, "Volume": 1000},
                {"Open": 98.0, "High": 99.0, "Low": 97.0, "Close": 98.0, "Volume": 1000},
                {"Open": 96.5, "High": 98.0, "Low": 95.5, "Close": 96.0, "Volume": 1000},
            ],
            index=pd.to_datetime(
                [
                    "2024-01-02 18:00",
                    "2024-01-02 19:45",
                    "2024-01-02 21:30",
                    "2024-01-02 23:15",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
