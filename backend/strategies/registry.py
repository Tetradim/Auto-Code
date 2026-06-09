"""
Strategy Registry - Backtest-ready strategies for Edge

This module provides:
- Built-in strategies: SMA, RSI, Breakout (from backtest/engine.py)
- Pattern-enhanced strategies: Use chart patterns as signals
- Strategy factory for easy instantiation

Usage:
    from strategies.registry import StrategyRegistry, create_strategy
    
    # Create by name
    strategy = create_strategy("sma", fast=10, slow=30)
    
    # Create with pattern filter
    strategy = create_strategy("rsi_with_patterns", patterns=["DOUBLE_BOTTOM", "HAMMER"])
"""
import logging
from typing import Dict, List, Optional, Any, Type
from datetime import datetime, time

from backtest.engine import (
    BacktestConfig,
    Strategy as BaseStrategy,
    SimpleMovingAverageStrategy as _SMA,
    RSIStrategy as _RSI,
    BreakoutStrategy as _Breakout
)

logger = logging.getLogger(__name__)


# ============================================================================
# Pattern-Enhanced Strategies
# ============================================================================

class PatternEnhancedStrategy(BaseStrategy):
    """Base class for strategies that incorporate chart patterns.
    
    Patterns can be used as:
    - Signal filters: Only trade when pattern confirms
    - Confidence boost: Increase confidence when pattern detected
    - Trade triggers: Pattern detection as primary signal
    """
    
    def __init__(self, config: BacktestConfig, pattern_mode: str = "filter"):
        super().__init__(config)
        self.pattern_mode = pattern_mode  # "filter", "boost", "trigger"
        self.detected_patterns: Dict[str, List] = {}
    
    async def generate_signals(
        self,
        symbol: str,
        data
    ) -> Any:
        """Override in subclass to include pattern detection"""
        raise NotImplementedError


class PatternAwareRSIStrategy(PatternEnhancedStrategy):
    """RSI strategy enhanced with pattern confirmation.
    
    Modes:
    - filter: Only buy when RSI oversold AND pattern bullish
    - boost: Increase confidence when pattern confirms RSI
    - trigger: Pattern detection triggers trade (RSI as secondary)
    """
    
    def __init__(
        self,
        config: BacktestConfig,
        period: int = 14,
        oversold: int = 30,
        overbought: int = 70,
        pattern_mode: str = "filter",
        enabled_patterns: Optional[List[str]] = None
    ):
        super().__init__(config, pattern_mode)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.enabled_patterns = enabled_patterns or [
            "DOUBLE_BOTTOM", "HEAD_SHOULDERS", "HAMMER", "MORNING_STAR"
        ]
        
        # Create base RSI strategy
        self.rsi_strategy = _RSI(config, period, oversold, overbought)
    
    async def generate_signals(
        self,
        symbol: str,
        data
    ) -> Any:
        """Generate RSI signals enhanced with pattern detection"""
        # Get base RSI signals
        signals = await self.rsi_strategy.generate_signals(symbol, data)
        
        # Detect patterns
        patterns = await self._detect_patterns(symbol, data)
        self.detected_patterns[symbol] = patterns
        
        if patterns and self.pattern_mode != "trigger":
            # Apply pattern enhancement
            for idx in signals.index:
                signal_row = signals.loc[idx]
                base_signal = signal_row.get('signal', 0)
                base_conf = signal_row.get('confidence', 0.5)
                
                # Find bullish patterns
                bullish_patterns = [p for p in patterns if p.get('direction') == 'bullish']
                bearish_patterns = [p for p in patterns if p.get('direction') == 'bearish']
                
                if self.pattern_mode == "filter":
                    # Only allow buy if bullish pattern, sell if bearish
                    if base_signal == 1 and not bullish_patterns:
                        signals.loc[idx, 'signal'] = 0
                    elif base_signal == -1 and not bearish_patterns:
                        signals.loc[idx, 'signal'] = 0
                
                elif self.pattern_mode == "boost":
                    # Boost confidence when pattern confirms
                    if base_signal == 1 and bullish_patterns:
                        avg_conf = sum(p.get('confidence', 0.5) for p in bullish_patterns) / len(bullish_patterns)
                        signals.loc[idx, 'confidence'] = min(1.0, base_conf + avg_conf * 0.3)
                        signals.loc[idx, 'reason'] += f" +pattern_confirm"
                    elif base_signal == -1 and bearish_patterns:
                        avg_conf = sum(p.get('confidence', 0.5) for p in bearish_patterns) / len(bearish_patterns)
                        signals.loc[idx, 'confidence'] = min(1.0, base_conf + avg_conf * 0.3)
        
        return signals
    
    async def _detect_patterns(self, symbol: str, data) -> List[Dict]:
        """Detect patterns in data"""
        patterns = []
        
        try:
            # Import pattern detector
            from signals_enhanced import SignalEngineEnhanced
            
            engine = SignalEngineEnhanced(
                enable_talib=True,
                multi_timeframe=False,
                enabled_patterns=self.enabled_patterns
            )
            
            result = await engine.analyze(symbol, data)
            
            # Convert PatternResult to dict
            for p in result.patterns:
                patterns.append({
                    'type': p.pattern_type.value,
                    'confidence': p.confidence,
                    'direction': p.direction.name.lower(),
                    'strength': p.strength
                })
        
        except Exception as e:
            logger.debug(f"Pattern detection failed for {symbol}: {e}")
        
        return patterns


