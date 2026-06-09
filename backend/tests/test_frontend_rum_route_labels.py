"""Unit tests for frontend RUM route label cardinality controls."""
import unittest

from backend.frontend_rum import normalise_rum_route


class FrontendRumRouteLabelTests(unittest.TestCase):
    def test_normalises_dynamic_ids_without_losing_route_shape(self):
        cases = {
            "/orders/123456789": "/orders/:id",
            "/backtest/run_01HX4Y9B7E0WJ5KJ5J5J5J5J5J": "/backtest/:id",
            "/positions/AAPL": "/positions/:symbol",
            "/tickers/BRK.B/config": "/tickers/:symbol/config",
            "/trace/550e8400-e29b-41d4-a716-446655440000": "/trace/:id",
            "https://edge.local/orders/987?tab=detail": "/orders/:id",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalise_rum_route(raw), expected)

    def test_keeps_stable_routes_and_bounds_length(self):
        self.assertEqual(normalise_rum_route("/settings"), "/settings")
        self.assertEqual(normalise_rum_route("/"), "/")
        self.assertLessEqual(len(normalise_rum_route("/" + "/".join(["segment"] * 40))), 80)


if __name__ == "__main__":
    unittest.main()
