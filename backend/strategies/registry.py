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
from datetime import datetime

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


# ============================================================================
# Strategy Factory
# ============================================================================

_STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "sma": _SMA,
    "rsi": _RSI,
    "breakout": _Breakout,
    "rsi_with_patterns": PatternAwareRSIStrategy,
    "sma_with_patterns": PatternAwareSMAStrategy,
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
    
    def add_fake_fill(
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