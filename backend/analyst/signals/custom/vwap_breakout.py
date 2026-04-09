"""
VWAP Breakout Signal Plugin — analyst/signals/custom/vwap_breakout.py

Drop-in BaseSignal that detects when price crosses above/below VWAP with
volume confirmation.  Registered automatically by discover_plugins().

VWAP (Volume-Weighted Average Price)
──────────────────────────────────────
  typical_price = (High + Low + Close) / 3
  VWAP = Σ(typical_price × volume) / Σ(volume)   [cumulative from day open]

Signal logic
────────────
  BUY  : price > VWAP + buffer AND volume_ratio >= min_volume_ratio
  SELL : price < VWAP - buffer AND volume_ratio >= min_volume_ratio

Confidence scales with how far price is from VWAP and volume ratio.
"""
import logging
from typing import Any, Dict, Optional

from analyst.signals.base import BaseSignal, Signal

logger = logging.getLogger(__name__)


class VWAPBreakout(BaseSignal):
    name = "vwap_breakout"
    version = "1.0.0"
    description = "VWAP cross with volume confirmation"
    author = "Sentinel Edge"
    tags = ["vwap", "intraday", "momentum", "volume"]
    requires_history_bars = 20

    default_config: Dict[str, Any] = {
        # Percentage buffer above/below VWAP required before signalling
        "vwap_buffer_pct": 0.003,       # 0.3 %
        # Minimum volume ratio vs average to confirm the breakout
        "min_volume_ratio": 1.25,
        # Min ATR as a % of price — avoids signalling in flat/choppy markets
        "min_atr_pct": 0.004,           # 0.4 %
        # Base confidence (0-1); scales up with volume ratio
        "confidence_base": 0.65,
        # Volume z-score threshold that boosts confidence further
        "zscore_boost_threshold": 2.0,
    }

    async def generate(
        self,
        symbol: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        """
        Return a Signal or None.

        Expected market_data keys
        ─────────────────────────
          ohlcv         : pandas DataFrame with columns High/Low/Close/Volume
          price         : float — latest price
          volume_ratio  : float — current volume ÷ EMA average
          atr           : float — current ATR
          volume_zscore : float — volume anomaly score
        """
        ohlcv = market_data.get("ohlcv")
        price = float(market_data.get("price", 0.0))
        volume_ratio = float(market_data.get("volume_ratio", 1.0))
        atr = float(market_data.get("atr", 0.0))
        volume_zscore = float(market_data.get("volume_zscore", 0.0))

        # ── Guard conditions ──────────────────────────────────────────────
        if ohlcv is None or ohlcv.empty or price == 0:
            return None

        # Require meaningful volatility — skip flat markets
        if atr > 0 and price > 0:
            atr_pct = atr / price
            if atr_pct < self.default_config["min_atr_pct"]:
                logger.debug("%s: VWAP skip — ATR %.4f%% below min", symbol, atr_pct * 100)
                return None

        # Require sufficient volume
        if volume_ratio < self.default_config["min_volume_ratio"]:
            return None

        # ── Compute VWAP ──────────────────────────────────────────────────
        vwap = self._compute_vwap(ohlcv)
        if vwap <= 0:
            return None

        buffer = vwap * self.default_config["vwap_buffer_pct"]

        # ── Confidence scaling ────────────────────────────────────────────
        base_conf = self.default_config["confidence_base"]
        # Each 0.1x above min_volume_ratio adds 2 % confidence
        vol_boost = (volume_ratio - self.default_config["min_volume_ratio"]) * 0.02
        # Z-score above threshold adds a further 5 % boost
        z_boost = 0.05 if volume_zscore >= self.default_config["zscore_boost_threshold"] else 0.0
        confidence = round(min(0.95, base_conf + vol_boost + z_boost), 3)

        deviation_pct = abs(price - vwap) / vwap * 100

        # ── Signal decision ───────────────────────────────────────────────
        if price > vwap + buffer:
            logger.info(
                "📈 VWAP BUY  %s  price=%.2f  vwap=%.2f  dev=+%.2f%%  vol=%.1fx  z=%.2f",
                symbol, price, vwap, deviation_pct, volume_ratio, volume_zscore,
            )
            return Signal.buy(
                symbol=symbol,
                confidence=confidence,
                reason=(
                    f"Price ${price:.2f} is {deviation_pct:.2f}% above VWAP ${vwap:.2f} "
                    f"with {volume_ratio:.1f}x volume"
                ),
                timeframe="5m",
                price=price,
                atr=atr,
                metadata={
                    "vwap": round(vwap, 4),
                    "deviation_pct": round(deviation_pct, 3),
                    "volume_ratio": round(volume_ratio, 3),
                    "volume_zscore": round(volume_zscore, 3),
                    "plugin": self.name,
                },
            )

        if price < vwap - buffer:
            logger.info(
                "📉 VWAP SELL %s  price=%.2f  vwap=%.2f  dev=-%.2f%%  vol=%.1fx  z=%.2f",
                symbol, price, vwap, deviation_pct, volume_ratio, volume_zscore,
            )
            return Signal.sell(
                symbol=symbol,
                confidence=confidence,
                reason=(
                    f"Price ${price:.2f} is {deviation_pct:.2f}% below VWAP ${vwap:.2f} "
                    f"with {volume_ratio:.1f}x volume"
                ),
                timeframe="5m",
                price=price,
                atr=atr,
                metadata={
                    "vwap": round(vwap, 4),
                    "deviation_pct": round(deviation_pct, 3),
                    "volume_ratio": round(volume_ratio, 3),
                    "volume_zscore": round(volume_zscore, 3),
                    "plugin": self.name,
                },
            )

        return None

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _compute_vwap(df) -> float:
        """
        VWAP = Σ(typical_price × volume) / Σ(volume)
        typical_price = (High + Low + Close) / 3
        """
        try:
            typical = (df["High"] + df["Low"] + df["Close"]) / 3
            cumulative_tp_vol = (typical * df["Volume"]).cumsum()
            cumulative_vol = df["Volume"].cumsum()
            vwap_series = cumulative_tp_vol / cumulative_vol
            val = float(vwap_series.iloc[-1])
            return val if val > 0 else 0.0
        except Exception as exc:
            logger.debug("VWAP computation error: %s", exc)
            return 0.0
