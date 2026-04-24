"""
Unified Greeks Engine
Combines Delta, Theta, Vega, Gamma, Rho, and IV analysis into single engine.
Allows selective computation of individual Greeks for performance optimization.

Features:
- Configurable Greek inclusion (exclude unused Greeks)
- IV percentile tracking (historical comparison)
- Volatility spike protection
- Real-time metric export to Prometheus
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class GreekType(Enum):
    """Available Greek types"""
    DELTA = "delta"
    THETA = "theta"
    VEGA = "vega"
    GAMMA = "gamma"
    RHO = "rho"
    VEX = "vex"  # Vega exposure aggregate
    GEX = "gex"  # Gamma exposure aggregate


class VolatilityRegime(Enum):
    """Market volatility regime"""
    SUPPRESSED = "suppressed"   # Low vol environment
    NORMAL = "normal"         # Typical vol
    ELEVATED = "elevated"      # High vol
    EXTREME = "extreme"       # Volatility spike/crisis


@dataclass
class GreeksConfig:
    """Configuration for Greeks engine"""
    # Which Greeks to compute (exclude unused for performance)
    enabled_greeks: Set[GreekType] = field(default_factory=lambda: {
        GreekType.DELTA,
        GreekType.THETA,
        GreekType.VEGA,
        GreekType.GAMMA,
        GreekType.RHO,
    })
    
    # IV percentile settings
    track_iv_percentiles: bool = True
    iv_percentile_window: int = 252  # 1 year by default
    
    # Volatility spike protection
    volatility_spike_threshold: float = 1.5  # 50% above normal triggers protection
    enable_spike_protection: bool = True
    
    # Contract settings
    contract_size: int = 100
    
    # Risk-free rate for Rho
    risk_free_rate: float = 0.05


@dataclass
class IVPercentileData:
    """IV percentile tracking"""
    current_iv: float = 0.0
    iv_history: List[float] = field(default_factory=list)
    
    # Percentiles
    percentile_1: float = 0.0   # 1st percentile (extremely low)
    percentile_5: float = 0.0   # 5th percentile (very low)
    percentile_10: float = 0.0  # 10th percentile (low)
    percentile_25: float = 0.0 # 25th percentile
    percentile_50: float = 0.0  # 50th percentile (median)
    percentile_75: float = 0.0  # 75th percentile
    percentile_90: float = 0.0  # 90th percentile
    percentile_95: float = 0.0  # 95th percentile (high)
    percentile_99: float = 0.0  # 99th percentile (extremely high)
    
    # Regime
    regime: str = "normal"
    regime_change: str = "stable"
    
    @property
    def iv_rank(self) -> float:
        """Current IV as percentile rank (0-100)"""
        if not self.iv_history or len(self.iv_history) < 10:
            return 50.0
        
        sorted_iv = sorted(self.iv_history)
        current_rank = sum(1 for iv in sorted_iv if iv < self.current_iv)
        return (current_rank / len(sorted_iv)) * 100
    
    @property
    def is_elevated(self) -> bool:
        """Is IV elevated compared to history"""
        return self.current_iv > self.percentile_75
    
    @property
    def is_extreme(self) -> bool:
        """Is IV at extreme levels"""
        return self.current_iv > self.percentile_95
    
    def update(self, iv: float, window: int = 252) -> None:
        """Update IV data with new observation"""
        prev_iv = self.current_iv
        self.current_iv = iv
        self.iv_history.append(iv)
        
        # Trim to window
        if len(self.iv_history) > window:
            self.iv_history = self.iv_history[-window:]
        
        # Recalculate percentiles if enough data
        if len(self.iv_history) >= 20:
            self._calculate_percentiles()
        
        # Detect regime change
        if prev_iv > 0:
            if iv > prev_iv * 1.1:
                self.regime_change = "rising"
            elif iv < prev_iv * 0.9:
                self.regime_change = "falling"
            else:
                self.regime_change = "stable"
        
        # Determine regime
        if self.current_iv < self.percentile_10:
            self.regime = VolatilityRegime.SUPPRESSED.value
        elif self.current_iv < self.percentile_75:
            self.regime = VolatilityRegime.NORMAL.value
        elif self.current_iv < self.percentile_95:
            self.regime = VolatilityRegime.ELEVATED.value
        else:
            self.regime = VolatilityRegime.EXTREME.value
    
    def _calculate_percentiles(self) -> None:
        """Calculate percentile rankings"""
        if not self.iv_history:
            return
        
        sorted_iv = sorted(self.iv_history)
        n = len(sorted_iv)
        
        def get_percentile(p: float) -> float:
            idx = int(n * p / 100)
            idx = min(idx, n - 1)
            return sorted_iv[idx]
        
        self.percentile_1 = get_percentile(1)
        self.percentile_5 = get_percentile(5)
        self.percentile_10 = get_percentile(10)
        self.percentile_25 = get_percentile(25)
        self.percentile_50 = get_percentile(50)
        self.percentile_75 = get_percentile(75)
        self.percentile_90 = get_percentile(90)
        self.percentile_95 = get_percentile(95)
        self.percentile_99 = get_percentile(99)


@dataclass
class UnifiedGreeks:
    """Complete Greeks output from unified engine"""
    symbol: str
    timestamp: datetime
    spot_price: float
    
    # Delta (Direction & Probability)
    delta: Optional[float] = None
    call_delta: Optional[float] = None
    put_delta: Optional[float] = None
    delta_direction: Optional[str] = None      # bullish/bearish/neutral
    delta_strength: Optional[float] = None  # 0-1
    prob_itm_call: Optional[float] = None
    prob_itm_put: Optional[float] = None
    
    # Theta (Time Decay)
    theta: Optional[float] = None
    call_theta: Optional[float] = None
    put_theta: Optional[float] = None
    theta_daily: Optional[float] = None
    theta_weekly: Optional[float] = None
    theta_monthly: Optional[float] = None
    theta_regime: Optional[str] = None
    
    # Vega (Volatility Sensitivity)
    vega: Optional[float] = None
    call_vega: Optional[float] = None
    put_vega: Optional[float] = None
    iv: Optional[float] = None
    iv_skew: Optional[float] = None
    iv_rank: Optional[float] = None
    
    # Gamma (Delta Acceleration)
    gamma: Optional[float] = None
    call_gamma: Optional[float] = None
    put_gamma: Optional[float] = None
    gamma_risk: Optional[str] = None
    
    # Rho (Interest Rate Sensitivity)
    rho: Optional[float] = None
    call_rho: Optional[float] = None
    put_rho: Optional[float] = None
    
    # Aggregated exposures
    gex: Optional[float] = None  # Gamma exposure
    vex: Optional[float] = None  # Vega exposure
    
    # IV percentile data
    iv_percentile: Optional[IVPercentileData] = None
    
    # Volatility spike protection flag
    volatility_spike: bool = False
    spike_warning: Optional[str] = None


class GreeksEngine:
    """
    Unified Greeks Engine
    
    Supports:
    - Selective Greek computation for performance
    - IV percentile tracking
    - Volatility spike detection
    - Prometheus export
    """
    
    def __init__(self, config: Optional[GreeksConfig] = None):
        self.config = config or GreeksConfig()
        self.history: List[UnifiedGreeks] = []
        self.symbol_iv_data: Dict[str, IVPercentileData] = {}
    
    def is_enabled(self, greek: GreekType) -> bool:
        """Check if a Greek is enabled in config"""
        return greek in self.config.enabled_greeks
    
    async def analyze(
        self,
        symbol: str,
        options_chain: List,  # List of OptionContract from gex.py
        spot_price: float,
        timestamp: Optional[datetime] = None
    ) -> UnifiedGreeks:
        """
        Run unified Greeks analysis
        
        Only computes Greeks that are enabled in config for performance.
        """
        from gex import OptionContract
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Initialize IV tracking for symbol
        if symbol not in self.symbol_iv_data:
            self.symbol_iv_data[symbol] = IVPercentileData()
        
        iv_data = self.symbol_iv_data[symbol]
        
        # Separate calls and puts
        calls = [o for o in options_chain if o.call_put.upper() == "CALL"]
        puts = [o for o in options_chain if o.call_put.upper() == "PUT"]
        
        # Calculate totals with Only enabled Greeks
        result = UnifiedGreeks(
            symbol=symbol,
            timestamp=timestamp,
            spot_price=spot_price
        )
        
        # Get ATM IV for percentile tracking
        atm_iv = self._calculate_atm_iv(options_chain, spot_price)
        if atm_iv > 0:
            iv_data.update(atm_iv, self.config.iv_percentile_window)
            result.iv = atm_iv
            result.iv_percentile = iv_data
        
        # Check for volatility spike
        if self.config.enable_spike_protection:
            result.volatility_spike = self._check_volatility_spike(iv_data)
            if result.volatility_spike:
                result.spike_warning = self._generate_spike_warning(iv_data)
        
        # ═══════════════════════════════════════════════════════════════════
        # DELTA (if enabled)
        # ═══════════════════════════════════════════════════════════════════
        if self.is_enabled(GreekType.DELTA):
            result.delta = self._calculate_delta(calls, puts)
            result.call_delta = self._calculate_call_delta(calls)
            result.put_delta = self._calculate_put_delta(puts)
            
            # Direction
            if result.delta and result.delta > 0:
                result.delta_direction = "bullish"
                result.delta_strength = min(1.0, abs(result.delta) / 1000)
            elif result.delta and result.delta < 0:
                result.delta_direction = "bearish"
                result.delta_strength = min(1.0, abs(result.delta) / 1000)
            else:
                result.delta_direction = "neutral"
                result.delta_strength = 0.0
            
            # Probability ITM
            result.prob_itm_call = self._calculate_prob_itm(calls)
            result.prob_itm_put = self._calculate_prob_itm(puts)
        
        # ═══════════════════════════════════════════════════════════════════
        # THETA (if enabled)
        # ═══════════════════════════════════════════════════════════════════
        if self.is_enabled(GreekType.THETA):
            result.theta = self._calculate_theta(calls, puts)
            result.call_theta = self._calculate_call_theta(calls)
            result.put_theta = self._calculate_put_theta(puts)
            
            # Daily decay
            result.theta_daily = abs(result.theta) if result.theta and result.theta < 0 else 0
            result.theta_weekly = result.theta_daily * 7 if result.theta_daily else 0
            result.theta_monthly = result.theta_daily * 30 if result.theta_daily else 0
            
            # Regime
            if result.theta_daily and result.theta_daily > 30:
                result.theta_regime = "accelerating"
            elif result.theta_daily and result.theta_daily > 15:
                result.theta_regime = "normal"
            else:
                result.theta_regime = "slow"
        
        # ═══════════════════════════════════════════════════════════════════
        # VEGA (if enabled)
        # ═══════════════════════════════════════════════════════════════════
        if self.is_enabled(GreekType.VEGA):
            result.vega = self._calculate_vega(calls, puts)
            result.call_vega = self._calculate_call_vega(calls)
            result.put_vega = self._calculate_put_vega(puts)
            
            # IV skew
            result.iv_skew = self._calculate_iv_skew(calls, puts)
            result.iv_rank = iv_data.iv_rank
        
        # ═══════════════════════════════════════════════════════════════════
        # GAMMA (if enabled)
        # ═══════════════════════════════════════════════════════════════════
        if self.is_enabled(GreekType.GAMMA):
            result.gamma = self._calculate_gamma(calls, puts)
            result.call_gamma = self._calculate_call_gamma(calls)
            result.put_gamma = self._calculate_put_gamma(puts)
            
            # Risk assessment
            if result.gamma and result.gamma > 30:
                result.gamma_risk = "high"
            elif result.gamma and result.gamma > 15:
                result.gamma_risk = "medium"
            else:
                result.gamma_risk = "low"
        
        # ═══════════════════════════════════════════════════════════════════
        # RHO (if enabled)
        # ═══════════════════════════════════════════════════════════════════
        if self.is_enabled(GreekType.RHO):
            result.rho = self._calculate_rho(calls, puts, spot_price)
            result.call_rho = self._calculate_call_rho(calls, spot_price)
            result.put_rho = self._calculate_put_rho(puts, spot_price)
        
        # ═══════════════════════════════════════════════════════════════════
        # GEX (if enabled)
        # ═══════════════════════════════════════════════════════════════════
        if self.is_enabled(GreekType.GEX):
            result.gex = self._calculate_gex(calls, puts)
        
        # ═══════════════════════════════════════════════════════════════════
        # VEX (if enabled)
        # ═══════════════════════════════════════════════════════════════════
        if self.is_enabled(GreekType.VEX):
            result.vex = self._calculate_vex(calls, puts)
        
        self.history.append(result)
        return result
    
    # ═══════════════════════════════════════════════════════════════════
    # Calculation Methods
    # ═══════════════════════════════════════════════════════════════════
    
    def _calculate_atm_iv(self, options_chain: List, spot: float) -> float:
        """Calculate ATM implied volatility"""
        if not options_chain:
            return 0.0
        
        atm_options = min(
            options_chain,
            key=lambda o: abs(o.strike - spot)
        )
        return atm_options.iv if atm_options else 0.0
    
    def _calculate_delta(self, calls: List, puts: List) -> float:
        """Net delta exposure"""
        call_delta = sum(
            o.delta * o.open_interest * self.config.contract_size
            for o in calls
        )
        put_delta = sum(
            o.delta * o.open_interest * self.config.contract_size
            for o in puts
        )
        return call_delta - put_delta
    
    def _calculate_call_delta(self, calls: List) -> float:
        """Call delta exposure"""
        return sum(
            o.delta * o.open_interest * self.config.contract_size
            for o in calls
        ) if calls else 0.0
    
    def _calculate_put_delta(self, puts: List) -> float:
        """Put delta exposure"""
        return sum(
            o.delta * o.open_interest * self.config.contract_size
            for o in puts
        ) if puts else 0.0
    
    def _calculate_prob_itm(self, options: List) -> float:
        """Probability of expiring ITM"""
        if not options:
            return 0.0
        
        total_oi = sum(o.open_interest for o in options)
        if total_oi == 0:
            return 0.0
        
        return sum(
            abs(o.delta) * o.open_interest
            for o in options
        ) / total_oi
    
    def _calculate_theta(self, calls: List, puts: List) -> float:
        """Net theta"""
        call_theta = sum(
            o.theta * o.open_interest * self.config.contract_size
            for o in calls
        )
        put_theta = sum(
            o.theta * o.open_interest * self.config.contract_size
            for o in puts
        )
        return call_theta - put_theta
    
    def _calculate_call_theta(self, calls: List) -> float:
        """Call theta"""
        return sum(
            o.theta * o.open_interest * self.config.contract_size
            for o in calls
        ) if calls else 0.0
    
    def _calculate_put_theta(self, puts: List) -> float:
        """Put theta"""
        return sum(
            o.theta * o.open_interest * self.config.contract_size
            for o in puts
        ) if puts else 0.0
    
    def _calculate_vega(self, calls: List, puts: List) -> float:
        """Net vega"""
        call_vega = sum(
            o.vega * o.open_interest * self.config.contract_size
            for o in calls
        )
        put_vega = sum(
            o.vega * o.open_interest * self.config.contract_size
            for o in puts
        )
        return call_vega - put_vega
    
    def _calculate_call_vega(self, calls: List) -> float:
        """Call vega"""
        return sum(
            o.vega * o.open_interest * self.config.contract_size
            for o in calls
        ) if calls else 0.0
    
    def _calculate_put_vega(self, puts: List) -> float:
        """Put vega"""
        return sum(
            o.vega * o.open_interest * self.config.contract_size
            for o in puts
        ) if puts else 0.0
    
    def _calculate_iv_skew(self, calls: List, puts: List) -> float:
        """IV skew = put IV - call IV"""
        if not calls or not puts:
            return 0.0
        
        call_iv = sum(o.iv * o.open_interest for o in calls) / sum(o.open_interest for o in calls)
        put_iv = sum(o.iv * o.open_interest for o in puts) / sum(o.open_interest for o in puts)
        
        return put_iv - call_iv
    
    def _calculate_gamma(self, calls: List, puts: List) -> float:
        """Net gamma"""
        call_gamma = sum(
            o.gamma * o.open_interest * self.config.contract_size
            for o in calls
        )
        put_gamma = sum(
            o.gamma * o.open_interest * self.config.contract_size
            for o in puts
        )
        return call_gamma - put_gamma
    
    def _calculate_call_gamma(self, calls: List) -> float:
        """Call gamma"""
        return sum(
            o.gamma * o.open_interest * self.config.contract_size
            for o in calls
        ) if calls else 0.0
    
    def _calculate_put_gamma(self, puts: List) -> float:
        """Put gamma"""
        return sum(
            o.gamma * o.open_interest * self.config.contract_size
            for o in puts
        ) if puts else 0.0
    
    def _calculate_rho(self, calls: List, puts: List, spot: float) -> float:
        """Net rho (interest rate sensitivity)"""
        call_rho = self._calculate_call_rho(calls, spot)
        put_rho = self._calculate_put_rho(puts, spot)
        return call_rho - put_rho
    
    def _calculate_call_rho(self, calls: List, spot: float) -> float:
        """Call rho"""
        # Simplified: Rho ≈ K * T * e^(-rT) * N(d2) for calls
        # For 100 shares per contract:
        r = self.config.risk_free_rate
        
        total = 0.0
        for o in calls:
            # Approximate: rho scales with time to expiry and strike
            T_years = 30 / 365  # Assume 30 DTE if not specified
            rho = o.strike * T_years * r * o.open_interest * self.config.contract_size
            total += rho
        
        return total
    
    def _calculate_put_rho(self, puts: List, spot: float) -> float:
        """Put rho"""
        # Simplified: Rho ≈ -K * T * e^(-rT) * N(-d2) for puts
        r = self.config.risk_free_rate
        
        total = 0.0
        for o in puts:
            T_years = 30 / 365
            rho = o.strike * T_years * r * o.open_interest * self.config.contract_size
            total += rho
        
        return total
    
    def _calculate_gex(self, calls: List, puts: List) -> float:
        """Gamma exposure = net gamma * OI"""
        return self._calculate_gamma(calls, puts)
    
    def _calculate_vex(self, calls: List, puts: List) -> float:
        """Vega exposure = net vega"""
        return self._calculate_vega(calls, puts)
    
    # ═══════════════════════════════════════════════════════════════════
    # Volatility Spike Protection
    # ═══════════════════════════════════════════════════════════════════
    
    def _check_volatility_spike(self, iv_data: IVPercentileData) -> bool:
        """Check if IV is experiencing a spike"""
        if not iv_data.iv_history or len(iv_data.iv_history) < 20:
            return False
        
        # Compare current IV to recent average
        recent_avg = sum(iv_data.iv_history[-20:]) / 20
        
        spike_multiplier = self.config.volatility_spike_threshold
        return iv_data.current_iv > recent_avg * spike_multiplier
    
    def _generate_spike_warning(self, iv_data: IVPercentileData) -> str:
        """Generate volatility spike warning message"""
        return (
            f"VOLATILITY SPIKE DETECTED: "
            f"IV at {iv_data.current_iv:.1%} vs "
            f"20-day avg {sum(iv_data.iv_history[-20:])/20:.1%}. "
            f"Regime: {iv_data.regime}"
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # Prometheus Export
    # ═══════════════════════════════════════════════════════════════════
    
    def export_to_prometheus(self, greeks: UnifiedGreeks) -> Dict[str, float]:
        """Export all enabled Greeks to Prometheus format"""
        metrics = {}
        
        prefix = f'greek_{greeks.symbol.lower()}'
        
        # Delta
        if self.is_enabled(GreekType.DELTA):
            metrics.update({
                f"{prefix}_delta_net": greeks.delta or 0,
                f"{prefix}_delta_call": greeks.call_delta or 0,
                f"{prefix}_delta_put": greeks.put_delta or 0,
                f"{prefix}_delta_direction_strength": greeks.delta_strength or 0,
                f"{prefix}_prob_itm_call": greeks.prob_itm_call or 0,
                f"{prefix}_prob_itm_put": greeks.prob_itm_put or 0,
            })
        
        # Theta
        if self.is_enabled(GreekType.THETA):
            metrics.update({
                f"{prefix}_theta_net": greeks.theta or 0,
                f"{prefix}_theta_daily": greeks.theta_daily or 0,
            })
        
        # Vega
        if self.is_enabled(GreekType.VEGA):
            metrics.update({
                f"{prefix}_vega_net": greeks.vega or 0,
                f"{prefix}_iv": greeks.iv or 0,
                f"{prefix}_iv_skew": greeks.iv_skew or 0,
            })
        
        # Gamma
        if self.is_enabled(GreekType.GAMMA):
            metrics.update({
                f"{prefix}_gamma_net": greeks.gamma or 0,
            })
        
        # Rho
        if self.is_enabled(GreekType.RHO):
            metrics.update({
                f"{prefix}_rho_net": greeks.rho or 0,
            })
        
        # GEX/VEX
        if self.is_enabled(GreekType.GEX):
            metrics[f"{prefix}_gex"] = greeks.gex or 0
        
        if self.is_enabled(GreekType.VEX):
            metrics[f"{prefix}_vex"] = greeks.vex or 0
        
        # Spike warning as metric
        if greeks.volatility_spike:
            metrics[f"{prefix}_volatility_spike"] = 1
        else:
            metrics[f"{prefix}_volatility_spike"] = 0
        
        return metrics


# ============================================================================
# Factory Functions
# ============================================================================

def create_greeks_engine(
    include_delta: bool = True,
    include_theta: bool = True,
    include_vega: bool = True,
    include_gamma: bool = True,
    include_rho: bool = False,
    track_iv_percentiles: bool = True,
    enable_spike_protection: bool = True,
) -> GreeksEngine:
    """Factory to create configured Greeks engine"""
    
    enabled = set()
    if include_delta:
        enabled.add(GreekType.DELTA)
    if include_theta:
        enabled.add(GreekType.THETA)
    if include_vega:
        enabled.add(GreekType.VEGA)
    if include_gamma:
        enabled.add(GreekType.GAMMA)
    if include_rho:
        enabled.add(GreekType.RHO)
    enabled.add(GreekType.GEX)
    enabled.add(GreekType.VEX)
    
    config = GreeksConfig(
        enabled_greeks=enabled,
        track_iv_percentiles=track_iv_percentiles,
        enable_spike_protection=enable_spike_protection,
    )
    
    return GreeksEngine(config)


# ============================================================================
# Utility for Settings Dashboard
# ============================================================================

GREEK_LABELS = {
    GreekType.DELTA: "Delta (Direction)",
    GreekType.THETA: "Theta (Time Decay)",
    GreekType.VEGA: "Vega (Volatility)",
    GreekType.GAMMA: "Gamma (Delta Accel)",
    GreekType.RHO: "Rho (Interest Rate)",
    GreekType.GEX: "GEX (Gamma Exposure)",
    GreekType.VEX: "VEX (Vega Exposure)",
}

GREEK_DESCRIPTIONS = {
    GreekType.DELTA: "Sensitivity to underlying price changes",
    GreekType.THETA: "Daily time decay value erosion",
    GreekType.VEGA: "Implied volatility sensitivity",
    GreekType.GAMMA: "Rate of delta change",
    GreekType.RHO: "Interest rate sensitivity",
    GreekType.GEX: "Aggregate gamma exposure",
    GreekType.VEX: "Aggregate vega exposure",
}