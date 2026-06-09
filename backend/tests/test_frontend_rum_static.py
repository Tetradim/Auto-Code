"""Static contract checks for frontend RUM ingestion.

These tests avoid importing the FastAPI app so they can run in lightweight
review environments while still protecting the endpoint and metric contract.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class FrontendRumStaticTests(unittest.TestCase):
    def test_backend_accepts_frontend_rum_snapshots_and_exports_metrics(self):
        server = read("backend/server.py")
        metrics = read("backend/metrics.py")

        self.assertIn("FrontendRumSnapshot", server)
        self.assertIn('@api_router.post("/frontend/rum")', server)
        self.assertIn('@api_router.get("/frontend/rum/status")', server)
        self.assertIn("frontend_rum_registry.record", server)
        self.assertIn("frontend_rum_registry.status", server)
        self.assertIn("edge_frontend_web_vital_value", metrics)
        self.assertIn("edge_frontend_rum_samples_total", metrics)

    def test_experience_dashboard_posts_snapshots_to_backend(self):
        dashboard = read("frontend/src/components/dashboards/ExperienceDashboard.tsx")
        api = read("frontend/src/lib/api.ts")

        self.assertIn("api.postFrontendRum", dashboard)
        self.assertIn("api.getFrontendRumStatus", dashboard)
        self.assertIn("async postFrontendRum", api)
        self.assertIn("async getFrontendRumStatus", api)
        self.assertIn("'/api/frontend/rum'", api)
        self.assertIn("'/api/frontend/rum/status'", api)


if __name__ == "__main__":
    unittest.main()
