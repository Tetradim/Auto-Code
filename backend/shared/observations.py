"""Observation Models - Pydantic schemas for real-time observations/feedback.

These models validate all observation data flowing through the system:
- WebSocket messages between Edge and Pulse
- MongoDB change stream events
- REST API payloads

Usage:
    # Validate incoming observation
    obs = Observation.from_dict(data)
    
    # Create new observation
    obs = PatternObservation(
        symbol="NVDA",
        source="PULSE",
        pattern_type="ORB_BREAKOUT",
        confidence=0.85,
        timestamp=datetime.utcnow()
    )
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator


class ObservationSource(str, Enum):
    """Who generated this observation"""
    PULSE = "PULSE"           # Execution broker (fills, positions)
    EDGE = "EDGE"             # Signal engine (patterns, signals)
    EXTERNAL = "EXTERNAL"      # Third-party (news, sentiment)
    SYSTEM = "SYSTEM"          # Internal (health, status)


class PatternType(str, Enum):
    """Types of patterns/observations"""
    # Price patterns
    ORB_BREAKOUT = "ORB_BREAKOUT"
    ORB_FAIL = "ORB_FAIL"
    GAP_UP = "GAP_UP"
    GAP_DOWN = "GAP_DOWN"
    VOLUME_SPIKE = "VOLUME_SPIKE"
    
    # Technical patterns  
    RSI_OVERBOUGHT = "RSI_OVERBOUGHT"
    RSI_OVERSOLD = "RSI_OVERSOLD"
    MACD_CROSS = "MACD_CROSS"
    MA_CROSS = "MA_CROSS"
    
    # Execution observations
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    STOP_TRIGGERED = "STOP_TRIGGERED"
    TRAILING_STOP_TRIGGERED = "TRAILING_STOP_TRIGGERED"
    
    # Risk observations
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    CONSECUTIVE_LOSS_LIMIT = "CONSECUTIVE_LOSS_LIMIT"
    CORRELATION_ALERT = "CORRELATION_ALERT"


class BaseObservation(BaseModel):
    """Base observation model with validation"""
    model_config = {"extra": "forbid"}  # Reject unknown fields
    
    id: str = Field(default_factory=lambda: f"obs_{datetime.utcnow().timestamp()}")
    symbol: str = Field(min_length=1, max_length=20)
    source: ObservationSource
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('symbol', mode='before')
    @classmethod
    def uppercase_symbol(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v


class PatternObservation(BaseObservation):
    """Pattern detected by analysis engine"""
    pattern_type: PatternType
    confidence: float = Field(ge=0.0, le=1.0)
    strength: float = Field(ge=0.0, le=1.0, default=0.5)  # How strong the pattern is
    
    # Context
    price_at_observation: Optional[float] = None
    volume_at_observation: Optional[float] = None
    
    # For scoring
    score_impact: float = 0.0  # How this should affect final score (-1 to +1)
    decay_rate: float = 1.0    # How fast observation becomes stale (1.0 = instant, 0.1 = slow)
    
    # Timeframe alignment
    observation_period: str = "1m"  # e.g., "1m", "5m", "1h"
    alignment_multiplier: float = 1.0  # Multiplier based on timeframe match


class ExecutionObservation(BaseObservation):
    """Order execution result from Pulse"""
    observation_type: Literal["ORDER_FILLED", "ORDER_REJECTED", "POSITION_UPDATE"] = "POSITION_UPDATE"
    
    # Execution details
    order_id: Optional[str] = None
    fill_price: Optional[float] = None
    quantity: Optional[float] = None
    side: Optional[Literal["BUY", "SELL"]] = None
    
    # Performance
    slippage: Optional[float] = None  # Actual vs expected price
    execution_latency_ms: Optional[int] = None  # Time from signal to fill
    
    # Position state after execution
    position_size: Optional[float] = None
    avg_entry: Optional[float] = None
    unrealized_pnl: Optional[float] = None


class RiskObservation(BaseObservation):
    """Risk-related observation"""
    observation_type: Literal["DAILY_LOSS_LIMIT", "CONSECUTIVE_LOSS_LIMIT", "CORRELATION_ALERT", "BROKER_DISCONNECT"]
    
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    limit_value: Optional[float] = None  # The limit that triggered (if any)
    current_value: Optional[float] = None  # Current measured value
    
    # For decision engine
    should_pause_trading: bool = False
    should_reduce_exposure: bool = False
    recommended_action: str = "MONITOR"


class HealthObservation(BaseObservation):
    """System health observation"""
    observation_type: Literal["PULSE_HEALTH", "EDGE_HEALTH", "BROKER_HEALTH", "WEBSOCKET_HEALTH"]
    
    healthy: bool
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    
    # Connection state
    connected: bool = True
    reconnect_attempts: int = 0


# ==================== Scoring & Weighting ====================

class ObservationWeights(BaseModel):
    """Weights for how observations affect signal scoring"""
    
    # Source weights (how much we trust each source)
    pulse_weight: float = 1.0      # Default: trust Pulse execution observations
    edge_weight: float = 1.0     # Default: trust Edge pattern observations  
    external_weight: float = 0.5  # Lower: external sources need more validation
    
    # Pattern type weights
    pattern_type_weights: Dict[PatternType, float] = Field(default_factory=dict)
    
    # Confidence multipliers
    min_confidence_threshold: float = 0.3
    high_confidence_multiplier: float = 1.25  # >0.8 confidence gets bonus
    
    # Timeframe alignment
    timeframe_match_bonus: float = 0.2   # Bonus if observation timeframe matches
    timeframe_mismatch_penalty: float = 0.5  # Penalty if mismatch
    
    # Recency weighting
    observation_max_age_seconds: int = 300  # 5 minutes max age
    
    # Desync handling
    max_timeframe_diff_seconds: int = 60  # Max allowed diff between observation time and eval time


# Global default weights
DEFAULT_WEIGHTS = ObservationWeights()


class ObservationScorer:
    """Calculate how much an observation should affect signal scoring"""
    
    def __init__(self, weights: ObservationWeights = DEFAULT_WEIGHTS):
        self.weights = weights
    
    def calculate_impact(
        self,
        observation: BaseObservation,
        eval_timestamp: datetime
    ) -> float:
        """Calculate the impact score for an observation.
        
        Returns:
            Impact value from -1.0 to +1.0
        """
        # Check age (desync protection)
        age_seconds = (eval_timestamp - observation.timestamp).total_seconds()
        if age_seconds > self.weights.observation_max_age_seconds:
            return 0.0  # Too old, no impact
        
        if age_seconds > self.weights.max_timeframe_diff_seconds:
            # Significant desync - reduce impact
            desync_penalty = 1.0 - (age_seconds / self.weights.observation_max_age_seconds)
            return -0.1 * desync_penalty  # Small negative for desync
        
        # Base impact from observation type
        impact = self._get_base_impact(observation)
        
        # Apply confidence multiplier
        if isinstance(observation, PatternObservation):
            if observation.confidence >= 0.8:
                impact *= self.weights.high_confidence_multiplier
        
        # Apply timeframe alignment
        if isinstance(observation, PatternObservation):
            impact *= observation.alignment_multiplier
        
        # Apply source weight
        source_weight = self._get_source_weight(observation.source)
        impact *= source_weight
        
        return max(-1.0, min(1.0, impact))  # Clamp to [-1, 1]
    
    def _get_base_impact(self, obs: BaseObservation) -> float:
        """Get base impact from observation type"""
        if isinstance(obs, PatternObservation):
            return obs.score_impact
        
        if isinstance(obs, ExecutionObservation):
            if obs.observation_type == "ORDER_FILLED":
                return 0.1  # Small positive for execution success
            elif obs.observation_type == "ORDER_REJECTED":
                return -0.2  # Negative for rejection
        
        if isinstance(obs, RiskObservation):
            if obs.risk_level == "CRITICAL":
                return -0.5
            elif obs.risk_level == "HIGH":
                return -0.25
            elif obs.risk_level == "MEDIUM":
                return -0.1
        
        return 0.0
    
    def _get_source_weight(self, source: ObservationSource) -> float:
        """Get weight for observation source"""
        if source == ObservationSource.PULSE:
            return self.weights.pulse_weight
        elif source == ObservationSource.EDGE:
            return self.weights.edge_weight
        elif source == ObservationSource.EXTERNAL:
            return self.weights.external_weight
        return 0.5  # Default for unknown sources
    
    def is_valid_for_scoring(
        self,
        observation: BaseObservation,
        eval_timestamp: datetime
    ) -> bool:
        """Check if observation is valid for scoring (desync check)"""
        age_seconds = (eval_timestamp - observation.timestamp).total_seconds()
        
        return (
            age_seconds >= 0 and  # Not in future
            age_seconds <= self.weights.observation_max_age_seconds and  # Not too old
            age_seconds <= self.weights.max_timeframe_diff_seconds + 30  # Allow some buffer
        )


# ==================== Validation & Serialization ====================

def validate_observation(data: Dict[str, Any]) -> BaseObservation:
    """Validate and return appropriate observation type.
    
    Args:
        data: Raw observation dict from WS/API/MongoDB
        
    Returns:
        Validated observation object (PatternObservation, ExecutionObservation, etc.)
        
    Raises:
        ValidationError: If data doesn't match any observation schema
    """
    # Try to determine observation type from data
    obs_type = data.get("observation_type") or data.get("pattern_type")
    
    # Attempt to parse as PatternObservation
    if obs_type in [p.value for p in PatternType]:
        return PatternObservation(**data)
    
    # Try ExecutionObservation
    if obs_type in ["ORDER_FILLED", "ORDER_REJECTED", "POSITION_UPDATE"]:
        return ExecutionObservation(**data)
    
    # Try RiskObservation
    if obs_type in ["DAILY_LOSS_LIMIT", "CONSECUTIVE_LOSS_LIMIT", "CORRELATION_ALERT", "BROKER_DISCONNECT"]:
        return RiskObservation(**data)
    
    # Try HealthObservation  
    if obs_type in ["PULSE_HEALTH", "EDGE_HEALTH", "BROKER_HEALTH", "WEBSOCKET_HEALTH"]:
        return HealthObservation(**data)
    
    # Default: try as BaseObservation (will fail if missing required fields)
    return BaseObservation(**data)


def serialize_observation(obs: BaseObservation) -> Dict[str, Any]:
    """Serialize observation for MongoDB/WebSocket transmission"""
    return obs.model_dump(mode='json')


# ==================== Desync Detection ====================

class ObservationDesyncMonitor:
    """Monitor for observation desync between Edge and Pulse"""
    
    def __init__(self, max_drift_seconds: int = 120):
        self.max_drift_seconds = max_drift_seconds
        self.last_observation_times: Dict[str, datetime] = {}
        self.desync_count = 0
    
    def check_desync(
        self,
        symbol: str,
        observation_time: datetime,
        current_time: datetime
    ) -> Optional[str]:
        """Check if there's a desync for this symbol.
        
        Returns:
            None if no desync, str describing the desync if detected
        """
        drift = (current_time - observation_time).total_seconds()
        
        if abs(drift) > self.max_drift_seconds:
            self.desync_count += 1
            return f"Desync detected: {drift:.0f}s drift for {symbol}"
        
        # Update last observation time
        if observation_time > self.last_observation_times.get(symbol, datetime.min):
            self.last_observation_times[symbol] = observation_time
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get desync monitor status"""
        return {
            "desync_count": self.desync_count,
            "last_observations": {
                sym: ts.isoformat() 
                for sym, ts in self.last_observation_times.items()
            },
            "max_drift_seconds": self.max_drift_seconds
        }


