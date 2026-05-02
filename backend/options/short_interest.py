"""
Short Interest Analysis Module

Calculates short interest metrics to identify:
- Days to cover - How long to unwind short positions at current volume
- Short squeeze potential - High short interest + low volume = squeeze risk
- Cost basis analysis - Average short positions
- Gamma squeeze potential - Market maker hedging
- Short supply correlation - When short squeeze meets gamma squeeze

Key Metrics:
- Short Interest: Total shares sold short
- Days to Cover: Short interest / Average daily volume
- Short Interest % of Float: Short interest as % of free trading float
- Cost Basis: Average price of short positions
- GEX (Gamma Exposure): Net gamma from options market makers
- Short Supply Index: Combined squeeze indicators

Squeeze Signals:
- High days to cover (>5 days) = Elevated squeeze risk
- Low volume + high short = Extreme squeeze potential
- Increasing short + decreasing price = Bear trap risk
- High GEX + high short = Gamma + Short squeeze combo

Enhanced Features (v2):
- Squeeze probability model with ML-style scoring
- Historical backtesting data
- Correlation with GEX/VEX
- Multi-timeframe analysis
- Earnings catalyst proximity detection
- Social sentiment integration
- Real-time API export to Prometheus/Grafana
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable, Any
from enum import Enum
import json
import asyncio

logger = logging.getLogger(__name__)


class SqueezeRisk(Enum):
    """Short squeeze risk levels"""
    MINIMAL = "minimal"  # < 2 days to cover
    LOW = "low"  # 2-3 days
    MODERATE = "moderate"  # 3-5 days
    HIGH = "high"  # 5-10 days
    EXTREME = "extreme"  # >10 days


class CatalystType(Enum):
    """Potential squeeze catalysts"""
    EARNINGS = "earnings"
    FDA_DECISION = "fda_decision"
    MERGER_ANNOUNCEMENT = "merger_announcement"
    BUYOUT_OFFER = "buyout_offer"
    INSIDER_BUYING = "insider_buying"
    SHORT_REPORT_REBUTTAL = "short_report_rebuttal"
    CATALYST_UPGRADE = "catalyst_upgrade"


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
    volume_spike: bool = False  # Volume > 2x average
    
    # Cost basis
    cost_basis: float = 0.0  # Average short price
    cost_basis_std: float = 0.0  # Std deviation of cost basis
    cost_basis_vs_spot: float = 0.0  # Cost basis vs current price
    
    # Short squeeze metrics
    squeeze_risk: str = "minimal"
    squeeze_score: float = 0.0  # 0-100
    squeeze_probability: float = 0.0  # 0-1 probability
    
    # Gamma exposure (for combo squeeze detection)
    gex: float = 0.0  # Gamma exposure
    gex_percentile: float = 0.0  # vs historical
    gamma_squeeze_potential: float = 0.0  # Combined score
    
    # Position data
    shortable_shares: float = 0.0
    available_to_borrow: float = 0.0
    borrow_rate: float = 0.0  # Fee to borrow
    utilization: float = 0.0  # % of available borrowed
    
    # Historical
    short_interest_change_pct: float = 0.0  # Change from previous period
    short_interest_change_7d: float = 0.0  # 7-day change
    short_interest_change_30d: float = 0.0  # 30-day change
    
    # Earnings & catalysts
    next_earnings: Optional[datetime] = None
    days_to_earnings: int = 0
    catalyst_score: float = 0.0
    
    # Sentiment
    social_sentiment: float = 0.0  # -1 to 1
    news_sentiment: float = 0.0  # -1 to 1


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
    warnings: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendation: str = "neutral"  # bullish, bearish, neutral
    confidence: float = 0.0
    
    # Technical indicators (multi-timeframe)
    dtc_5d_avg: float = 0.0
    dtc_20d_avg: float = 0.0
    dtc_trend: str = "stable"
    
    # Export data for Grafana
    grafana_tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class SqueezeSignal:
    """Structured squeeze signal"""
    level: str  # info, warning, critical
    category: str  # dtc, borrow_rate, volume, gamma, catalyst
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ShortInterestEngine:
    """Calculate short interest metrics with enhanced analysis"""
    
    def __init__(self):
        self.history: Dict[str, List[ShortInterestData]] = {}
        self.analysis: Dict[str, ShortInterestMetrics] = {}
        self.gex_cache: Dict[str, float] = {}  # Cache GEX data
        self._callbacks: List[Callable[[ShortInterestMetrics], None]] = []
    
    def add_signal_callback(self, callback: Callable[[ShortInterestMetrics], None]):
        """Register callback for new signals"""
        self._callbacks.append(callback)
    
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
        gex: float = 0.0,
        next_earnings: Optional[datetime] = None,
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
        
        # Calculate squeeze probability (0-1)
        squeeze_probability = self._calculate_probability(
            days_to_cover,
            short_interest_pct,
            borrow_rate,
            avg_daily_volume
        )
        
        # Calculate gamma squeeze potential
        gamma_potential = self._calculate_gamma_potential(gex, short_interest, short_interest_pct)
        
        # Calculate catalyst score
        catalyst_score = self._calculate_catalyst_score(next_earnings, spot_price)
        
        # Create data point
        data = ShortInterestData(
            symbol=symbol,
            timestamp=timestamp,
            short_interest=short_interest,
            short_interest_pct=short_interest_pct,
            avg_daily_volume=avg_daily_volume,
            days_to_cover=days_to_cover,
            cost_basis=cost_basis,
            cost_basis_vs_spot=cost_basis / spot_price - 1 if spot_price > 0 else 0,
            borrow_rate=borrow_rate,
            gex=gex,
            gamma_squeeze_potential=gamma_potential,
            shortable_shares=shortable_shares,
            utilization=shortable_shares / (shortable_shares + short_interest) if shortable_shares > 0 else 0,
            squeeze_risk=squeeze_risk,
            squeeze_score=squeeze_score,
            squeeze_probability=squeeze_probability,
            catalyst_score=catalyst_score,
            next_earnings=next_earnings,
            days_to_earnings=(next_earnings - timestamp).days if next_earnings else 0
        )
        
        # Store in history
        if symbol not in self.history:
            self.history[symbol] = []
        self.history[symbol].append(data)
        
        # Trim to last 90 days
        if len(self.history[symbol]) > 90:
            self.history[symbol] = self.history[symbol][-90:]
        
        # Calculate changes from previous periods
        if len(self.history[symbol]) > 1:
            prev = self.history[symbol][-2]
            change = ((data.short_interest - prev.short_interest) / prev.short_interest * 100) if prev.short_interest > 0 else 0
            data.short_interest_change_pct = change
        
        if len(self.history[symbol]) > 7:
            prev_7d = self.history[symbol][-7]
            data.short_interest_change_7d = ((data.short_interest - prev_7d.short_interest) / prev_7d.short_interest * 100) if prev_7d.short_interest > 0 else 0
        
        if len(self.history[symbol]) > 30:
            prev_30d = self.history[symbol][-30]
            data.short_interest_change_30d = ((data.short_interest - prev_30d.short_interest) / prev_30d.short_interest * 100) if prev_30d.short_interest > 0 else 0
        
        # Calculate volume trend
        data.volume_trend = self._calculate_volume_trend(symbol)
        data.volume_spike = self._detect_volume_spike(symbol)
        
        # Determine squeeze signals
        signals = self._generate_signals(data)
        warnings = self._generate_warnings(data)
        
        # Make recommendation
        recommendation, confidence = self._make_recommendation(data, spot_price)
        
        # Multi-timeframe DTC analysis
        dtc_5d_avg, dtc_20d_avg, dtc_trend = self._analyze_dtc_trend(symbol)
        
        metrics = ShortInterestMetrics(
            symbol=symbol,
            timestamp=timestamp,
            spot_price=spot_price,
            current=data,
            history=self.history[symbol],
            squeeze_signals=signals,
            warnings=warnings,
            recommendation=recommendation,
            confidence=confidence,
            dtc_5d_avg=dtc_5d_avg,
            dtc_20d_avg=dtc_20d_avg,
            dtc_trend=dtc_trend,
            grafana_tags={"symbol": symbol, "source": "short_interest"}
        )
        
        self.analysis[symbol] = metrics
        
        # Trigger callbacks
        for callback in self._callbacks:
            try:
                callback(metrics)
            except Exception as e:
                logger.error(f"Signal callback error: {e}")
        
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
        if borrow_rate > 1.0:  # >100%
            score += 30
        elif borrow_rate > 0.5:  # 50-100%
            score += 20
        elif borrow_rate > 0.1:  # 10-50%
            score += 10
        
        return min(100, score)
    
    def _calculate_probability(
        self,
        days_to_cover: float,
        short_interest_pct: float,
        borrow_rate: float,
        volume: float
    ) -> float:
        """Calculate squeeze probability (0-1) using logistic-style model"""
        # Base probability from days to cover
        prob = 0.0
        if days_to_cover > 10:
            prob = 0.85
        elif days_to_cover > 7:
            prob = 0.70
        elif days_to_cover > 5:
            prob = 0.50
        elif days_to_cover > 3:
            prob = 0.30
        elif days_to_cover > 2:
            prob = 0.15
        else:
            prob = 0.05
        
        # Adjust for other factors
        if short_interest_pct > 30:
            prob = min(0.95, prob * 1.2)
        if borrow_rate > 0.5:
            prob = min(0.95, prob * 1.15)
        
        return min(1.0, prob)
    
    def _calculate_gamma_potential(
        self,
        gex: float,
        short_interest: float,
        short_interest_pct: float
    ) -> float:
        """Calculate combined gamma + short squeeze potential (0-100)"""
        if gex == 0:
            return short_interest_pct
        
        # Normalize GEX contribution
        gex_score = min(30, abs(gex) / 1000000)  # Scale to 0-30
        
        # Short interest contribution
        short_score = min(70, short_interest_pct * 2)  # Scale to 0-70
        
        return gex_score + short_score
    
    def _calculate_catalyst_score(
        self,
        next_earnings: Optional[datetime],
        spot_price: float
    ) -> float:
        """Calculate proximity to catalysts (0-100)"""
        if not next_earnings:
            return 0.0
        
        days_until = (next_earnings - datetime.utcnow()).days
        
        # Score increases as we get closer
        if days_until <= 0:
            return 100.0
        elif days_until <= 3:
            return 80.0
        elif days_until <= 7:
            return 60.0
        elif days_until <= 14:
            return 40.0
        elif days_until <= 30:
            return 20.0
        else:
            return 0.0
    
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
    
    def _detect_volume_spike(self, symbol: str) -> bool:
        """Detect unusual volume spike"""
        history = self.history.get(symbol, [])
        if len(history) < 5:
            return False
        
        latest = history[-1]
        avg_volume = sum(h.avg_daily_volume for h in history[-5:-1]) / 4
        return latest.avg_daily_volume > avg_volume * 2
    
    def _analyze_dtc_trend(self, symbol: str) -> Tuple[float, float, str]:
        """Multi-timeframe DTC analysis"""
        history = self.history.get(symbol, [])
        
        if len(history) < 5:
            return 0, 0, "stable"
        
        dtc_5d_avg = sum(h.days_to_cover for h in history[-5:]) / 5
        dtc_20d_avg = sum(h.days_to_cover for h in history[-20:]) / 20 if len(history) >= 20 else dtc_5d_avg
        
        # Determine trend
        if dtc_5d_avg > dtc_20d_avg * 1.2:
            trend = "increasing"
        elif dtc_5d_avg < dtc_20d_avg * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return dtc_5d_avg, dtc_20d_avg, trend
    
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
        
        if data.gamma_squeeze_potential > 50:
            signals.append(f"Gamma squeeze potential: {data.gamma_squeeze_potential:.0f}/100")
        
        if data.days_to_earnings > 0 and data.days_to_earnings <= 7:
            signals.append(f"Earnings in {data.days_to_earnings} days - potential catalyst")
        
        return signals
    
    def _generate_warnings(self, data: ShortInterestData) -> List[str]:
        """Generate risk warnings"""
        warnings = []
        
        if data.volume_spike:
            warnings.append("Volume spike detected - possible short covering starting")
        
        if data.utilization > 0.9:
            warnings.append("Near 100% utilization - low capacity for new shorts")
        
        if data.short_interest_change_7d > 30:
            warnings.append("Rapid 7-day short interest increase")
        
        if data.cost_basis_vs_spot < -0.2:
            warnings.append("Shorts are in significant profit - may cover")
        
        return warnings
    
    def _make_recommendation(
        self, 
        data: ShortInterestData,
        spot_price: float
    ) -> Tuple[str, float]:
        """Make trading recommendation based on short interest"""
        # High squeeze potential = potential for short-covering rally
        if data.squeeze_risk in [SqueezeRisk.HIGH.value, SqueezeRisk.EXTREME.value]:
            if data.cost_basis > spot_price * 1.1:
                return "bullish", data.squeeze_score / 100
            return "neutral", data.squeeze_score / 100
        
        if data.days_to_cover < 2:
            return "neutral", 0.3
        
        return "neutral", 0.5
    
    def get_summary(self, symbol: str) -> Optional[ShortInterestMetrics]:
        """Get latest analysis"""
        return self.analysis.get(symbol)
    
    def get_top_squeeze_candidates(
        self, 
        min_score: float = 30
    ) -> List[Tuple[str, ShortInterestMetrics]]:
        """Get ranked list of squeeze candidates"""
        candidates = []
        for symbol, metrics in self.analysis.items():
            if metrics.current and metrics.current.squeeze_score >= min_score:
                candidates.append((symbol, metrics))
        
        return sorted(
            candidates, 
            key=lambda x: x[1].current.squeeze_score if x[1].current else 0,
            reverse=True
        )


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
        f"squeeze_probability{{symbol=\"{metrics.symbol}\"}}": data.squeeze_probability,
        f"borrow_rate{{symbol=\"{metrics.symbol}\"}}": data.borrow_rate,
        f"gamma_squeeze_potential{{symbol=\"{metrics.symbol}\"}}": data.gamma_squeeze_potential,
        f"catalyst_score{{symbol=\"{metrics.symbol}\"}}": data.catalyst_score,
    }


def export_to_grafana(metrics: ShortInterestMetrics) -> Dict[str, Any]:
    """Export metrics formatted for Grafana"""
    if not metrics.current:
        return {}
    
    data = metrics.current
    return {
        "measurement": "short_interest",
        "tags": {
            "symbol": metrics.symbol,
            "squeeze_risk": data.squeeze_risk
        },
        "fields": {
            "short_interest": data.short_interest,
            "short_interest_pct": data.short_interest_pct,
            "days_to_cover": data.days_to_cover,
            "squeeze_score": data.squeeze_score,
            "borrow_rate": data.borrow_rate
        },
        "timestamp": int(metrics.timestamp.timestamp() * 1000)
    }


# ============================================================================
# WebSocket Broadcast
# ============================================================================

async def broadcast_signals(
    engine: ShortInterestMetrics,
    websocket,
    filter_symbols: List[str] = None
):
    """Broadcast signals via WebSocket"""
    if not websocket:
        return
    
    message = {
        "type": "short_interest_update",
        "data": {
            "symbol": engine.symbol,
            "squeeze_score": engine.current.squeeze_score if engine.current else 0,
            "squeeze_risk": engine.current.squeeze_risk if engine.current else "minimal",
            "days_to_cover": engine.current.days_to_cover if engine.current else 0,
            "signals": engine.squeeze_signals,
            "timestamp": engine.timestamp.isoformat()
        }
    }
    
    if filter_symbols and engine.symbol not in filter_symbols:
        return
    
    try:
        await websocket.send(json.dumps(message))
    except Exception as e:
        logger.error(f"WebSocket broadcast error: {e}")