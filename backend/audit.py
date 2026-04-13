"""Audit trail & trade replay for Sentinel Edge.

Provides:
- Append-only audit log (SQLite file for beta)
- Decision logging with full context
- Edge vector snapshots
- Order lifecycle tracking
- Prometheus counters
- CLI replay command

Usage:
    from audit import AuditTrail, setup_audit_logging
    
    audit = AuditTrail(db_path=Path("/app/data/audit.db"))
    await audit.init()
    
    # Log decision
    await audit.log_decision(
        symbol="BTCUSDT",
        decision="LONG",
        edge=82,
        edge_vectors={"trend": 35, "volume": 22, "momentum": 15},
        risk={"size": 0.02, "stop": 0.015},
    )
    
    # Log order
    await audit.log_order_created(order_id, symbol, "LONG", price, size)
    await audit.log_order_filled(order_id, fill_price, pnl)
    
    # CLI replay:
    # python -m audit replay --trade-id=xxx
"""
import asyncio
import json
import logging
import sqlite3
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Prometheus Counters
# ═══════════════════════════════════════════════════════════

AUDIT_DECISIONS_TOTAL = Counter(
    "sentinel_audit_decisions_total",
    "Total decisions logged",
    ["symbol", "decision", "edge_bucket"]
)

AUDIT_ORDERS_CREATED_TOTAL = Counter(
    "sentinel_audit_orders_created_total",
    "Total orders created",
    ["symbol", "side"]
)

AUDIT_ORDERS_FILLED_TOTAL = Counter(
    "sentinel_audit_orders_filled_total",
    "Total orders filled",
    ["symbol", "side"]
)

AUDIT_ORDERS_FAILED_TOTAL = Counter(
    "sentinel_audit_orders_failed_total",
    "Total orders failed",
    ["symbol", "side", "error"]
)

AUDIT_LATENCY = Histogram(
    "sentinel_audit_log_latency_seconds",
    "Audit log write latency",
    ["event_type"]
)


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class DecisionRecord:
    """Decision audit record."""
    id: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    symbol: str = ""
    decision: str = ""  # LONG, SHORT, FLAT, COOLDOWN
    edge: float = 0.0
    edge_vectors: Dict[str, float] = field(default_factory=dict)
    risk_size: float = 0.0
    risk_stop: float = 0.0
    market_regime: str = ""
    volatility_atr: float = 0.0
    trend_score: float = 0.0
    volume_zscore: float = 0.0
    order_sent: bool = False
    order_id: Optional[str] = None


@dataclass
class OrderRecord:
    """Order lifecycle audit record."""
    id: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    order_id: str = ""
    signal_id: str = ""
    symbol: str = ""
    side: str = ""  # LONG or SHORT
    status: str = ""  # created, filled, cancelled, failed
    price: float = 0.0
    size: float = 0.0
    fill_price: Optional[float] = None
    fill_time: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    error: Optional[str] = None
    config_hash: Optional[str] = None  # Added: config that produced this trade


@dataclass
class TickRecord:
    """Tick/signal audit record."""
    id: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    symbol: str = ""
    price: float = 0.0
    volume: float = 0.0
    atr: float = 0.0
    vwap: float = 0.0


# ═══════════════════════════════════════════════════════════
# Audit Trail
# ═══════════════════════════════════════════════════════════

