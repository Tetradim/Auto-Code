"""Static checks for market-hours-aware automation handoff."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCHEDULER = ROOT / "backend" / "scheduler.py"


class MarketHoursHandoffGuardStaticTests(unittest.TestCase):
    def test_handoff_is_suppressed_when_symbol_market_is_closed(self):
        text = SCHEDULER.read_text(encoding="utf-8")
        handoff = text[text.index("async def _handoff_to_pulse"):]

        self.assertIn("market_status = self.market_hours.market_status", handoff)
        self.assertIn('market_status.get("reason", "closed")', handoff)
        self.assertIn('f"market_closed:{market_reason}"', handoff)
        self.assertIn("self.automation.record_suppressed(command, gate_reason)", handoff)
        self.assertIn('"market_status": market_status', handoff)


if __name__ == "__main__":
    unittest.main()
