"""Market Hours Tracker for Global Markets"""
import logging
from datetime import date, datetime, time
from typing import Dict, Optional, Tuple
import pytz
from metrics import market_open_status, market_lunch_break, market_minutes_to_close

logger = logging.getLogger(__name__)

# Default market if none specified (US equity)
DEFAULT_MARKET = "NYSE"
US_EQUITY_MARKETS = {"NYSE", "NASDAQ"}
US_EQUITY_HOLIDAYS = {
    # NYSE/Nasdaq full-day closures for 2026.
    date(2026, 1, 1),
    date(2026, 1, 19),
    date(2026, 2, 16),
    date(2026, 4, 3),
    date(2026, 5, 25),
    date(2026, 6, 19),
    date(2026, 7, 3),
    date(2026, 9, 7),
    date(2026, 11, 26),
    date(2026, 12, 25),
    # Published NYSE closures for 2027.
    date(2027, 1, 1),
    date(2027, 1, 18),
    date(2027, 2, 15),
    date(2027, 3, 26),
    date(2027, 5, 31),
    date(2027, 6, 18),
    date(2027, 7, 5),
    date(2027, 9, 6),
    date(2027, 11, 25),
    date(2027, 12, 24),
    # Published NYSE closures for 2028.
    date(2028, 1, 17),
    date(2028, 2, 21),
    date(2028, 4, 14),
    date(2028, 5, 29),
    date(2028, 6, 19),
    date(2028, 7, 4),
    date(2028, 9, 4),
    date(2028, 11, 23),
    date(2028, 12, 25),
}
US_EQUITY_EARLY_CLOSES = {
    date(2026, 11, 27): time(13, 0),
    date(2026, 12, 24): time(13, 0),
    date(2027, 11, 26): time(13, 0),
    date(2028, 7, 3): time(13, 0),
    date(2028, 11, 24): time(13, 0),
}


