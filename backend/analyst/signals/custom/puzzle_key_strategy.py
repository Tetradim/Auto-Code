"""Puzzle Key Strategy live signal plugin.

The plugin is intentionally opt-in. Set EDGE_PUZZLE_KEY_ENABLED=true to let
Edge evaluate this session-based strategy during live ticker evaluation.
"""
import os
from typing import Any, Dict, Optional

from analyst.signals.base import BaseSignal, Signal
from backtest.engine import BacktestConfig
from strategies.registry import create_strategy


class PuzzleKeySignal(BaseSignal):
    name = "puzzle_key_strategy"
    version = "1.0.0"
    description = "Opt-in Puzzle Key session reversal and trend-pullback strategy"
    author = "Sentinel Edge"
    tags = ["intraday", "session", "mean-reversion", "trend-pullback", "stocks", "etfs"]
    requires_history_bars = 30

    default_config: Dict[str, Any] = {
        "enabled_env": "EDGE_PUZZLE_KEY_ENABLED",
        "mode_env": "EDGE_PUZZLE_KEY_MODE",
        "default_mode": "combined",
        "default_night_session": "18:00-07:00",
        "default_day_session": "07:00-15:00",
        "default_reversal_lookback": 3,
        "default_atr_period": 14,
        "default_atr_multiplier": 0.75,
        "default_trend_period": 20,
        "default_trade_direction": "both",
        "default_confidence_floor": 0.55,
    }

    async def generate(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Signal]:
        if os.getenv("EDGE_PUZZLE_KEY_ENABLED", "false").lower() not in {"1", "true", "yes", "on"}:
            return None

        ohlcv = market_data.get("ohlcv")
        if ohlcv is None or getattr(ohlcv, "empty", True):
            return None

        strategy = create_strategy(
            "puzzle_key_strategy",
            BacktestConfig(symbols=[symbol]),
            mode=os.getenv("EDGE_PUZZLE_KEY_MODE", self.default_config["default_mode"]),
            night_session=os.getenv("EDGE_PUZZLE_KEY_NIGHT_SESSION", self.default_config["default_night_session"]),
            day_session=os.getenv("EDGE_PUZZLE_KEY_DAY_SESSION", self.default_config["default_day_session"]),
            night_bar_minutes=_env_int("EDGE_PUZZLE_KEY_NIGHT_BAR_MINUTES", 105),
            day_bar_minutes=_env_int("EDGE_PUZZLE_KEY_DAY_BAR_MINUTES", 60),
            reversal_lookback=_env_int(
                "EDGE_PUZZLE_KEY_REVERSAL_LOOKBACK",
                self.default_config["default_reversal_lookback"],
            ),
            atr_period=_env_int("EDGE_PUZZLE_KEY_ATR_PERIOD", self.default_config["default_atr_period"]),
            atr_multiplier=_env_float(
                "EDGE_PUZZLE_KEY_ATR_MULTIPLIER",
                self.default_config["default_atr_multiplier"],
            ),
            trend_period=_env_int("EDGE_PUZZLE_KEY_TREND_PERIOD", self.default_config["default_trend_period"]),
            trade_direction=os.getenv(
                "EDGE_PUZZLE_KEY_TRADE_DIRECTION",
                self.default_config["default_trade_direction"],
            ),
            confidence_floor=_env_float(
                "EDGE_PUZZLE_KEY_CONFIDENCE_FLOOR",
                self.default_config["default_confidence_floor"],
            ),
            no_new_entries_after=os.getenv("EDGE_PUZZLE_KEY_NO_NEW_ENTRIES_AFTER", ""),
        )
        signals = await strategy.generate_signals(symbol, ohlcv)
        if signals.empty:
            return None

        latest = signals.iloc[-1]
        signal_value = int(latest.get("signal", 0))
        if signal_value == 0:
            return None

        price = float(market_data.get("price") or latest.get("close") or 0.0)
        confidence = float(latest.get("confidence", 0.0))
        reason = str(latest.get("reason", "puzzle_key_strategy"))
        metadata = {
            "plugin": self.name,
            "strategy": "puzzle_key_strategy",
            "mode": strategy.mode,
            "night_session": strategy.night_session,
            "day_session": strategy.day_session,
            "atr_multiplier": strategy.atr_multiplier,
            "trend_period": strategy.trend_period,
            "trade_direction": strategy.trade_direction,
        }

        if signal_value > 0:
            return Signal.buy(
                symbol=symbol,
                confidence=confidence,
                reason=reason,
                timeframe=_timeframe_for_reason(reason, strategy),
                price=price,
                atr=float(market_data.get("atr", 0.0) or 0.0),
                metadata=metadata,
            )
        return Signal.sell(
            symbol=symbol,
            confidence=confidence,
            reason=reason,
            timeframe=_timeframe_for_reason(reason, strategy),
            price=price,
            atr=float(market_data.get("atr", 0.0) or 0.0),
            metadata=metadata,
        )


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _timeframe_for_reason(reason: str, strategy) -> str:
    if "_night_" in reason:
        return f"{strategy.night_bar_minutes}m"
    return f"{strategy.day_bar_minutes}m"
