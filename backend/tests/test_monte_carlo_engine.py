"""Behavior tests for Monte Carlo risk simulation."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from backtest.monte_carlo import MonteCarloEngine, MonteCarloSettings


class MonteCarloEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrap_simulation_is_seeded_and_returns_tail_risk_metrics(self):
        base_results = {
            "symbol": "SPY",
            "initial_capital": 10000,
            "trades": [
                {"pnl_pct": 2.0},
                {"pnl_pct": -1.0},
                {"pnl_pct": 1.5},
                {"pnl_pct": -2.5},
                {"pnl_pct": 3.0},
            ],
        }
        settings = MonteCarloSettings(
            enabled=True,
            num_simulations=250,
            method="bootstrap",
            random_seed=42,
            confidence_level=0.95,
            include_paths=True,
            saved_charts=False,
            sample_path_count=8,
            histogram_bins=12,
        )

        first = await MonteCarloEngine().run_simulation(base_results, settings)
        second = await MonteCarloEngine().run_simulation(base_results, settings)

        self.assertEqual(first["settings"]["method"], "bootstrap")
        self.assertEqual(first["simulations"], 250)
        self.assertEqual(first["confidence_level"], 0.95)
        self.assertEqual(first["random_seed"], 42)
        self.assertEqual(first["final_equity_percentiles"], second["final_equity_percentiles"])
        self.assertIn("value_at_risk", first)
        self.assertIn("conditional_value_at_risk", first)
        self.assertIn("confidence_band", first)
        self.assertLessEqual(len(first["sample_paths"]), 8)
        self.assertEqual(len(first["final_equity_histogram"]), 12)

    async def test_saved_chart_bundle_writes_chart_ready_json(self):
        base_results = {
            "symbol": "AAPL",
            "initial_capital": 25000,
            "trades": [{"pnl_pct": 1.0}, {"pnl_pct": -0.5}, {"pnl_pct": 2.0}],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = MonteCarloSettings(
                enabled=True,
                num_simulations=50,
                method="shuffle",
                random_seed=7,
                include_paths=True,
                saved_charts=True,
                chart_output_dir=tmpdir,
                sample_path_count=5,
            )
            result = await MonteCarloEngine().run_simulation(base_results, settings)

            chart_set = result["saved_chart_set"]
            self.assertEqual(chart_set["chart_count"], 4)
            for chart in chart_set["charts"]:
                chart_path = Path(chart["path"])
                self.assertTrue(chart_path.exists())
                payload = json.loads(chart_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["run_id"], chart_set["run_id"])
                self.assertIn("data", payload)

    async def test_disabled_simulation_reports_disabled_status(self):
        result = await MonteCarloEngine().run_simulation(
            {"symbol": "MSFT", "trades": [{"pnl_pct": 1.0}]},
            MonteCarloSettings(enabled=False),
        )

        self.assertEqual(result["status"], "disabled")


if __name__ == "__main__":
    unittest.main()
