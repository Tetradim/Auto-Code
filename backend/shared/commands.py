"""Shared Command & Event Schema - Pulse ↔ Sentinel Edge"""
from datetime import datetime
from enum import Enum
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field


class CommandType(str, Enum):
    # === Pulse → Edge (Feedback Loop) ===
    ORDER_FILLED = "ORDER_FILLED"
    POSITION_UPDATE = "POSITION_UPDATE"
    ACCOUNT_UPDATE = "ACCOUNT_UPDATE"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    PULSE_STATUS = "PULSE_STATUS"          # Pulse heartbeat/status
    BROKER_STATUS = "BROKER_STATUS"        # Broker connectivity update
    AUTO_STOP_TRIGGERED = "AUTO_STOP_TRIGGERED"  # Auto-stop fired

    # === Edge → Pulse (Signals) ===
    SIGNAL_UPDATE = "SIGNAL_UPDATE"
    CORRELATION_ALERT = "CORRELATION_ALERT"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"
    BRACKET_CONFIG = "BRACKET_CONFIG"     # Configure bracket trading
    TRAILING_CONFIG = "TRAILING_CONFIG"    # Configure trailing stop
    PARTIAL_FILL_CONFIG = "PARTIAL_FILL_CONFIG"  # Scale in/out config


class BaseCommand(BaseModel):
    command_type: CommandType
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== Pulse → Edge Commands ====================


class OrderFilledCommand(BaseCommand):
    command_type: Literal[CommandType.ORDER_FILLED]
    order_id: str
    fill_price: float
    quantity: float
    side: Literal["BUY", "SELL"]
    pnl_realized: Optional[float] = 0.0
    fees: Optional[float] = 0.0
    order_type: Optional[str] = "MARKET"  # MARKET, LIMIT, STOP
    trading_mode: Optional[str] = "paper"  # paper or live


class PositionUpdateCommand(BaseCommand):
    command_type: Literal[CommandType.POSITION_UPDATE]
    position_size: float  # positive = long, negative = short, 0 = flat
    entry_price: Optional[float] = None
    current_pnl_pct: float = 0.0
    current_pnl_dollar: float = 0.0
    market_value: Optional[float] = None


class AccountUpdateCommand(BaseCommand):
    command_type: Literal[CommandType.ACCOUNT_UPDATE]
    buying_power: float
    total_equity: float
    day_pnl_pct: float = 0.0
    day_pnl_dollar: float = 0.0


class PulseStatusCommand(BaseCommand):
    """Pulse sends heartbeat/status to Edge."""
    command_type: Literal[CommandType.PULSE_STATUS]
    trading_mode: str = "paper"  # paper or live
    simulate_24_7: bool = False
    market_hours_only: bool = True
    paused: bool = False
    running: bool = False
    market_open: bool = False


class BrokerStatusCommand(BaseCommand):
    """Broker connectivity update from Pulse."""
    command_type: Literal[CommandType.BROKER_STATUS]
    broker_id: str
    connected: bool
    error: Optional[str] = None


class AutoStopTriggeredCommand(BaseCommand):
    """Pulse reports auto-stop was triggered (daily loss, consecutive losses)."""
    command_type: Literal[CommandType.AUTO_STOP_TRIGGERED]
    reason: str  # "daily_loss_exceeded", "consecutive_losses_exceeded"
    limit_value: float
    current_value: float


class AccountUpdateCommand(BaseCommand):
    command_type: Literal[CommandType.ACCOUNT_UPDATE]
    buying_power: float
    total_equity: float
    day_pnl_pct: float = 0.0
    day_pnl_dollar: float = 0.0


class OrderRejectedCommand(BaseCommand):
    command_type: Literal[CommandType.ORDER_REJECTED]
    order_id: str
    reason: str
    exchange_error_code: Optional[str] = None


class OrderCancelledCommand(BaseCommand):
    command_type: Literal[CommandType.ORDER_CANCELLED]
    order_id: str
    reason: Optional[str] = None


# ==================== Edge → Pulse Commands ====================