class MarketHours:
    """Track market hours for global markets"""
    
    MARKETS = {
        "NYSE": {
            "timezone": "America/New_York",
            "open": time(9, 30),
            "close": time(16, 0),
            "lunch": None,
            "name": "New York Stock Exchange"
        },
        "NASDAQ": {
            "timezone": "America/New_York",
            "open": time(9, 30),
            "close": time(16, 0),
            "lunch": None,
            "name": "NASDAQ"
        },
        "LSE": {  # London Stock Exchange
            "timezone": "Europe/London",
            "open": time(8, 0),
            "close": time(16, 30),
            "lunch": None,
            "name": "London Stock Exchange"
        },
        "TSE": {  # Tokyo Stock Exchange
            "timezone": "Asia/Tokyo",
            "open": time(9, 0),
            "close": time(15, 0),
            "lunch": (time(11, 30), time(12, 30)),  # Lunch break
            "name": "Tokyo Stock Exchange"
        },
        "HKEX": {  # Hong Kong Exchange
            "timezone": "Asia/Hong_Kong",
            "open": time(9, 30),
            "close": time(16, 0),
            "lunch": (time(12, 0), time(13, 0)),
            "name": "Hong Kong Exchange"
        },
        "SSE": {  # Shanghai Stock Exchange
            "timezone": "Asia/Shanghai",
            "open": time(9, 30),
            "close": time(15, 0),
            "lunch": (time(11, 30), time(13, 0)),
            "name": "Shanghai Stock Exchange"
        },
        "BSE": {  # Bombay Stock Exchange (India)
            "timezone": "Asia/Kolkata",
            "open": time(9, 15),
            "close": time(15, 30),
            "lunch": None,
            "name": "Bombay Stock Exchange"
        },
        # Crypto markets (24/7)
        "CRYPTO": {
            "timezone": "UTC",
            "open": time(0, 0),
            "close": time(23, 59),
            "lunch": None,
            "name": "Crypto Markets (24/7)"
        }
    }
    
    # Map symbols to their primary market
    SYMBOL_MARKET_MAP = {
        # US
        "SPY": "NYSE", "QQQ": "NASDAQ", "AAPL": "NASDAQ", "MSFT": "NASDAQ",
        "GOOGL": "NASDAQ", "AMZN": "NASDAQ", "TSLA": "NASDAQ", "NVDA": "NASDAQ",
        "META": "NASDAQ", "AMD": "NASDAQ", "NFLX": "NASDAQ",
        # UK
        "BP": "LSE", "SHEL": "LSE", "HSBC": "LSE", "AZN": "LSE",
        # Japan
        "7203.T": "TSE", "9984.T": "TSE", "6758.T": "TSE",
        # Hong Kong
        "0700.HK": "HKEX", "0941.HK": "HKEX", "3690.HK": "HKEX",
        # China
        "600519.SS": "SSE", "000001.SS": "SSE",
        # India
        "RELIANCE.BO": "BSE", "TCS.BO": "BSE",
        # Crypto (24/7)
        "BTC": "CRYPTO", "ETH": "CRYPTO", "SOL": "CRYPTO",
    }
    
    def __init__(self):
        self.timezones = {name: pytz.timezone(info["timezone"]) for name, info in self.MARKETS.items()}
        logger.info(f"Market Hours Tracker initialized for {len(self.MARKETS)} markets")
    
    def get_market_for_symbol(self, symbol: str) -> str:
        """Get the primary market for a trading symbol.
        
        Args:
            symbol: Trading symbol (e.g., "AAPL", "7203.T")
            
        Returns:
            Market name (e.g., "NYSE", "TSE", "CRYPTO")
        """
        # Check exact match
        if symbol in self.SYMBOL_MARKET_MAP:
            return self.SYMBOL_MARKET_MAP[symbol]
        
        # Check prefix for US tickers (common patterns)
        symbol_upper = symbol.upper()
        if not any(c.isdigit() for c in symbol_upper):
            # Likely a US ticker without exchange suffix
            return "NYSE"  # Default to NYSE for US equities
        
        # Check exchange suffix
        if "." in symbol:
            suffix = symbol.split(".")[1].upper()
            if suffix in ["T", "TOKYO"]:
                return "TSE"
            elif suffix in ["HK", "HONGKONG"]:
                return "HKEX"
            elif suffix in ["SS", "SH", "SHANGHAI"]:
                return "SSE"
            elif suffix in ["BO", "BOMBAY"]:
                return "BSE"
            elif suffix in ["L", "LSE", "LON"]:
                return "LSE"
        
        # Default fallback
        return DEFAULT_MARKET
    
    def is_market_open(self, market: Optional[str] = None, now: Optional[datetime] = None) -> bool:
        """Check if market is currently open.
        
        Args:
            market: Market name (e.g., "NYSE"). If None, checks default (NYSE).
            now: Optional datetime for deterministic checks. Naive values are
                interpreted in the market's local timezone.
            
        Returns:
            True if market is open, False otherwise
        """
        return bool(self.market_status(market, now=now)["open"])
    
    def is_symbol_tradeable(self, symbol: str, now: Optional[datetime] = None) -> bool:
        """Check if a symbol's market is currently open.
        
        This is the method scheduler should call - it handles the
        symbol-to-market mapping automatically.
        
        Args:
            symbol: Trading symbol (e.g., "AAPL", "7203.T")
            
        Returns:
            True if the symbol's market is open
        """
        market = self.get_market_for_symbol(symbol)
        return self.is_market_open(market, now=now)
    
    def is_lunch_break(self, market: str, now: Optional[datetime] = None) -> bool:
        """Check if market is in lunch break"""
        if market not in self.MARKETS:
            return False
        
        info = self.MARKETS[market]
        if not info["lunch"]:
            return False
        
        now = self._market_now(market, now).time()
        lunch_start, lunch_end = info["lunch"]
        
        return lunch_start <= now <= lunch_end
    
    def minutes_to_close(self, market: str, now: Optional[datetime] = None) -> int:
        """Get minutes until market close"""
        if market not in self.MARKETS:
            return 0
        
        info = self.MARKETS[market]
        now = self._market_now(market, now)
        
        # Create close datetime for today
        close_time = self._close_time_for(market, now.date(), info["close"])
        close_dt = now.replace(hour=close_time.hour, minute=close_time.minute, second=0, microsecond=0)
        
        if now > close_dt:
            return 0
        
        delta = close_dt - now
        return int(delta.total_seconds() / 60)

    def market_status(self, market: Optional[str] = None, now: Optional[datetime] = None) -> Dict:
        """Return market-open state with a machine-readable reason."""
        market = market or DEFAULT_MARKET

        if market not in self.MARKETS:
            return {
                "market": market,
                "open": False,
                "reason": "unknown_market",
                "lunch_break": False,
                "minutes_to_close": 0,
            }

        info = self.MARKETS[market]
        local_now = self._market_now(market, now)
        market_date = local_now.date()
        current_time = local_now.time()
        open_time = info["open"]
        close_time = self._close_time_for(market, market_date, info["close"])
        lunch_break = self.is_lunch_break(market, now=local_now)

        reason = "open"
        is_open = True

        if market == "CRYPTO":
            is_open = True
            reason = "open"
        elif market in US_EQUITY_MARKETS and local_now.weekday() >= 5:
            is_open = False
            reason = "weekend"
        elif market in US_EQUITY_MARKETS and market_date in US_EQUITY_HOLIDAYS:
            is_open = False
            reason = "holiday"
        elif current_time < open_time:
            is_open = False
            reason = "before_open"
        elif current_time > close_time:
            is_open = False
            reason = "after_close"
        elif lunch_break:
            is_open = False
            reason = "lunch_break"

        return {
            "market": market,
            "name": info["name"],
            "timezone": info["timezone"],
            "open": is_open,
            "reason": reason,
            "date": market_date.isoformat(),
            "time": local_now.strftime("%H:%M:%S"),
            "open_time": open_time.strftime("%H:%M"),
            "close": close_time.strftime("%H:%M"),
            "lunch_break": lunch_break,
            "minutes_to_close": self.minutes_to_close(market, now=local_now) if is_open else 0,
        }
    
    def update_metrics(self):
        """Update Prometheus metrics for all markets"""
        for market in self.MARKETS.keys():
            is_open = self.is_market_open(market)
            in_lunch = self.is_lunch_break(market)
            mins_to_close = self.minutes_to_close(market) if is_open else 0
            
            market_open_status.labels(market=market).set(1 if is_open else 0)
            market_lunch_break.labels(market=market).set(1 if in_lunch else 0)
            market_minutes_to_close.labels(market=market).set(mins_to_close)
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Get status of all markets"""
        status = {}
        for market in self.MARKETS.keys():
            status[market] = self.market_status(market)
        return status

    def _market_now(self, market: str, now: Optional[datetime] = None) -> datetime:
        tz = self.timezones[market]
        if now is None:
            return datetime.now(tz)
        if now.tzinfo is None:
            return tz.localize(now)
        return now.astimezone(tz)

    @staticmethod
    def _close_time_for(market: str, market_date: date, regular_close: time) -> time:
        if market in US_EQUITY_MARKETS:
            return US_EQUITY_EARLY_CLOSES.get(market_date, regular_close)
        return regular_close
