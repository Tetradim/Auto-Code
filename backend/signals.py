"""Signal Analysis Engine - Bullish/Bearish Pattern Detection"""
import logging
from typing import Tuple, Dict, Optional
from enum import Enum
from metrics import edge_signal_strength, edge_trend_direction, edge_volume_ratio

logger = logging.getLogger(__name__)

class TrendDirection(Enum):
    BULLISH = 1
    NEUTRAL = 0
    BEARISH = -1

class SignalEngine:
    """Analyze market signals for bullish/bearish patterns"""
    
    def __init__(self):
        # Store average volume: {symbol: avg_volume}
        self.avg_volume: Dict[str, float] = {}
        logger.info("Signal Engine initialized")
    
    def update_avg_volume(self, symbol: str, volume: float):
        """Update average volume for symbol"""
        if symbol not in self.avg_volume:
            self.avg_volume[symbol] = volume
        else:
            # Exponential moving average
            self.avg_volume[symbol] = (self.avg_volume[symbol] * 0.9) + (volume * 0.1)
    
    def get_volume_ratio(self, symbol: str, current_volume: float) -> float:
        """Calculate volume ratio vs average"""
        if symbol not in self.avg_volume or self.avg_volume[symbol] == 0:
            return 1.0
        
        ratio = current_volume / self.avg_volume[symbol]
        edge_volume_ratio.labels(symbol=symbol).set(ratio)
        return ratio
    
    def evaluate_signal(
        self,
        symbol: str,
        price: float,
        orb_high: Optional[float] = None,
        orb_low: Optional[float] = None,
        volume_ratio: float = 1.0,
        atr: float = 0.0,
        price_change_pct: float = 0.0
    ) -> Tuple[TrendDirection, float]:
        """
        Evaluate trading signal strength
        
        Returns:
            (TrendDirection, signal_strength)
            signal_strength: -10 (strong bearish) to +10 (strong bullish)
        """
        
        score = 0.0
        
        # ═══════════════════════════════════════════════════════════
        # 1. ORB Breakout Analysis (±3 points)
        # ═══════════════════════════════════════════════════════════
        if orb_high is not None and orb_low is not None:
            if price > orb_high:
                score += 3.0
                logger.debug(f"{symbol}: Above ORB high (+3.0)")
            elif price < orb_low:
                score -= 3.0
                logger.debug(f"{symbol}: Below ORB low (-3.0)")
        
        # ═══════════════════════════════════════════════════════════
        # 2. Volume Confirmation (±2 points)
        # ═══════════════════════════════════════════════════════════
        if volume_ratio > 1.5:
            # High volume amplifies the signal
            volume_boost = min(2.0, (volume_ratio - 1.0) * 1.5)
            if score > 0:
                score += volume_boost
            elif score < 0:
                score -= volume_boost
            logger.debug(f"{symbol}: High volume ratio {volume_ratio:.2f} (±{volume_boost:.2f})")
        elif volume_ratio < 0.5:
            # Low volume weakens the signal
            score *= 0.5
            logger.debug(f"{symbol}: Low volume ratio {volume_ratio:.2f} (dampened)")
        
        # ═════════════════════════════════════════════════════════════
        # 3. Price Momentum (±2 points)
        # ═══════════════════════════════════════════════════════════
        if price_change_pct > 2.0:
            score += 2.0
            logger.debug(f"{symbol}: Strong upward momentum +{price_change_pct:.2f}% (+2.0)")
        elif price_change_pct < -2.0:
            score -= 2.0
            logger.debug(f"{symbol}: Strong downward momentum {price_change_pct:.2f}% (-2.0)")
        elif price_change_pct > 1.0:
            score += 1.0
        elif price_change_pct < -1.0:
            score -= 1.0
        
        # ═══════════════════════════════════════════════════════════
        # 4. Volatility Adjustment (±1 point)
        # ═══════════════════════════════════════════════════════════
        if atr > 0 and price > 0:
            volatility_pct = (atr / price) * 100
            if volatility_pct > 4.0:
                # Very high volatility - caution
                score *= 0.7
                logger.debug(f"{symbol}: High volatility {volatility_pct:.2f}% (dampened)")
            elif volatility_pct < 1.0:
                # Low volatility - safer
                if abs(score) > 2:
                    score *= 1.2
                    logger.debug(f"{symbol}: Low volatility {volatility_pct:.2f}% (boosted)")
        
        # Clamp score to [-10, 10]
        score = max(-10.0, min(10.0, score))
        
        # Determine trend direction
        if score >= 2.0:
            direction = TrendDirection.BULLISH
        elif score <= -2.0:
            direction = TrendDirection.BEARISH
        else:
            direction = TrendDirection.NEUTRAL
        
        # Update metrics
        edge_signal_strength.labels(symbol=symbol).set(score)
        edge_trend_direction.labels(symbol=symbol).set(direction.value)
        
        logger.info(
            f"📊 {symbol} Signal: {direction.name} (strength: {score:.2f}) "
            f"[ORB: {orb_high is not None}, Vol: {volume_ratio:.2f}x, Mom: {price_change_pct:+.2f}%]"
        )
        
        return direction, score
    
    def should_increase_position(self, signal_strength: float, current_positions: int = 0) -> bool:
        """Determine if we should increase position size"""
        # Strong bullish signal and not too many positions
        return signal_strength >= 5.0 and current_positions < 3
    
    def should_tighten_stops(self, signal_strength: float) -> bool:
        """Determine if we should tighten stop losses"""
        # Weakening signal
        return -2.0 <= signal_strength <= 2.0
