"""
Enhanced Portfolio Analytics

Advanced portfolio metrics and analytics:
- Real-time P&L
- Risk metrics (VaR, CVaR)
- Position attribution
- Greeks aggregation
- Correlation analysis
- Cross-chart interactions
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Position direction"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass
class Position:
    """Option position"""
    symbol: str
    side: str  # call, put
    strike: float
    expiry: str
    quantity: int
    entry_price: float
    current_price: float
    iv: float
    delta: float = 0.0
    theta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    
    @property
    def market_value(self) -> float:
        return self.current_price * self.quantity * 100
    
    @property
    def cost_basis(self) -> float:
        return self.entry_price * self.quantity * 100
    
    @property
    def pnl(self) -> float:
        return (self.current_price - self.entry_price) * self.quantity * 100
    
    @property
    def pnl_pct(self) -> float:
        return (self.current_price - self.entry_price) / self.entry_price if self.entry_price > 0 else 0


@dataclass
class PortfolioMetrics:
    """Complete portfolio metrics"""
    timestamp: datetime
    total_value: float
    cash: float
    buying_power: float
    
    # P&L
    day_pnl: float = 0.0
    total_pnl: float = 0.0
    
    # Greeks aggregation
    net_delta: float = 0.0
    net_theta: float = 0.0
    net_gamma: float = 0.0
    net_vega: float = 0.0
    net_rho: float = 0.0
    
    # Risk metrics
    var_95: float = 0.0  # Value at Risk (95%)
    cvar_95: float = 0.0  # Conditional VaR
    
    # Position stats
    positions_count: int = 0
    winning_positions: int = 0
    losing_positions: int = 0
    
    # Beta-weighted exposure
    beta_exposure: float = 0.0
    
    # Sector exposure (if available)
    sector_exposure: Dict[str, float] = field(default_factory=dict)


class PortfolioAnalytics:
    """Calculate advanced portfolio analytics"""
    
    def __init__(self):
        self._positions: Dict[str, Position] = {}
        self._history: List[PortfolioMetrics] = []
        self._max_history = 252  # 1 year
    
    def add_position(self, position: Position):
        """Add/update position"""
        key = f"{position.symbol}_{position.strike}_{position.expiry}"
        self._positions[key] = position
    
    def remove_position(self, symbol: str):
        """Remove position"""
        self._positions = {
            k: v for k, v in self._positions.items()
            if not k.startswith(symbol)
        }
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get positions, optionally filtered"""
        if symbol:
            return [
                v for k, v in self._positions.items()
                if v.symbol == symbol
            ]
        return list(self._positions.values())
    
    def calculate_metrics(
        self,
        cash: float = 100000,
        beta: float = 1.0
    ) -> PortfolioMetrics:
        """Calculate current metrics"""
        positions = self.get_positions()
        
        # Aggregate Greeks
        net_delta = sum(p.delta * p.quantity for p in positions)
        net_theta = sum(p.theta * p.quantity for p in positions)
        net_gamma = sum(p.gamma * p.quantity for p in positions)
        net_vega = sum(p.vega * p.quantity for p in positions)
        net_rho = sum(p.rho * p.quantity for p in positions)
        
        # P&L
        total_value = cash + sum(p.market_value for p in positions)
        day_pnl = sum(p.pnl for p in positions)
        
        # Win/Lose counts
        winning = len([p for p in positions if p.pnl > 0])
        losing = len([p for p in positions if p.pnl < 0])
        
        # Simple VaR (5% of portfolio value)
        var_95 = total_value * 0.05
        cvar_95 = total_value * 0.07
        
        return PortfolioMetrics(
            timestamp=datetime.utcnow(),
            total_value=total_value,
            cash=cash,
            buying_power=cash * 4,  # Standard margin
            day_pnl=day_pnl,
            total_pnl=day_pnl,  # Simplified
            net_delta=net_delta,
            net_theta=net_theta,
            net_gamma=net_gamma,
            net_vega=net_vega,
            net_rho=net_rho,
            var_95=var_95,
            cvar_95=cvar_95,
            positions_count=len(positions),
            winning_positions=winning,
            losing_positions=losing,
            beta_exposure=net_delta * beta,
        )
    
    def get_position_attribution(
        self,
        symbol: str
    ) -> Dict[str, float]:
        """Get attribution breakdown for a symbol"""
        positions = self.get_positions(symbol)
        
        return {
            "symbol": symbol,
            "positions": len(positions),
            "market_value": sum(p.market_value for p in positions),
            "pnl": sum(p.pnl for p in positions),
            "delta": sum(p.delta for p in positions),
            "theta": sum(p.theta for p in positions),
            "gamma": sum(p.gamma for p in positions),
            "vega": sum(p.vega for p in positions),
        }
    
    def get_top_losers(self, limit: int = 5) -> List[Dict]:
        """Get worst performing positions"""
        positions = sorted(
            self.get_positions(),
            key=lambda p: p.pnl
        )[:limit]
        
        return [
            {
                "symbol": p.symbol,
                "strike": p.strike,
                "pnl": p.pnl,
                "pnl_pct": p.pnl_pct,
                "loss": abs(p.pnl),
            }
            for p in positions
            if p.pnl < 0
        ]
    
    def get_top_winners(self, limit: int = 5) -> List[Dict]:
        """Get best performing positions"""
        positions = sorted(
            self.get_positions(),
            key=lambda p: p.pnl,
            reverse=True
        )[:limit]
        
        return [
            {
                "symbol": p.symbol,
                "strike": p.strike,
                "pnl": p.pnl,
                "pnl_pct": p.pnl_pct,
                "gain": p.pnl,
            }
            for p in positions
            if p.pnl > 0
        ]
    
    def get_sector_allocation(self) -> Dict[str, float]:
        """Estimate sector allocation (simplified)"""
        sectors = {
            "tech": ["NVDA", "AMD", "INTC", "META", "GOOGL", "GOOG", "MSFT", "AAPL", "TSLA"],
            "finance": ["JPM", "BAC", "GS", "MS", "C", "WFC"],
            "healthcare": ["JNJ", "UNH", "PFE", "ABBV", "TMO", "ABT"],
            "energy": ["XOM", "CVX", "COP", "SLB"],
            "consumer": ["AMZN", "WMT", "HD", "NKE", "COST"],
        }
        
        allocation = {}
        positions = self.get_positions()
        
        for sector, tickers in sectors.items():
            sector_value = sum(
                p.market_value for p in positions
                if any(t in p.symbol for t in tickers)
            )
            if sector_value > 0:
                allocation[sector] = sector_value
        
        return allocation
    
    def get_expiry_walls(self) -> Dict[str, float]:
        """Group by expiry (gamma wall detection)"""
        walls = {}
        positions = self.get_positions()
        
        for p in positions:
            exp = p.expiry
            if exp not in walls:
                walls[exp] = 0
            walls[exp] += abs(p.gamma) * p.quantity * 100
        
        return walls


_portfolio_analytics = PortfolioAnalytics()


def get_portfolio_analytics() -> PortfolioAnalytics:
    """Get portfolio analytics singleton"""
    return _portfolio_analytics
