"""Opening Range Breakout (ORB) Tracker"""
import logging
from datetime import datetime, time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from metrics import edge_orb_high, edge_orb_low, edge_orb_range_width, edge_orb_breakouts_total

logger = logging.getLogger(__name__)

@dataclass
class ORBLevel:
    """ORB level for a specific timeframe"""
    high: float = 0.0
    low: float = float('inf')
    locked: bool = False
    start_time: Optional[datetime] = None
    lock_time: Optional[datetime] = None
    date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    
    @property
    def range_width(self) -> float:
        """Calculate the ORB range width"""
        if self.low == float('inf'):
            return 0.0
        return self.high - self.low
    
    @property
    def is_valid(self) -> bool:
        """Check if ORB level is valid"""
        return self.high > 0 and self.low < float('inf')


class ORBTracker:
    """Multi-timeframe ORB tracker"""
    
    # Timeframes in minutes
    TIMEFRAMES = [5, 15, 30]
    
    # Market open time (NYSE: 9:30 AM EST)
    MARKET_OPEN = time(9, 30)
    
    def __init__(self):
        # Structure: {symbol: {timeframe: ORBLevel}}
        self.orb_levels: Dict[str, Dict[int, ORBLevel]] = {}
        logger.info(f"ORB Tracker initialized with timeframes: {self.TIMEFRAMES}")
    
    def update(self, symbol: str, price: float, timestamp: datetime) -> Dict[int, ORBLevel]:
        """Update ORB levels for a symbol with new price data"""
        
        # Initialize symbol if not exists
        if symbol not in self.orb_levels:
            self.orb_levels[symbol] = {}
            for tf in self.TIMEFRAMES:
                self.orb_levels[symbol][tf] = ORBLevel(start_time=timestamp)
        
        # Get current date
        current_date = timestamp.strftime('%Y-%m-%d')
        
        # Reset if new trading day
        for tf in self.TIMEFRAMES:
            level = self.orb_levels[symbol][tf]
            if level.date != current_date:
                self.orb_levels[symbol][tf] = ORBLevel(start_time=timestamp)
                logger.info(f"Reset ORB levels for {symbol} (new trading day)")
        
        # Update each timeframe
        for tf in self.TIMEFRAMES:
            level = self.orb_levels[symbol][tf]
            
            # Auto-lock after timeframe duration
            if not level.locked and level.start_time:
                minutes_elapsed = (timestamp - level.start_time).total_seconds() / 60
                if minutes_elapsed >= tf:
                    self.lock(symbol, tf)
                    logger.info(f"Auto-locked ORB {tf}m for {symbol} at {timestamp}")
            
            # Update high/low if not locked
            if not level.locked:
                if price > level.high:
                    level.high = price
                if price < level.low:
                    level.low = price
                
                # Update metrics
                if level.is_valid:
                    edge_orb_high.labels(symbol=symbol, timeframe=f"{tf}m").set(level.high)
                    edge_orb_low.labels(symbol=symbol, timeframe=f"{tf}m").set(level.low)
                    edge_orb_range_width.labels(symbol=symbol, timeframe=f"{tf}m").set(level.range_width)
        
        return self.orb_levels[symbol]
    
    def lock(self, symbol: str, timeframe: int) -> bool:
        """Lock ORB level for a specific timeframe"""
        if symbol in self.orb_levels and timeframe in self.orb_levels[symbol]:
            level = self.orb_levels[symbol][timeframe]
            if not level.locked:
                level.locked = True
                level.lock_time = datetime.now()
                logger.info(f"Locked ORB {timeframe}m for {symbol}: High={level.high:.2f}, Low={level.low:.2f}")
                return True
        return False
    
    def check_breakout(self, symbol: str, current_price: float) -> list:
        """Check for ORB breakouts"""
        breakouts = []
        
        if symbol not in self.orb_levels:
            return breakouts
        
        for tf, level in self.orb_levels[symbol].items():
            if not level.locked or not level.is_valid:
                continue
            
            direction = None
            
            # Check bullish breakout
            if current_price > level.high:
                direction = "bullish"
                edge_orb_breakouts_total.labels(
                    symbol=symbol,
                    direction=direction,
                    timeframe=f"{tf}m"
                ).inc()
            
            # Check bearish breakout
            elif current_price < level.low:
                direction = "bearish"
                edge_orb_breakouts_total.labels(
                    symbol=symbol,
                    direction=direction,
                    timeframe=f"{tf}m"
                ).inc()
            
            if direction:
                breakouts.append({
                    'symbol': symbol,
                    'timeframe': tf,
                    'direction': direction,
                    'price': current_price,
                    'orb_high': level.high,
                    'orb_low': level.low,
                    'timestamp': datetime.now()
                })
                logger.warning(
                    f"🚨 ORB BREAKOUT: {symbol} {direction.upper()} on {tf}m "
                    f"(Price: ${current_price:.2f}, Range: ${level.low:.2f}-${level.high:.2f})"
                )
        
        return breakouts
    
    def get_levels(self, symbol: str) -> Optional[Dict[int, ORBLevel]]:
        """Get ORB levels for a symbol"""
        return self.orb_levels.get(symbol)
    
    def get_all_levels(self) -> Dict[str, Dict[int, ORBLevel]]:
        """Get all ORB levels"""
        return self.orb_levels
