"""Pulse Communication Service - High-level interface for Edge ↔ Pulse communication.

This module provides a unified service layer that abstracts the details of
communication with Sentinel Pulse, whether via REST API, WebSocket, or MongoDB.

Usage:
    from services.pulse_service import PulseService
    
    pulse_service = PulseService(pulse_client=pulse_client, decision_engine=decisions)
    
    # Send a buy signal
    await pulse_service.send_buy_signal("NVDA", 8.5, 0.8, "Strong momentum + ORB breakout")
    
    # Get real position from Pulse
    position = await pulse_service.get_real_position("NVDA")
    
    # Handle correlation alert
    await pulse_service.send_correlation_warning(cluster_id, symbols, 0.9)
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from engine import DecisionEngine
from pulse_client import PulseClient
from shared.commands import (
    SignalUpdateCommand,
    CorrelationAlertCommand,
    OrderFilledCommand,
    PositionUpdateCommand,
)


logger = logging.getLogger(__name__)


class PulseService:
    """High-level service for Edge ↔ Pulse communication.
    
    This service provides:
    - Clean methods for sending signals to Pulse
    - Position state synchronization from Pulse
    - Correlation alert handling
    - Emergency exit handling
    - Health monitoring
    """
    
    def __init__(
        self,
        pulse_client: PulseClient,
        decision_engine: Optional[DecisionEngine] = None,
    ):
        self.pulse = pulse_client
        self.decisions = decision_engine
        
        logger.info("PulseService initialized")
    
    # ====================== SIGNAL SENDING ======================
    
    async def send_buy_signal(
        self,
        symbol: str,
        signal_score: float,
        confidence: float,
        reason: str,
        risk_size: float = 0.1,
        stop_loss: Optional[float] = None,
    ) -> bool:
        """Send a BUY signal to Pulse.
        
        Args:
            symbol: Trading symbol
            signal_score: Signal strength (0-10)
            confidence: Confidence level (0.0-1.0)
            reason: Human-readable reason
            risk_size: Position size (fraction of portfolio)
            stop_loss: Optional stop loss price
            
        Returns:
            True if signal sent successfully
        """
        return await self.pulse.send_signal(
            symbol=symbol,
            signal_score=signal_score,
            action="BUY",
            confidence=confidence,
            reason=reason,
            risk_size=risk_size,
            stop_loss=stop_loss or 0.0,
        )
    
    async def send_sell_signal(
        self,
        symbol: str,
        signal_score: float,
        confidence: float,
        reason: str,
        take_profit: Optional[float] = None,
    ) -> bool:
        """Send a SELL signal to Pulse (exit or reduce position).
        
        Args:
            symbol: Trading symbol
            signal_score: Signal strength (-10 to 0)
            confidence: Confidence level (0.0-1.0)
            reason: Human-readable reason
            take_profit: Optional take profit price
            
        Returns:
            True if signal sent successfully
        """
        return await self.pulse.send_signal(
            symbol=symbol,
            signal_score=signal_score,
            action="SELL",
            confidence=confidence,
            reason=reason,
            risk_size=0.0,
            stop_loss=take_profit or 0.0,
        )
    
    async def send_hold_signal(
        self,
        symbol: str,
        signal_score: float,
        reason: str,
    ) -> bool:
        """Send a HOLD signal (no action but logged).
        
        This is useful for observability - Pulse knows Edge is
        actively monitoring but chose not to act.
        """
        return await self.pulse.send_signal(
            symbol=symbol,
            signal_score=signal_score,
            action="HOLD",
            confidence=0.5,
            reason=reason,
        )
    
    # ====================== RISK MANAGEMENT ======================
    
    async def emergency_exit(
        self,
        symbol: str,
        reason: str = "",
    ) -> bool:
        """Send emergency exit command to Pulse.
        
        Use this when risk parameters are breached and position
        must be closed immediately.
        """
        logger.critical(f"🚨 Emergency exit requested: {symbol} | {reason}")
        return await self.pulse.send_emergency_exit(symbol, reason)
    
    async def enable_trailing_stop(
        self,
        symbol: str,
        trailing_percent: float = 1.5,
    ) -> bool:
        """Enable trailing stop for existing position."""
        return await self.pulse.enable_trailing_stop(symbol, trailing_percent)
    
    async def stop_buying(
        self,
        symbol: str,
        reason: str = "Consecutive losses threshold",
    ) -> bool:
        """Stop buying for symbol (maintain existing position)."""
        return await self.pulse.stop_buying(symbol)
    
    async def tighten_stop(
        self,
        symbol: str,
        new_stop_percent: float = 0.5,
    ) -> bool:
        """Tighten the stop loss on existing position."""
        return await self.pulse.send_decision(
            symbol,
            "tighten_stop",
            stop_percent=new_stop_percent,
        )
    
    # ====================== POSITION SYNC ======================
    
    async def get_real_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real position state from DecisionEngine (synced from Pulse).
        
        This returns the position data that Edge maintains, which is
        kept in sync via MongoDB Change Streams from Pulse.
        
        Returns:
            Position dict with size, entry_price, pnl_pct, etc. or None
        """
        if self.decisions:
            return self.decisions.get_position(symbol)
        return None
    
    async def sync_position_from_pulse(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Force sync position from Pulse API (bypass cache).
        
        Use this when you need the absolute latest from Pulse rather
        than relying on Change Stream updates.
        
        Returns:
            Position dict or None if unavailable
        """
        return await self.pulse.get_position(symbol)
    
    async def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all positions from DecisionEngine."""
        if self.decisions:
            return self.decisions.get_all_positions()
        return {}
    
    async def get_account_from_pulse(self) -> Optional[Dict[str, Any]]:
        """Get account status directly from Pulse."""
        return await self.pulse.get_account_status()
    
    # ====================== CORRELATION ALERTS ======================
    
    async def send_correlation_warning(
        self,
        cluster_id: str,
        correlated_symbols: List[str],
        cluster_strength: float,
    ) -> bool:
        """Send correlation cluster warning to Pulse.
        
        Called when correlation engine detects:
        - Many symbols moving together (breadth extreme)
        - Cluster formation or breakup
        - Systemic risk conditions
        """
        alert_type = "BREADTH_EXTREME" if cluster_strength > 0.8 else "CLUSTER_FORMED"
        recommended = "REDUCE_SIZE" if cluster_strength > 0.7 else "HOLD"
        
        logger.warning(
            f"Correlation alert: cluster={cluster_id} strength={cluster_strength:.2f} "
            f"symbols={len(correlated_symbols)}"
        )
        
        return await self.pulse.send_correlation_alert(
            cluster_id=cluster_id,
            correlated_symbols=correlated_symbols,
            cluster_strength=cluster_strength,
            alert_type=alert_type,
            recommended_action=recommended,
        )
    
    # ====================== HEALTH & STATUS ======================
    
    async def get_connection_health(self) -> Dict[str, Any]:
        """Get Pulse connection health status."""
        return await self.pulse.health_check_detailed()
    
    async def is_pulse_available(self) -> bool:
        """Check if Pulse is available."""
        return self.pulse.pulse_available
    
    async def get_retry_queue_status(self) -> Dict[str, Any]:
        """Get status of retry queue for failed decisions."""
        return self.pulse.queue_stats()
    
    # ====================== DECISION FORWARDING ======================
    
    async def forward_decision(
        self,
        symbol: str,
        decision: "Decision",  # Forward reference to Decision enum
        signal_score: float,
        reason: str,
    ) -> bool:
        """Forward a Decision enum to Pulse.
        
        This is the main entry point for the scheduler to send
        decisions to Pulse.
        
        Args:
            symbol: Trading symbol
            decision: Decision enum from engine.py
            signal_score: Signal strength
            reason: Human-readable reason
            
        Returns:
            True if decision sent successfully
        """
        from engine import Decision as EngineDecision
        
        if decision == EngineDecision.BUY:
            return await self.send_buy_signal(
                symbol, signal_score, 0.7, reason
            )
        elif decision == EngineDecision.STOP_BUYING:
            return await self.stop_buying(symbol, reason)
        elif decision == EngineDecision.ENABLE_TRAILING_STOP:
            return await self.enable_trailing_stop(symbol)
        elif decision == EngineDecision.TIGHTEN_TRAILING_STOP:
            return await self.enable_trailing_stop(symbol, 0.5)
        elif decision == EngineDecision.TIGHTEN_STOP:
            return await self.tighten_stop(symbol)
        elif decision == EngineDecision.EMERGENCY_EXIT:
            return await self.emergency_exit(symbol, reason)
        else:
            logger.debug(f"HOLD decision for {symbol} - no action needed")
            return True


# Singleton instance - set by server.py during startup
_pulse_service: Optional[PulseService] = None


def get_pulse_service() -> Optional[PulseService]:
    """Get the global PulseService instance."""
    return _pulse_service


def set_pulse_service(service: PulseService) -> None:
    """Set the global PulseService instance."""
    global _pulse_service
    _pulse_service = service
    logger.info("Global PulseService instance set")