# ==================== Global Instances ====================

# Scorer instance for use throughout the system
observation_scorer = ObservationScorer()

# Desync monitor
desync_monitor = ObservationDesyncMonitor()


# ==================== Pattern Detection Integration ====================

def generate_pattern_observation(
    symbol: str,
    patterns: List[Dict[str, Any]],
    source: str = "PULSE_BROKER"
) -> Dict[str, Any]:
    """Generate Edge-ready observation payload from pattern detection.
    
    This is the bridge between Pulse's ChartPatternDetector and Edge's
    observation system. Use this to send patterns to Edge for confidence boost.
    
    Args:
        symbol: Trading symbol
        patterns: List of pattern dicts from ChartPatternDetector
        source: Source identifier ("PULSE_BROKER", "EDGE_ANALYST", etc.)
        
    Returns:
        Ready-to-send payload for WebSocket/MongoDB
    """
    return {
        "type": "observation",
        "subtype": "pattern",
        "source": source,
        "symbol": symbol.upper(),
        "patterns": patterns,
        "timestamp": datetime.utcnow().isoformat(),
        "confidence_boost": _calculate_pattern_boost(patterns)
    }


def _calculate_pattern_boost(patterns: List[Dict]) -> float:
    """Calculate confidence boost from patterns.
    
    Args:
        patterns: List of pattern dicts with confidence scores
        
    Returns:
        Boost value from 0.0 to 1.0
    """
    if not patterns:
        return 0.0
    
    # Weight by confidence and strength
    total_boost = 0.0
    for p in patterns:
        conf = p.get("confidence", 0.5)
        strength = p.get("strength", "moderate")
        
        # Strong patterns get more weight
        strength_mult = 1.25 if strength == "strong" else 1.0
        
        total_boost += conf * strength_mult
    
    # Average and cap at 1.0
    return min(1.0, total_boost / len(patterns))


