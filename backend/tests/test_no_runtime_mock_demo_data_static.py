"""Static guard against runtime mock/demo data in app code.

This intentionally ignores docs and tests. Standalone/no-Mongo infrastructure
may still exist, but runtime UI/API code should not fabricate market,
portfolio, PnL, broker, or analytics data.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class NoRuntimeMockDemoDataTests(unittest.TestCase):
    def test_removed_runtime_mock_demo_modules(self):
        removed = [
            "frontend/src/lib/mockData.ts",
            "frontend/src/components/dashboards/PaperTrading.tsx",
            "frontend/src/components/dashboards/BrokerHealth.tsx",
            "frontend/src/components/dashboards/ShortSqueezeDashboard.tsx",
            "frontend/src/components/dashboards/GreeksDashboard.tsx",
            "frontend/src/components/analytics/AnalyticsDashboard.tsx",
            "backend/data_feeder.py",
        ]
        for relative_path in removed:
            self.assertFalse((ROOT / relative_path).exists(), relative_path)

    def test_runtime_files_do_not_fabricate_data(self):
        scanned_files = [
            "frontend/src/App.tsx",
            "frontend/src/store/useStore.ts",
            "frontend/src/components/dashboards/TradingOverview.tsx",
            "frontend/src/components/dashboards/PnLTracking.tsx",
            "frontend/src/components/dashboards/PortfolioAnalytics.tsx",
            "backend/server.py",
            "backend/analyst/portfolio_analytics.py",
            "backend/analyst/correlation_matrix.py",
        ]
        banned_fragments = [
            "mockMode",
            "Mock data",
            "Mock execution",
            "generateMock",
            "generateDemo",
            "demoData",
            "create_demo",
            "/paper/",
            "PaperBroker",
            "DataSource.MOCK",
        ]

        for relative_path in scanned_files:
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            for fragment in banned_fragments:
                self.assertNotIn(fragment, text, f"{fragment!r} found in {relative_path}")


if __name__ == "__main__":
    unittest.main()