class PatternAwareSMAStrategy(PatternEnhancedStrategy):
    """SMA strategy enhanced with pattern confirmation"""
    
    def __init__(
        self,
        config: BacktestConfig,
        fast: int = 10,
        slow: int = 30,
        pattern_mode: str = "filter"
    ):
        super().__init__(config, pattern_mode)
        self.fast = fast
        self.slow = slow
        self.sma_strategy = _SMA(config, fast, slow)
    
    async def generate_signals(
        self,
        symbol: str,
        data
    ) -> Any:
        signals = await self.sma_strategy.generate_signals(symbol, data)
        
        # Add pattern detection similar to PatternAwareRSI
        # (can extend similarly)
        
        return signals


class PuzzleKeyStrategy(BaseStrategy):
    """Session-based day trading strategy for configurable stock/ETF symbols.

    This is an original implementation inspired by public descriptions of a
    two-session Euro strategy framework: an overnight reversal component and a
    daytime trend-aligned pullback component. It does not encode proprietary
    Kevin Davey parameters.
    """

    def __init__(
        self,
        config: BacktestConfig,
        mode: str = "combined",
        night_session: str = "18:00-07:00",
        day_session: str = "07:00-15:00",
        night_bar_minutes: int = 105,
        day_bar_minutes: int = 60,
        reversal_lookback: int = 3,
        atr_period: int = 14,
        atr_multiplier: float = 0.75,
        trend_period: int = 20,
        trade_direction: str = "both",
        confidence_floor: float = 0.55,
        no_new_entries_after: str = "",
    ):
        super().__init__(config)
        self.mode = mode if mode in {"night", "day", "combined"} else "combined"
        self.night_session = night_session
        self.day_session = day_session
        self.night_bar_minutes = max(1, int(night_bar_minutes))
        self.day_bar_minutes = max(1, int(day_bar_minutes))
        self.reversal_lookback = max(2, int(reversal_lookback))
        self.atr_period = max(2, int(atr_period))
        self.atr_multiplier = max(0.0, float(atr_multiplier))
        self.trend_period = max(2, int(trend_period))
        self.trade_direction = trade_direction if trade_direction in {"long", "short", "both"} else "both"
        self.confidence_floor = min(1.0, max(0.0, float(confidence_floor)))
        self.no_new_entries_after = no_new_entries_after
        self._night_start, self._night_end = self._parse_session(night_session)
        self._day_start, self._day_end = self._parse_session(day_session)

    async def __call__(self, symbol: str, data) -> Any:
        return await self.generate_signals(symbol, data)

    async def generate_signals(self, symbol: str, data) -> Any:
        df = data.copy()
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("Puzzle Key Strategy requires pandas for signal generation") from exc

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(column).lower() for column in df.columns]
        for required in ["open", "high", "low", "close"]:
            if required not in df.columns:
                raise ValueError(f"Missing '{required}' column in data for {symbol}")
        if "volume" not in df.columns:
            df["volume"] = 0

        df["puzzle_atr"] = self._average_true_range(df)
        df["avg_high"] = df["high"].shift(1).rolling(self.reversal_lookback).mean()
        df["avg_low"] = df["low"].shift(1).rolling(self.reversal_lookback).mean()
        df["trend_anchor"] = df["close"].shift(1)
        df["trend_ma"] = df["close"].shift(1).rolling(self.trend_period).mean()
        df["trend_slope"] = df["close"].shift(1) - df["close"].shift(self.trend_period)
        df["signal"] = 0
        df["confidence"] = 0.0
        df["reason"] = "puzzle_key_waiting"

        for idx in df.index:
            session = self._session_for_index(idx)
            if session is None:
                df.at[idx, "reason"] = "puzzle_key_out_of_session"
                continue
            if self._entries_blocked_after(idx, session):
                df.at[idx, "reason"] = "puzzle_key_entry_cutoff"
                continue

            row = df.loc[idx]
            if self._missing_inputs(row):
                df.at[idx, "reason"] = "puzzle_key_warmup"
                continue

            atr = float(row["puzzle_atr"])
            lower_trigger = float(row["avg_low"]) - atr * self.atr_multiplier
            upper_trigger = float(row["avg_high"]) + atr * self.atr_multiplier

            if session == "night":
                signal, reason, confidence = self._night_signal(row, lower_trigger, upper_trigger, atr)
            else:
                day_lower_trigger = float(row["avg_low"]) + atr * self.atr_multiplier
                day_upper_trigger = float(row["avg_high"]) - atr * self.atr_multiplier
                signal, reason, confidence = self._day_signal(row, day_lower_trigger, day_upper_trigger, atr)

            df.at[idx, "signal"] = signal
            df.at[idx, "confidence"] = confidence
            df.at[idx, "reason"] = reason

        return df[["open", "high", "low", "close", "volume", "signal", "confidence", "reason"]]

    def _night_signal(self, row, lower_trigger: float, upper_trigger: float, atr: float):
        close = float(row["close"])
        if self.trade_direction in {"long", "both"} and close <= lower_trigger:
            return 1, "puzzle_key_night_reversal_buy", self._confidence(close, lower_trigger, atr)
        if self.trade_direction in {"short", "both"} and close >= upper_trigger:
            return -1, "puzzle_key_night_reversal_sell", self._confidence(close, upper_trigger, atr)
        return 0, "puzzle_key_night_no_trigger", 0.0

    def _day_signal(self, row, lower_trigger: float, upper_trigger: float, atr: float):
        close = float(row["close"])
        trend_ma = float(row["trend_ma"])
        trend_anchor = float(row["trend_anchor"])
        trend_slope = float(row["trend_slope"])
        trend_up = trend_anchor >= trend_ma and trend_slope >= 0
        trend_down = trend_anchor <= trend_ma and trend_slope <= 0

        if self.trade_direction in {"long", "both"} and trend_up and close <= lower_trigger:
            return 1, "puzzle_key_day_trend_pullback_buy", self._confidence(close, lower_trigger, atr)
        if self.trade_direction in {"short", "both"} and trend_down and close >= upper_trigger:
            return -1, "puzzle_key_day_trend_pullback_sell", self._confidence(close, upper_trigger, atr)
        return 0, "puzzle_key_day_no_trigger", 0.0

    def _average_true_range(self, df):
        previous_close = df["close"].shift(1)
        true_range = df[["high", "low"]].assign(
            high_close=(df["high"] - previous_close).abs(),
            low_close=(df["low"] - previous_close).abs(),
        )
        true_range["range"] = true_range["high"] - true_range["low"]
        return true_range[["range", "high_close", "low_close"]].max(axis=1).rolling(self.atr_period).mean()

    def _session_for_index(self, idx) -> Optional[str]:
        current = idx.time() if hasattr(idx, "time") else None
        if current is None:
            return None
        if self.mode in {"night", "combined"} and self._in_session(current, self._night_start, self._night_end):
            return "night"
        if self.mode in {"day", "combined"} and self._in_session(current, self._day_start, self._day_end):
            return "day"
        return None

    def _entries_blocked_after(self, idx, session: str) -> bool:
        if session != "night" or not self.no_new_entries_after:
            return False
        cutoff = self._parse_time(self.no_new_entries_after)
        current = idx.time() if hasattr(idx, "time") else None
        return bool(current and current >= cutoff and current < self._night_end)

    def _missing_inputs(self, row) -> bool:
        inputs = [row["puzzle_atr"], row["avg_high"], row["avg_low"]]
        if self._session_for_index(row.name) == "day":
            inputs.extend([row["trend_anchor"], row["trend_ma"], row["trend_slope"]])
        return any(value != value for value in inputs)

    def _confidence(self, close: float, trigger: float, atr: float) -> float:
        if atr <= 0:
            return self.confidence_floor
        distance = abs(close - trigger) / atr
        return min(1.0, max(self.confidence_floor, self.confidence_floor + distance * 0.25))

    @staticmethod
    def _parse_session(value: str):
        start, end = value.split("-", 1)
        return PuzzleKeyStrategy._parse_time(start), PuzzleKeyStrategy._parse_time(end)

    @staticmethod
    def _parse_time(value: str) -> time:
        hour, minute = value.strip().split(":", 1)
        return time(hour=int(hour), minute=int(minute))

    @staticmethod
    def _in_session(current: time, start: time, end: time) -> bool:
        if start <= end:
            return start <= current < end
        return current >= start or current < end


