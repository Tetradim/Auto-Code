"""Command serialization helpers for Pulse ↔ Edge communication.

This module provides utility functions for creating, serializing, and
validating commands sent between Sentinel Edge and Sentinel Pulse.

Usage:
    from shared.commands_utils import (
        create_order_filled,
        create_position_update,
        create_signal,
        serialize_command,
    )
    
    # Create an ORDER_FILLED command
    cmd = create_order_filled(
        symbol="NVDA",
        order_id="ord_123",
        fill_price=142.35,
        quantity=50,
        side="BUY",
    )
    
    # Serialize for MongoDB
    doc = serialize_command(cmd)
    await db.commands.insert_one(doc)
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from shared.commands import (
    CommandType,
    OrderFilledCommand,
    PositionUpdateCommand,
    AccountUpdateCommand,
    SignalUpdateCommand,
    CorrelationAlertCommand,
)


logger = logging.getLogger(__name__)


# ==================== Command Builders ====================

def create_order_filled(
    symbol: str,
    order_id: str,
    fill_price: float,
    quantity: float,
    side: str,
    pnl_realized: Optional[float] = None,
    fees: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> OrderFilledCommand:
    """Create an ORDER_FILLED command (Pulse → Edge).
    
    This command is sent when Pulse executes an order at the broker.
    It closes the feedback loop so Edge knows the exact fill price.
    """
    return OrderFilledCommand(
        command_type=CommandType.ORDER_FILLED,
        symbol=symbol.upper(),
        order_id=order_id,
        fill_price=fill_price,
        quantity=quantity,
        side=side.upper(),
        pnl_realized=pnl_realized or 0.0,
        fees=fees or 0.0,
        metadata=metadata or {},
    )


def create_position_update(
    symbol: str,
    position_size: float,
    entry_price: Optional[float] = None,
    current_pnl_pct: float = 0.0,
    current_pnl_dollar: float = 0.0,
    market_value: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> PositionUpdateCommand:
    """Create a POSITION_UPDATE command (Pulse → Edge).
    
    This command syncs real-time position state including unrealized PnL.
    Edge uses this to make risk-aware decisions with actual position data.
    """
    return PositionUpdateCommand(
        command_type=CommandType.POSITION_UPDATE,
        symbol=symbol.upper(),
        position_size=position_size,
        entry_price=entry_price,
        current_pnl_pct=current_pnl_pct,
        current_pnl_dollar=current_pnl_dollar,
        market_value=market_value,
        metadata=metadata or {},
    )


def create_account_update(
    symbol: str,
    buying_power: float,
    total_equity: float,
    day_pnl_pct: float = 0.0,
    day_pnl_dollar: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> AccountUpdateCommand:
    """Create an ACCOUNT_UPDATE command (Pulse → Edge).
    
    This command provides account-level metrics for risk management.
    """
    return AccountUpdateCommand(
        command_type=CommandType.ACCOUNT_UPDATE,
        symbol=symbol.upper(),
        buying_power=buying_power,
        total_equity=total_equity,
        day_pnl_pct=day_pnl_pct,
        day_pnl_dollar=day_pnl_dollar,
        metadata=metadata or {},
    )


def create_signal(
    symbol: str,
    signal_score: float,
    action: str,
    confidence: float = 0.5,
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> SignalUpdateCommand:
    """Create a SIGNAL_UPDATE command (Edge → Pulse).
    
    This is the primary command Edge sends to Pulse to execute trades.
    """
    return SignalUpdateCommand(
        command_type=CommandType.SIGNAL_UPDATE,
        symbol=symbol.upper(),
        signal_score=signal_score,
        action=action.upper(),
        confidence=confidence,
        reason=reason,
        metadata=metadata or {},
    )


def create_correlation_alert(
    correlated_symbols: list[str],
    cluster_strength: float,
    recommended_action: str = "REDUCE_SIZE",
    metadata: Optional[Dict[str, Any]] = None,
) -> CorrelationAlertCommand:
    """Create a CORRELATION_ALERT command (Edge → Pulse).
    
    This alerts Pulse to market-wide risk conditions when many symbols
    are moving together (correlation cluster).
    """
    return CorrelationAlertCommand(
        command_type=CommandType.CORRELATION_ALERT,
        symbol=correlated_symbols[0] if correlated_symbols else "MARKET",
        correlated_symbols=correlated_symbols,
        cluster_strength=cluster_strength,
        recommended_action=recommended_action,
        metadata=metadata or {},
    )


# ==================== Serialization ====================

def serialize_command(cmd: Any) -> Dict[str, Any]:
    """Serialize a command to a MongoDB-compatible dict.
    
    Args:
        cmd: A Pydantic command model
        
    Returns:
        Dict ready for MongoDB insertion
    """
    doc = cmd.model_dump()
    
    # Ensure timestamp is set
    if 'timestamp' not in doc or doc['timestamp'] is None:
        doc['timestamp'] = datetime.now(timezone.utc).isoformat()
    
    # Convert enum values to strings for MongoDB
    if 'command_type' in doc and hasattr(cmd.command_type, 'value'):
        doc['command_type'] = cmd.command_type.value
    
    return doc


def serialize_command_json(cmd: Any) -> str:
    """Serialize a command to JSON string.
    
    Useful for logging or sending over WebSocket.
    """
    return json.dumps(serialize_command(cmd), default=str)


# ==================== Validation ====================

def validate_command(doc: Dict[str, Any]) -> bool:
    """Validate a command document has required fields.
    
    Args:
        doc: Command dict from MongoDB
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['command_type', 'symbol']
    
    for field in required_fields:
        if field not in doc or not doc[field]:
            logger.warning(f"Invalid command: missing '{field}'")
            return False
    
    # Validate command_type is known
    valid_types = [ct.value for ct in CommandType]
    if doc['command_type'] not in valid_types:
        logger.warning(f"Invalid command_type: {doc['command_type']}")
        return False
    
    return True


# ==================== Test Helpers ====================

def create_test_command(
    command_type: str,
    symbol: str = "TEST",
) -> Dict[str, Any]:
    """Create a test command for validation.
    
    Args:
        command_type: Type of command to create
        symbol: Symbol for the command
        
    Returns:
        Command dict ready for insertion
    """
    timestamp = datetime.now(timezone.utc)
    
    if command_type == CommandType.ORDER_FILLED:
        cmd = create_order_filled(
            symbol=symbol,
            order_id=f"test_{timestamp.timestamp()}",
            fill_price=100.0,
            quantity=10,
            side="BUY",
        )
    elif command_type == CommandType.POSITION_UPDATE:
        cmd = create_position_update(
            symbol=symbol,
            position_size=10,
            entry_price=100.0,
            current_pnl_pct=2.5,
            current_pnl_dollar=25.0,
        )
    elif command_type == CommandType.ACCOUNT_UPDATE:
        cmd = create_account_update(
            symbol=symbol,
            buying_power=50000.0,
            total_equity=100000.0,
            day_pnl_pct=1.5,
            day_pnl_dollar=1500.0,
        )
    elif command_type == CommandType.SIGNAL_UPDATE:
        cmd = create_signal(
            symbol=symbol,
            signal_score=7.5,
            action="BUY",
            confidence=0.8,
            reason="Test signal",
        )
    else:
        raise ValueError(f"Unknown command type: {command_type}")
    
    return serialize_command(cmd)