class SignalUpdateCommand(BaseCommand):
    command_type: Literal[CommandType.SIGNAL_UPDATE]
    signal_score: float
    action: str  # BUY, SELL, HOLD, EMERGENCY_SELL, BRACKET_ONLY, TRAILING_ONLY
    confidence: float = 0.0
    reason: str = ""
    # Extended fields matching Set-Trader's capabilities
    buy_offset: Optional[float] = None  # Buy target offset (e.g., -3.0)
    buy_percent: Optional[bool] = True    # True = %, False = $
    buy_order_type: Optional[str] = "limit"  # limit, market
    sell_offset: Optional[float] = None  # Sell target offset
    sell_percent: Optional[bool] = True
    sell_order_type: Optional[str] = "limit"
    stop_offset: Optional[float] = None  # Stop loss offset
    stop_percent: Optional[bool] = True
    stop_order_type: Optional[str] = "limit"
    trailing_enabled: Optional[bool] = False
    trailing_percent: Optional[float] = 2.0
    trailing_percent_mode: Optional[bool] = True  # True = %, False = $
    trailing_order_type: Optional[str] = "limit"
    opening_bell_enabled: Optional[bool] = False  # Opening Bell Mode
    opening_bell_trail_value: Optional[float] = 1.0
    partial_fills_enabled: Optional[bool] = False
    buy_legs: Optional[List[Dict[str, Any]]] = None  # Partial fill legs
    sell_legs: Optional[List[Dict[str, Any]]] = None


class BracketConfigCommand(BaseCommand):
    """Configure bracket trading parameters for a symbol."""
    command_type: Literal[CommandType.BRACKET_CONFIG]
    buy_offset: float
    buy_percent: bool = True
    buy_order_type: str = "limit"
    sell_offset: float
    sell_percent: bool = True
    sell_order_type: str = "limit"
    stop_offset: float
    stop_percent: bool = True
    stop_order_type: str = "limit"


class TrailingConfigCommand(BaseCommand):
    """Configure trailing stop parameters."""
    command_type: Literal[CommandType.TRAILING_CONFIG]
    enabled: bool = True
    percent: float = 2.0
    percent_mode: bool = True  # True = %, False = $
    order_type: str = "limit"
    lock_at_open: bool = False  # Lock during opening window


class PartialFillConfigCommand(BaseCommand):
    """Configure partial fills (scale in/out)."""
    command_type: Literal[CommandType.PARTIAL_FILL_CONFIG]
    enabled: bool = True
    buy_legs: List[Dict[str, Any]] = []  # [{"alloc_pct": 50, "offset": -3.0, "is_percent": True}]
    sell_legs: List[Dict[str, Any]] = []


class CorrelationAlertCommand(BaseCommand):
    command_type: Literal[CommandType.CORRELATION_ALERT]
    correlated_symbols: List[str]
    cluster_strength: float
    recommended_action: str = "REDUCE_SIZE"


# ==================== Helpers ====================

Command = (
    OrderFilledCommand
    | PositionUpdateCommand
    | AccountUpdateCommand
    | PulseStatusCommand
    | BrokerStatusCommand
    | AutoStopTriggeredCommand
    | OrderRejectedCommand
    | OrderCancelledCommand
    | SignalUpdateCommand
    | BracketConfigCommand
    | TrailingConfigCommand
    | PartialFillConfigCommand
    | CorrelationAlertCommand
)


def command_from_dict(data: dict) -> BaseCommand:
    """Create appropriate command object from MongoDB document."""
    cmd_type = data.get("command_type")

    command_map = {
        # Pulse → Edge
        CommandType.ORDER_FILLED: OrderFilledCommand,
        CommandType.POSITION_UPDATE: PositionUpdateCommand,
        CommandType.ACCOUNT_UPDATE: AccountUpdateCommand,
        CommandType.ORDER_REJECTED: OrderRejectedCommand,
        CommandType.ORDER_CANCELLED: OrderCancelledCommand,
        CommandType.PULSE_STATUS: PulseStatusCommand,
        CommandType.BROKER_STATUS: BrokerStatusCommand,
        CommandType.AUTO_STOP_TRIGGERED: AutoStopTriggeredCommand,
        # Edge → Pulse
        CommandType.SIGNAL_UPDATE: SignalUpdateCommand,
        CommandType.BRACKET_CONFIG: BracketConfigCommand,
        CommandType.TRAILING_CONFIG: TrailingConfigCommand,
        CommandType.PARTIAL_FILL_CONFIG: PartialFillConfigCommand,
        CommandType.CORRELATION_ALERT: CorrelationAlertCommand,
    }

    cls = command_map.get(cmd_type)
    if cls is None:
        raise ValueError(f"Unknown command_type: {cmd_type}")

    return cls(**data)


# MongoDB collection name for commands
COMMANDS_COLLECTION = "commands"