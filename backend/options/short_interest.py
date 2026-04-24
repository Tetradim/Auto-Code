"""
Short Interest Analysis Module

Calculates short interest metrics to identify:
- Days to cover - How long to unwind short positions at current volume
- Short squeeze potential - High short interest + low volume = squeeze risk
- Cost basis analysis - Average short positions

Key Metrics:
- Short Interest: Total shares sold short
- Days to Cover: Short interest / Average daily volume
- Short Interest % of Float: Short interest as % of free trading float
- Cost Basis: Average price of short positions

Squeeze Signals:
- High days to cover (>5 days) = Elevated squeeze risk
- Low volume + high short = Extreme squeeze potential
- Increasing short + decreasing price = Bear trap risk
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SqueezeRisk(Enum):
    """Short squeeze risk levels"""
    MINIMAL = "minimal"  # < 2 days to cover
    LOW = "low"  # 2-3 days
    MODERATE = "moderate"  # 3-5 days
    HIGH = "high"  # 5-10 days
    EXTREME = "extreme"  # >10 days


@dataclass
class ShortInterestData:
    """Short interest data for a symbol"""
    symbol: str
    timestamp: datetime
    
    # Core metrics
    short_interest: float = 0.0  # Shares sold short
    short_interest_pct: float = 0.0  # % of float
    avg_daily_volume: float = 0.0  # Average daily volume
    days_to_cover: float = 0.0  # Short interest / ADV
    
    # Volume analysis
    volume_ratio: float = 0.0  # Current volume / average
    volume_trend: str = "stable"  # increasing, decreasing, stable
    
    # Cost basis
    cost_basis: float = 0.0  # Average short price
    cost_basis_std: float = 0.0  # Std deviation of cost basis
    
    # Short squeeze metrics
    squeeze_risk: str = "minimal"
    squeeze_score: float = 0.0  # 0-100
    
    # Position data
    shortable_shares: float = 0.0
    available_to_borrow: float = 0.0
    borrow_rate: float = 0.0  # Fee to borrow
    
    # Historical
    short_interest_change_pct: float = 0.0  # Change from previous period


@dataclass
class ShortInterestMetrics:
    """Aggregated short interest analysis"""
    symbol: str
    timestamp: datetime
    spot_price: float
    
    # Current state
    current: Optional[ShortInterestData] = None
    
    # Historical
    history: List[ShortInterestData] = field(default_factory=list)
    
    # Analysis
    squeeze_signals: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendation: str = "neutral"  # bullish, bearish, neutral
    confidence: float = 0.0


class ShortInterestEngine:
    """Calculate short interest metrics"""
    
    def __init__(self):
        self.history: Dict[str, List[ShortInterestData]] = {}
        self.analysis: Dict[str, ShortInterestMetrics] = {}
    
    async def analyze(
        self,
        symbol: str,
        short_interest: float,
        short_interest_pct: float,
        avg_daily_volume: float,
        spot_price: float,
        cost_basis: float = 0.0,
        borrow_rate: float = 0.0,
        shortable_shares: float = 0.0,
        timestamp: Optional[datetime] = None
    ) -> ShortInterestMetrics:
        """Analyze short interest and calculate squeeze potential"""
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Calculate days to cover
        days_to_cover = short_interest / avg_daily_volume if avg_daily_volume > 0 else 0
        
        # Calculate squeeze risk
        squeeze_risk = self._calculate_risk(days_to_cover)
        
        # Calculate squeeze score (0-100)
        squeeze_score = self._calculate_squeeze_score(
            days_to_cover, 
            short_interest_pct,
            borrow_rate
        )
        
        # Create data point
        data = ShortInterestData(
            symbol=symbol,
            timestamp=timestamp,
            short_interest=short_interest,
            short_interest_pct=short_interest_pct,
            avg_daily_volume=avg_daily_volume,
            days_to_cover=days_to_cover,
            cost_basis=cost_basis,
            borrow_rate=borrow_rate,
            shortable_shares=shortable_shares,
            squeeze_risk=squeeze_risk,
            squeeze_score=squeeze_score
        )
        
        # Store in history
        if symbol not in self.history:
            self.history[symbol] = []
        self.history[symbol].append(data)
        
        # Trim to last 30 days
        if len(self.history[symbol]) > 30:
            self.history[symbol] = self.history[symbol][-30:]
        
        # Calculate change from previous
        if len(self.history[symbol]) > 1:
            prev = self.history[symbol][-2]
            change = ((data.short_interest - prev.short_interest) / prev.short_interest * 100) if prev.short_interest > 0 else 0
            data.short_interest_change_pct = change
        
        # Calculate volume trend
        data.volume_trend = self._calculate_volume_trend(symbol)
        
        # Determine squeeze signals
        signals = self._generate_signals(data)
        
        # Make recommendation
        recommendation, confidence = self._make_recommendation(data, spot_price)
        
        metrics = ShortInterestMetrics(
            symbol=symbol,
            timestamp=timestamp,
            spot_price=spot_price,
            current=data,
            history=self.history[symbol],
            squeeze_signals=signals,
            recommendation=recommendation,
            confidence=confidence
        )
        
        self.analysis[symbol] = metrics
        return metrics
    
    def _calculate_risk(self, days_to_cover: float) -> str:
        """Determine squeeze risk level"""
        if days_to_cover < 2:
            return SqueezeRisk.MINIMAL.value
        elif days_to_cover < 3:
            return SqueezeRisk.LOW.value
        elif days_to_cover < 5:
            return SqueezeRisk.MODERATE.value
        elif days_to_cover < 10:
            return SqueezeRisk.HIGH.value
        else:
            return SqueezeRisk.EXTREME.value
    
    def _calculate_squeeze_score(
        self, 
        days_to_cover: float,
        short_interest_pct: float,
        borrow_rate: float
    ) -> float:
        """Calculate short squeeze probability score (0-100)"""
        score = 0.0
        
        # Days to cover contributes 0-40 points
        if days_to_cover > 10:
            score += 40
        elif days_to_cover > 5:
            score += 30
        elif days_to_cover > 3:
            score += 20
        elif days_to_cover > 1:
            score += 10
        
        # Short interest % of float contributes 0-30 points
        if short_interest_pct > 30:
            score += 30
        elif short_interest_pct > 20:
            score += 20
        elif short_interest_pct > 10:
            score += 10
        
        # Borrow rate contributes 0-30 points (high fee = high demand to short)
        if borrow_rate > 1.0:  # >100% (very high)
            score += 30
        elif borrow_rate > 0.5:  # 50-100%
            score += 20
        elif borrow_rate > 0.1:  # 10-50%
            score += 10
        
        return min(100, score)
    
    def _calculate_volume_trend(self, symbol: str) -> str:
        """Determine volume trend from history"""
        history = self.history.get(symbol, [])
        if len(history) < 5:
            return "stable"
        
        recent = [h.avg_daily_volume for h in history[-5:]]
        if all(recent[i] <= recent[i+1] for i in range(len(recent)-1)):
            return "increasing"
        elif all(recent[i] >= recent[i+1] for i in range(len(recent)-1)):
            return "decreasing"
        else:
            return "stable"
    
    def _generate_signals(self, data: ShortInterestData) -> List[str]:
        """Generate squeeze warning signals"""
        signals = []
        
        if data.days_to_cover > 10:
            signals.append(f"EXTREME: {data.days_to_cover:.1f} days to cover - extreme squeeze potential")
        elif data.days_to_cover > 5:
            signals.append(f"HIGH: {data.days_to_cover:.1f} days to cover - elevated squeeze risk")
        
        if data.short_interest_pct > 30:
            signals.append(f"Short Interest at {data.short_interest_pct:.1f}% of float - very high")
        
        if data.borrow_rate > 1.0:
            signals.append(f"Borrow fee {data.borrow_rate*100:.1f}% - expensive to short")
        
        if data.volume_trend == "decreasing" and data.days_to_cover > 5:
            signals.append("Declining volume + high short - squeeze trigger potential")
        
        if data.short_interest_change_pct > 20:
            signals.append(f"Short interest up {data.short_interest_change_pct:.1f}% - increasing bearish sentiment")
        
        return signals
    
    def _make_recommendation(
        self, 
        data: ShortInterestData,
        spot_price: float
    ) -> Tuple[str, float]:
        """Make trading recommendation based on short interest"""
        # High squeeze potential = potential for short-covering rally
        if data.squeeze_risk in [SqueezeRisk.HIGH.value, SqueezeRisk.EXTREME.value]:
            # If price already dropped significantly, potential bounce
            if data.cost_basis > spot_price * 1.1:
                return "bullish", data.squeeze_score / 100
            # If price hasn't dropped yet, still risky
            return "neutral", data.squeeze_score / 100
        
        # Low short interest - no squeeze potential
        if data.days_to_cover < 2:
            return "neutral", 0.3
        
        # Moderate - lean based on price action
        return "neutral", 0.5
    
    def get_summary(self, symbol: str) -> Optional[ShortInterestMetrics]:
        """Get latest analysis"""
        return self.analysis.get(symbol)


# ============================================================================
# Prometheus Export
# ============================================================================

def export_to_prometheus(metrics: ShortInterestMetrics) -> Dict[str, float]:
    """Export short interest metrics"""
    if not metrics.current:
        return {}
    
    data = metrics.current
    return {
        f"short_interest{{symbol=\"{metrics.symbol}\"}}": data.short_interest,
        f"short_interest_pct{{symbol=\"{metrics.symbol}\"}}": data.short_interest_pct,
        f"days_to_cover{{symbol=\"{metrics.symbol}\"}}": data.days_to_cover,
        f"squeeze_score{{symbol=\"{metrics.symbol}\"}}": data.squeeze_score,
        f"borrow_rate{{symbol=\"{metrics.symbol}\"}}": data.borrow_rate,
    }