def create_pattern_observation_from_result(
    symbol: str,
    pattern_results: List["PatternResult"],  # Forward reference
    source: str = "EDGE_ANALYST"
) -> PatternObservation:
    """Create a PatternObservation from SignalEngineEnhanced results.
    
    Args:
        symbol: Trading symbol
        pattern_results: List of PatternResult from signals_enhanced.py
        source: Source identifier
        
    Returns:
        PatternObservation ready for Edge scoring
    """
    from signals_enhanced import TrendDirection
    
    # Get strongest pattern
    if not pattern_results:
        raise ValueError("No patterns to convert")
    
    strongest = max(pattern_results, key=lambda p: p.confidence)
    
    # Map TrendDirection to our ObservationSource
    direction_map = {
        TrendDirection.BULLISH: "bullish",
        TrendDirection.BEARISH: "bearish",
        TrendDirection.NEUTRAL: "neutral"
    }
    
    return PatternObservation(
        symbol=symbol,
        source=ObservationSource(source),
        pattern_type=PatternType(strongest.pattern_type.value),
        confidence=strongest.confidence,
        strength=strongest.strength,
        score_impact=_pattern_to_impact(strongest),
        metadata=strongest.metadata
    )


def _pattern_to_impact(result: "PatternResult") -> float:
    """Convert pattern result to impact score (-1 to +1)"""
    from signals_enhanced import TrendDirection
    
    base = result.confidence * result.strength / 100
    
    if result.direction == TrendDirection.BULLISH:
        return min(1.0, base)
    elif result.direction == TrendDirection.BEARISH:
        return max(-1.0, -base)
    return 0.0