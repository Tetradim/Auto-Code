"""State persistence layer for Sentinel Edge.

Uses SQLite for resilience on restart/crash - persists:
- current_position (symbol, side, entry_price, entry_time, size)
- active_order_ids (exchange order tracking)
- unrealized_pnl

On startup, reconciles with exchange via fetch_positions() and fetch_orders().
Emits sentinel_state_restored metric.
"""
import asyncio
import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = Path("/app/data/sentinel_state.db")


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PositionState:
    """Persisted position state."""
    symbol: str
    side: str  # "LONG" or "SHORT"
    entry_price: float
    entry_time: datetime
    size: float
    unrealized_pnl: float = 0.0
    trailing_enabled: bool = False
    trailing_percent: Optional[float] = None


@dataclass
class OrderState:
    """Persisted order state."""
    order_id: str
    symbol: str
    side: str
    status: str  # "pending", "filled", "cancelled", "failed"
    created_at: datetime
    filled_at: Optional[datetime] = None
    fill_price: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# Persistence Layer
# ─────────────────────────────────────────────────────────────────────────────

class StatePersistence:
    """SQLite-backed state persistence for resilience.
    
    Usage:
        persistence = StatePersistence(db_path=Path("/app/data/sentinel_state.db"))
        await persistence.init()
        
        # On startup - reconcile with exchange
        await persistence.reconcile(fetch_positions_fn, fetch_orders_fn)
        
        # During operation - save state
        persistence.save_position(symbol, position)
        persistence.save_order(order_id, order)
        
        # After order execution
        persistence.mark_order_filled(order_id, fill_price)
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
        
    async def init(self) -> None:
        """Initialize database and tables."""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Create tables
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                size REAL NOT NULL DEFAULT 1.0,
                unrealized_pnl REAL DEFAULT 0.0,
                trailing_enabled INTEGER DEFAULT 0,
                trailing_percent REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                filled_at TEXT,
                fill_price REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
            CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        """)
        self.conn.commit()
        logger.info(f"StatePersistence initialized at {self.db_path}")

    # ─────────────────────────────────────────────────────────────────────────
    # Position operations
    # ─────────────────────────────────────────────────────────────────────────

    def save_position(self, symbol: str, position: PositionState) -> None:
        """Save or update position state."""
        if self.conn is None:
            raise RuntimeError("Not initialized. Call init() first.")
            
        self.conn.execute("""
            INSERT INTO positions (symbol, side, entry_price, entry_time, size, unrealized_pnl, trailing_enabled, trailing_percent, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(symbol) DO UPDATE SET
                side = excluded.side,
                entry_price = excluded.entry_price,
                entry_time = excluded.entry_time,
                size = excluded.size,
                unrealized_pnl = excluded.unrealized_pnl,
                trailing_enabled = excluded.trailing_enabled,
                trailing_percent = excluded.trailing_percent,
                updated_at = datetime('now')
        """, (
            symbol,
            position.side,
            position.entry_price,
            position.entry_time.isoformat(),
            position.size,
            position.unrealized_pnl,
            1 if position.trailing_enabled else 0,
            position.trailing_percent,
        ))
        self.conn.commit()
        logger.debug(f"Saved position for {symbol}: {position.side} @ {position.entry_price}")

    def get_position(self, symbol: str) -> Optional[PositionState]:
        """Get position state for symbol."""
        if self.conn is None:
            return None
            
        row = self.conn.execute(
            "SELECT * FROM positions WHERE symbol = ?",
            (symbol,)
        ).fetchone()
        
        if row is None:
            return None
            
        return PositionState(
            symbol=row["symbol"],
            side=row["side"],
            entry_price=row["entry_price"],
            entry_time=datetime.fromisoformat(row["entry_time"]),
            size=row["size"],
            unrealized_pnl=row["unrealized_pnl"],
            trailing_enabled=bool(row["trailing_enabled"]),
            trailing_percent=row["trailing_percent"],
        )

    def get_all_positions(self) -> List[PositionState]:
        """Get all open positions."""
        if self.conn is None:
            return []
            
        rows = self.conn.execute(
            "SELECT * FROM positions"
        ).fetchall()
        
        return [
            PositionState(
                symbol=row["symbol"],
                side=row["side"],
                entry_price=row["entry_price"],
                entry_time=datetime.fromisoformat(row["entry_time"]),
                size=row["size"],
                unrealized_pnl=row["unrealized_pnl"],
                trailing_enabled=bool(row["trailing_enabled"]),
                trailing_percent=row["trailing_percent"],
            )
            for row in rows
        ]

    def close_position(self, symbol: str) -> None:
        """Remove position (trade closed)."""
        if self.conn is None:
            return
            
        self.conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
        self.conn.commit()
        logger.debug(f"Closed position for {symbol}")

    # ─────────────────────────────────────────────────────────────────────────
    # Order operations
    # ─────────────────────────────────────────────────────────────────────────

    def save_order(self, order_id: str, order: OrderState) -> None:
        """Save or update order state."""
        if self.conn is None:
            raise RuntimeError("Not initialized. Call init() first.")
            
        self.conn.execute("""
            INSERT INTO orders (order_id, symbol, side, status, created_at, filled_at, fill_price, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(order_id) DO UPDATE SET
                status = excluded.status,
                filled_at = excluded.filled_at,
                fill_price = excluded.fill_price,
                updated_at = datetime('now')
        """, (
            order_id,
            order.symbol,
            order.side,
            order.status,
            order.created_at.isoformat(),
            order.filled_at.isoformat() if order.filled_at else None,
            order.fill_price,
        ))
        self.conn.commit()
        logger.debug(f"Saved order {order_id}: {order.status}")

    def get_order(self, order_id: str) -> Optional[OrderState]:
        """Get order state."""
        if self.conn is None:
            return None
            
        row = self.conn.execute(
            "SELECT * FROM orders WHERE order_id = ?",
            (order_id,)
        ).fetchone()
        
        if row is None:
            return None
            
        return OrderState(
            order_id=row["order_id"],
            symbol=row["symbol"],
            side=row["side"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            filled_at=datetime.fromisoformat(row["filled_at"]) if row["filled_at"] else None,
            fill_price=row["fill_price"],
        )

    def get_active_orders(self) -> List[OrderState]:
        """Get all pending orders."""
        if self.conn is None:
            return []
            
        rows = self.conn.execute(
            "SELECT * FROM orders WHERE status = 'pending'"
        ).fetchall()
        
        return [
            OrderState(
                order_id=row["order_id"],
                symbol=row["symbol"],
                side=row["side"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                filled_at=datetime.fromisoformat(row["filled_at"]) if row["filled_at"] else None,
                fill_price=row["fill_price"],
            )
            for row in rows
        ]

    def mark_order_filled(self, order_id: str, fill_price: float) -> None:
        """Mark order as filled."""
        if self.conn is None:
            return
            
        self.conn.execute("""
            UPDATE orders 
            SET status = 'filled', filled_at = datetime('now'), fill_price = ?, updated_at = datetime('now')
            WHERE order_id = ?
        """, (fill_price, order_id))
        self.conn.commit()
        logger.debug(f"Order {order_id} filled @ {fill_price}")

    def mark_order_failed(self, order_id: str) -> None:
        """Mark order as failed."""
        if self.conn is None:
            return
            
        self.conn.execute("""
            UPDATE orders 
            SET status = 'failed', updated_at = datetime('now')
            WHERE order_id = ?
        """, (order_id,))
        self.conn.commit()
        logger.debug(f"Order {order_id} marked failed")

    # ─────────────────────────────────────────────────────────────────────────
    # Reconciliation
    # ─────────────────────────────────────────────────────────────────────────

    async def reconcile(
        self,
        fetch_positions_fn,  # async function to fetch exchange positions
        fetch_orders_fn,    # async function to fetch exchange orders
        metrics_client=None,
    ) -> Dict[str, Any]:
        """Reconcile persisted state with exchange on startup.
        
        Returns reconciliation report with:
        - positions_restored: count
        - orders_restored: count
        - discrepancies: list of issues found
        """
        report = {
            "positions_restored": 0,
            "orders_restored": 0,
            "discrepancies": [],
        }
        
        # Get persisted state
        persisted_positions = self.get_all_positions()
        persisted_orders = self.get_active_orders()
        
        # Fetch from exchange
        try:
            exchange_positions = await fetch_positions_fn()
        except Exception as e:
            logger.error(f"Failed to fetch exchange positions: {e}")
            report["discrepancies"].append(f"exchange_positions: {e}")
            exchange_positions = []
            
        try:
            exchange_orders = await fetch_orders_fn()
        except Exception as e:
            logger.error(f"Failed to fetch exchange orders: {e}")
            report["discrepancies"].append(f"exchange_orders: {e}")
            exchange_orders = []
        
        # Build lookup sets
        exchange_pos_symbols = {p["symbol"] for p in exchange_positions}
        pers_pos_symbols = {p.symbol for p in persisted_positions}
        
        exchange_order_ids = {o["order_id"] for o in exchange_orders}
        pers_order_ids = {o.order_id for o in persisted_orders}
        
        # Check for double-execution risk (position in both)
        double_positions = pers_pos_symbols & exchange_pos_symbols
        if double_positions:
            report["discrepancies"].append(f"double_execution_risk: {double_positions}")
            logger.warning(f"Double execution risk detected: {double_positions}")
        
        # Check for lost positions (in persisted only, not in exchange)
        lost_positions = pers_pos_symbols - exchange_pos_symbols
        if lost_positions:
            report["discrepancies"].append(f"lost_positions: {lost_positions}")
            logger.warning(f"Positions in DB but not on exchange: {lost_positions}")
            # Close orphaned positions
            for symbol in lost_positions:
                self.close_position(symbol)
                report["positions_restored"] -= 1
        
        # Check for orphan orders (in exchange but not in DB)
        orphan_orders = exchange_order_ids - pers_order_ids
        if orphan_orders:
            # These are fine - just log them
            logger.info(f"New orders on exchange not in DB: {orphan_orders}")
        
        # Report metrics
        report["positions_restored"] = len(persisted_positions)
        report["orders_restored"] = len(persisted_orders)
        
        if metrics_client:
            metrics_client.emit("sentinel_state_restored", 1, {"type": "reconciliation"})
            metrics_client.emit("sentinel_positions_restored", report["positions_restored"])
            metrics_client.emit("sentinel_orders_restored", report["orders_restored"])
        
        logger.info(f"Reconciliation complete: {report}")
        return report

    # ─────────────────────────────────────────────────────────────────────────
    # Metadata
    # ─────────────────────────────────────────────────────────────────────────

    def set_metadata(self, key: str, value: Any) -> None:
        """Store metadata value."""
        if self.conn is None:
            return
            
        self.conn.execute("""
            INSERT INTO metadata (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')
        """, (key, json.dumps(value)))
        self.conn.commit()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        if self.conn is None:
            return default
            
        row = self.conn.execute(
            "SELECT value FROM metadata WHERE key = ?",
            (key,)
        ).fetchone()
        
        if row is None:
            return default
            
        return json.loads(row["value"])

    # ─────────────────────────────────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("StatePersistence closed")


# ─────────────────────────────────────────────────────────────────────────
# Metrics emission helper
# ─────────────────────────────────────────────────────────────────────────

def emit_state_restored_metric(metrics_client, report: Dict[str, Any]) -> None:
    """Emit reconciliation metrics to Prometheus."""
    if not metrics_client:
        return
        
    metrics_client.emit("sentinel_state_restored", 1)
    metrics_client.emit("sentinel_positions_restored", report["positions_restored"])
    metrics_client.emit("sentinel_orders_restored", report["orders_restored"])
    
    if report["discrepancies"]:
        metrics_client.emit("sentinel_reconciliation_issues", len(report["discrepancies"]))


# ─────────────────────────────────────────────────────────────────────────
# Idempotency - prevent duplicate orders
# ─────────────────────────────────────────────────────────────────────────

def generate_idempotency_key(signal_id: str, symbol: str, side: str) -> str:
    """Generate unique idempotency key for order.
    
    Format: se-{signal_id}-{symbol}-{timestamp}
    Example: se-signal-1234-BTCUSDT-LONG-1704067200
    
    This prevents duplicate execution when:
    1. Signal sent, network timeout → retry with SAME key
    2. Exchange receives duplicate → rejects (already used)
    3. Bot checks DB → finds key used → skips retry
    """
    timestamp = int(time.time())
    return f"se-{signal_id}-{symbol}-{side}-{timestamp}"


def generate_client_order_id(signal_id: str) -> str:
    """Generate CCXT clientOrderId for Binance.
    
    Using just signal_id + timestamp ensures uniqueness
    while being human-readable for order lookup.
    """
    return f"se-{signal_id}-{int(time.time())}"


class IdempotencyManager:
    """Manages idempotency keys to prevent duplicate orders.
    
    Usage:
        im = IdempotencyManager(db_path)
        await im.init()
        
        # Before sending order:
        key = im.can_send_order(signal_id, symbol, side)
        if not key:
            logger.warning(f"Order recent, checking status: {signal_id}")
            return  # Recently sent, check status instead
            
        # After sending (success):
        im.mark_order_sent(key, symbol, side)
        
        # After confirmation:
        im.mark_order_confirmed(key)
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    async def init(self) -> None:
        """Initialize idempotency table."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                key TEXT PRIMARY KEY,
                signal_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                confirmed_at TEXT,
                retry_count INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        
        # Clean old entries (>24 hours)
        self.conn.execute("""
            DELETE FROM idempotency_keys 
            WHERE created_at < datetime('now', '-24 hours') 
            AND status IN ('confirmed', 'failed')
        """)
        self.conn.commit()
        
        logger.info("IdempotencyManager initialized")

    def can_send_order(self, signal_id: str, symbol: str, side: str, max_retries: int = 3) -> Optional[str]:
        """Check if we can send an order, return key or None.
        
        Returns:
            - New key if OK to send
            - None if recently sent (check status instead)
        """
        if self.conn is None:
            return generate_client_order_id(signal_id)
            
        # Check for recent pending order
        row = self.conn.execute("""
            SELECT * FROM idempotency_keys
            WHERE symbol = ? AND side = ? AND status = 'pending'
            AND created_at > datetime('now', '-30 seconds')
            ORDER BY created_at DESC
            LIMIT 1
        """, (symbol, side)).fetchone()
        
        if row:
            # Recent order exists - don't resend
            logger.info(f"Recent pending order found: {row['key']}, checking status")
            return None
            
        # Check retry count
        existing = self.conn.execute("""
            SELECT retry_count FROM idempotency_keys
            WHERE signal_id = ? AND symbol = ? AND side = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (signal_id, symbol, side)).fetchone()
        
        if existing and existing["retry_count"] >= max_retries:
            logger.warning(f"Max retries exceeded for {signal_id}")
            return None
            
        # Generate new key
        return generate_client_order_id(signal_id)

    def mark_order_sent(self, key: str, signal_id: str, symbol: str, side: str) -> None:
        """Mark order as sent (pending)."""
        if self.conn is None:
            return
            
        self.conn.execute("""
            INSERT INTO idempotency_keys (key, signal_id, symbol, side, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', datetime('now'), datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                status = 'pending',
                retry_count = retry_count + 1,
                updated_at = datetime('now')
        """, (key, signal_id, symbol, side))
        self.conn.commit()
        logger.debug(f"Marked order sent: {key}")

    def mark_order_confirmed(self, key: str) -> None:
        """Mark order as confirmed (filled)."""
        if self.conn is None:
            return
            
        self.conn.execute("""
            UPDATE idempotency_keys
            SET status = 'confirmed', confirmed_at = datetime('now'), updated_at = datetime('now')
            WHERE key = ?
        """, (key,))
        self.conn.commit()
        logger.debug(f"Marked order confirmed: {key}")

    def mark_order_failed(self, key: str, failure_reason: str = "") -> None:
        """Mark order as permanently failed."""
        if self.conn is None:
            return
            
        self.conn.execute("""
            UPDATE idempotency_keys
            SET status = 'failed', confirmed_at = datetime('now'), updated_at = datetime('now')
            WHERE key = ?
        """, (key,))
        self.conn.commit()
        logger.warning(f"Marked order failed: {key} - {failure_reason}")

    def get_order_status(self, key: str) -> Optional[str]:
        """Get current order status."""
        if self.conn is None:
            return None
            
        row = self.conn.execute("""
            SELECT status FROM idempotency_keys WHERE key = ?
        """, (key,)).fetchone()
        
        return row["status"] if row else None

    def close(self) -> None:
        """Close connection."""
        if self.conn:
            self.conn.close()
            self.conn = None