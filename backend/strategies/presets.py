"""
Strategy Presets System

Save and load custom strategy configurations:
- Backtest parameter sets
- Signal engine configs  
- Risk management parameters
- UI layouts and themes
"""
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

PRESETS_DIR = Path("data/presets")


@dataclass
class StrategyPreset:
    """A saved strategy configuration"""
    name: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Strategy parameters
    strategy_type: str = "breakout"  # breakout, rsi, sma, pattern
    entry_threshold: float = 5.0
    exit_threshold: float = -3.0
    position_sizing: str = "fixed"  # fixed, atr, volatility
    
    # Risk parameters
    max_position_pct: float = 0.10  # 10% max per position
    max_portfolio_pct: float = 0.30  # 30% max total exposure
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.06  # 6% take profit
    
    # Backtest parameters
    initial_capital: float = 10000.0
    slippage_pct: float = 0.05
    commission_pct: float = 0.1
    
    @classmethod
    def from_dict(cls, data: Dict) -> "StrategyPreset":
        """Create from dictionary"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            strategy_type=data.get("strategy_type", "breakout"),
            entry_threshold=data.get("entry_threshold", 5.0),
            exit_threshold=data.get("exit_threshold", -3.0),
            position_sizing=data.get("position_sizing", "fixed"),
            max_position_pct=data.get("max_position_pct", 0.10),
            max_portfolio_pct=data.get("max_portfolio_pct", 0.30),
            stop_loss_pct=data.get("stop_loss_pct", 0.02),
            take_profit_pct=data.get("take_profit_pct", 0.06),
            initial_capital=data.get("initial_capital", 10000.0),
            slippage_pct=data.get("slippage_pct", 0.05),
            commission_pct=data.get("commission_pct", 0.1),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class RiskPreset:
    """Risk management preset"""
    name: str
    description: str = ""
    
    # Loss limits
    max_consecutive_losses: int = 3
    max_drawdown_pct: float = 0.10  # 10%
    daily_loss_limit_pct: float = 0.05  # 5%
    
    # Position management
    max_positions: int = 5
    max_positions_per_ticker: int = 1
    
    # Greeks-based exits
    theta_exit_threshold: float = 0.0  # Exit when theta reaches this
    gamma_alert_threshold: float = 0.10  # Alert when gamma exceeds
    
    # Correlation limits
    max_correlation_exposure: float = 0.40  # 40% in correlated positions
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RiskPreset":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            max_consecutive_losses=data.get("max_consecutive_losses", 3),
            max_drawdown_pct=data.get("max_drawdown_pct", 0.10),
            daily_loss_limit_pct=data.get("daily_loss_limit_pct", 0.05),
            max_positions=data.get("max_positions", 5),
            max_positions_per_ticker=data.get("max_positions_per_ticker", 1),
            theta_exit_threshold=data.get("theta_exit_threshold", 0.0),
            gamma_alert_threshold=data.get("gamma_alert_threshold", 0.10),
            max_correlation_exposure=data.get("max_correlation_exposure", 0.40),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass  
class ChartPreset:
    """Chart display preset"""
    name: str
    description: str = ""
    
    # Display
    chart_type: str = "line"  # area, bar, line, candlestick
    layout: str = "grid"  # grid, list, heatmap
    timeframe: str = "1D"
    
    # Colors (dark theme)
    primary_color: str = "#10b981"
    secondary_color: str = "#3b82f6"
    background_color: str = "#0a0a0a"
    grid_color: str = "#1f2937"
    
    # Indicators
    show_bollinger: bool = False
    show_volume: bool = True
    show_ma: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ChartPreset":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            chart_type=data.get("chart_type", "line"),
            layout=data.get("layout", "grid"),
            timeframe=data.get("timeframe", "1D"),
            primary_color=data.get("primary_color", "#10b981"),
            secondary_color=data.get("secondary_color", "#3b82f6"),
            background_color=data.get("background_color", "#0a0a0a"),
            grid_color=data.get("grid_color", "#1f2937"),
            show_bollinger=data.get("show_bollinger", False),
            show_volume=data.get("show_volume", True),
            show_ma=data.get("show_ma", True),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PresetManager:
    """Manage all presets"""
    
    def __init__(self):
        self.strategy_presets: Dict[str, StrategyPreset] = {}
        self.risk_presets: Dict[str, RiskPreset] = {}
        self.chart_presets: Dict[str, ChartPreset] = {}
        
        self._init_defaults()
        self._load_all()
    
    def _init_defaults(self):
        """Initialize default presets"""
        # Strategy presets
        self.strategy_presets["conservative"] = StrategyPreset(
            name="conservative",
            description="Low risk - requires strong signals",
            strategy_type="breakout",
            entry_threshold=7.0,
            exit_threshold=-2.0,
            position_sizing="atr",
            max_position_pct=0.05,
            max_portfolio_pct=0.20,
            stop_loss_pct=0.01,
            take_profit_pct=0.03,
        )
        
        self.strategy_presets["aggressive"] = StrategyPreset(
            name="aggressive", 
            description="Higher risk - faster signals",
            strategy_type="breakout",
            entry_threshold=3.0,
            exit_threshold=-1.0,
            position_sizing="fixed",
            max_position_pct=0.15,
            max_portfolio_pct=0.50,
            stop_loss_pct=0.03,
            take_profit_pct=0.10,
        )
        
        # Risk presets
        self.risk_presets["default"] = RiskPreset(
            name="default",
            description="Balanced risk management",
            max_consecutive_losses=3,
            max_drawdown_pct=0.10,
        )
        
        self.risk_presets["tight"] = RiskPreset(
            name="tight",
            description="Tight stops - quick exits",
            max_consecutive_losses=2,
            max_drawdown_pct=0.05,
            daily_loss_limit_pct=0.03,
        )
        
        # Chart presets
        self.chart_presets["default"] = ChartPreset(
            name="default",
            description="Standard dark theme"
        )
        
        self.chart_presets["candlestick"] = ChartPreset(
            name="candlestick",
            description="Candlestick view",
            chart_type="candlestick",
        )
    
    def _load_all(self):
        """Load presets from disk"""
        if not PRESETS_DIR.exists():
            return
        
        # Load JSON presets
        for file in PRESETS_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                preset_type = file.stem.split("_")[0]
                
                if preset_type == "strategy":
                    for name, items in data.items():
                        self.strategy_presets[name] = StrategyPreset.from_dict(items)
                elif preset_type == "risk":
                    for name, items in data.items():
                        self.risk_presets[name] = RiskPreset.from_dict(items)
                elif preset_type == "chart":
                    for name, items in data.items():
                        self.chart_presets[name] = ChartPreset.from_dict(items)
            except Exception as e:
                logger.warning(f"Failed to load {file}: {e}")
    
    def _save_preset(self, preset_type: str, preset: Any):
        """Save a preset to disk"""
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        
        filename = f"{preset_type}_presets.json"
        filepath = PRESETS_DIR / filename
        
        data = {}
        if filepath.exists():
            data = json.loads(filepath.read_text())
        
        data[preset.name] = preset.to_dict()
        filepath.write_text(json.dumps(data, indent=2))
    
    # Strategy presets
    def save_strategy(self, preset: StrategyPreset):
        """Save a strategy preset"""
        preset.updated_at = datetime.utcnow().isoformat()
        self.strategy_presets[preset.name] = preset
        self._save_preset("strategy", preset)
    
    def get_strategy(self, name: str) -> Optional[StrategyPreset]:
        """Get strategy preset"""
        return self.strategy_presets.get(name)
    
    def list_strategies(self) -> List[str]:
        """List strategy presets"""
        return list(self.strategy_presets.keys())
    
    # Risk presets
    def save_risk(self, preset: RiskPreset):
        """Save a risk preset"""
        self.risk_presets[preset.name] = preset
        self._save_preset("risk", preset)
    
    def get_risk(self, name: str) -> Optional[RiskPreset]:
        """Get risk preset"""
        return self.risk_presets.get(name)
    
    def list_risks(self) -> List[str]:
        """List risk presets"""
        return list(self.risk_presets.keys())
    
    # Chart presets
    def save_chart(self, preset: ChartPreset):
        """Save a chart preset"""
        self.chart_presets[preset.name] = preset
        self._save_preset("chart", preset)
    
    def get_chart(self, name: str) -> Optional[ChartPreset]:
        """Get chart preset"""
        return self.chart_presets.get(name)
    
    def list_charts(self) -> List[str]:
        """List chart presets"""
        return list(self.chart_presets.keys())
    
    # Delete
    def delete_strategy(self, name: str):
        """Delete strategy preset"""
        if name in self.strategy_presets:
            del self.strategy_presets[name]
    
    def delete_risk(self, name: str):
        """Delete risk preset"""
        if name in self.risk_presets:
            del self.risk_presets[name]
    
    def delete_chart(self, name: str):
        """Delete chart preset"""
        if name in self.chart_presets:
            del self.chart_presets[name]


# Singleton
_preset_manager = PresetManager()


def get_preset_manager() -> PresetManager:
    """Get preset manager singleton"""
    return _preset_manager