"""Opening Range Breakout (ORB) Tracker.

Design decisions
────────────────
- All time comparisons are done in US/Eastern (ET) regardless of the server's
  local timezone or the naive datetime passed by the scheduler.
- The opening range is anchored to true NYSE market open (09:30 ET), not to
  the first price update received by the bot.
- Prices arriving before 09:30 ET (pre-market), after 16:00 ET (after-hours),
  on weekends, or on US market holidays are silently ignored.
- Each breakout direction fires exactly once per symbol per timeframe per
  trading day (deduplication via breakouts_fired).

Holiday coverage
────────────────
Full-day NYSE closures for 2025 and 2026 are hardcoded below.
TODO: replace with `exchange_calendars.get_calendar("XNYS")` for a
self-updating calendar that also handles early closes (half-days).
"""
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from metrics import (
    edge_orb_breakouts_total,
    edge_orb_high,
    edge_orb_low,
    edge_orb_range_width,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Timezone
# ─────────────────────────────────────────────────────────────────────────────

ET = ZoneInfo("America/New_York")

# ─────────────────────────────────────────────────────────────────────────────
# US market holiday calendar (NYSE full-day closures)
# Add years as needed; consider replacing with exchange_calendars.
# ─────────────────────────────────────────────────────────────────────────────

_NYSE_HOLIDAYS: Set[date] = {
    # 2025
    date(2025,  1,  1),   # New Year's Day
    date(2025,  1, 20),   # Martin Luther King Jr. Day
    date(2025,  2, 17),   # Presidents' Day
    date(2025,  4, 18),   # Good Friday
    date(2025,  5, 26),   # Memorial Day
    date(2025,  6, 19),   # Juneteenth National Independence Day
    date(2025,  7,  4),   # Independence Day
    date(2025,  9,  1),   # Labor Day
    date(2025, 11, 27),   # Thanksgiving Day
    date(2025, 12, 25),   # Christmas Day
    # 2026
    date(2026,  1,  1),   # New Year's Day
    date(2026,  1, 19),   # Martin Luther King Jr. Day
    date(2026,  2, 16),   # Presidents' Day
    date(2026,  4,  3),   # Good Friday
    date(2026,  5, 25),   # Memorial Day
    date(2026,  6, 19),   # Juneteenth National Independence Day
    date(2026,  7,  3),   # Independence Day (observed)
    date(2026,  9,  7),   # Labor Day
    date(2026, 11, 26),   # Thanksgiving Day
    date(2026, 12, 25),   # Christmas Day
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

MARKET_OPEN  = time(9, 30)   # NYSE / NASDAQ regular session open
MARKET_CLOSE = time(16, 0)   # NYSE / NASDAQ regular session close


def _et_now() -> datetime:
    """Current wall-clock time in US/Eastern."""
    return datetime.now(ET)


def _to_et(dt: datetime) -> datetime:
    """Attach ET timezone to a naive datetime or convert a aware one."""
    if dt.tzinfo is None:
        # Treat the naive datetime as ET rather than converting from UTC,
        # because the scheduler uses datetime.now() which is local time.
        # On a UTC server this would be wrong — consider switching the
        # scheduler to datetime.now(ET) for full correctness.
        return dt.replace(tzinfo=ET)
    return dt.astimezone(ET)


def _is_trading_day(et_date: date) -> bool:
    """Return True when US equity markets are open on *et_date*.

    Checks weekends and the hardcoded NYSE holiday calendar.
    Does not currently account for early closes (half-days).
    """
    if et_date.weekday() >= 5:          # Saturday=5, Sunday=6
        return False
    return et_date not in _NYSE_HOLIDAYS


def _session_open_dt(et_date: date) -> datetime:
    """Return the NYSE open datetime (09:30:00 ET) for *et_date*."""
    return datetime(
        et_date.year, et_date.month, et_date.day,
        9, 30, 0,
        tzinfo=ET,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ORBLevel:
    """ORB high/low range for one symbol on one timeframe for one trading day."""

    high:       float = 0.0
    low:        float = float("inf")
    locked:     bool  = False
    start_time: Optional[datetime] = None    # always 09:30 ET on the trading day
    lock_time:  Optional[datetime] = None    # ET time the range was sealed
    date:       str   = field(default_factory=lambda: datetime.now(ET).strftime("%Y-%m-%d"))

    @property
    def range_width(self) -> float:
        if self.low == float("inf"):
            return 0.0
        return self.high - self.low

    @property
    def is_valid(self) -> bool:
        """True once at least one price bar has been captured inside the range."""
        return self.high > 0 and self.low < float("inf")


# ─────────────────────────────────────────────────────────────────────────────
# Tracker
# ─────────────────────────────────────────────────────────────────────────────

class ORBTracker:
    """Multi-timeframe ORB tracker for US equities.

    Attributes
    ──────────
    TIMEFRAMES      : opening-range window durations in minutes (5, 15, 30)
    orb_levels      : {symbol: {timeframe: ORBLevel}}
    breakouts_fired : {symbol: set of (date_str, direction, timeframe)} — dedup
    """

    TIMEFRAMES: List[int] = [5, 15, 30]

    def __init__(self) -> None:
        self.orb_levels:      Dict[str, Dict[int, ORBLevel]]       = {}
        self.breakouts_fired: Dict[str, Set[Tuple[str, str, int]]] = {}
        logger.info("ORBTracker initialised — timeframes: %s", self.TIMEFRAMES)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _init_symbol(self, symbol: str, session_open: datetime, date_str: str) -> None:
        """Create fresh ORBLevel entries anchored to true NYSE market open."""
        self.orb_levels[symbol]      = {}
        self.breakouts_fired[symbol] = set()
        for tf in self.TIMEFRAMES:
            self.orb_levels[symbol][tf] = ORBLevel(
                start_time=session_open,
                date=date_str,
            )

    def _reset_if_new_day(self, symbol: str, date_str: str, session_open: datetime) -> bool:
        """Reset levels and dedup set when the trading date has rolled over.

        Returns True if a reset occurred.
        """
        existing = self.orb_levels.get(symbol, {})
        if not existing:
            return False
        # Sample any timeframe — they all share the same trading date
        sample = next(iter(existing.values()))
        if sample.date != date_str:
            logger.info("New trading day for %s — resetting ORB levels", symbol)
            self._init_symbol(symbol, session_open, date_str)
            return True
        return False

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, symbol: str, price: float, timestamp: datetime) -> Dict[int, ORBLevel]:
        """Ingest a new price observation and update all timeframe ranges.

        Parameters
        ──────────
        symbol    : ticker symbol (e.g. "SPY")
        price     : latest trade price
        timestamp : evaluation time from the scheduler (may be naive or aware)

        Returns the symbol's current {timeframe: ORBLevel} dict.
        Prices outside regular market hours or on non-trading days are ignored
        and the current levels are returned unchanged.
        """
        et = _to_et(timestamp)
        et_date = et.date()

        # ── Guard 1: non-trading day ──────────────────────────────────────────
        if not _is_trading_day(et_date):
            return self.orb_levels.get(symbol, {})

        # ── Guard 2: outside regular session ─────────────────────────────────
        t = et.time()
        if t < MARKET_OPEN or t > MARKET_CLOSE:
            return self.orb_levels.get(symbol, {})

        date_str     = et_date.strftime("%Y-%m-%d")
        session_open = _session_open_dt(et_date)

        # ── Initialise or reset ───────────────────────────────────────────────
        if symbol not in self.orb_levels:
            self._init_symbol(symbol, session_open, date_str)
        else:
            self._reset_if_new_day(symbol, date_str, session_open)

        # ── Update each timeframe ─────────────────────────────────────────────
        for tf in self.TIMEFRAMES:
            level = self.orb_levels[symbol][tf]

            # Auto-lock: seal the range once the opening window has elapsed.
            # Computed against true market open — not the first price received.
            if not level.locked:
                lock_at = session_open + timedelta(minutes=tf)
                if et >= lock_at:
                    self._lock(symbol, tf, at=et)

            # Accumulate high/low while the window is still open
            if not level.locked:
                if price > level.high:
                    level.high = price
                if price < level.low:
                    level.low = price

                if level.is_valid:
                    edge_orb_high.labels(symbol=symbol, timeframe=f"{tf}m").set(level.high)
                    edge_orb_low.labels(symbol=symbol, timeframe=f"{tf}m").set(level.low)
                    edge_orb_range_width.labels(symbol=symbol, timeframe=f"{tf}m").set(level.range_width)

        return self.orb_levels[symbol]

    def _lock(self, symbol: str, timeframe: int, at: Optional[datetime] = None) -> bool:
        """Seal the ORB range for *timeframe* — internal, ET-aware."""
        levels = self.orb_levels.get(symbol)
        if not levels or timeframe not in levels:
            return False
        level = levels[timeframe]
        if level.locked:
            return False
        level.locked    = True
        level.lock_time = at or _et_now()
        if level.is_valid:
            logger.info(
                "Locked %dm ORB for %s: $%.2f – $%.2f (range $%.2f)",
                timeframe, symbol, level.low, level.high, level.range_width,
            )
        else:
            logger.warning(
                "Locked %dm ORB for %s with no valid data (bot may have started late)",
                timeframe, symbol,
            )
        return True

    def lock(self, symbol: str, timeframe: int) -> bool:
        """Public API: manually lock the ORB range for *timeframe*."""
        return self._lock(symbol, timeframe, at=_et_now())

    def check_breakout(self, symbol: str, current_price: float) -> list:
        """Detect ORB breakouts for *symbol*, firing each direction exactly once
        per timeframe per trading day.

        Returns a list of breakout dicts for any *new* breakouts detected.
        Repeated calls on the same tick or subsequent ticks do not re-fire.
        """
        breakouts: list = []

        if symbol not in self.orb_levels:
            return breakouts

        fired = self.breakouts_fired.setdefault(symbol, set())

        for tf, level in self.orb_levels[symbol].items():
            if not level.locked or not level.is_valid:
                continue

            direction: Optional[str] = None
            if current_price > level.high:
                direction = "bullish"
            elif current_price < level.low:
                direction = "bearish"

            if direction is None:
                continue

            # ── Deduplication: fire once per (date, direction, timeframe) ─────
            dedup_key = (level.date, direction, tf)
            if dedup_key in fired:
                continue
            fired.add(dedup_key)

            edge_orb_breakouts_total.labels(
                symbol=symbol,
                direction=direction,
                timeframe=f"{tf}m",
            ).inc()

            breakouts.append({
                "symbol":    symbol,
                "timeframe": tf,
                "direction": direction,
                "price":     current_price,
                "orb_high":  level.high,
                "orb_low":   level.low,
                "timestamp": _et_now(),
            })

            logger.warning(
                "🚨 ORB BREAKOUT: %s %s on %dm "
                "(price $%.2f, range $%.2f–$%.2f)",
                symbol, direction.upper(), tf,
                current_price, level.low, level.high,
            )

        return breakouts

    # ── Getters ───────────────────────────────────────────────────────────────

    def get_levels(self, symbol: str) -> Optional[Dict[int, ORBLevel]]:
        return self.orb_levels.get(symbol)

    def get_all_levels(self) -> Dict[str, Dict[int, ORBLevel]]:
        return self.orb_levels
