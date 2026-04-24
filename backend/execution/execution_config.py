"""
Execution Customization Module

Default order settings and execution preferences:
- Order type defaults
- Fill tolerance  
- Time-in-force options
- Partial fill settings
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class TimeInForce(Enum):
    """Time in force options"""
    DAY = "day"  # Cancel at end of day
    GTC = "gtc"  # Good until cancelled
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill
    GTD = "gtd"  # Good until date


@dataclass
class ExecutionConfig:
    """Default execution settings"""
    default_order_type: str = "market"
    default_tif: str = "day"
    limit_offset_pct: float = 0.0
    limit_improve_pct: float = 0.0
    stop_offset_pct: float = 0.0
    use_amao: bool = True
    allow_partial_fills: bool = True
    min_fill_pct: float = 0.50
    fill_timeout_seconds: int = 30
    max_slippage_pct: float = 0.10
    use_market_hours: bool = True
    prefer_routing: str = "smart"
    require_confirmation: bool = False
    confirm_threshold_pct: float = 0.05


@dataclass
class PerTickerExecution:
    """Per-ticker execution overrides"""
    symbol: str
    order_type: str = "market"
    max_contracts: int = 0
    preferred_expiry_days: int = 0
    strike_type: str = "atm"
    otm_percent: float = 0.0
    min_premium: float = 0.50
    max_premium_pct: float = 0.10
    execute_on_fill: bool = True
    allow_amd: bool = True
    
    @classmethod
    def from_dict(cls, data: dict) -> "PerTickerExecution":
        return cls(
            symbol=data.get("symbol", ""),
            order_type=data.get("order_type", "market"),
            max_contracts=data.get("max_contracts", 0),
            preferred_expiry_days=data.get("preferred_expiry_days", 0),
            strike_type=data.get("strike_type", "atm"),
            otm_percent=data.get("otm_percent", 0.0),
            min_premium=data.get("min_premium", 0.50),
            max_premium_pct=data.get("max_premium_pct", 0.10),
            execute_on_fill=data.get("execute_on_fill", True),
            allow_amd=data.get("allow_amd", True),
        )
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "order_type": self.order_type,
            "max_contracts": self.max_contracts,
            "preferred_expiry_days": self.preferred_expiry_days,
            "strike_type": self.strike_type,
            "otm_percent": self.otm_percent,
            "min_premium": self.min_premium,
            "max_premium_pct": self.max_premium_pct,
            "execute_on_fill": self.execute_on_fill,
            "allow_amd": self.allow_amd,
        }


class ExecutionCustomizer:
    """Customize execution per-ticker or globally"""
    
    def __init__(self):
        self.global_config = ExecutionConfig()
        self.per_ticker: dict[str, PerTickerExecution] = {}
    
    def get_config(self, symbol: str) -> ExecutionConfig:
        """Get config for symbol"""
        return self.global_config
    
    def set_per_ticker(self, config: PerTickerExecution):
        """Set per-ticker config"""
        self.per_ticker[config.symbol] = config
    
    def set_global(self, config: ExecutionConfig):
        """Set global defaults"""
        self.global_config = config
    
    def get_available_strikes(
        self,
        symbol: str,
        underlying_price: float
    ) -> List[float]:
        """Get available strike prices"""
        strikes = []
        
        inc = 2.5 if underlying_price < 50 else 5 if underlying_price < 200 else 10
        atm = round(underlying_price / inc) * inc
        
        for i in range(-5, 6):
            strike = atm + (i * inc)
            if strike > 0:
                strikes.append(strike)
        
        return strikes
    
    def select_strike(
        self,
        underlying_price: float,
        option_type: str = "call",
        preference: str = "atm"
    ) -> float:
        """Select strike based on preference"""
        strikes = self.get_available_strikes("", underlying_price)
        
        if not strikes:
            return underlying_price
        
        if preference == "atm":
            return min(strikes, key=lambda x: abs(x - underlying_price))
        elif preference == "otm":
            if option_type == "call":
                return min([s for s in strikes if s > underlying_price], default=strikes[-1])
            else:
                return max([s for s in strikes if s < underlying_price], default=strikes[0])
        elif preference == "itm":
            if option_type == "call":
                return max([s for s in strikes if s < underlying_price], default=strikes[0])
            else:
                return min([s for s in strikes if s > underlying_price], default=strikes[-1])
        
        return strikes[len(strikes) // 2]
    
    def estimate_premium(
        self,
        strike: float,
        underlying: float,
        days_to_expiry: int = 30,
        volatility: float = 0.25,
        option_type: str = "call"
    ) -> float:
        """Estimate option premium"""
        import math
        
        S = underlying
        K = strike
        T = days_to_expiry / 365
        r = 0.05
        sigma = volatility
        
        if T <= 0:
            return 0.0
        
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        from math import exp
        
        if option_type == "call":
            premium = S * self._norm_cdf(d1) - K * exp(-r * T) * self._norm_cdf(d2)
        else:
            premium = K * exp(-r * T) * self._norm_cdf(-d2) - S * self._norm_cdf(-d1)
        
        return max(premium, 0.01)
    
    def _norm_cdf(self, x: float) -> float:
        """Normal CDF approximation"""
        import math
        
        a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
        p = 0.3275911
        
        sign = -1 if x < 0 else 1
        x = abs(x) / math.sqrt(2)
        
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        
        return 0.5 * (1.0 + sign * y)


_execution_customizer = ExecutionCustomizer()


def get_execution_customizer() -> ExecutionCustomizer:
    return _execution_customizer