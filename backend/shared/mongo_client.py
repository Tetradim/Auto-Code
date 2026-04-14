"""Shared MongoDB Command Client - Used by both Pulse and Edge.

This module provides a lightweight client for sending commands via MongoDB
Change Streams. It can be used by:
- Pulse: To send ORDER_FILLED, POSITION_UPDATE to Edge
- Edge: To send SIGNAL_UPDATE, BRACKET_CONFIG to Pulse (via HTTP, not Mongo)

The primary communication path is:
- Pulse → Edge: MongoDB Change Streams (this client inserts commands)
- Edge → Pulse: REST API (pulse_client.py calls Pulse directly)

Usage in Pulse:
    from shared.mongo_client import SentinelMongoClient
    
    edge_client = SentinelMongoClient(db)
    await edge_client.notify_order_filled(
        symbol="NVDA",
        order_id="ord_123",
        fill_price=142.35,
        quantity=50,
        side="BUY"
    )
"""
import logging
from datetime import datetime
from typing import Literal, Optional, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorDatabase


logger = logging.getLogger(__name__)


class SentinelMongoClient:
    """Lightweight client for Pulse ↔ Edge communication via MongoDB Change Streams.
    
    This client is primarily used by Pulse to send feedback to Edge.
    Edge typically uses REST API (pulse_client.py) to send commands to Pulse.
    """
    
    # Collection name for shared commands
    COMMANDS_COLLECTION = "commands"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with MongoDB database instance.
        
        Args:
            db: AsyncIOMotorDatabase instance (from deps.db or similar)
        """
        self.db = db
        self.commands_collection = db[self.COMMANDS_COLLECTION]
        
        # Create indexes for efficient querying
        self._ensure_indexes()
        
        logger.info(f"SentinelMongoClient initialized with collection: {self.COMMANDS_COLLECTION}")
    
    def _ensure_indexes(self):
        """Create indexes for efficient command processing."""
        try:
            # Index on command_type for filtering
            self.commands_collection.create_index("command_type")
            # Index on symbol for per-ticker commands
            self.commands_collection.create_index("symbol")
            # Index on timestamp for time-based queries
            self.commands_collection.create_index("timestamp")
        except Exception as e:
            logger.debug(f"Index creation: {e}")
    
    # ==================== Core Methods ====================
    
    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send any command to the other service via MongoDB Change Stream.
        
        Args:
            command: Command dict with at least 'command_type' and 'symbol'
            
        Returns:
            True if inserted successfully, False otherwise
        """
        try:
            # Add timestamp if not present
            if "timestamp" not in command:
                command["timestamp"] = datetime.utcnow()
            
            # Ensure symbol is uppercase
            if "symbol" in command and command["symbol"]:
                command["symbol"] = command["symbol"].upper()
            
            result = await self.commands_collection.insert_one(command)
            
            logger.info(
                f"📤 Sent command to Edge: {command.get('command_type')} | "
                f"{command.get('symbol')} | order_id={command.get('order_id', 'N/A')}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send command to Edge: {e}")
            return False
    
    async def send_command_batch(self, commands: List[Dict[str, Any]]) -> int:
        """Send multiple commands in a single batch operation.
        
        Args:
            commands: List of command dicts
            
        Returns:
            Number of commands successfully inserted
        """
        if not commands:
            return 0
            
        try:
            # Add timestamps to all commands
            now = datetime.utcnow()
            for cmd in commands:
                if "timestamp" not in cmd:
                    cmd["timestamp"] = now
                if "symbol" in cmd and cmd["symbol"]:
                    cmd["symbol"] = cmd["symbol"].upper()
            
            result = await self.commands_collection.insert_many(commands)
            logger.info(f"📤 Sent batch of {len(result.inserted_ids)} commands to Edge")
            return len(result.inserted_ids)
            
        except Exception as e:
            logger.error(f"Failed to send command batch: {e}")
            return 0
    
    # ==================== Pulse → Edge Commands ====================
    
    async def notify_order_filled(
        self,
        symbol: str,
        order_id: str,
        fill_price: float,
        quantity: float,
        side: Literal["BUY", "SELL"],
        pnl_realized: Optional[float] = None,
        fees: Optional[float] = 0.0,
        order_type: str = "MARKET",
        trading_mode: str = "paper",
        metadata: Optional[Dict] = None
    ) -> bool:
        """Notify Edge that an order was filled.
        
        This is the key command that closes the feedback loop - Edge
        uses this to update position state and calculate realized PnL.
        
        Args:
            symbol: Trading symbol (e.g., "NVDA", "AAPL")
            order_id: Exchange order ID
            fill_price: Actual fill price
            quantity: Filled quantity
            side: Order side ("BUY" or "SELL")
            pnl_realized: Realized PnL (for SELL orders)
            fees: Commission/fees paid
            order_type: Order type ("MARKET", "LIMIT", "STOP")
            trading_mode: "paper" or "live"
            metadata: Additional context
            
        Returns:
            True if command sent successfully
        """
        command = {
            "command_type": "ORDER_FILLED",
            "symbol": symbol.upper(),
            "order_id": order_id,
            "fill_price": fill_price,
            "quantity": quantity,
            "side": side.upper(),
            "pnl_realized": pnl_realized,
            "fees": fees,
            "order_type": order_type,
            "trading_mode": trading_mode,
            "metadata": metadata or {}
        }
        return await self.send_command(command)
    
    async def update_position(
        self,
        symbol: str,
        position_size: float,
        entry_price: Optional[float] = None,
        current_pnl_pct: float = 0.0,
        current_pnl_dollar: float = 0.0,
        market_value: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Send real-time position update to Edge.
        
        Edge uses this to track open positions and calculate unrealized PnL.
        
        Args:
            symbol: Trading symbol
            position_size: Current position size (positive=long, negative=short, 0=flat)
            entry_price: Average entry price
            current_pnl_pct: Unrealized PnL percentage
            current_pnl_dollar: Unrealized PnL in dollars
            market_value: Current market value of position
            metadata: Additional context
            
        Returns:
            True if command sent successfully
        """
        command = {
            "command_type": "POSITION_UPDATE",
            "symbol": symbol.upper(),
            "position_size": position_size,
            "entry_price": entry_price,
            "current_pnl_pct": current_pnl_pct,
            "current_pnl_dollar": current_pnl_dollar,
            "market_value": market_value,
            "metadata": metadata or {}
        }
        return await self.send_command(command)
    
    async def update_account(
        self,
        symbol: str,
        buying_power: float,
        total_equity: float,
        day_pnl_pct: float = 0.0,
        day_pnl_dollar: float = 0.0,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Send account-level updates to Edge.
        
        Args:
            symbol: Usually "ACCOUNT" for account-wide updates
            buying_power: Available buying power
            total_equity: Total account equity
            day_pnl_pct: Day's PnL percentage
            day_pnl_dollar: Day's PnL in dollars
            metadata: Additional context
            
        Returns:
            True if command sent successfully
        """
        command = {
            "command_type": "ACCOUNT_UPDATE",
            "symbol": symbol.upper(),
            "buying_power": buying_power,
            "total_equity": total_equity,
            "day_pnl_pct": day_pnl_pct,
            "day_pnl_dollar": day_pnl_dollar,
            "metadata": metadata or {}
        }
        return await self.send_command(command)
    
    async def notify_order_rejected(
        self,
        symbol: str,
        order_id: str,
        reason: str,
        exchange_error_code: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Notify Edge that an order was rejected.
        
        Args:
            symbol: Trading symbol
            order_id: Original order ID
            reason: Rejection reason
            exchange_error_code: Exchange error code if available
            metadata: Additional context
            
        Returns:
            True if command sent successfully
        """
        command = {
            "command_type": "ORDER_REJECTED",
            "symbol": symbol.upper(),
            "order_id": order_id,
            "reason": reason,
            "exchange_error_code": exchange_error_code,
            "metadata": metadata or {}
        }
        return await self.send_command(command)
    
    async def notify_order_cancelled(
        self,
        symbol: str,
        order_id: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Notify Edge that an order was cancelled.
        
        Args:
            symbol: Trading symbol
            order_id: Cancelled order ID
            reason: Cancellation reason
            metadata: Additional context
            
        Returns:
            True if command sent successfully
        """
        command = {
            "command_type": "ORDER_CANCELLED",
            "symbol": symbol.upper(),
            "order_id": order_id,
            "reason": reason,
            "metadata": metadata or {}
        }
        return await self.send_command(command)
    
    # ==================== Status & Heartbeat Commands ====================
    
    async def send_pulse_status(
        self,
        trading_mode: str = "paper",
        simulate_24_7: bool = False,
        market_hours_only: bool = True,
        paused: bool = False,
        running: bool = False,
        market_open: bool = False,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Send Pulse status/heartbeat to Edge.
        
        Args:
            trading_mode: "paper" or "live"
            simulate_24_7: Whether running in 24/7 simulation mode
            market_hours_only: Whether restricted to market hours
            paused: Whether trading is paused
            running: Whether engine is running
            market_open: Whether market is currently open
            metadata: Additional context
            
        Returns:
            True if command sent successfully
        """
        command = {
            "command_type": "PULSE_STATUS",
            "symbol": "SYSTEM",
            "trading_mode": trading_mode,
            "simulate_24_7": simulate_24_7,
            "market_hours_only": market_hours_only,
            "paused": paused,
            "running": running,
            "market_open": market_open,
            "metadata": metadata or {}
        }
        return await self.send_command(command)
    
    async def notify_broker_status(
        self,
        broker_id: str,
        connected: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Send broker connectivity update to Edge.
        
        Args:
            broker_id: Broker identifier
            connected: Whether broker is connected
            error: Error message if not connected
            metadata: Additional context
            
        Returns:
            True if command sent successfully
        """
        command = {
            "command_type": "BROKER_STATUS",
            "symbol": "SYSTEM",
            "broker_id": broker_id,
            "connected": connected,
            "error": error,
            "metadata": metadata or {}
        }
        return await self.send_command(command)
    
    async def notify_auto_stop(
        self,
        symbol: str,
        reason: str,
        limit_value: float,
        current_value: float,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Notify Edge that auto-stop was triggered.
        
        Args:
            symbol: Symbol where auto-stop triggered (or "ACCOUNT" for account-level)
            reason: "daily_loss_exceeded" or "consecutive_losses_exceeded"
            limit_value: The limit that was exceeded
            current_value: Current value (e.g., current daily loss)
            metadata: Additional context
            
        Returns:
            True if command sent successfully
        """
        command = {
            "command_type": "AUTO_STOP_TRIGGERED",
            "symbol": symbol.upper(),
            "reason": reason,
            "limit_value": limit_value,
            "current_value": current_value,
            "metadata": metadata or {}
        }
        return await self.send_command(command)
    
    # ==================== Query Methods ====================
    
    async def get_recent_commands(
        self,
        command_type: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent commands from the collection.
        
        Useful for debugging and replay.
        
        Args:
            command_type: Filter by command type
            symbol: Filter by symbol
            limit: Maximum number of commands to return
            
        Returns:
            List of command documents
        """
        query = {}
        if command_type:
            query["command_type"] = command_type
        if symbol:
            query["symbol"] = symbol.upper()
        
        cursor = self.commands_collection.find(query).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(limit)
    
    async def clear_commands(
        self,
        older_than_hours: Optional[int] = None
    ) -> int:
        """Clear old commands from the collection.
        
        Args:
            older_than_hours: Only clear commands older than this many hours.
                             If None, clears all commands.
                             
        Returns:
            Number of commands deleted
        """
        query = {}
        if older_than_hours:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
            query["timestamp"] = {"$lt": cutoff}
        
        result = await self.commands_collection.delete_many(query)
        logger.info(f"Cleared {result.deleted_count} commands from collection")
        return result.deleted_count


# ==================== Convenience Factory ====================

async def create_client_from_config(config: Dict[str, Any]) -> SentinelMongoClient:
    """Create a SentinelMongoClient from configuration.
    
    This is useful when configuring the client from environment
    variables or a config file.
    
    Args:
        config: Dict with 'mongo_url', 'db_name', etc.
        
    Returns:
        Initialized SentinelMongoClient
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    
    mongo_url = config.get("mongo_url", "mongodb://localhost:27017")
    db_name = config.get("db_name", "sentinel_edge")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    return SentinelMongoClient(db)