# ============================================================================
# Strategy Factory
# ============================================================================

_STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "sma": _SMA,
    "rsi": _RSI,
    "breakout": _Breakout,
    "rsi_with_patterns": PatternAwareRSIStrategy,
    "sma_with_patterns": PatternAwareSMAStrategy,
    "puzzle_key_strategy": PuzzleKeyStrategy,
}


class StrategyRegistry:
    """Registry for all available strategies"""
    
    _strategies = {
        "sma": {
            "class": _SMA,
            "params": {
                "fast": (int, "Fast SMA period", 10),
                "slow": (int, "Slow SMA period", 30)
            },
            "description": "Simple Moving Average crossover"
        },
        "rsi": {
            "class": _RSI,
            "params": {
                "period": (int, "RSI period", 14),
                "oversold": (int, "Oversold threshold", 30),
                "overbought": (int, "Overbought threshold", 70)
            },
            "description": "RSI overbought/oversold strategy"
        },
        "breakout": {
            "class": _Breakout,
            "params": {
                "lookback": (int, "Channel lookback period", 20)
            },
            "description": "Channel breakout strategy"
        },
        "rsi_with_patterns": {
            "class": PatternAwareRSIStrategy,
            "params": {
                "period": (int, "RSI period", 14),
                "oversold": (int, "Oversold threshold", 30),
                "overbought": (int, "Overbought threshold", 70),
                "pattern_mode": (str, "filter|boost|trigger", "filter")
            },
            "description": "RSI with chart pattern confirmation"
        },
        "sma_with_patterns": {
            "class": PatternAwareSMAStrategy,
            "params": {
                "fast": (int, "Fast SMA period", 10),
                "slow": (int, "Slow SMA period", 30),
                "pattern_mode": (str, "filter|boost|trigger", "filter")
            },
            "description": "SMA with chart pattern confirmation"
        },
        "puzzle_key_strategy": {
            "class": PuzzleKeyStrategy,
            "params": {
                "mode": (str, "night|day|combined session mode", "combined"),
                "night_session": (str, "Night session window in ET, HH:MM-HH:MM", "18:00-07:00"),
                "day_session": (str, "Day session window in ET, HH:MM-HH:MM", "07:00-15:00"),
                "night_bar_minutes": (int, "Night strategy bar length in minutes", 105),
                "day_bar_minutes": (int, "Day strategy bar length in minutes", 60),
                "reversal_lookback": (int, "Previous bars used for average high/low triggers", 3),
                "atr_period": (int, "ATR lookback period", 14),
                "atr_multiplier": (float, "ATR multiplier applied to reversal/pullback triggers", 0.75),
                "trend_period": (int, "Trend moving-average period for day-session filter", 20),
                "trade_direction": (str, "long|short|both", "both"),
                "confidence_floor": (float, "Minimum confidence assigned to valid triggers", 0.55),
                "no_new_entries_after": (str, "Optional night entry cutoff in HH:MM ET", "")
            },
            "description": "Puzzle Key Strategy: customizable session reversal and trend-pullback day trading package"
        }
    }
    
    @classmethod
    def list_strategies(cls) -> Dict:
        """List all available strategies"""
        return {
            name: {
                "description": info["description"],
                "params": {k: v[1] for k, v in info["params"].items()}
            }
            for name, info in cls._strategies.items()
        }
    
    @classmethod
    def get_strategy_info(cls, name: str) -> Optional[Dict]:
        """Get info about a specific strategy"""
        return cls._strategies.get(name)
    
    @classmethod
    def create(
        cls,
        name: str,
        config: Optional[BacktestConfig] = None,
        **kwargs
    ) -> BaseStrategy:
        """Create a strategy instance by name"""
        if config is None:
            config = BacktestConfig()
        
        strategy_info = cls._strategies.get(name)
        if not strategy_info:
            raise ValueError(f"Unknown strategy: {name}. Available: {list(cls._strategies.keys())}")
        
        strategy_class = strategy_info["class"]
        
        # Filter kwargs to only include valid params
        valid_params = strategy_info["params"].keys()
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
        
        return strategy_class(config, **filtered_kwargs)


