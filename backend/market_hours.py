"""Market Hours Tracker for Global Markets"""
import logging
from datetime import datetime, time
from typing import Dict, Optional, Tuple
import pytz
from metrics import market_open_status, market_lunch_break, market_minutes_to_close

logger = logging.getLogger(__name__)

# Default market if none specified (US equity)
DEFAULT_MARKET = "NYSE"


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
    
    def is_market_open(self, market: Optional[str] = None) -> bool:
        """Check if market is currently open.
        
        Args:
            market: Market name (e.g., "NYSE"). If None, checks default (NYSE).
            
        Returns:
            True if market is open, False otherwise
        """
        market = market or DEFAULT_MARKET
        
        if market not in self.MARKETS:
            return False
        
        # Crypto markets are 24/7
        if market == "CRYPTO":
            return True
        
        info = self.MARKETS[market]
        tz = self.timezones[market]
        now = datetime.now(tz).time()
        
        # Check if within trading hours
        if not (info["open"] <= now <= info["close"]):
            return False
        
        # Check lunch break
        if info["lunch"]:
            lunch_start, lunch_end = info["lunch"]
            if lunch_start <= now <= lunch_end:
                return False
        
        return True
    
    def is_symbol_tradeable(self, symbol: str) -> bool:
        """Check if a symbol's market is currently open.
        
        This is the method scheduler should call - it handles the
        symbol-to-market mapping automatically.
        
        Args:
            symbol: Trading symbol (e.g., "AAPL", "7203.T")
            
        Returns:
            True if the symbol's market is open
        """
        market = self.get_market_for_symbol(symbol)
        return self.is_market_open(market)
    
    def is_lunch_break(self, market: str) -> bool:
        """Check if market is in lunch break"""
        if market not in self.MARKETS:
            return False
        
        info = self.MARKETS[market]
        if not info["lunch"]:
            return False
        
        tz = self.timezones[market]
        now = datetime.now(tz).time()
        lunch_start, lunch_end = info["lunch"]
        
        return lunch_start <= now <= lunch_end
    
    def minutes_to_close(self, market: str) -> int:
        """Get minutes until market close"""
        if market not in self.MARKETS:
            return 0
        
        info = self.MARKETS[market]
        tz = self.timezones[market]
        now = datetime.now(tz)
        
        # Create close datetime for today
        close_time = info["close"]
        close_dt = now.replace(hour=close_time.hour, minute=close_time.minute, second=0, microsecond=0)
        
        if now > close_dt:
            return 0
        
        delta = close_dt - now
        return int(delta.total_seconds() / 60)
    
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
            status[market] = {
                "open": self.is_market_open(market),
                "lunch_break": self.is_lunch_break(market),
                "minutes_to_close": self.minutes_to_close(market)
            }
        return status
