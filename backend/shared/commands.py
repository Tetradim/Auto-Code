"""Shared command/event types for Pulse ↔ Edge communication.

This module defines the contract for messages sent over the shared Command Bus
via MongoDB Change Streams. This enables Pulse to report fills and position
updates back to Edge, closing the feedback loop.

Usage:
    from shared.commands import (
        CommandType, OrderFilledCommand, PositionUpdateCommand,
        AccountUpdateCommand, OrderRejectedCommand
    )
    
    # Create a command
    cmd = OrderFilledCommand(
        order_id="se-order-123",
        symbol="BTCUSDT",
        fill_price=42000.0,
        quantity=0.1,
        side="BUY",
        pnl_realized=50.0
    )
    
    # Serialize for MongoDB
    doc = cmd.model_dump()
"""
from enum import Enum
from datetime import datetime, timezone
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field


class CommandType(str, Enum):
    """Command types for Pulse ↔ Edge communication."""
    
    # Pulse → Edge (these are the new ones enabling feedback loop)
    ORDER_FILLED = "ORDER_FILLED"
    POSITION_UPDATE = "POSITION_UPDATE"
    ACCOUNT_UPDATE = "ACCOUNT_UPDATE"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    
    # Edge → Pulse (already exist, formalizing for consistency)
    SIGNAL_UPDATE = "SIGNAL_UPDATE"
    CORRELATION_ALERT = "CORRELATION_ALERT"
    DECISION_UPDATE = "DECISION_UPDATE"


class BaseCommand(BaseModel):
    """Base command schema with common fields."""
    command_type: CommandType
    symbol: str = Field(..., description="Trading symbol, e.g., BTCUSDT")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    class Config:
        use_enum_values = True


class OrderFilledCommand(BaseCommand):
    """Pulse reports that an order was filled.
    
    This is the key command that closes the PnL feedback loop.
    When Edge receives this, it can update position state and
    calculate realized PnL.
    """
    command_type: Literal[CommandType.ORDER_FILLED] = CommandType.ORDER_FILLED
    order_id: str = Field(..., description="Exchange order ID")
    fill_price: float = Field(..., description="Actual fill price")
    quantity: float = Field(..., description="Filled quantity")
    side: Literal["BUY", "SELL"] = Field(..., description="Order side")
    pnl_realized: Optional[float] = Field(None, description="Realized PnL in quote currency")
    commission: Optional[float] = Field(None, description="Commission paid")
    exchange_order_id: Optional[str] = Field(None, description="Exchange's order ID")


class PositionUpdateCommand(BaseCommand):
    """Pulse reports current position state.
    
    Edge uses this to track open positions and calculate unrealized PnL.
    This enables the risk logic in DecisionEngine to work with real data.
    """
    command_type: Literal[CommandType.POSITION_UPDATE] = CommandType.POSITION_UPDATE
    position_size: float = Field(..., description="Position size (>0 = long, <0 = short)")
    entry_price: Optional[float] = Field(None, description="Average entry price")
    current_pnl_pct: float = Field(default=0.0, description="Unrealized PnL percentage")
    current_pnl_dollar: float = Field(default=0.0, description="Unrealized PnL in dollars")
    leverage: Optional[float] = Field(None, description="Leverage used")
    liquidation_price: Optional[float] = Field(None, description="Liquidation price if applicable")


class AccountUpdateCommand(BaseCommand):
    """Pulse reports account-level updates.
    
    Includes balance changes, margin usage, and overall risk metrics.
    """
    command_type: Literal[CommandType.ACCOUNT_UPDATE] = CommandType.ACCOUNT_UPDATE
    total_equity: float = Field(..., description="Total account equity")
    available_balance: float = Field(..., description="Available balance")
    total_margin_used: float = Field(default=0.0, description="Total margin in use")
    unrealized_pnl: float = Field(default=0.0, description="Total unrealized PnL")
    leverage_avg: Optional[float] = Field(None, description="Average leverage across positions")


class OrderRejectedCommand(BaseCommand):
    """Pulse reports that an order was rejected.
    
    Edge can use this to update its order state and potentially retry.
    """
    command_type: Literal[CommandType.ORDER_REJECTED] = CommandType.ORDER_REJECTED
    order_id: str = Field(..., description="Original order ID")
    reason: str = Field(..., description="Rejection reason")
    exchange_error_code: Optional[str] = Field(None, description="Exchange error code")


class OrderCancelledCommand(BaseCommand):
    """Pulse reports that an order was cancelled."""
    command_type: Literal[CommandType.ORDER_CANCELLED] = CommandType.ORDER_CANCELLED
    order_id: str = Field(..., description="Cancelled order ID")
    reason: Optional[str] = Field(None, description="Cancellation reason")


class SignalUpdateCommand(BaseCommand):
    """Edge sends signal updates to Pulse (already exists, formalizing)."""
    command_type: Literal[CommandType.SIGNAL_UPDATE] = CommandType.SIGNAL_UPDATE
    edge_score: float = Field(..., description="Edge score 0-100")
    decision: Literal["LONG", "SHORT", "HOLD"] = Field(..., description="Trading decision")
    confidence: float = Field(default=0.5, description="Confidence 0-1")
    risk_size: Optional[float] = Field(None, description="Position size if entry")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")


class CorrelationAlertCommand(BaseCommand):
    """Edge sends correlation cluster alerts to Pulse."""
    command_type: Literal[CommandType.CORRELATION_ALERT] = CommandType.CORRELATION_ALERT
    cluster_id: str = Field(..., description="Correlation cluster ID")
    cluster_size: int = Field(..., description="Number of symbols in cluster")
    breadth_score: float = Field(..., description="Market breadth 0-1")
    alert_type: Literal["CLUSTER_FORMED", "CLUSTER_BROKE", "BREADTH_EXTREME"] = Field(...)


# Type alias for any command
Command = (
    OrderFilledCommand
    | PositionUpdateCommand
    | AccountUpdateCommand
    | OrderRejectedCommand
    | OrderCancelledCommand
    | SignalUpdateCommand
    | CorrelationAlertCommand
)


# Helper to create command from dict (for Change Stream processing)
def command_from_dict(data: dict) -> BaseCommand:
    """Create appropriate command object from MongoDB document.
    
    Usage:
        doc = await db.commands.find_one({"command_type": "ORDER_FILLED"})
        cmd = command_from_dict(doc)
    """
    cmd_type = data.get("command_type")
    
    command_map = {
        CommandType.ORDER_FILLED: OrderFilledCommand,
        CommandType.POSITION_UPDATE: PositionUpdateCommand,
        CommandType.ACCOUNT_UPDATE: AccountUpdateCommand,
        CommandType.ORDER_REJECTED: OrderRejectedCommand,
        CommandType.ORDER_CANCELLED: OrderCancelledCommand,
        CommandType.SIGNAL_UPDATE: SignalUpdateCommand,
        CommandType.CORRELATION_ALERT: CorrelationAlertCommand,
    }
    
    cls = command_map.get(cmd_type)
    if cls is None:
        raise ValueError(f"Unknown command_type: {cmd_type}")
    
    return cls(**data)


# MongoDB collection name for commands
COMMANDS_COLLECTION = "commands"