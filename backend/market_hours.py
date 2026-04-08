"""Market Hours Tracker for Global Markets"""
import logging
from datetime import datetime, time
from typing import Dict, Tuple
import pytz
from metrics import market_open_status, market_lunch_break, market_minutes_to_close

logger = logging.getLogger(__name__)

class MarketHours:
    """Track market hours for global markets"""
    
    MARKETS = {
        "NYSE": {
            "timezone": "America/New_York",
            "open": time(9, 30),
            "close": time(16, 0),
            "lunch": None
        },
        "NASDAQ": {
            "timezone": "America/New_York",
            "open": time(9, 30),
            "close": time(16, 0),
            "lunch": None
        },
        "LSE": {  # London Stock Exchange
            "timezone": "Europe/London",
            "open": time(8, 0),
            "close": time(16, 30),
            "lunch": None
        },
        "TSE": {  # Tokyo Stock Exchange
            "timezone": "Asia/Tokyo",
            "open": time(9, 0),
            "close": time(15, 0),
            "lunch": (time(11, 30), time(12, 30))  # Lunch break
        },
        "HKEX": {  # Hong Kong Exchange
            "timezone": "Asia/Hong_Kong",
            "open": time(9, 30),
            "close": time(16, 0),
            "lunch": (time(12, 0), time(13, 0))
        },
        "SSE": {  # Shanghai Stock Exchange
            "timezone": "Asia/Shanghai",
            "open": time(9, 30),
            "close": time(15, 0),
            "lunch": (time(11, 30), time(13, 0))
        },
        "BSE": {  # Bombay Stock Exchange
            "timezone": "Asia/Kolkata",
            "open": time(9, 15),
            "close": time(15, 30),
            "lunch": None
        }
    }
    
    def __init__(self):
        self.timezones = {name: pytz.timezone(info["timezone"]) for name, info in self.MARKETS.items()}
        logger.info(f"Market Hours Tracker initialized for {len(self.MARKETS)} markets")
    
    def is_market_open(self, market: str) -> bool:
        """Check if market is currently open"""
        if market not in self.MARKETS:
            return False
        
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
