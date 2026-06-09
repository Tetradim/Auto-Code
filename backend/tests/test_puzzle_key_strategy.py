"""Tests for the Puzzle Key Strategy package."""
import asyncio
from pathlib import Path
import sys
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from backtest.engine import BacktestConfig
from strategies.registry import StrategyRegistry, create_strategy


class PuzzleKeyStrategyTests(unittest.TestCase):
    def test_strategy_registry_exposes_puzzle_key_customization(self):
        strategies = StrategyRegistry.list_strategies()

        self.assertIn("puzzle_key_strategy", strategies)
        params = strategies["puzzle_key_strategy"]["params"]
        self.assertIn("mode", params)
        self.assertIn("night_session", params)
        self.assertIn("day_session", params)
        self.assertIn("atr_multiplier", params)
        self.assertIn("trend_period", params)
        self.assertIn("trade_direction", params)

    def test_night_reversal_buys_at_atr_adjusted_lower_extreme(self):
        strategy = create_strategy(
            "puzzle_key_strategy",
            BacktestConfig(),
            mode="night",
            reversal_lookback=3,
            atr_period=3,
            atr_multiplier=0.5,
            trade_direction="long",
        )
        data = pd.DataFrame(
            [
                {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000},
                {"open": 99.0, "high": 100.0, "low": 98.0, "close": 99.0, "volume": 1000},
                {"open": 98.0, "high": 99.0, "low": 97.0, "close": 98.0, "volume": 1000},
                {"open": 96.5, "high": 98.0, "low": 95.5, "close": 96.0, "volume": 1000},
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

        signals = asyncio.run(strategy.generate_signals("SPY", data))

        self.assertEqual(int(signals.iloc[-1]["signal"]), 1)
        self.assertIn("night_reversal_buy", signals.iloc[-1]["reason"])
        self.assertGreater(float(signals.iloc[-1]["confidence"]), 0.5)

    def test_day_pullback_buys_only_when_main_trend_is_up(self):
        strategy = create_strategy(
            "puzzle_key_strategy",
            BacktestConfig(),
            mode="day",
            trend_period=3,
            reversal_lookback=3,
            atr_period=3,
            atr_multiplier=0.25,
            trade_direction="long",
        )
        data = pd.DataFrame(
            [
                {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000},
                {"open": 102.0, "high": 103.0, "low": 101.0, "close": 102.0, "volume": 1000},
                {"open": 104.0, "high": 105.0, "low": 103.0, "close": 104.0, "volume": 1000},
                {"open": 101.5, "high": 103.0, "low": 100.5, "close": 101.0, "volume": 1000},
            ],
            index=pd.to_datetime(
                [
                    "2024-01-03 09:00",
                    "2024-01-03 10:00",
                    "2024-01-03 11:00",
                    "2024-01-03 12:00",
                ]
            ),
        )

        signals = asyncio.run(strategy.generate_signals("QQQ", data))

        self.assertEqual(int(signals.iloc[-1]["signal"]), 1)
        self.assertIn("day_trend_pullback_buy", signals.iloc[-1]["reason"])

    def test_out_of_session_rows_hold(self):
        strategy = create_strategy("puzzle_key_strategy", BacktestConfig(), mode="combined")
        data = pd.DataFrame(
            [{"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000}],
            index=pd.to_datetime(["2024-01-03 16:30"]),
        )

        signals = asyncio.run(strategy.generate_signals("IWM", data))

        self.assertEqual(int(signals.iloc[-1]["signal"]), 0)
        self.assertEqual(signals.iloc[-1]["reason"], "puzzle_key_out_of_session")


if __name__ == "__main__":
    unittest.main()
