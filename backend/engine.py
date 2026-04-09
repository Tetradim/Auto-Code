"""Decision Engine - Trading Logic"""
import logging
from typing import Dict, Optional
from enum import Enum
from signals import TrendDirection
from metrics import edge_decision_total, edge_consecutive_losses, edge_win_rate

logger = logging.getLogger(__name__)

class Decision(Enum):
    BUY = "buy"
    STOP_BUYING = "stop_buying"
    ENABLE_TRAILING_STOP = "enable_trailing_stop"
    TIGHTEN_TRAILING_STOP = "tighten_trailing_stop"   # auto-tighten on strong move
    TIGHTEN_STOP = "tighten_stop"
    HOLD = "hold"
    EMERGENCY_EXIT = "emergency_exit"

class DecisionEngine:
    """Make trading decisions based on signals and risk management"""
    
    # Risk thresholds
    MAX_CONSECUTIVE_LOSSES = 3
    MAX_DRAWDOWN_PCT = 10.0
    TRAILING_STOP_PROFIT_THRESHOLD = 2.0  # Enable trailing after 2% profit
    
    def __init__(self):
        # Track state per symbol
        self.position_pnl: Dict[str, float] = {}
        self.consecutive_losses: Dict[str, int] = {}
        self.total_trades: Dict[str, int] = {}
        self.winning_trades: Dict[str, int] = {}
        self.peak_equity: Dict[str, float] = {}
        logger.info("Decision Engine initialized")
    
    def decide(
        self,
        symbol: str,
        trend: TrendDirection,
        signal_strength: float,
        pnl: float = 0.0,
        pnl_pct: float = 0.0,
        current_drawdown: float = 0.0,
        has_position: bool = False,
        trailing_enabled: bool = False
    ) -> Decision:
        """
        Make trading decision based on current state
        
        Args:
            symbol: Ticker symbol
            trend: Current trend direction
            signal_strength: Signal strength (-10 to +10)
            pnl: Current P&L in dollars
            pnl_pct: Current P&L percentage
            current_drawdown: Current drawdown percentage
            has_position: Whether we have an active position
            trailing_enabled: Whether trailing stop is already enabled
        
        Returns:
            Decision enum
        """
        
        # Initialize tracking
        if symbol not in self.consecutive_losses:
            self.consecutive_losses[symbol] = 0
            self.total_trades[symbol] = 0
            self.winning_trades[symbol] = 0
            self.peak_equity[symbol] = 0.0
        
        # Update metrics
        edge_consecutive_losses.labels(symbol=symbol).set(self.consecutive_losses[symbol])
        if self.total_trades[symbol] > 0:
            win_rate = (self.winning_trades[symbol] / self.total_trades[symbol]) * 100
            edge_win_rate.labels(symbol=symbol).set(win_rate)
        
        # ═══════════════════════════════════════════════════════════
        # EMERGENCY CONDITIONS
        # ═══════════════════════════════════════════════════════════
        
        # Too many consecutive losses
        if self.consecutive_losses[symbol] >= self.MAX_CONSECUTIVE_LOSSES:
            logger.warning(
                f"⛔ {symbol}: Max consecutive losses reached ({self.consecutive_losses[symbol]})"
            )
            decision = Decision.EMERGENCY_EXIT
            edge_decision_total.labels(symbol=symbol, decision=decision.value).inc()
            return decision
        
        # Excessive drawdown
        if current_drawdown > self.MAX_DRAWDOWN_PCT:
            logger.warning(
                f"⛔ {symbol}: Excessive drawdown ({current_drawdown:.2f}%)"
            )
            decision = Decision.EMERGENCY_EXIT
            edge_decision_total.labels(symbol=symbol, decision=decision.value).inc()
            return decision
        
        # ═══════════════════════════════════════════════════════════
        # POSITION MANAGEMENT
        # ═══════════════════════════════════════════════════════════
        
        if has_position:
            # Strong move while already trailing — auto-tighten to 0.5 %
            if (
                trailing_enabled
                and signal_strength >= 7.0
                and pnl_pct > 5.0
            ):
                logger.info(
                    f"🎯 {symbol}: Strong move + profit >{pnl_pct:.1f}% → tightening trailing stop"
                )
                decision = Decision.TIGHTEN_TRAILING_STOP
                edge_decision_total.labels(symbol=symbol, decision=decision.value).inc()
                return decision

            # Already in profit - enable trailing stop
            if pnl_pct > self.TRAILING_STOP_PROFIT_THRESHOLD and not trailing_enabled:
                logger.info(
                    f"✅ {symbol}: Profit threshold reached ({pnl_pct:.2f}%), enabling trailing stop"
                )
                decision = Decision.ENABLE_TRAILING_STOP
                edge_decision_total.labels(symbol=symbol, decision=decision.value).inc()
                return decision
            
            # Trend reversing - tighten stops
            if trend == TrendDirection.BEARISH and signal_strength < -3.0:
                logger.warning(
                    f"⚠️ {symbol}: Bearish reversal detected (strength: {signal_strength:.2f})"
                )
                decision = Decision.TIGHTEN_STOP
                edge_decision_total.labels(symbol=symbol, decision=decision.value).inc()
                return decision
        
        # ═══════════════════════════════════════════════════════════
        # ENTRY/EXIT LOGIC
        # ═══════════════════════════════════════════════════════════
        
        if trend == TrendDirection.BULLISH:
            if signal_strength >= 5.0:
                # Strong bullish signal - buy
                logger.info(
                    f"🚀 {symbol}: Strong bullish signal (strength: {signal_strength:.2f}) - BUY"
                )
                decision = Decision.BUY
            elif signal_strength >= 3.0:
                # Moderate bullish - buy if not too risky
                if self.consecutive_losses[symbol] < 2:
                    decision = Decision.BUY
                else:
                    decision = Decision.HOLD
            else:
                decision = Decision.HOLD
        
        elif trend == TrendDirection.BEARISH:
            if signal_strength <= -5.0:
                # Strong bearish - stop buying
                logger.warning(
                    f"🔻 {symbol}: Strong bearish signal (strength: {signal_strength:.2f}) - STOP BUYING"
                )
                decision = Decision.STOP_BUYING
            elif signal_strength <= -3.0:
                # Moderate bearish
                decision = Decision.STOP_BUYING if has_position else Decision.HOLD
            else:
                decision = Decision.HOLD
        
        else:
            # Neutral trend
            decision = Decision.HOLD
        
        # Record decision
        edge_decision_total.labels(symbol=symbol, decision=decision.value).inc()
        
        return decision
    
    def record_trade_result(self, symbol: str, profit: float):
        """Record trade result for tracking"""
        if symbol not in self.total_trades:
            self.total_trades[symbol] = 0
            self.winning_trades[symbol] = 0
            self.consecutive_losses[symbol] = 0
        
        self.total_trades[symbol] += 1
        
        if profit > 0:
            self.winning_trades[symbol] += 1
            self.consecutive_losses[symbol] = 0
            logger.info(f"✅ {symbol}: Winning trade (+${profit:.2f})")
        else:
            self.consecutive_losses[symbol] += 1
            logger.warning(
                f"❌ {symbol}: Losing trade (-${abs(profit):.2f}) "
                f"[Streak: {self.consecutive_losses[symbol]}]"
            )
        
        # Update metrics
        edge_consecutive_losses.labels(symbol=symbol).set(self.consecutive_losses[symbol])
        win_rate = (self.winning_trades[symbol] / self.total_trades[symbol]) * 100
        edge_win_rate.labels(symbol=symbol).set(win_rate)
