"""
Gamma Analysis Module

Pure gamma calculations and Greeks analysis:
- Individual position gamma tracking
- Portfolio aggregate gamma
- Delta hedging signals
- Gamma scalping opportunities

Gamma = Second derivative of option price wrt underlying
- Measures rate of delta change
- Higher gamma = faster delta changes = more rebalancing needed
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Position direction"""
    LONG = 1
    SHORT = -1


@dataclass
class GammaPosition:
    """Single options position with gamma"""
    position_id: str
    symbol: str
    strike: float
    expiration: str
    call_put: str
    side: PositionSide
    quantity: int
    entry_price: float
    current_price: float
    gamma: float
    delta: float
    theta: float
    vega: float
    contract_size: int = 100
    
    @property
    def gamma_exposure(self) -> float:
        """Total gamma exposure"""
        return self.gamma * self.quantity * self.contract_size * self.side.value
    
    @property
    def delta_exposure(self) -> float:
        """Total delta exposure"""
        return self.delta * self.quantity * self.contract_size * self.side.value


@dataclass
class PortfolioGamma:
    """Aggregate gamma for portfolio"""
    symbol: str
    timestamp: datetime
    
    # Directional gamma
    net_gamma: float = 0.0  # Sum of all gamma exposures
    call_gamma: float = 0.0
    put_gamma: float = 0.0
    
    # Moneyness
    itm_count: int = 0
    atm_count: int = 0
    otm_count: int = 0
    
    # Risk metrics
    gamma_pnl_1pct: float = 0.0  # P&L if stock moves 1%
    gamma_pnl_2pct: float = 0.0  # P&L if stock moves 2%
    max_gamma_loss: float = 0.0
    
    # Hedging
    rebalance_threshold: float = 0.25  # Delta change triggers rebalance
    next_rebalance_level: float = 0.0


@dataclass
class GammaSignal:
    """Trading signal from gamma analysis"""
    signal_type: str  # rebalance, scalp, adjust
    action: str  # buy, sell, hold
    reason: str
    confidence: float
    target_delta: float
    current_delta: float


class GammaEngine:
    """Calculate and track gamma exposures"""
    
    def __init__(
        self,
        rebalance_threshold: float = 0.25,
        gamma_coefficient: float = 0.5  # Delta per 1% move
    ):
        self.rebalance_threshold = rebalance_threshold
        self.gamma_coefficient = gamma_coefficient
        self.positions: Dict[str, GammaPosition] = {}
        self.history: List[PortfolioGamma] = []
    
    def add_position(
        self,
        position: GammaPosition
    ):
        """Add or update a position"""
        self.positions[position.position_id] = position
    
    def remove_position(self, position_id: str):
        """Remove a position"""
        if position_id in self.positions:
            del self.positions[position_id]
    
    def calculate_portfolio(self, symbol: str) -> PortfolioGamma:
        """Calculate aggregate portfolio gamma"""
        symbol_positions = [
            p for p in self.positions.values()
            if p.symbol == symbol
        ]
        
        if not symbol_positions:
            return None
        
        timestamp = datetime.utcnow()
        
        # Aggregate gamma
        call_gamma = sum(
            p.gamma_exposure for p in symbol_positions
            if p.call_put.upper() == "CALL"
        )
        put_gamma = sum(
            p.gamma_exposure for p in symbol_positions
            if p.call_put.upper() == "PUT"
        )
        net_gamma = call_gamma + put_gamma
        
        # Moneyness classification
        spot = symbol_positions[0].current_price
        itm_count = sum(
            1 for p in symbol_positions
            if (p.call_put.upper() == "CALL" and p.strike < spot) or
               (p.call_put.upper() == "PUT" and p.strike > spot)
        )
        otm_count = sum(
            1 for p in symbol_positions
            if (p.call_put.upper() == "CALL" and p.strike > spot) or
               (p.call_put.upper() == "PUT" and p.strike < spot)
        )
        atm_count = len(symbol_positions) - itm_count - otm_count
        
        # Aggregate delta
        net_delta = sum(p.delta_exposure for p in symbol_positions)
        
        # Gamma P&L estimates
        # Delta change per 1% = Gamma * 0.01 * shares
        gamma_pnl_1pct = net_gamma * 0.01 * spot * 0.01
        gamma_pnl_2pct = net_gamma * 0.02 * spot * 0.02
        
        # Max loss exposure
        max_gamma_loss = abs(gamma_pnl_2pct)
        
        portfolio = PortfolioGamma(
            symbol=symbol,
            timestamp=timestamp,
            net_gamma=net_gamma,
            call_gamma=call_gamma,
            put_gamma=put_gamma,
            itm_count=itm_count,
            atm_count=atm_count,
            otm_count=otm_count,
            gamma_pnl_1pct=gamma_pnl_1pct,
            gamma_pnl_2pct=gamma_pnl_2pct,
            max_gamma_loss=max_gamma_loss,
            current_delta=net_delta
        )
        
        self.history.append(portfolio)
        return portfolio
    
    def generate_signal(self, symbol: str) -> Optional[GammaSignal]:
        """Generate trading signal from gamma analysis"""
        portfolio = self.calculate_portfolio(symbol)
        
        if portfolio is None:
            return None
        
        # Delta rebalance signal
        delta_change = abs(portfolio.current_delta - portfolio.next_rebalance_level)
        
        if delta_change > self.rebalance_threshold:
            action = "sell" if portfolio.current_delta > 0 else "buy"
            
            return GammaSignal(
                signal_type="rebalance",
                action=action,
                reason=f"Delta shift {delta_change:.2f} exceeds threshold",
                confidence=min(1.0, delta_change / self.rebalance_threshold),
                target_delta=0,  # Target delta-neutral
                current_delta=portfolio.current_delta
            )
        
        # High gamma = scalping opportunity
        if abs(portfolio.net_gamma) > portfolio.call_gamma * 0.5:
            return GammaSignal(
                signal_type="scalp",
                action="hold",
                reason=f"High gamma {portfolio.net_gamma:.0f} - scalp premium",
                confidence=min(1.0, abs(portfolio.net_gamma) / 1000),
                target_delta=0,
                current_delta=portfolio.current_delta
            )
        
        return GammaSignal(
            signal_type="none",
            action="hold",
            reason="No signal",
            confidence=0.0,
            target_delta=0,
            current_delta=portfolio.current_delta
        )
    
    def get_hedge_ratio(self, symbol: str) -> float:
        """Get delta hedge ratio for underlying"""
        portfolio = self.calculate_portfolio(symbol)
        
        if portfolio is None:
            return 0.0
        
        # Hedge ratio = -delta / shares
        return -portfolio.current_delta / 100
    
    def get_gamma_risk(self, symbol: str) -> Dict:
        """Get gamma risk assessment"""
        portfolio = self.calculate_portfolio(symbol)
        
        if portfolio is None:
            return {"risk": "none", "level": 0}
        
        if portfolio.net_gamma > 500:
            return {"risk": "high", "level": 1.0}
        elif portfolio.net_gamma > 200:
            return {"risk": "medium", "level": 0.5}
        elif portfolio.net_gamma > 50:
            return {"risk": "low", "level": 0.25}
        else:
            return {"risk": "minimal", "level": 0.1}


