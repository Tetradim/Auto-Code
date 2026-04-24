"""
Delta (Direction & Probability) Analysis Module

Calculates delta exposure from options chain data to identify:
- Directional sensitivity to underlying price changes
- Probability of expiring in-the-money (ITM)
- Net directional pressure from market makers
- Support/resistance levels based on delta clustering

Delta = Rate of change of option price with respect to underlying price
- Positive Delta = Moving with underlying (bullish exposure)
- Negative Delta = Moving against underlying (bearish exposure)
- Delta closest to 1 or -1 = High probability of ITM at expiration

For Long (Buying) Positions:
- Goal: High Delta (closer to ±1) means strong directional exposure
- Higher absolute delta = More profit per $1 move in underlying
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class DeltaDirection(Enum):
    """Direction based on delta"""
    BULLISH = "bullish"  # Delta > 0
    BEARISH = "bearish"  # Delta < 0
    NEUTRAL = "neutral"  # Delta ≈ 0


class Moneyness(Enum):
    """Option moneyness"""
    ITM = "itm"  # In-the-money
    ATM = "atm"  # At-the-money
    OTM = "otm"  # Out-of-the-money


@dataclass
class DeltaMetrics:
    """Aggregated Delta metrics for an options chain"""
    symbol: str
    timestamp: datetime
    spot_price: float
    
    # Total Delta Exposure
    total_call_delta: float = 0.0
    total_put_delta: float = 0.0
    net_delta: float = 0.0  # Calls - Puts
    
    # Directional Analysis
    direction: str = "neutral"  # bullish, bearish, neutral
    direction_strength: float = 0.0  # 0-1 scale
    
    # Probability Metrics
    prob_itm_call: float = 0.0  # Probability of calls expiring ITM
    prob_itm_put: float = 0.0  # Probability of puts expiring ITM
    weighted_prob_itm: float = 0.0  # OI-weighted probability
    
    # Strike Analysis
    call_delta_max_strike: float = 0.0  # Highest delta call strike
    put_delta_max_strike: float = 0.0  # Lowest (most negative) put strike
    
    # Delta Clustering
    delta_cluster_zones: List[Tuple[float, float]] = field(default_factory=list)
    support_zone: Optional[float] = None  # Call delta support
    resistance_zone: Optional[float] = None  # Put delta resistance
    
    # Risk Metrics
    delta_risk: str = "low"  # low, medium, high
    delta_exposure_pct: float = 0.0  # % of portfolio exposed


@dataclass
class OptionDelta:
    """Delta for a single option"""
    strike: float
    expiration: str
    call_put: str
    bid: float
    ask: float
    iv: float
    gamma: float
    theta: float
    vega: float
    delta: float
    open_interest: int
    volume: int
    contract_size: int = 100
    
    @property
    def delta_exposure(self) -> float:
        """Total delta exposure = Delta × OI × Contract Size"""
        return self.delta * self.open_interest * self.contract_size
    
    @property
    def prob_itm(self) -> float:
        """Approximate probability of expiring ITM using delta ≈ N(d1) for calls, N(d1)-1 for puts"""
        from math import abs
        
        if self.call_put.upper() == "CALL":
            # Delta ≈ N(d1) for calls, so delta itself is approx probability
            return max(0, min(1, self.delta))
        else:
            # Delta ≈ N(d1) - 1 for puts
            return max(0, min(1, abs(self.delta)))


class DeltaEngine:
    """Calculate Delta from options chain data"""
    
    def __init__(self):
        self.history: List[DeltaMetrics] = []
    
    async def analyze(
        self,
        symbol: str,
        options_chain: List,
        spot_price: float,
        timestamp: Optional[datetime] = None
    ) -> DeltaMetrics:
        """Analyze options chain and calculate Delta"""
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        from gex import OptionContract
        
        # Separate calls and puts
        calls = [o for o in options_chain if o.call_put.upper() == "CALL"]
        puts = [o for o in options_chain if o.call_put.upper() == "PUT"]
        
        # Calculate total delta exposure
        total_call_delta = sum(
            o.delta * o.open_interest * o.contract_size
            for o in calls
        )
        total_put_delta = sum(
            o.delta * o.open_interest * o.contract_size
            for o in puts
        )
        net_delta = total_call_delta - total_put_delta
        
        # Direction analysis
        if net_delta > 0:
            direction = DeltaDirection.BULLISH.value
            direction_strength = min(1.0, abs(net_delta) / (abs(total_call_delta) + abs(total_put_delta) + 1))
        elif net_delta < 0:
            direction = DeltaDirection.BEARISH.value
            direction_strength = min(1.0, abs(net_delta) / (abs(total_call_delta) + abs(total_put_delta) + 1))
        else:
            direction = DeltaDirection.NEUTRAL.value
            direction_strength = 0.0
        
        # Probability of ITM
        if calls:
            call_oi = sum(o.open_interest for o in calls)
            prob_itm_call = sum(o.delta * o.open_interest for o in calls) / max(1, call_oi)
        else:
            prob_itm_call = 0.0
        
        if puts:
            put_oi = sum(o.open_interest for o in puts)
            # For puts, delta is negative, so use absolute value for prob
            prob_itm_put = sum(abs(o.delta) * o.open_interest for o in puts) / max(1, put_oi)
        else:
            prob_itm_put = 0.0
        
        # Weighted probability of ITM
        total_oi = sum(o.open_interest for o in options_chain)
        if total_oi > 0:
            weighted_prob_itm = (
                sum(o.delta * o.open_interest for o in options_chain if o.call_put.upper() == "CALL") +
                sum(abs(o.delta) * o.open_interest for o in options_chain if o.call_put.upper() == "PUT")
            ) / total_oi
        else:
            weighted_prob_itm = 0.0
        
        # Find max delta strikes
        if calls:
            call_max = max(calls, key=lambda x: x.delta)
            call_delta_max_strike = call_max.strike
        else:
            call_delta_max_strike = spot_price
        
        if puts:
            put_min = min(puts, key=lambda x: x.delta)
            put_delta_max_strike = put_min.strike
        else:
            put_delta_max_strike = spot_price
        
        # Delta clustering zones
        delta_cluster_zones = self._find_delta_clusters(options_chain, spot_price)
        
        # Support/resistance zones
        # Calls with high delta act as support (they want price up)
        call_zones = [o.strike for o in calls if o.delta > 0.3]
        # Puts with low (negative) delta act as resistance (they want price down)
        put_zones = [o.strike for o in puts if o.delta < -0.3]
        
        support_zone = max(call_zones) if call_zones else None
        resistance_zone = min(put_zones) if put_zones else None
        
        # Delta risk assessment
        delta_exposure_pct = abs(net_delta) / (spot_price * 100)  # Normalized
        if delta_exposure_pct > 0.5:
            delta_risk = "high"
        elif delta_exposure_pct > 0.25:
            delta_risk = "medium"
        else:
            delta_risk = "low"
        
        metrics = DeltaMetrics(
            symbol=symbol,
            timestamp=timestamp,
            spot_price=spot_price,
            total_call_delta=total_call_delta,
            total_put_delta=total_put_delta,
            net_delta=net_delta,
            direction=direction,
            direction_strength=direction_strength,
            prob_itm_call=prob_itm_call,
            prob_itm_put=prob_itm_put,
            weighted_prob_itm=weighted_prob_itm,
            call_delta_max_strike=call_delta_max_strike,
            put_delta_max_strike=put_delta_max_strike,
            delta_cluster_zones=delta_cluster_zones,
            support_zone=support_zone,
            resistance_zone=resistance_zone,
            delta_risk=delta_risk,
            delta_exposure_pct=delta_exposure_pct
        )
        
        self.history.append(metrics)
        return metrics
    
    def _find_delta_clusters(
        self,
        options_chain: List,
        spot_price: float,
        threshold_pct: float = 0.02
    ) -> List[Tuple[float, float]]:
        """Find zones of high delta concentration"""
        from gex import OptionContract
        
        # Aggregate delta by strike
        strike_delta: Dict[float, float] = {}
        
        for opt in options_chain:
            if opt.strike not in strike_delta:
                strike_delta[opt.strike] = 0.0
            strike_delta[opt.strike] += opt.delta * opt.open_interest * opt.contract_size
        
        if not strike_delta:
            return []
        
        # Sort by absolute delta
        sorted_strikes = sorted(
            strike_delta.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        # Top 3 delta clusters
        clusters = []
        for strike, delta in sorted_strikes[:3]:
            if abs(delta) > 0:
                clusters.append((
                    strike * (1 - threshold_pct),
                    strike * (1 + threshold_pct)
                ))
        
        return clusters
    
    def get_direction_signal(self, symbol: str) -> Optional[Dict]:
        """Generate directional trading signal from Delta"""
        recent = [m for m in self.history[-3:] if m.symbol == symbol]
        
        if len(recent) < 3:
            return None
        
        latest = recent[-1]
        prev = recent[-2]
        
        # Strong bullish momentum
        if prev.direction == "bearish" and latest.direction == "bullish":
            return {
                "signal": "long",
                "direction": "bullish",
                "reason": "Delta flipped bullish - institutional buying",
                "entry": latest.support_zone or latest.spot_price * 0.98,
                "stop": latest.spot_price * 0.95,
                "confidence": latest.direction_strength
            }
        
        # Strong bearish momentum
        if prev.direction == "bullish" and latest.direction == "bearish":
            return {
                "signal": "short",
                "direction": "bearish",
                "reason": "Delta flipped bearish - institutional selling",
                "entry": latest.resistance_zone or latest.spot_price * 1.02,
                "stop": latest.spot_price * 1.05,
                "confidence": latest.direction_strength
            }
        
        return None
    
    def get_probability_signal(self, symbol: str) -> Optional[Dict]:
        """Generate probability-based signal"""
        recent = [m for m in self.history[-3:] if m.symbol == symbol]
        
        if not recent:
            return None
        
        latest = recent[-1]
        
        # High ITM probability
        if latest.weighted_prob_itm > 0.7:
            return {
                "signal": "high_prob",
                "type": "momentum",
                "direction": "bullish" if latest.net_delta > 0 else "bearish",
                "prob_itm": latest.weighted_prob_itm,
                "reason": f"High probability {latest.weighted_prob_itm:.0%} of ITM expiration"
            }
        
        # Low ITM probability - expect reversal
        if latest.weighted_prob_itm < 0.3:
            return {
                "signal": "low_prob",
                "type": "reversal",
                "direction": "bearish" if latest.net_delta > 0 else "bullish",
                "prob_itm": latest.weighted_prob_itm,
                "reason": f"Low probability {latest.weighted_prob_itm:.0%} of ITM expiration"
            }
        
        return None


# ============================================================================
# Prometheus Metrics Export
# ============================================================================

def export_to_prometheus(delta: DeltaMetrics) -> Dict[str, float]:
    """Export Delta metrics for Prometheus scraping"""
    return {
        f"delta_total_call{{symbol=\"{delta.symbol}\"}}": delta.total_call_delta,
        f"delta_total_put{{symbol=\"{delta.symbol}\"}}": delta.total_put_delta,
        f"delta_net{{symbol=\"{delta.symbol}\"}}": delta.net_delta,
        f"delta_direction_strength{{symbol=\"{delta.symbol}\"}}": delta.direction_strength,
        f"delta_prob_itm_call{{symbol=\"{delta.symbol}\"}}": delta.prob_itm_call,
        f"delta_prob_itm_put{{symbol=\"{delta.symbol}\"}}": delta.prob_itm_put,
        f"delta_weighted_prob_itm{{symbol=\"{delta.symbol}\"}}": delta.weighted_prob_itm,
        f"delta_call_max_strike{{symbol=\"{delta.symbol}\"}}": delta.call_delta_max_strike,
        f"delta_put_max_strike{{symbol=\"{delta.symbol}\"}}": delta.put_delta_max_strike,
        f"delta_exposure_pct{{symbol=\"{delta.symbol}\"}}": delta.delta_exposure_pct,
        f"delta_spot_price{{symbol=\"{delta.symbol}\"}}": delta.spot_price
    }


# ============================================================================
# Backtest Integration
# ============================================================================

class DeltaSignalGenerator:
    """Generate signals based on Delta for backtesting"""
    
    def __init__(self, delta_engine: DeltaEngine):
        self.delta_engine = delta_engine
    
    def generate_signal(self, symbol: str) -> int:
        """Generate trading signal: 1=long, -1=short, 0=neutral"""
        signal = self.delta_engine.get_direction_signal(symbol)
        
        if signal is None:
            return 0
        
        return 1 if signal["signal"] == "long" else -1
    
    def get_confidence(self, symbol: str) -> float:
        """Get signal confidence 0-1"""
        recent = self.delta_engine.history[-3:] if self.delta_engine.history else []
        
        if len(recent) < 3:
            return 0.0
        
        latest = recent[-1]
        return latest.direction_strength