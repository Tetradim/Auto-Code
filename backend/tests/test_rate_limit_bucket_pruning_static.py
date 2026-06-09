"""Static checks for bounded in-memory rate-limit bucket state."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "backend" / "server.py"


class RateLimitBucketPruningStaticTests(unittest.TestCase):
    def test_rate_limit_buckets_are_pruned_before_new_requests(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("def _prune_rate_limit_buckets(now: float) -> None:", text)
        self.assertIn("_prune_rate_limit_buckets(now)", text)
        self.assertIn("stale_clients", text)
        self.assertIn("del _rate_limit_buckets[client]", text)

    def test_pruning_removes_clients_outside_fixed_window(self):
        text = SERVER.read_text(encoding="utf-8")

        self.assertIn("cutoff = now - _RATE_LIMIT_WINDOW_SECONDS", text)
        self.assertIn("timestamps[-1] < cutoff", text)
        self.assertIn("not timestamps", text)


if __name__ == "__main__":
    unittest.main()
