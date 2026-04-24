"""
GEX (Gamma Exposure) Analysis Module

Calculates aggregate gamma exposure from options chain data to identify:
- Net directional pressure from market makers
- Support/resistance zones based on gamma clustering
- Potential volatility expansion points

GEX = Sum(Gamma × Open Interest × Contract Size × Direction)
- Positive GEX = Market maker long gamma (hedged, less volatility)
- Negative GEX = Market maker short gamma (unhedged, more volatility)
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class OptionContract:
    """Single option contract"""
    strike: float
    expiration: str
    call_put: str  # "CALL" or "PUT"
    bid: float
    ask: float
    iv: float  # Implied volatility
    gamma: float  # Greeks: gamma per contract
    theta: float
    vega: float
    delta: float
    open_interest: int
    volume: int
    contract_size: int = 100  # Standard: 100 shares


@dataclass
class StrikeCluster:
    """Gamma exposure at a specific strike"""
    strike: float
    call_gamma: float = 0.0
    put_gamma: float = 0.0
    call_oi: int = 0
    put_oi: int = 0
    net_gamma_exposure: float = 0.0
    weighted_gamma: float = 0.0


@dataclass
class GEXMetrics:
    """Aggregated GEX metrics for an options chain"""
    symbol: str
    timestamp: datetime
    spot_price: float
    
    # Total GEX
    total_call_gamma: float = 0.0
    total_put_gamma: float = 0.0
    net_gex: float = 0.0  # Calls - Puts
    
    # GEX Zones
    max_gamma_strike: float = 0.0
    call_gamma_max_strike: float = 0.0
    put_gamma_max_strike: float = 0.0
    
    # Support/Resistance
    gamma_cluster_zones: List[Tuple[float, float]] = field(default_factory=list)
    support_zone: Optional[float] = None
    resistance_zone: Optional[float] = None
    
    # Market bias
    market_bias: str = "neutral"  # bullish, bearish, neutral
    bias_strength: float = 0.0
    
    # Volatility signal
    vol_signal: str = "normal"  # suppressed, normal, elevated


class GEXEngine:
    """Calculate GEX from options chain data"""
    
    def __init__(self, spot_reference: Optional[float] = None):
        self.spot_reference = spot_reference
        self.history: List[GEXMetrics] = []
    
    async def analyze(
        self,
        symbol: str,
        options_chain: List[OptionContract],
        spot_price: float,
        timestamp: Optional[datetime] = None
    ) -> GEXMetrics:
        """Analyze options chain and calculate GEX"""
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Group by strike
        strikes: Dict[float, StrikeCluster] = {}
        
        for opt in options_chain:
            # Calculate gamma exposure
            # GEX = Gamma × OI × Contract Size
            gamma_exposure = opt.gamma * opt.open_interest * opt.contract_size
            
            if opt.strike not in strikes:
                strikes[opt.strike] = StrikeCluster(strike=opt.strike)
            
            cluster = strikes[opt.strike]
            
            if opt.call_put.upper() == "CALL":
                cluster.call_gamma += gamma_exposure
                cluster.call_oi += opt.open_interest
            else:
                cluster.put_gamma += gamma_exposure
                cluster.put_oi += opt.open_interest
        
        # Calculate net gamma exposure per strike
        for strike, cluster in strikes.items():
            cluster.net_gamma_exposure = cluster.call_gamma - cluster.put_gamma
            # Weighted by OI for zone detection
            cluster.weighted_gamma = (
                cluster.call_gamma + cluster.put_gamma
            ) * (1 + abs(cluster.net_gamma_exposure) / (cluster.call_gamma + cluster.put_gamma + 1))
        
        # Aggregate totals
        total_call_gamma = sum(s.call_gamma for s in strikes.values())
        total_put_gamma = sum(s.put_gamma for s in strikes.values())
        net_gex = total_call_gamma - total_put_gamma
        
        # Find max gamma strikes
        if strikes:
            call_max = max(strikes.items(), key=lambda x: x[1].call_gamma)
            put_max = max(strikes.items(), key=lambda x: x[1].put_gamma)
            total_max = max(strikes.items(), key=lambda x: x[1].weighted_gamma)
            
            call_gamma_max_strike = call_max[0]
            put_gamma_max_strike = put_max[0]
            max_gamma_strike = total_max[0]
        else:
            call_gamma_max_strike = put_gamma_max_strike = max_gamma_strike = spot_price
        
        # Identify support/resistance zones (gamma clustering)
        gamma_cluster_zones = self._find_gamma_clusters(strikes, spot_price)
        
        # Determine bias
        if net_gex > 0:
            market_bias = "bullish"
            bias_strength = min(1.0, abs(net_gex) / (total_call_gamma + total_put_gamma + 1))
        elif net_gex < 0:
            market_bias = "bearish"
            bias_strength = min(1.0, abs(net_gex) / (total_call_gamma + total_put_gamma + 1))
        else:
            market_bias = "neutral"
            bias_strength = 0.0
        
        # Volatility signal based on net GEX magnitude
        gex_magnitude = abs(net_gex) / (total_call_gamma + total_put_gamma + 1)
        if gex_magnitude < 0.2:
            vol_signal = "suppressed"
        elif gex_magnitude > 0.6:
            vol_signal = "elevated"
        else:
            vol_signal = "normal"
        
        # Support/resistance from gamma walls
        support_zone = call_gamma_max_strike if call_gamma_max_strike < spot_price else None
        resistance_zone = put_gamma_max_strike if put_gamma_max_strike > spot_price else None
        
        metrics = GEXMetrics(
            symbol=symbol,
            timestamp=timestamp,
            spot_price=spot_price,
            total_call_gamma=total_call_gamma,
            total_put_gamma=total_put_gamma,
            net_gex=net_gex,
            max_gamma_strike=max_gamma_strike,
            call_gamma_max_strike=call_gamma_max_strike,
            put_gamma_max_strike=put_gamma_max_strike,
            gamma_cluster_zones=gamma_cluster_zones,
            support_zone=support_zone,
            resistance_zone=resistance_zone,
            market_bias=market_bias,
            bias_strength=bias_strength,
            vol_signal=vol_signal
        )
        
        self.history.append(metrics)
        return metrics
    
    def _find_gamma_clusters(
        self,
        strikes: Dict[float, StrikeCluster],
        spot_price: float,
        threshold_pct: float = 0.02
    ) -> List[Tuple[float, float]]:
        """Find zones of high gamma concentration"""
        if not strikes:
            return []
        
        # Sort by weighted gamma
        sorted_strikes = sorted(
            strikes.items(),
            key=lambda x: x[1].weighted_gamma,
            reverse=True
        )
        
        # Take top 3 as clusters
        clusters = []
        for strike, cluster in sorted_strikes[:3]:
            if cluster.weighted_gamma > 0:
                clusters.append((
                    strike * (1 - threshold_pct),
                    strike * (1 + threshold_pct)
                ))
        
        return clusters
    
    def get_support_resistance(
        self,
        symbol: str,
        lookback: int = 5
    ) -> Dict[str, Optional[float]]:
        """Get SR levels from recent GEX history"""
        recent = [m for m in self.history[-lookback:] if m.symbol == symbol]
        
        if not recent:
            return {"support": None, "resistance": None}
        
        support = None
        resistance = None
        
        for m in recent:
            if m.support_zone and (support is None or m.support_zone > support):
                support = m.support_zone
            if m.resistance_zone and (resistance is None or m.resistance_zone < resistance):
                resistance = m.resistance_zone
        
        return {"support": support, "resistance": resistance}
    
    def get_trade_signal(self, symbol: str) -> Optional[Dict]:
        """Generate trade signal from GEX"""
        recent = [m for m in self.history[-3:] if m.symbol == symbol]
        
        if len(recent) < 3:
            return None
        
        latest = recent[-1]
        prev = recent[-2]
        
        # GEX going from negative to positive = suppressed vol, potential rally
        if prev.net_gex < 0 and latest.net_gex > 0:
            return {
                "signal": "long",
                "reason": "GEX_turning_positive_suppressed_vol",
                "entry": latest.support_zone or latest.spot_price * 0.98,
                "stop": latest.spot_price * 0.95
            }
        
        # GEX going from positive to negative = elevated vol, potential decline
        if prev.net_gex > 0 and latest.net_gex < 0:
            return {
                "signal": "short",
                "reason": "GEX_turning_negative_elevated_vol",
                "entry": latest.resistance_zone or latest.spot_price * 1.02,
                "stop": latest.spot_price * 1.05
            }
        
        return None


# ============================================================================
# Prometheus Metrics Export
# ============================================================================

def export_to_prometheus(gex: GEXMetrics) -> Dict[str, float]:
    """Export GEX metrics for Prometheus scraping"""
    return {
        f"gex_total_call{{symbol=\"{gex.symbol}\"}}": gex.total_call_gamma,
        f"gex_total_put{{symbol=\"{gex.symbol}\"}}": gex.total_put_gamma,
        f"gex_net{{symbol=\"{gex.symbol}\"}}": gex.net_gex,
        f"gex_max_strike{{symbol=\"{gex.symbol}\"}}": gex.max_gamma_strike,
        f"gex_call_max_strike{{symbol=\"{gex.symbol}\"}}": gex.call_gamma_max_strike,
        f"gex_put_max_strike{{symbol=\"{gex.symbol}\"}}": gex.put_gamma_max_strike,
        f"gex_bias_strength{{symbol=\"{gex.symbol}\"}}": gex.bias_strength,
        f"gex_spot_price{{symbol=\"{gex.symbol}\"}}": gex.spot_price
    }


# ============================================================================
# Backtest Integration
# ============================================================================

class GEXSignalGenerator:
    """Generate signals based on GEX for backtesting"""
    
    def __init__(self, gex_engine: GEXEngine):
        self.gex_engine = gex_engine
    
    def generate_signal(self, symbol: str) -> int:
        """Generate trading signal: 1=long, -1=short, 0=neutral"""
        signal = self.gex_engine.get_trade_signal(symbol)
        
        if signal is None:
            return 0
        
        return 1 if signal["signal"] == "long" else -1
    
    def get_confidence(self, symbol: str) -> float:
        """Get signal confidence 0-1"""
        recent = self.gex_engine.history[-3:] if self.gex_engine.history else []
        
        if len(recent) < 3:
            return 0.0
        
        latest = recent[-1]
        return latest.bias_strength