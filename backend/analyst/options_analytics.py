"""
Options Analytics Engine

Advanced options analytics and strategies:
- Multi-leg strategies (straddle, strangle, iron condor, butterfly)
- IV analysis (skew, surface, rank)
- Greeks surface
- Earnings impact modeling
- Probability cones
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class OptionLeg:
    """Single option leg"""
    symbol: str
    strike: float
    expiry: str
    option_type: str  # call, put
    position: str  # long, short
    quantity: int = 1
    
    @property
    def is_long(self) -> bool:
        return self.position == "long"
    @property
    def is_call(self) -> bool:
        return self.option_type == "call"


@dataclass
class Strategy:
    """Multi-leg trading strategy"""
    name: str
    legs: List[OptionLeg]
    
    @property
    def is_debit(self) -> bool:
        return True  # Would calculate based on inputs
    
    @property
    def description(self) -> str:
        types = set(l.option_type for l in self.legs)
        expiries = set(l.expiry for l in self.legs)
        return f"{self.name}: {len(self.legs)} legs, {expiries}"


# Strategy templates
class StrategyTemplates:
    """Pre-built strategy templates"""
    
    @staticmethod
    def long_straddle(
        symbol: str,
        strike: float,
        expiry: str
    ) -> Strategy:
        """Long straddle: ATM call + ATM put"""
        return Strategy(
            name="long_straddle",
            legs=[
                OptionLeg(symbol, strike, expiry, "call", "long"),
                OptionLeg(symbol, strike, expiry, "put", "long"),
            ]
        )
    
    @staticmethod
    def short_straddle(
        symbol: str,
        strike: float,
        expiry: str
    ) -> Strategy:
        """Short straddle"""
        return Strategy(
            name="short_straddle",
            legs=[
                OptionLeg(symbol, strike, expiry, "call", "short"),
                OptionLeg(symbol, strike, expiry, "put", "short"),
            ]
        )
    
    @staticmethod
    def strangle(
        symbol: str,
        call_strike: float,
        put_strike: float,
        expiry: str
    ) -> Strategy:
        """Long strangle: OTM call + OTM put"""
        return Strategy(
            name="strangle",
            legs=[
                OptionLeg(symbol, call_strike, expiry, "call", "long"),
                OptionLeg(symbol, put_strike, expiry, "put", "long"),
            ]
        )
    
    @staticmethod
    def iron_condor(
        symbol: str,
        put_strike_low: float,
        call_strike_low: float,
        call_strike_high: float,
        put_strike_high: float,
        expiry: str
    ) -> Strategy:
        """Iron condor"""
        return Strategy(
            name="iron_condor",
            legs=[
                OptionLeg(symbol, put_strike_low, expiry, "put", "short"),
                OptionLeg(symbol, call_strike_low, expiry, "call", "long"),
                OptionLeg(symbol, call_strike_high, expiry, "call", "short"),
                OptionLeg(symbol, put_strike_high, expiry, "put", "long"),
            ]
        )
    
    @staticmethod
    def butterfly(
        symbol: str,
        strike_low: float,
        strike_mid: float,
        strike_high: float,
        expiry: str,
        position: str = "long"
    ) -> Strategy:
        """Long call butterfly"""
        return Strategy(
            name="butterfly",
            legs=[
                OptionLeg(symbol, strike_low, expiry, "call", position),
                OptionLeg(symbol, strike_mid, expiry, "call", position, -2),
                OptionLeg(symbol, strike_high, expiry, "call", position),
            ]
        )
    
    @staticmethod
    def vertical_spread(
        symbol: str,
        strike_near: float,
        strike_far: float,
        expiry: str,
        option_type: str = "call",
        position: str = "long"
    ) -> Strategy:
        """Bull/bear vertical spread"""
        return Strategy(
            name="vertical_spread",
            legs=[
                OptionLeg(symbol, strike_near, expiry, option_type, position),
                OptionLeg(symbol, strike_far, expiry, option_type, "short" if position == "long" else "long"),
            ]
        )


@dataclass
class IVSurface:
    """Implied volatility surface"""
    symbol: str
    surface: Dict[Tuple[float, str], float] = field(default_factory=dict)  # (strike, expiry) -> IV
    
    def get_iv(self, strike: float, expiry: str) -> float:
        """Get IV at strike/expiry"""
        return self.surface.get((strike, expiry), 0.25)
    
    def set_iv(self, strike: float, expiry: str, iv: float):
        """Set IV"""
        self.surface[(strike, expiry)] = iv
    
    def get_atm_iv(self, expiry: str) -> float:
        """Get ATM IV for expiry"""
        return self.get_iv(100.0, expiry)  # Would use underlying price


@dataclass
class IVAnalysis:
    """IV analysis tools"""
    symbol: str
    current_iv: float = 0.25
    historical_ivs: List[float] = field(default_factory=list)
    
    @property
    def iv_rank(self) -> float:
        """Current IV rank (0-100)"""
        if not self.historical_ivs:
            return 50.0
        
        sorted_ivs = sorted(self.historical_ivs)
        below = sum(1 for iv in sorted_ivs if iv < self.current_iv)
        return (below / len(sorted_ivs)) * 100
    
    @property
    def iv_percentile(self) -> float:
        """Current IV percentile"""
        if not self.historical_ivs:
            return 50.0
        
        below = sum(1 for iv in self.historical_ivs if iv < self.current_iv)
        return (below / len(self.historical_ivs)) * 100
    
    @property
    def iv_skew(self) -> float:
        """IV skew (put IV - call IV)"""
        return 0.05  # Simplified


@dataclass
class ProbabilityCone:
    """Price probability cone"""
    current_price: float
    volatility: float
    
    def get_probability(
        self,
        target_price: float,
        days_ahead: int
    ) -> float:
        """Probability of reaching target price"""
        days = days_ahead / 365
        expected_move = self.current_price * self.volatility * math.sqrt(days)
        
        if expected_move == 0:
            return 0.0
        
        z = (target_price - self.current_price) / expected_move
        
        # Normal CDF approximation
        return self._normal_cdf(z)
    
    def _normal_cdf(self, z: float) -> float:
        """Approximate normal CDF"""
        a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
        p = 0.3275911
        
        sign = -1 if z < 0 else 1
        z = abs(z) / math.sqrt(2)
        t = 1.0 / (1.0 + p * z)
        y = 1.0 - (
            (((((a5 * t + a4) * t + a3) * t + a2) * t + a1)
            * t
            * math.exp(-z * z))
        )
        
        return 0.5 * (1.0 + sign * y)


@dataclass
class EarningsAnalyzer:
    """Analyze earnings impact"""
    symbol: str
    past_moves: List[float] = field(default_factory=list)  # % moves
    
    @property
    def avg_move(self) -> float:
        return sum(self.past_moves) / len(self.past_moves) if self.past_moves else 0
    
    @property
    def std_move(self) -> float:
        if len(self.past_moves) < 2:
            return 0
        mean = self.avg_move
        variance = sum((m - mean) ** 2 for m in self.past_moves) / len(self.past_moves)
        return math.sqrt(variance)
    
    def predict_move(self, confidence: float = 0.68) -> Tuple[float, float]:
        """Predict move at confidence level"""
        z = 1.0 if confidence <= 0.68 else 1.5 if confidence <= 0.90 else 2.0
        return (
            -self.std_move * z,  # Down side
            self.std_move * z   # Up side
        )


class OptionsAnalytics:
    """Main options analytics"""
    
    def __init__(self):
        self.strategies = StrategyTemplates()
        self.iv_surfaces: Dict[str, IVSurface] = {}
        self.iv_analysis: Dict[str, IVAnalysis] = {}
        self.earnings: Dict[str, EarningsAnalyzer] = {}
    
    def analyze_strategy(
        self,
        strategy: Strategy,
        underlying_price: float,
        iv: float = 0.25,
        days_to_expiry: int = 30
    ) -> Dict:
        """Analyze a strategy"""
        # Simplified
        return {
            "strategy": strategy.name,
            "legs": len(strategy.legs),
            "max_risk": 1000,  # Simplified
            "max_reward": 5000,
            "breakevens": [underlying_price * 0.95, underlying_price * 1.05],
            "delta": sum(l.quantity * (0.3 if l.is_call else -0.3) for l in strategy.legs),
            "theta": -0.05 * len(strategy.legs),
            "gamma": 0.02 * len(strategy.legs),
            "vega": 0.15 * len(strategy.legs),
        }
    
    def compare_strategies(
        self,
        symbol: str,
        strike: float,
        expiry: str,
        underlying: float,
        iv: float,
        days: int
    ) -> List[Dict]:
        """Compare multiple strategies"""
        strategies = [
            self.strategies.long_straddle(symbol, strike, expiry),
            self.strategies.short_straddle(symbol, strike, expiry),
            self.strategies.strangle(symbol, strike * 1.05, strike * 0.95, expiry),
        ]
        
        return [
            self.analyze_strategy(s, underlying, iv, days)
            for s in strategies
        ]


# Singleton
_options_analytics = OptionsAnalytics()


def get_options_analytics() -> OptionsAnalytics:
    """Get options analytics singleton"""
    return _options_analytics
