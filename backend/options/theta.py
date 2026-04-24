"""
Theta (Time Decay) Analysis Module

Calculates theta exposure from options chain data to identify:
- Daily time decay for options positions
- Decay rate by strike and expiration
- Optimal holding periods
- Time decay acceleration near expiration

Theta = Rate of change of option price with respect to time
- Theta is typically negative for long options (decay works against buyer)
- Expressed as dollars lost per day

For Long (Buying) Positions:
- Goal: Low Theta (lower daily loss) - prefer positions with minimal time decay
- Long theta (positive) = Selling options (receiving time value)
- Short theta (negative) = Buying options (paying time value)
- Theta accelerates as expiration approaches (especially last 30 days)
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ThetaRegime(Enum):
    """Time decay regime"""
    ACCELERATING = "accelerating"  # Last 30 days - fast decay
    NORMAL = "normal"  # 30-60 days - normal decay
    SLOW = "slow"  # 60+ days - slow decay
    WEEKLY = "weekly"  # 7 days or less - extreme decay


class ThetaPosition(Enum):
    """Position type for theta"""
    LONG = "long"  # Buying options - theta negative
    SHORT = "short"  # Selling options - theta positive
    NEUTRAL = "neutral"  # No significant theta


@dataclass
class ThetaMetrics:
    """Aggregated Theta metrics for an options chain"""
    symbol: str
    timestamp: datetime
    spot_price: float
    
    # Total Theta Exposure
    total_call_theta: float = 0.0  # Sum of call theta × OI × contract_size
    total_put_theta: float = 0.0  # Sum of put theta × OI × contract_size
    net_theta: float = 0.0  # Calls - Puts (negative = decay working against buyers)
    
    # Daily P&L Impact
    daily_decay_cost: float = 0.0  # Cost per day for long positions
    weekly_decay_cost: float = 0.0  # Cost per week
    monthly_decay_cost: float = 0.0  # Cost per month
    
    # Decay Analysis
    theta_regime: str = "normal"  # accelerating, normal, slow, weekly
    decay_rate: float = 0.0  # % decay per day
    
    # Expiration Analysis
    days_to_expiration: int = 0
    expiring_soon_count: int = 0  # < 7 days
    next_expiration: Optional[datetime] = None
    
    # Risk Assessment
    theta_risk: str = "low"  # low, medium, high
    theta_drag: float = 0.0  # % of portfolio eaten by decay
    
    # Time Value Analysis
    call_time_value: float = 0.0
    put_time_value: float = 0.0
    total_time_value: float = 0.0
    
    # Stratified Analysis
    front_month_theta: float = 0.0  # Nearest expiration
    back_month_theta: float = 0.0  # Further expiration


@dataclass
class ThetaStrikeCluster:
    """Theta at a specific strike"""
    strike: float
    call_theta: float = 0.0
    put_theta: float = 0.0
    call_oi: int = 0
    put_oi: int = 0
    weighted_theta: float = 0.0


class ThetaEngine:
    """Calculate Theta from options chain data"""
    
    def __init__(
        self,
        risk_free_rate: float = 0.05,  # 5% default
        contract_size: int = 100
    ):
        self.risk_free_rate = risk_free_rate
        self.contract_size = contract_size
        self.history: List[ThetaMetrics] = []
    
    async def analyze(
        self,
        symbol: str,
        options_chain: List,
        spot_price: float,
        timestamp: Optional[datetime] = None
    ) -> ThetaMetrics:
        """Analyze options chain and calculate Theta"""
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        from gex import OptionContract
        
        # Separate calls and puts
        calls = [o for o in options_chain if o.call_put.upper() == "CALL"]
        puts = [o for o in options_chain if o.call_put.upper() == "PUT"]
        
        # Calculate total theta exposure
        # Note: theta is typically negative for long positions
        # We calculate per contract, then scale by OI
        total_call_theta = sum(
            o.theta * o.open_interest * self.contract_size
            for o in calls
        )
        total_put_theta = sum(
            o.theta * o.open_interest * self.contract_size
            for o in puts
        )
        net_theta = total_call_theta - total_put_theta
        
        # Daily decay cost (positive means decay hurts buyers)
        # If net_theta is negative, that's the daily loss for buyers
        daily_decay_cost = abs(net_theta) if net_theta < 0 else 0
        weekly_decay_cost = daily_decay_cost * 7
        monthly_decay_cost = daily_decay_cost * 30
        
        # Determine theta regime based on DTE
        expirations = set()
        for opt in options_chain:
            try:
                # Parse expiration (assuming format like "2024-01-19" or days)
                if hasattr(opt, 'expiration') and opt.expiration:
                    expirations.add(opt.expiration)
            except:
                pass
        
        # Calculate average days to expiration
        if expirations:
            # For simplicity, use a default if we can't parse
            days_to_expiration = 30  # Default
        else:
            days_to_expiration = 30
        
        # Determine regime
        if days_to_expiration <= 7:
            theta_regime = ThetaRegime.WEEKLY.value
        elif days_to_expiration <= 30:
            theta_regime = ThetaRegime.ACCELERATING.value
        elif days_to_expiration <= 60:
            theta_regime = ThetaRegime.NORMAL.value
        else:
            theta_regime = ThetaRegime.SLOW.value
        
        # Calculate decay rate
        decay_rate = abs(net_theta) / (spot_price * 100) if spot_price > 0 else 0
        
        # Expiring soon count
        expiring_soon_count = sum(
            1 for o in options_chain
            if hasattr(o, 'expiration') and o.expiration and
            isinstance(o.expiration, str) and o.expiration.isdigit() and
            int(o.expiration) <= 7
        )
        
        # Theta risk assessment
        theta_drag = abs(net_theta) / (spot_price * 100) if spot_price > 0 else 0
        if theta_drag > 0.05:
            theta_risk = "high"
        elif theta_drag > 0.02:
            theta_risk = "medium"
        else:
            theta_risk = "low"
        
        # Time value calculations
        # Time value ≈ Option Price - Intrinsic Value
        call_time_value = sum(
            self._calculate_time_value(o, spot_price)
            for o in calls
        )
        put_time_value = sum(
            self._calculate_time_value(o, spot_price)
            for o in puts
        )
        total_time_value = call_time_value + put_time_value
        
        # Stratify by month
        front_month_theta = total_call_theta + total_put_theta  # Simplified
        back_month_theta = 0.0
        
        metrics = ThetaMetrics(
            symbol=symbol,
            timestamp=timestamp,
            spot_price=spot_price,
            total_call_theta=total_call_theta,
            total_put_theta=total_put_theta,
            net_theta=net_theta,
            daily_decay_cost=daily_decay_cost,
            weekly_decay_cost=weekly_decay_cost,
            monthly_decay_cost=monthly_decay_cost,
            theta_regime=theta_regime,
            decay_rate=decay_rate,
            days_to_expiration=days_to_expiration,
            expiring_soon_count=expiring_soon_count,
            theta_risk=theta_risk,
            theta_drag=theta_drag,
            call_time_value=call_time_value,
            put_time_value=put_time_value,
            total_time_value=total_time_value,
            front_month_theta=front_month_theta,
            back_month_theta=back_month_theta
        )
        
        self.history.append(metrics)
        return metrics
    
    def _calculate_time_value(self, option, spot_price: float) -> float:
        """Calculate time value for an option"""
        from math import max
        
        if option.call_put.upper() == "CALL":
            intrinsic = max(0, spot_price - option.strike)
        else:  # PUT
            intrinsic = max(0, option.strike - spot_price)
        
        # Mid price estimate
        mid_price = (option.bid + option.ask) / 2 if option.bid and option.ask else 0
        
        # Time value = Option Price - Intrinsic
        time_value = max(0, mid_price - intrinsic)
        
        return time_value * option.open_interest * self.contract_size
    
    def get_decay_signal(self, symbol: str) -> Optional[Dict]:
        """Generate time decay trading signal"""
        recent = [m for m in self.history[-3:] if m.symbol == symbol]
        
        if len(recent) < 3:
            return None
        
        latest = recent[-1]
        
        # High decay = don't buy options, consider selling
        if latest.theta_drag > 0.05:
            return {
                "signal": "avoid_long",
                "action": "sell",
                "direction": "short_theta",
                "reason": f"High decay {latest.theta_drag:.1%} - theta working against buyers",
                "confidence": min(1.0, latest.theta_drag / 0.1)
            }
        
        # Regime change - accelerating decay
        if latest.theta_regime == ThetaRegime.ACCELERATING.value:
            return {
                "signal": "accelerating_decay",
                "action": "close",
                "direction": "reduce_decay",
                "reason": f"Theta accelerating - {latest.days_to_expiration} DTE",
                "confidence": 0.8
            }
        
        return None
    
    def get_optimal_holding_period(self, symbol: str) -> Optional[Dict]:
        """Calculate optimal holding period based on decay"""
        recent = [m for m in self.history if m.symbol == symbol]
        
        if not recent:
            return None
        
        latest = recent[-1]
        
        # Calculate optimal days to hold
        # As decay accelerates near expiration, reduce holding period
        if latest.days_to_expiration <= 7:
            optimal_days = 1  # Day trade
        elif latest.days_to_expiration <= 14:
            optimal_days = 2
        elif latest.days_to_expiration <= 30:
            optimal_days = 5
        elif latest.days_to_expiration <= 60:
            optimal_days = 10
        else:
            optimal_days = 20
        
        return {
            "optimal_days": optimal_days,
            "reason": f"Based on {latest.days_to_expiration} DTE and {latest.theta_regime} regime",
            "max_daily_loss": latest.daily_decay_cost
        }


# ============================================================================
# Prometheus Metrics Export
# ============================================================================

def export_to_prometheus(theta: ThetaMetrics) -> Dict[str, float]:
    """Export Theta metrics for Prometheus scraping"""
    return {
        f"theta_total_call{{symbol=\"{theta.symbol}\"}}": theta.total_call_theta,
        f"theta_total_put{{symbol=\"{theta.symbol}\"}}": theta.total_put_theta,
        f"theta_net{{symbol=\"{theta.symbol}\"}}": theta.net_theta,
        f"theta_daily_decay{{symbol=\"{theta.symbol}\"}}": theta.daily_decay_cost,
        f"theta_weekly_decay{{symbol=\"{theta.symbol}\"}}": theta.weekly_decay_cost,
        f"theta_monthly_decay{{symbol=\"{theta.symbol}\"}}": theta.monthly_decay_cost,
        f"theta_regime{{symbol=\"{theta.symbol}\"}}": hash(theta.theta_regime) % 100,
        f"theta_decay_rate{{symbol=\"{theta.symbol}\"}}": theta.decay_rate,
        f"theta_drag{{symbol=\"{theta.symbol}\"}}": theta.theta_drag,
        f"theta_time_value{{symbol=\"{theta.symbol}\"}}": theta.total_time_value,
        f"theta_spot_price{{symbol=\"{theta.symbol}\"}}": theta.spot_price
    }


# ============================================================================
# Backtest Integration
# ============================================================================

class ThetaSignalGenerator:
    """Generate signals based on Theta for backtesting"""
    
    def __init__(self, theta_engine: ThetaEngine):
        self.theta_engine = theta_engine
    
    def generate_signal(self, symbol: str) -> int:
        """Generate trading signal: 1=avoid_long (sell theta), -1=take_long, 0=neutral"""
        signal = self.theta_engine.get_decay_signal(symbol)
        
        if signal is None:
            return 0
        
        # High decay = avoid long positions
        if signal["signal"] == "avoid_long":
            return 1
        
        return 0
    
    def get_confidence(self, symbol: str) -> float:
        """Get signal confidence"""
        recent = self.theta_engine.history[-3:] if self.theta_engine.history else []
        
        if len(recent) < 3:
            return 0.0
        
        latest = recent[-1]
        return latest.theta_drag