"""
VEX (Vega Exposure) Analysis Module

Calculates aggregate vega exposure from options chain data to identify:
- Volatility sentiment (long vega = expecting vol increase)
- Volatility support/resistance zones
- Implied volatility regime changes

VEX = Sum(Vega × Open Interest × Contract Size × Direction)
- Positive VEX = Net long vega (benefited by vol increase)
- Negative VEX = Net short vega (hurt by vol increase)
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class VEXMetrics:
    """Aggregated VEX metrics for an options chain"""
    symbol: str
    timestamp: datetime
    spot_price: float
    
    # Total VEX
    total_call_vega: float = 0.0
    total_put_vega: float = 0.0
    net_vex: float = 0.0
    
    # IV Analysis
    atm_iv: float = 0.0
    call_iv: float = 0.0
    put_iv: float = 0.0
    iv_skul = 0.0  # IV Skew: put IV - call IV
    
    # Vol regime
    vol_regime: str = "normal"  # suppressed, normal, elevated, extreme
    vol_regime_change: str = "stable"  # rising, falling, stable
    
    # Support/resistance by vega
    vega_cluster_zones: List[Tuple[float, float]] = field(default_factory=list)
    vol_support: Optional[float] = None
    vol_resistance: Optional[float] = None
    
    # Sentiment
    sentiment: str = "neutral"  # bullish_vol, bearish_vol, neutral
    sentiment_strength: float = 0.0


class VEXEngine:
    """Calculate VEX from options chain data"""
    
    def __init__(self):
        self.history: List[VEXMetrics] = []
    
    async def analyze(
        self,
        symbol: str,
        options_chain: List,  # Uses OptionContract from gex.py
        spot_price: float,
        timestamp: Optional[datetime] = None
    ) -> VEXMetrics:
        """Analyze options chain and calculate VEX"""
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Import from gex module
        from gex import OptionContract
        
        # Separate calls and puts
        calls = [o for o in options_chain if o.call_put.upper() == "CALL"]
        puts = [o for o in options_chain if o.call_put.upper() == "PUT"]
        
        # Calculate total vega
        total_call_vega = sum(
            o.vega * o.open_interest * o.contract_size
            for o in calls
        )
        total_put_vega = sum(
            o.vega * o.open_interest * o.contract_size
            for o in puts
        )
        net_vex = total_call_vega - total_put_vega
        
        # Calculate IV metrics
        if calls:
            call_iv = sum(o.iv * o.open_interest for o in calls) / sum(o.open_interest for o in calls)
        else:
            call_iv = 0.0
        
        if puts:
            put_iv = sum(o.iv * o.open_interest for o in puts) / sum(o.open_interest for o in puts)
        else:
            put_iv = 0.0
        
        # Find ATM strike
        atm_strike = min(
            (abs(o.strike - spot_price), o.strike)
            for o in options_chain
        )[1]
        
        atm_options = [o for o in options_chain if abs(o.strike - atm_strike) < 0.01]
        if atm_options:
            atm_iv = sum(o.iv for o in atm_options) / len(atm_options)
        else:
            atm_iv = (call_iv + put_iv) / 2
        
        # IV skew (put IV > call IV = fear premium)
        iv_skul = put_iv - call_iv
        
        # Determine vol regime
        if atm_iv < 0.15:
            vol_regime = "suppressed"
        elif atm_iv < 0.25:
            vol_regime = "normal"
        elif atm_iv < 0.40:
            vol_regime = "elevated"
        else:
            vol_regime = "extreme"
        
        # Vol regime change detection
        vol_regime_change = "stable"
        if self.history:
            prev = self.history[-1]
            if prev.atm_iv > 0 and atm_iv > prev.atm_iv * 1.1:
                vol_regime_change = "rising"
            elif prev.atm_iv > 0 and atm_iv < prev.atm_iv * 0.9:
                vol_regime_change = "falling"
        
        # Vega clustering zones
        vega_cluster_zones = self._find_vega_clusters(options_chain, spot_price)
        
        # Vol support/resistance from vega walls
        call_zones = [
            o.strike for o in calls
            if o.strike < spot_price
        ]
        put_zones = [
            o.strike for o in puts
            if o.strike > spot_price
        ]
        
        vol_support = max(call_zones) if call_zones else spot_price * 0.95
        vol_resistance = min(put_zones) if put_zones else spot_price * 1.05
        
        # Sentiment from vega imbalance
        if net_vex > 0:
            sentiment = "bullish_vol"  # Long call vega = expecting up move
            sentiment_strength = min(1.0, abs(net_vex) / (total_call_vega + total_put_vega + 1))
        elif net_vex < 0:
            sentiment = "bearish_vol"  # Long put vega = expecting down move
            sentiment_strength = min(1.0, abs(net_vex) / (total_call_vega + total_put_vega + 1))
        else:
            sentiment = "neutral"
            sentiment_strength = 0.0
        
        metrics = VEXMetrics(
            symbol=symbol,
            timestamp=timestamp,
            spot_price=spot_price,
            total_call_vega=total_call_vega,
            total_put_vega=total_put_vega,
            net_vex=net_vex,
            atm_iv=atm_iv,
            call_iv=call_iv,
            put_iv=put_iv,
            iv_skul=iv_skul,
            vol_regime=vol_regime,
            vol_regime_change=vol_regime_change,
            vega_cluster_zones=vega_cluster_zones,
            vol_support=vol_support,
            vol_resistance=vol_resistance,
            sentiment=sentiment,
            sentiment_strength=sentiment_strength
        )
        
        self.history.append(metrics)
        return metrics
    
    def _find_vega_clusters(
        self,
        options_chain: List,
        spot_price: float,
        threshold_pct: float = 0.02
    ) -> List[Tuple[float, float]]:
        """Find zones of high vega concentration"""
        from gex import OptionContract
        
        # Aggregate vega by strike
        strike_vega: Dict[float, float] = {}
        
        for opt in options_chain:
            if opt.strike not in strike_vega:
                strike_vega[opt.strike] = 0.0
            strike_vega[opt.strike] += opt.vega * opt.open_interest * opt.contract_size
        
        if not strike_vega:
            return []
        
        # Sort by vega
        sorted_strikes = sorted(
            strike_vega.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Top 3 vega clusters
        clusters = []
        for strike, vega in sorted_strikes[:3]:
            if vega > 0:
                clusters.append((
                    strike * (1 - threshold_pct),
                    strike * (1 + threshold_pct)
                ))
        
        return clusters
    
    def get_vol_signal(self, symbol: str) -> Optional[Dict]:
        """Generate volatility trading signal"""
        recent = [m for m in self.history[-3:] if m.symbol == symbol]
        
        if len(recent) < 3:
            return None
        
        latest = recent[-1]
        prev = recent[-2]
        
        # Vol regime change signals
        if prev.vol_regime_change == "stable" and latest.vol_regime_change == "rising":
            return {
                "signal": "vol_expanding",
                "direction": "long_vol",
                "entry": latest.atm_iv,
                "reason": f"IV rising from {prev.atm_iv:.1%} to {latest.atm_iv:.1%}"
            }
        
        if prev.vol_regime_change == "rising" and latest.vol_regime_change == "falling":
            return {
                "signal": "vol_contracting",
                "direction": "short_vol",
                "entry": latest.atm_iv,
                "reason": "IV peak detected, expecting decline"
            }
        
        return None
    
    def get_iv_regime(self, symbol: str) -> str:
        """Get current IV regime"""
        recent = [m for m in self.history if m.symbol == symbol]
        
        if not recent:
            return "unknown"
        
        return recent[-1].vol_regime


# ============================================================================
# Prometheus Metrics Export
# ============================================================================

def export_to_prometheus(vex: VEXMetrics) -> Dict[str, float]:
    """Export VEX metrics for Prometheus scraping"""
    return {
        f"vex_total_call{{symbol=\"{vex.symbol}\"}}": vex.total_call_vega,
        f"vex_total_put{{symbol=\"{vex.symbol}\"}}": vex.total_put_vega,
        f"vex_net{{symbol=\"{vex.symbol}\"}}": vex.net_vex,
        f"vex_atm_iv{{symbol=\"{vex.symbol}\"}}": vex.atm_iv,
        f"vex_call_iv{{symbol=\"{vex.symbol}\"}}": vex.call_iv,
        f"vex_put_iv{{symbol=\"{vex.symbol}\"}}": vex.put_iv,
        f"vex_iv_skul{{symbol=\"{vex.symbol}\"}}": vex.iv_skul,
        f"vex_sentiment_strength{{symbol=\"{vex.symbol}\"}}": vex.sentiment_strength,
        f"vex_spot_price{{symbol=\"{vex.symbol}\"}}": vex.spot_price
    }


# ============================================================================
# Backtest Integration
# ============================================================================

class VEXSignalGenerator:
    """Generate signals based on VEX for backtesting"""
    
    def __init__(self, vex_engine: VEXEngine):
        self.vex_engine = vex_engine
    
    def generate_signal(self, symbol: str) -> int:
        """Generate volatility signal: 1=long_vol, -1=short_vol, 0=neutral"""
        signal = self.vex_engine.get_vol_signal(symbol)
        
        if signal is None:
            return 0
        
        return 1 if signal["direction"] == "long_vol" else -1
    
    def get_confidence(self, symbol: str) -> float:
        """Get signal confidence"""
        recent = self.vex_engine.history[-3:] if self.vex_engine.history else []
        
        if len(recent) < 3:
            return 0.0
        
        return recent[-1].sentiment_strength