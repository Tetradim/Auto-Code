"""Static checks for low-cardinality frontend RUM Prometheus labels."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"
METRICS = ROOT / "backend" / "metrics.py"


class FrontendRumCardinalityStaticTests(unittest.TestCase):
    def test_web_vital_metric_names_are_allow_listed(self):
        server = SERVER.read_text(encoding="utf-8")

        self.assertIn("FRONTEND_RUM_WEB_VITAL_METRICS", server)
        for metric in ("inp", "lcp", "cls", "ttfb", "fcp"):
            self.assertIn(f'"{metric}"', server)
        self.assertIn("if metric_name not in FRONTEND_RUM_WEB_VITAL_METRICS", server)
        self.assertNotIn("metric_name = metric_label(item.name, limit=24)", server)

    def test_dropped_metric_counter_observes_unexpected_names_without_labeling_them(self):
        server = SERVER.read_text(encoding="utf-8")
        metrics = METRICS.read_text(encoding="utf-8")

        self.assertIn("edge_frontend_rum_dropped_metrics_total", metrics)
        self.assertIn('"reason"', metrics)
        self.assertIn("edge_frontend_rum_dropped_metrics_total.labels(reason=\"unknown_metric\").inc()", server)


if __name__ == "__main__":
    unittest.main()
