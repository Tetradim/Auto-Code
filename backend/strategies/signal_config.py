"""
Signal Engine Customization Module

Customizable signal layers with per-ticker overrides:
- ORB breakout proximity
- ATR momentum
- Volume Z-score
- Trend alignment
- Mean reversion

Each layer can be:
- Enabled/disabled per ticker
- Weighted differently per ticker
- Given custom thresholds per ticker
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SignalLayer(Enum):
    """Available signal layers"""
    ORB = "orb"  # Opening Range Breakout
    MOMENTUM = "momentum"  # ATR-normalized momentum
    VOLUME = "volume"  # Volume Z-score
    TREND = "trend"  # Trend alignment
    MEAN_REV = "mean_reversion"  # Mean reversion


@dataclass
class LayerConfig:
    """Configuration for a single signal layer"""
    enabled: bool = True
    weight: float = 1.0  # Layer weight in final composite (0-2)
    threshold_buy: float = 1.0  # Threshold to contribute +signal
    threshold_sell: float = -1.0  # Threshold to contribute -signal
    min_confidence: float = 0.5  # Minimum confidence to include in composite


@dataclass
class SignalEngineConfig:
    """Complete signal engine configuration"""
    # Layer configs
    orb: LayerConfig = field(default_factory=LayerConfig)
    momentum: LayerConfig = field(default_factory=LayerConfig)
    volume: LayerConfig = field(default_factory=LayerConfig)
    trend: LayerConfig = field(default_factory=LayerConfig)
    mean_rev: LayerConfig = field(default_factory=LayerConfig)
    
    # Global settings
    composite_threshold_buy: float = 5.0  # Total score for BUY signal
    composite_threshold_sell: float = -5.0  # Total score for SELL signal
    min_layers_active: int = 2  # Minimum layers must agree
    
    # Time filters
    trading_hours_only: bool = True
    start_hour: int = 9  # 9:30 AM ET
    end_hour: int = 16  # 4:00 PM ET
    
    # Day filters
    avoid_mondays: bool = False
    avoid_fridays: bool = False
    
    # Volatility filters
    min_volume: float = 100000  # Minimum avg volume
    max_volatility_percentile: float = 95  # Skip if IV > 95th percentile
    
    # Earnings filters
    earnings_avoid_days: int = 0  # Days before/after earnings to avoid (0 = disabled)


class SignalEngineCustomizer:
    """Customize signal engine per-ticker"""
    
    def __init__(self):
        self.per_ticker: Dict[str, SignalEngineConfig] = {}
        self.presets: Dict[str, SignalEngineConfig] = {}
        self._init_presets()
    
    def _init_presets(self):
        """Initialize default presets"""
        # Aggressive - high weights on momentum and volume
        self.presets["aggressive"] = SignalEngineConfig(
            momentum=LayerConfig(weight=1.5),
            volume=LayerConfig(weight=1.5),
            composite_threshold_buy=3.0,
            min_layers_active=1,
        )
        
        # Conservative - require more agreement
        self.presets["conservative"] = SignalEngineConfig(
            momentum=LayerConfig(weight=0.8),
            volume=LayerConfig(weight=0.8),
            trend=LayerConfig(weight=1.2),
            composite_threshold_buy=7.0,
            min_layers_active=3,
        )
        
        # Earnings - avoid holding through earnings
        self.presets["earnings-safe"] = SignalEngineConfig(
            earnings_avoid_days=3,
            max_volatility_percentile=80,
        )
        
        # Opening range focus
        self.presets["orb-focused"] = SignalEngineConfig(
            orb=LayerConfig(weight=1.5, threshold_buy=0.5),
            momentum=LayerConfig(weight=0.5),
            composite_threshold_buy=4.0,
        )
    
    def get_config(self, symbol: str) -> SignalEngineConfig:
        """Get config for symbol (or default)"""
        return self.per_ticker.get(symbol, SignalEngineConfig())
    
    def set_config(self, symbol: str, config: SignalEngineConfig):
        """Set custom config for symbol"""
        self.per_ticker[symbol] = config
    
    def apply_preset(self, symbol: str, preset_name: str):
        """Apply a preset to a symbol"""
        if preset_name not in self.presets:
            logger.warning(f"Unknown preset: {preset_name}")
            return
        
        preset = self.presets[preset_name]
        # Merge with defaults
        config = self._merge_config(SignalEngineConfig(), preset)
        self.per_ticker[symbol] = config
    
    def _merge_config(
        self, 
        base: SignalEngineConfig, 
        override: SignalEngineConfig
    ) -> SignalEngineConfig:
        """Merge override into base config"""
        # Simple merge - override non-default values
        result = SignalEngineConfig()
        
        for field_name in ["orb", "momentum", "volume", "trend", "mean_rev"]:
            base_layer = getattr(base, field_name)
            override_layer = getattr(override, field_name)
            
            if override_layer.weight != 1.0:
                base_layer.weight = override_layer.weight
            if override_layer.threshold_buy != 1.0:
                base_layer.threshold_buy = override_layer.threshold_buy
            if override_layer.threshold_sell != -1.0:
                base_layer.threshold_sell = override_layer.threshold_sell
                
            setattr(result, field_name, base_layer)
        
        if override.composite_threshold_buy != 5.0:
            result.composite_threshold_buy = override.composite_threshold_buy
        if override.composite_threshold_sell != -5.0:
            result.composite_threshold_sell = override.composite_threshold_sell
        if override.min_layers_active != 2:
            result.min_layers_active = override.min_layers_active
        if override.earnings_avoid_days != 0:
            result.earnings_avoid_days = override.earnings_avoid_days
            
        return result
    
    def calculate_composite(
        self,
        symbol: str,
        layer_scores: Dict[str, float]
    ) -> float:
        """Calculate weighted composite score"""
        config = self.get_config(symbol)
        
        total_weight = 0.0
        total_score = 0.0
        active_count = 0
        
        layer_map = {
            "orb": config.orb,
            "momentum": config.momentum,
            "volume": config.volume,
            "trend": config.trend,
            "mean_rev": config.mean_rev,
        }
        
        for layer_name, score in layer_scores.items():
            if layer_name in layer_map:
                layer = layer_map[layer_name]
                if layer.enabled:
                    total_score += score * layer.weight
                    total_weight += layer.weight
                    active_count += 1
        
        # Require minimum layers
        if active_count < config.min_layers_active:
            return 0.0
        
        # Normalize by total weight
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def list_presets(self) -> List[str]:
        """List available preset names"""
        return list(self.presets.keys())
    
    def create_custom_preset(
        self,
        name: str,
        config: SignalEngineConfig
    ):
        """Create a custom preset"""
        self.presets[name] = config
    
    def get_preset(self, name: str) -> Optional[SignalEngineConfig]:
        """Get a preset by name"""
        return self.presets.get(name)


# Export singleton
_signal_engine = SignalEngineCustomizer()


def get_signal_customizer() -> SignalEngineCustomizer:
    """Get the signal customizer singleton"""
    return _signal_engine