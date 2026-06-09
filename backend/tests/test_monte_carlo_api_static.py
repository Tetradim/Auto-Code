"""Static checks for Monte Carlo API integration."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"
API = ROOT / "frontend" / "src" / "lib" / "api.ts"
TICKER_MODAL = ROOT / "frontend" / "src" / "components" / "TickerConfigModal.tsx"
RESULTS_CHART = ROOT / "frontend" / "src" / "components" / "BacktestResultsChart.tsx"
METRICS = ROOT / "backend" / "metrics.py"


class MonteCarloApiStaticTests(unittest.TestCase):
    def test_backtest_request_exposes_custom_monte_carlo_settings(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("monte_carlo_enabled: bool = True", text)
        self.assertIn('monte_carlo_method: str = Field("bootstrap"', text)
        self.assertIn("monte_carlo_confidence_level: float", text)
        self.assertIn("monte_carlo_random_seed: Optional[int]", text)
        self.assertIn("monte_carlo_saved_charts: bool = True", text)
        self.assertIn("monte_carlo_block_size: int", text)

    def test_backtest_endpoint_attaches_monte_carlo_result(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("MonteCarloEngine", text)
        self.assertIn("MonteCarloSettings", text)
        self.assertIn('result["monte_carlo"]', text)
        self.assertIn('_record_monte_carlo_metrics(request.symbol, result["monte_carlo"])', text)
        self.assertIn('@api_router.get("/backtest/monte-carlo/charts")', text)
        self.assertIn('@api_router.get("/backtest/monte-carlo/charts/{run_id}/{chart_name}")', text)
        self.assertIn("_safe_monte_carlo_chart_name", text)
        self.assertIn("_record_monte_carlo_metrics", text)

    def test_monte_carlo_prometheus_metrics_cover_tail_risk_dashboard(self):
        metrics = METRICS.read_text(encoding="utf-8")
        server = SERVER.read_text(encoding="utf-8")

        self.assertIn("edge_monte_carlo_profit_prob", metrics)
        self.assertIn("edge_monte_carlo_var_5pct", metrics)
        self.assertIn("edge_monte_carlo_expected_shortfall", metrics)
        self.assertIn("edge_monte_carlo_median_equity", metrics)
        self.assertIn("edge_monte_carlo_mean_drawdown", metrics)
        self.assertIn("edge_monte_carlo_ruin_prob", metrics)
        self.assertIn("monte_carlo_var_5pct.labels(symbol=label).set", server)
        self.assertIn("monte_carlo_expected_shortfall.labels(symbol=label).set", server)

    def test_frontend_sends_and_displays_custom_monte_carlo_settings(self):
        api = API.read_text(encoding="utf-8")
        modal = TICKER_MODAL.read_text(encoding="utf-8")
        chart = RESULTS_CHART.read_text(encoding="utf-8")

        self.assertIn("monteCarlo", api)
        self.assertIn("monte_carlo_method", api)
        self.assertIn("monteCarloSettings", modal)
        self.assertIn("Monte Carlo Settings", modal)
        self.assertIn("Saved Chart Bundle", chart)
        self.assertIn("api_path", chart)
        self.assertIn("value_at_risk", chart)
        self.assertIn("conditional_value_at_risk", chart)


if __name__ == "__main__":
    unittest.main()
