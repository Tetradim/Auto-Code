"""Average True Range (ATR) Calculator"""
import logging
from typing import List, Dict
from collections import deque
from metrics import edge_atr_value, edge_volatility_percentile

logger = logging.getLogger(__name__)

class ATRCalculator:
    """Calculate ATR for volatility analysis"""
    
    DEFAULT_PERIOD = 14
    
    def __init__(self, period: int = DEFAULT_PERIOD):
        self.period = period
        # Store price history: {symbol: deque of (high, low, close)}
        self.price_history: Dict[str, deque] = {}
        # Store ATR values: {symbol: float}
        self.atr_values: Dict[str, float] = {}
        logger.info(f"ATR Calculator initialized with period={period}")
    
    def update(self, symbol: str, high: float, low: float, close: float) -> float:
        """Update ATR with new price data"""
        
        # Initialize history for new symbol
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.period + 1)
        
        # Add new price bar
        self.price_history[symbol].append((high, low, close))
        
        # Need at least 2 bars to calculate TR
        if len(self.price_history[symbol]) < 2:
            return 0.0
        
        # Calculate True Range for current bar
        history = self.price_history[symbol]
        prev_close = history[-2][2]
        current_high = history[-1][0]
        current_low = history[-1][1]
        
        tr = max(
            current_high - current_low,
            abs(current_high - prev_close),
            abs(current_low - prev_close)
        )
        
        # Calculate ATR (simple moving average of TR)
        if len(history) >= self.period:
            tr_values = []
            for i in range(1, len(history)):
                prev_close_i = history[i-1][2]
                high_i = history[i][0]
                low_i = history[i][1]
                
                tr_i = max(
                    high_i - low_i,
                    abs(high_i - prev_close_i),
                    abs(low_i - prev_close_i)
                )
                tr_values.append(tr_i)
            
            atr = sum(tr_values[-self.period:]) / self.period
            self.atr_values[symbol] = atr
            
            # Update metric
            edge_atr_value.labels(symbol=symbol, period=str(self.period)).set(atr)
            
            # Calculate volatility percentile (0-100)
            if close > 0:
                volatility_pct = (atr / close) * 100
                edge_volatility_percentile.labels(symbol=symbol).set(volatility_pct)
            
            return atr
        
        return 0.0
    
    def get_atr(self, symbol: str) -> float:
        """Get current ATR value for symbol"""
        return self.atr_values.get(symbol, 0.0)
    
    def get_trailing_stop_offset(self, symbol: str, multiplier: float = 2.0) -> float:
        """Calculate trailing stop offset based on ATR"""
        atr = self.get_atr(symbol)
        return atr * multiplier
    
    def is_high_volatility(self, symbol: str, threshold_pct: float = 3.0) -> bool:
        """Check if symbol is in high volatility regime"""
        atr = self.get_atr(symbol)
        if symbol not in self.price_history or len(self.price_history[symbol]) == 0:
            return False
        
        latest_close = self.price_history[symbol][-1][2]
        if latest_close == 0:
            return False
        
        volatility_pct = (atr / latest_close) * 100
        return volatility_pct > threshold_pct
