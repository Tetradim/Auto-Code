"""Signal Analysis Engine — Bullish/Bearish Pattern Detection + Volume Z-Score"""
import logging
import math
from collections import deque
from typing import Dict, Optional, Tuple
from enum import Enum

from metrics import (
    edge_signal_strength,
    edge_trend_direction,
    edge_volume_ratio,
    edge_volume_zscore,
)

logger = logging.getLogger(__name__)

# History window for z-score (number of evaluations = seconds at 1s interval)
_ZSCORE_WINDOW = 60          # 60-second rolling window
_ZSCORE_MIN_SAMPLES = 15     # minimum samples before z-score is meaningful
_ANOMALY_THRESHOLD = 2.5     # z-score above which volume is anomalous
_EXTREME_THRESHOLD = 3.5     # z-score above which volume is extreme


class TrendDirection(Enum):
    BULLISH = 1
    NEUTRAL = 0
    BEARISH = -1


class SignalEngine:
    """
    Analyse market signals for bullish/bearish patterns.

    Scoring layers (total ±10)
    ──────────────────────────
    1. ORB breakout analysis   ±3 pts
    2. Volume confirmation      ±2 pts
    3. Price momentum           ±2 pts
    4. Volatility adjustment    ±1 pt
    5. Volume anomaly Z-score   ±2 pts  ← NEW
    """

    def __init__(self):
        # EMA of average volume per symbol
        self.avg_volume: Dict[str, float] = {}
        # Rolling history for z-score computation
        self.volume_history: Dict[str, deque] = {}
        logger.info("Signal Engine initialized")

    # ── Volume tracking ──────────────────────────────────────────────────────

    def update_avg_volume(self, symbol: str, volume: float) -> None:
        """Update EMA average and rolling history for z-score."""
        if symbol not in self.avg_volume:
            self.avg_volume[symbol] = volume
        else:
            self.avg_volume[symbol] = self.avg_volume[symbol] * 0.9 + volume * 0.1

        if symbol not in self.volume_history:
            self.volume_history[symbol] = deque(maxlen=_ZSCORE_WINDOW)
        self.volume_history[symbol].append(volume)

    def get_volume_ratio(self, symbol: str, current_volume: float) -> float:
        """Current volume ÷ EMA average."""
        if symbol not in self.avg_volume or self.avg_volume[symbol] == 0:
            return 1.0
        ratio = current_volume / self.avg_volume[symbol]
        edge_volume_ratio.labels(symbol=symbol).set(ratio)
        return ratio

    def compute_volume_zscore(self, symbol: str, current_volume: float) -> float:
        """
        Z-score = (current_volume − rolling_mean) / rolling_std

        Returns 0.0 until at least _ZSCORE_MIN_SAMPLES readings are available.
        A high positive z-score means unusually heavy volume.
        A negative z-score means unusually light volume.
        """
        history = self.volume_history.get(symbol)
        if not history or len(history) < _ZSCORE_MIN_SAMPLES:
            return 0.0

        values = list(history)
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)

        if std < 1.0:   # avoid division by near-zero for low-volume assets
            return 0.0

        zscore = (current_volume - mean) / std

        try:
            edge_volume_zscore.labels(symbol=symbol).set(zscore)
        except Exception:
            pass

        return zscore

    # ── Signal evaluation ────────────────────────────────────────────────────

    def evaluate_signal(
        self,
        symbol: str,
        price: float,
        orb_high: Optional[float] = None,
        orb_low: Optional[float] = None,
        volume_ratio: float = 1.0,
        atr: float = 0.0,
        price_change_pct: float = 0.0,
        volume_zscore: float = 0.0,
    ) -> Tuple[TrendDirection, float]:
        """
        Evaluate trading signal strength.

        Returns
        ───────
        (TrendDirection, signal_strength)
        signal_strength: -10 (strong bearish) → +10 (strong bullish)
        """
        score = 0.0

        # ── 1. ORB Breakout Analysis (±3 pts) ──────────────────────────────
        if orb_high is not None and orb_low is not None:
            if price > orb_high:
                score += 3.0
                logger.debug("%s: Above ORB high (+3.0)", symbol)
            elif price < orb_low:
                score -= 3.0
                logger.debug("%s: Below ORB low (-3.0)", symbol)

        # ── 2. Volume Confirmation (±2 pts) ────────────────────────────────
        if volume_ratio > 1.5:
            boost = min(2.0, (volume_ratio - 1.0) * 1.5)
            score += boost if score > 0 else -boost
            logger.debug("%s: High volume ratio %.2fx (±%.2f)", symbol, volume_ratio, boost)
        elif volume_ratio < 0.5:
            score *= 0.5
            logger.debug("%s: Low volume ratio %.2fx (dampened)", symbol, volume_ratio)

        # ── 3. Price Momentum (±2 pts) ──────────────────────────────────────
        if price_change_pct > 2.0:
            score += 2.0
        elif price_change_pct < -2.0:
            score -= 2.0
        elif price_change_pct > 1.0:
            score += 1.0
        elif price_change_pct < -1.0:
            score -= 1.0

        # ── 4. Volatility Adjustment (±1 pt) ───────────────────────────────
        if atr > 0 and price > 0:
            vol_pct = (atr / price) * 100
            if vol_pct > 4.0:
                score *= 0.7
                logger.debug("%s: High volatility %.2f%% (dampened)", symbol, vol_pct)
            elif vol_pct < 1.0 and abs(score) > 2:
                score *= 1.2
                logger.debug("%s: Low volatility %.2f%% (boosted)", symbol, vol_pct)

        # ── 5. Volume Anomaly Z-Score (±2 pts) ─────────────────────────────
        if volume_zscore != 0.0:
            if volume_zscore >= _EXTREME_THRESHOLD:
                # Extreme volume spike — strongly amplifies direction
                boost = min(2.0, volume_zscore * 0.5)
                score += boost if score >= 0 else -boost
                logger.info(
                    "%s: EXTREME volume anomaly z=%.2f → signal %+.1f",
                    symbol, volume_zscore, boost if score >= 0 else -boost,
                )
            elif volume_zscore >= _ANOMALY_THRESHOLD:
                # Significant volume spike — moderately amplifies direction
                boost = min(1.5, volume_zscore * 0.4)
                score += boost if score >= 0 else -boost
                logger.debug("%s: Volume anomaly z=%.2f (±%.2f)", symbol, volume_zscore, boost)
            elif volume_zscore <= -1.5:
                # Abnormally low volume — reduce conviction
                score *= 0.75
                logger.debug("%s: Low-volume anomaly z=%.2f (dampened)", symbol, volume_zscore)

        # Clamp to [-10, 10]
        score = max(-10.0, min(10.0, score))

        # Determine direction
        if score >= 2.0:
            direction = TrendDirection.BULLISH
        elif score <= -2.0:
            direction = TrendDirection.BEARISH
        else:
            direction = TrendDirection.NEUTRAL

        edge_signal_strength.labels(symbol=symbol).set(score)
        edge_trend_direction.labels(symbol=symbol).set(direction.value)

        logger.info(
            "📊 %s Signal: %s (strength: %.2f) "
            "[ORB: %s, Vol: %.2fx, z=%.2f, Mom: %+.2f%%]",
            symbol, direction.name, score,
            orb_high is not None, volume_ratio, volume_zscore, price_change_pct,
        )

        return direction, score

    # ── Position helpers ─────────────────────────────────────────────────────

    def should_increase_position(self, signal_strength: float, current_positions: int = 0) -> bool:
        return signal_strength >= 5.0 and current_positions < 3

    def should_tighten_stops(self, signal_strength: float) -> bool:
        return -2.0 <= signal_strength <= 2.0