def create_strategy(
    name: str,
    config: Optional[BacktestConfig] = None,
    **kwargs
) -> BaseStrategy:
    """Convenience function to create strategy"""
    return StrategyRegistry.create(name, config, **kwargs)


# ============================================================================
# Strategy Parameter Grids for Optimization
# ============================================================================

PARAM_GRIDS = {
    "sma": {
        "fast": [5, 10, 15, 20],
        "slow": [20, 30, 50, 70]
    },
    "rsi": {
        "period": [7, 14, 21],
        "oversold": [20, 25, 30, 35],
        "overbought": [65, 70, 75, 80]
    },
    "breakout": {
        "lookback": [10, 15, 20, 30, 50]
    },
    "rsi_with_patterns": {
        "period": [7, 14, 21],
        "oversold": [20, 25, 30],
        "overbought": [70, 75, 80],
        "pattern_mode": ["filter", "boost"]
    }
}


def get_param_grid(strategy_name: str) -> Dict[str, List]:
    """Get parameter grid for optimization"""
    return PARAM_GRIDS.get(strategy_name, {})


# ============================================================================
# Observation Replay for Backtesting
# ============================================================================

class ObservationReplay:
    """Replay historical observations in backtests to simulate Pulse feedback.
    
    This simulates the Edge ↔ Pulse feedback loop during backtesting:
    - Broker patterns (fills, rejections) feed back to Edge
    - Position updates affect decision making
    - Realistic execution simulation
    """
    
    def __init__(self):
        self.observations: List[Dict] = []
        self.position_history: Dict[str, List[Dict]] = {}
    
    def load_observations(self, observations: List[Dict]):
        """Load historical observations"""
        self.observations = sorted(
            observations,
            key=lambda x: x.get('timestamp', '')
        )
    
    def add_replay_fill(
        self,
        symbol: str,
        timestamp: datetime,
        side: str,
        price: float,
        quantity: float
    ):
        """Add a synthetic order fill observation"""
        self.observations.append({
            "type": "observation",
            "subtype": "execution",
            "observation_type": "ORDER_FILLED",
            "symbol": symbol,
            "timestamp": timestamp.isoformat(),
            "side": side,
            "fill_price": price,
            "quantity": quantity,
            "source": "backtest_simulator"
        })
    
    def get_observations_before(self, timestamp: datetime) -> List[Dict]:
        """Get all observations before a given timestamp"""
        ts_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
        return [o for o in self.observations if o.get('timestamp', '') <= ts_str]
    
    def simulate_pnl_update(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[float]:
        """Calculate unrealized PnL based on position history"""
        positions = self.position_history.get(symbol, [])
        if not positions:
            return None
        
        # Get most recent position
        entry = positions[-1].get('entry_price', 0)
        if entry > 0:
            return (current_price - entry) / entry * 100
        
        return None


# ============================================================================
# Backtest with Observation Replay
# ============================================================================

class BacktestWithObservations:
    """Backtest engine that replays observations to simulate Edge ↔ Pulse loop"""
    
    def __init__(
        self,
        config: BacktestConfig,
        strategy: BaseStrategy,
        observation_replay: Optional[ObservationReplay] = None
    ):
        from backtest.engine import BacktestEngine as _BE
        
        self._engine = _BE(config, strategy)
        self.observation_replay = observation_replay or ObservationReplay()
        self.config = config
    
    async def run(self):
        """Run backtest with observation replay"""
        # Run base backtest
        metrics = await self._engine.run()
        
        # Enhance metrics with observation stats
        metrics.observation_count = len(self.observation_replay.observations)
        
        return metrics
    
    def get_replay_stats(self) -> Dict:
        """Get observation replay statistics"""
        return {
            "total_observations": len(self.observation_replay.observations),
            "symbols_tracked": list(self.observation_replay.position_history.keys()),
            "fills_simulated": sum(
                1 for o in self.observation_replay.observations
                if o.get('observation_type') == 'ORDER_FILLED'
            )
        }