class AuditTrail:
    """Append-only audit trail for post-mortems.
    
    Usage:
        audit = AuditTrail()
        await audit.init()
        
        await audit.log_decision(...)
        await audit.log_order_created(...)
        
        # Replay
        records = await audit.replay_trade(trade_id)
    """
    
    DEFAULT_DB_PATH = Path("/app/data/audit.db")
    
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    async def init(self) -> None:
        """Initialize database and tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                decision TEXT NOT NULL,
                edge REAL NOT NULL,
                edge_vectors TEXT NOT NULL,
                risk_size REAL NOT NULL,
                risk_stop REAL NOT NULL,
                market_regime TEXT,
                volatility_atr REAL,
                trend_score REAL,
                volume_zscore REAL,
                order_sent INTEGER DEFAULT 0,
                order_id TEXT
            );
            
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                order_id TEXT NOT NULL UNIQUE,
                signal_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                status TEXT NOT NULL,
                price REAL NOT NULL,
                size REAL NOT NULL,
                fill_price REAL,
                fill_time TEXT,
                pnl REAL,
                pnl_pct REAL,
                error TEXT,
                config_hash TEXT
            );
            
            CREATE TABLE IF NOT EXISTS ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume REAL,
                atr REAL,
                vwap REAL
            );
            
            CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON decisions(symbol);
            CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id);
            CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
            CREATE INDEX IF NOT EXISTS idx_ticks_symbol ON ticks(symbol);
            CREATE INDEX IF NOT EXISTS idx_ticks_timestamp ON ticks(timestamp);
        """)
        self.conn.commit()
        logger.info(f"AuditTrail initialized: {self.db_path}")
    
    # ─────────────────────────────────────────────────────
    # Decision Logging
    # ─────────────────────────────────────────────────────
    
    async def log_decision(
        self,
        symbol: str,
        decision: str,
        edge: float,
        edge_vectors: Dict[str, float],
        risk_size: float,
        risk_stop: float,
        market_regime: str = "",
        volatility_atr: float = 0.0,
        trend_score: float = 0.0,
        volume_zscore: float = 0.0,
        order_id: Optional[str] = None,
    ) -> int:
        """Log a trading decision with full context."""
        start = time.perf_counter()
        
        self.conn.execute("""
            INSERT INTO decisions (
                timestamp, symbol, decision, edge, edge_vectors,
                risk_size, risk_stop, market_regime, volatility_atr,
                trend_score, volume_zscore, order_sent, order_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            symbol,
            decision,
            edge,
            json.dumps(edge_vectors),
            risk_size,
            risk_stop,
            market_regime,
            volatility_atr,
            trend_score,
            volume_zscore,
            1 if order_id else 0,
            order_id,
        ))
        self.conn.commit()
        
        # Metrics
        edge_bucket = self._edge_bucket(edge)
        AUDIT_DECISIONS_TOTAL.labels(symbol=symbol, decision=decision, edge_bucket=edge_bucket).inc()
        AUDIT_LATENCY.labels(event_type="decision").observe(time.perf_counter() - start)
        
        return self.conn.lastrowid
    
    def _edge_bucket(self, edge: float) -> str:
        """Bucket edge score for metrics."""
        if edge >= 80:
            return "80-100"
        elif edge >= 65:
            return "65-79"
        elif edge >= 50:
            return "50-64"
        else:
            return "0-49"
    
    # ─────────────────────────────────────────────────────
    # Order Logging
    # ─────────────────────────────────────────────────────
    
    async def log_order_created(
        self,
        order_id: str,
        signal_id: str,
        symbol: str,
        side: str,
        price: float,
        size: float,
        config_hash: Optional[str] = None,
    ) -> int:
        """Log order creation with config hash."""
        start = time.perf_counter()
        
        self.conn.execute("""
            INSERT INTO orders (order_id, signal_id, symbol, side, status, price, size, timestamp, config_hash)
            VALUES (?, ?, ?, ?, 'created', ?, ?, ?, ?)
        """, (
            order_id,
            signal_id,
            symbol,
            side,
            price,
            size,
            datetime.now(timezone.utc).isoformat(),
            config_hash,
        ))
        self.conn.commit()
        
        AUDIT_ORDERS_CREATED_TOTAL.labels(symbol=symbol, side=side).inc()
        AUDIT_LATENCY.labels(event_type="order_created").observe(time.perf_counter() - start)
        
        return self.conn.lastrowid
    
    async def log_order_filled(
        self,
        order_id: str,
        fill_price: float,
        pnl: float,
        pnl_pct: float,
    ) -> int:
        """Log order fill."""
        start = time.perf_counter()
        
        self.conn.execute("""
            UPDATE orders
            SET status = 'filled', fill_price = ?, fill_time = ?, pnl = ?, pnl_pct = ?
            WHERE order_id = ?
        """, (
            fill_price,
            datetime.now(timezone.utc).isoformat(),
            pnl,
            pnl_pct,
            order_id,
        ))
        self.conn.commit()
        
        # Get symbol/side for metrics
        row = self.conn.execute(
            "SELECT symbol, side FROM orders WHERE order_id = ?",
            (order_id,)
        ).fetchone()
        
        if row:
            AUDIT_ORDERS_FILLED_TOTAL.labels(symbol=row["symbol"], side=row["side"]).inc()
        AUDIT_LATENCY.labels(event_type="order_filled").observe(time.perf_counter() - start)
        
        return self.conn.lastrowid
    
    async def log_order_failed(
        self,
        order_id: str,
        error: str,
    ) -> int:
        """Log order failure."""
        start = time.perf_counter()
        
        self.conn.execute("""
            UPDATE orders SET status = 'failed', error = ? WHERE order_id = ?
        """, (error, order_id))
        self.conn.commit()
        
        row = self.conn.execute(
            "SELECT symbol, side FROM orders WHERE order_id = ?",
            (order_id,)
        ).fetchone()
        
        if row:
            error_bucket = "network" if "timeout" in error.lower() else "other"
            AUDIT_ORDERS_FAILED_TOTAL.labels(
                symbol=row["symbol"], side=row["side"], error=error_bucket
            ).inc()
        AUDIT_LATENCY.labels(event_type="order_failed").observe(time.perf_counter() - start)
        
        return self.conn.lastrowid
    
    # ─────────────────────────────────────────────────────
    # Tick Logging
    # ─────────────────────────────────────────────────────
    
    async def log_tick(
        self,
        symbol: str,
        price: float,
        volume: float,
        atr: float,
        vwap: float,
    ) -> int:
        """Log tick data."""
        self.conn.execute("""
            INSERT INTO ticks (timestamp, symbol, price, volume, atr, vwap)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            symbol,
            price,
            volume,
            atr,
            vwap,
        ))
        self.conn.commit()
        return self.conn.lastrowid
    
    # ─────────────────────────────────────────────────────
    # Replay
    # ─────────────────────────────────────────────────────
    
    async def replay_trade(
        self,
        trade_id: str,
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Replay a trade for post-mortem.
        
        Returns full audit trail:
        - Decision context
        - Order lifecycle
        - PnL outcome
        """
        # Find by order_id or trade_id
        if order_id:
            where = "order_id = ?"
            params = (order_id,)
        else:
            where = "id = ?"
            params = (int(trade_id),)
        
        # Get order record
        order = self.conn.execute(
            f"SELECT * FROM orders WHERE {where}",
            params
        ).fetchone()
        
        if not order:
            return {"error": "Trade not found"}
        
        # Get related decisions
        decisions = self.conn.execute("""
            SELECT * FROM decisions 
            WHERE symbol = ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (order["symbol"], order["timestamp"])).fetchall()
        
        # Get ticks around the trade
        ticker = order["symbol"]
        time_before = order["timestamp"]
        ticks = self.conn.execute("""
            SELECT * FROM ticks
            WHERE symbol = ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT 60
        """, (ticker, time_before)).fetchall()
        
        return {
            "trade": dict(order),
            "decisions": [dict(d) for d in decisions],
            "ticks": [dict(t) for t in ticks],
        }
    
    async def get_decisions_by_symbol(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent decisions for symbol."""
        rows = self.conn.execute("""
            SELECT * FROM decisions
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (symbol, limit)).fetchall()
        return [dict(r) for r in rows]
    
    async def get_orders_by_symbol(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent orders for symbol."""
        rows = self.conn.execute("""
            SELECT * FROM orders
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (symbol, limit)).fetchall()
        return [dict(r) for r in rows]
    
    def close(self) -> None:
        """Close connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# ═══════════════════════════════════════════════════════════
# CLI Replay Command
# ═══════════════════════════════════════════════════════════

async def replay_cli():
    """CLI for trade replay."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Replay a trade for post-mortem")
    parser.add_argument("--trade-id", type=str, help="Trade ID (database row id)")
    parser.add_argument("--order-id", type=str, help="Order ID")
    args = parser.parse_args()
    
    if not args.trade_id and not args.order_id:
        parser.error("Either --trade-id or --order-id required")
    
    audit = AuditTrail()
    await audit.init()
    
    result = await audit.replay_trade(args.trade_id, args.order_id)
    
    print(json.dumps(result, indent=2, default=str))
    
    await audit.close()


if __name__ == "__main__":
    asyncio.run(replay_cli())