# ============================================================================
# Prometheus Metrics Export
# ============================================================================

def export_to_prometheus(gamma: PortfolioGamma) -> Dict[str, float]:
    """Export gamma metrics for Prometheus"""
    return {
        f"gamma_net{{symbol=\"{gamma.symbol}\"}}": gamma.net_gamma,
        f"gamma_call{{symbol=\"{gamma.symbol}\"}}": gamma.call_gamma,
        f"gamma_put{{symbol=\"{gamma.symbol}\"}}": gamma.put_gamma,
        f"gamma_itm{{symbol=\"{gamma.symbol}\"}}": gamma.itm_count,
        f"gamma_atm{{symbol=\"{gamma.symbol}\"}}": gamma.atm_count,
        f"gamma_otm{{symbol=\"{gamma.symbol}\"}}": gamma.otm_count,
        f"gamma_pnl_1pct{{symbol=\"{gamma.symbol}\"}}": gamma.gamma_pnl_1pct,
        f"gamma_pnl_2pct{{symbol=\"{gamma.symbol}\"}}": gamma.gamma_pnl_2pct,
        f"gamma_delta{{symbol=\"{gamma.symbol}\"}}": gamma.current_delta
    }


# ============================================================================
# Options Greeks Calculator
# ============================================================================

class GreeksCalculator:
    """Calculate Black-Scholes Greeks"""
    
    @staticmethod
    def calculate(
        S: float,  # Spot price
        K: float,  # Strike
        T: float,  # Time to expiration (years)
        r: float,  # Risk-free rate
        sigma: float,  # Volatility
        q: float = 0.0,  # Dividend yield
        option_type: str = "call"
    ) -> Dict[str, float]:
        """Calculate all Greeks"""
        from math import sqrt, exp, log, sqrt
        
        # d1 and d2
        d1 = (log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)
        
        # Common terms
        nd1 = (1 / sqrt(2 * 3.14159265)) * exp(-0.5 * d1 ** 2)
        sqrt_t = sqrt(T)
        
        if option_type.lower() == "call":
            N_d1 = 0.5 * (1 + (2 / 3.14159265) * atan(d1 / sqrt(2)))  # Approx normal CDF
            N_d2 = 0.5 * (1 + (2 / 3.14159265) * atan(d2 / sqrt(2)))
            
            price = S * exp(-q * T) * N_d1 - K * exp(-r * T) * N_d2
            delta = exp(-q * T) * N_d1
            rho = K * T * exp(-r * T) * N_d2
        else:  # Put
            N_minus_d1 = 0.5 * (1 - (2 / 3.14159265) * atan(d1 / sqrt(2)))  # Approx normal CDF
            N_minus_d2 = 0.5 * (1 - (2 / 3.14159265) * atan(d2 / sqrt(2)))
            
            price = K * exp(-r * T) * N_minus_d2 - S * exp(-q * T) * N_minus_d1
            delta = exp(-q * T) * (N_d1 - 1)
            rho = -K * T * exp(-r * T) * N_minus_d2
        
        # Gamma (same for call and put)
        gamma = exp(-q * T) * nd1 / (S * sigma * sqrt_t)
        
        # Vega (same for call and put)
        vega = S * exp(-q * T) * nd1 * sqrt_t / 100
        
        # Theta (call)
        theta = (-(S * sigma * exp(-q * T) * nd1) / (2 * sqrt_t)
                - r * K * exp(-r * T) * N_d2 * exp(q * T)
                + q * S * exp(-q * T) * N_d1) / 365
        
        return {
            "price": price,
            "delta": delta,
            "gamma": gamma,
            "vega": vega,
            "theta": theta,
            "rho": rho
        }