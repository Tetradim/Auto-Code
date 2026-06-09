"""Behavior tests for stock market calendar safety."""
from datetime import datetime
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from market_hours import MarketHours  # noqa: E402


class MarketHoursCalendarTests(unittest.TestCase):
    def setUp(self):
        self.market_hours = MarketHours()

    def test_us_equities_are_closed_on_weekends_even_during_regular_hours(self):
        saturday_regular_hours = datetime(2026, 6, 13, 10, 0)

        self.assertFalse(
            self.market_hours.is_market_open("NYSE", now=saturday_regular_hours)
        )
        self.assertEqual(
            self.market_hours.market_status("NYSE", now=saturday_regular_hours)["reason"],
            "weekend",
        )

    def test_us_equities_are_closed_on_nyse_holidays(self):
        juneteenth_regular_hours = datetime(2026, 6, 19, 10, 0)

        self.assertFalse(
            self.market_hours.is_market_open("NASDAQ", now=juneteenth_regular_hours)
        )
        self.assertEqual(
            self.market_hours.market_status("NASDAQ", now=juneteenth_regular_hours)["reason"],
            "holiday",
        )

    def test_us_equities_honor_nyse_early_close_days(self):
        black_friday_after_early_close = datetime(2026, 11, 27, 13, 30)

        self.assertFalse(
            self.market_hours.is_market_open("NYSE", now=black_friday_after_early_close)
        )
        status = self.market_hours.market_status("NYSE", now=black_friday_after_early_close)
        self.assertEqual(status["reason"], "after_close")
        self.assertEqual(status["close"], "13:00")

    def test_us_equities_are_open_on_regular_business_day(self):
        regular_session = datetime(2026, 6, 18, 10, 0)

        self.assertTrue(self.market_hours.is_market_open("NYSE", now=regular_session))
        self.assertEqual(
            self.market_hours.market_status("NYSE", now=regular_session)["reason"],
            "open",
        )


if __name__ == "__main__":
    unittest.main()
