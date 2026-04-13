"""Backtest vs Live drift detection for Sentinel Edge.

Provides:
- sentinel_backtest_vs_live_pnl_delta_pct metric
- Drift detection and alerting (>5% threshold)
- Weekly reconciliation job
- Historical drift tracking

Usage:
    from drift_detection import DriftDetector, run_weekly_reconciliation
    
    detector = DriftDetector()
    await detector.init()
    
    # On trade close, compare:
    drift = await detector.compare_trade(
        symbol="BTCUSDT",
        backtest_pnl=50.0,
        live_pnl=47.5,
    )
    
    # Weekly job:
    await run_weekly_reconciliation()
"""
import asyncio
import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from prometheus_client import Gauge, Counter, Histogram

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Prometheus Metrics
# ═══════════════════════════════════════════════════════════

BACKTEST_LIVE_DELTA_PCT = Gauge(
    "sentinel_backtest_vs_live_pnl_delta_pct",
    "Backtest vs Live PnL delta percentage",
    ["symbol", "side"]
)

BACKTEST_LIVE_DRIFT_ALERTS = Counter(
    "sentinel_backtest_vs_live_drift_alerts_total",
    "Total drift alerts triggered",
    ["symbol", "severity"]
)

BACKTEST_LIVE_DRIFT_HISTOGRAM = Histogram(
    "sentinel_backtest_vs_live_drift_histogram",
    "Distribution of drift percentages",
    buckets=[-10, -5, -2, 0, 2, 5, 10]
)

DRIFT_CHECKS_TOTAL = Counter(
    "sentinel_drift_checks_total",
    "Total drift checks performed"
)


# ═══════════════════════════════════════════════════════════
# Drift Thresholds
# ═══════════════════════════════════════════════════════════

DRIFT_THRESHOLD_CRITICAL = 5.0   # 5% triggers critical alert
DRIFT_THRESHOLD_WARNING = 2.0     # 2% triggers warning


# ═══════════════════════════════════════════════════════════

class DriftDetector:
    """Detect and track backtest vs live drift.
    
    Usage:
        detector = DriftDetector()
        await detector.init()
        
        drift = await detector.compare_trade(
            symbol="BTCUSDT",
            backtest_pnl=50.0,
            live_pnl=47.5,
        )
        
        if drift['pct'] > 5.0:
            logger.warning(f"CRITICAL DRIFT: {drift}")
    """
    
    DEFAULT_DB_PATH = Path("/app/data/drift.db")
    
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    async def init(self) -> None:
        """Initialize drift tracking database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS drift_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                backtest_pnl REAL NOT NULL,
                live_pnl REAL NOT NULL,
                drift_pct REAL NOT NULL,
                order_id TEXT,
                config_hash TEXT,
                is_systematic INTEGER DEFAULT 0,
                acknowledged INTEGER DEFAULT 0,
                notes TEXT
            );
            
            CREATE TABLE IF NOT EXISTS reconciliation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                total_backtest_pnl REAL NOT NULL,
                total_live_pnl REAL NOT NULL,
                total_drift_pct REAL NOT NULL,
                trade_count INTEGER NOT NULL,
                systematic_drift_pct REAL,
                created_at TEXT NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_drift_symbol ON drift_records(symbol);
            CREATE INDEX IF NOT EXISTS idx_drift_timestamp ON drift_records(timestamp);
            CREATE INDEX IF NOT EXISTS idx_drift_order ON drift_records(order_id);
        """)
        self.conn.commit()
        
        logger.info(f"DriftDetector initialized: {self.db_path}")
    
    # ─────────────────────────────────────────────────────
    # Compare Trade
    # ─────────────────────────────────────────────────────
    
    async def compare_trade(
        self,
        symbol: str,
        backtest_pnl: float,
        live_pnl: float,
        side: str = "",
        order_id: Optional[str] = None,
        config_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare backtest vs live PnL for a single trade."""
        DRIFT_CHECKS_TOTAL.inc()
        
        # Calculate drift percentage
        if backtest_pnl == 0:
            drift_pct = 0.0
        else:
            drift_pct = ((live_pnl - backtest_pnl) / abs(backtest_pnl)) * 100
        
        # Determine if systematic (multiple trades with similar drift)
        is_systematic = await self._check_systematic_drift(symbol, drift_pct)
        
        # Record in DB
        self.conn.execute("""
            INSERT INTO drift_records (
                timestamp, symbol, side, backtest_pnl, live_pnl,
                drift_pct, order_id, config_hash, is_systematic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            symbol,
            side,
            backtest_pnl,
            live_pnl,
            drift_pct,
            order_id,
            config_hash,
            1 if is_systematic else 0,
        ))
        self.conn.commit()
        
        # Update metrics
        BACKTEST_LIVE_DELTA_PCT.labels(symbol=symbol, side=side).set(drift_pct)
        BACKTEST_LIVE_DRIFT_HISTOGRAM.observe(drift_pct)
        
        result = {
            "symbol": symbol,
            "side": side,
            "backtest_pnl": backtest_pnl,
            "live_pnl": live_pnl,
            "drift_pct": drift_pct,
            "is_systematic": is_systematic,
            "order_id": order_id,
        }
        
        # Alert if critical drift
        if abs(drift_pct) > DRIFT_THRESHOLD_CRITICAL:
            severity = "critical" if drift_pct < 0 else "warning"
            BACKTEST_LIVE_DRIFT_ALERTS.labels(
                symbol=symbol, severity=severity
            ).inc()
            
            logger.warning(
                f"DRIFT ALERT [{severity}]: {symbol} {side} "
                f"backtest={backtest_pnl} live={live_pnl} drift={drift_pct:.1f}%"
            )
        
        return result
    
    async def _check_systematic_drift(
        self,
        symbol: str,
        current_drift: float,
    ) -> bool:
        """Check if drift is systematic (>3 of last 5 trades same direction)."""
        # Get last 5 trades for this symbol
        rows = self.conn.execute("""
            SELECT drift_pct FROM drift_records
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (symbol,)).fetchall()
        
        if len(rows) < 3:
            return False
        
        # Count same-direction drifts
        direction = "negative" if current_drift < -1 else "positive" if current_drift > 1 else "neutral"
        
        same_direction = sum(
            1 for r in rows
            if (r["drift_pct"] < -1 and direction == "negative") or
               (r["drift_pct"] > 1 and direction == "positive")
        )
        
        return same_direction >= 3
    
    # ─────────────────────────────────────────────────────
    # Drift Statistics
    # ─────────────────────────────────────────────────────
    
    async def get_drift_stats(
        self,
        symbol: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get drift statistics for period."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        where = "timestamp >= ?"
        params = [since]
        
        if symbol:
            where += " AND symbol = ?"
            params.append(symbol)
        
        # Get stats
        rows = self.conn.execute(f"""
            SELECT 
                COUNT(*) as count,
                AVG(drift_pct) as avg_drift,
                MAX(drift_pct) as max_drift,
                MIN(drift_pct) as min_drift,
                SUM(CASE WHEN is_systematic = 1 THEN 1 ELSE 0 END) as systematic_count
            FROM drift_records
            WHERE {where}
        """, params).fetchone()
        
        # Get by symbol breakdown
        symbol_rows = self.conn.execute(f"""
            SELECT 
                symbol,
                COUNT(*) as count,
                AVG(drift_pct) as avg_drift
            FROM drift_records
            WHERE {where}
            GROUP BY symbol
            ORDER BY avg_drift
        """, params).fetchall()
        
        return {
            "period_days": days,
            "total_trades": rows["count"],
            "avg_drift_pct": rows["avg_drift"] or 0,
            "max_drift_pct": rows["max_drift"] or 0,
            "min_drift_pct": rows["min_drift"] or 0,
            "systematic_count": rows["systematic_count"],
            "by_symbol": [dict(r) for r in symbol_rows],
        }
    
    # ─────────────────────────────────────────────────────
    # Weekly Reconciliation
    # ─────────────────────────────────────────────────────
    
    async def run_reconciliation(
        self,
        period_days: int = 7,
    ) -> Dict[str, Any]:
        """Run weekly reconciliation between backtest and live."""
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=period_days)
        
        # Get totals for period
        rows = self.conn.execute("""
            SELECT 
                SUM(backtest_pnl) as total_backtest,
                SUM(live_pnl) as total_live,
                COUNT(*) as trade_count,
                AVG(drift_pct) as avg_drift,
                SUM(CASE WHEN is_systematic = 1 THEN 1 ELSE 0 END) as systematic_count
            FROM drift_records
            WHERE timestamp >= ? AND timestamp <= ?
        """, (period_start.isoformat(), period_end.isoformat())).fetchone()
        
        total_backtest = rows["total_backtest"] or 0
        total_live = rows["total_live"] or 0
        
        if total_backtest != 0:
            total_drift_pct = ((total_live - total_backtest) / abs(total_backtest)) * 100
        else:
            total_drift_pct = 0
        
        # Check for systematic drift (if >50% trades have >2% drift)
        avg_drift = rows["avg_drift"] or 0
        systematic = abs(avg_drift) > DRIFT_THRESHOLD_CRITICAL and rows["systematic_count"] > 3
        
        # Record summary
        self.conn.execute("""
            INSERT INTO reconciliation_summaries (
                period_start, period_end, total_backtest_pnl, total_live_pnl,
                total_drift_pct, trade_count, systematic_drift_pct, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            period_start.isoformat(),
            period_end.isoformat(),
            total_backtest,
            total_live,
            total_drift_pct,
            rows["trade_count"] or 0,
            avg_drift if systematic else None,
            datetime.now(timezone.utc).isoformat(),
        ))
        self.conn.commit()
        
        result = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_backtest_pnl": total_backtest,
            "total_live_pnl": total_live,
            "total_drift_pct": total_drift_pct,
            "trade_count": rows["trade_count"] or 0,
            "systematic_drift": systematic,
            "systematic_drift_pct": avg_drift if systematic else None,
        }
        
        # Alert if significant drift
        if abs(total_drift_pct) > DRIFT_THRESHOLD_CRITICAL:
            logger.warning(f"RECONCILIATION ALERT: {total_drift_pct:.1f}% drift")
        
        return result
    
    def close(self) -> None:
        """Close connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# ═══════════════════════════════════════════════════════════
# Weekly Job
# ═══════════════════════════════════════════════════════════

async def run_weekly_reconciliation():
    """Run weekly drift reconciliation.
    
    Can be scheduled via cron:
        0 0 * * 0 python -m drift_detection run-weekly
    """
    detector = DriftDetector()
    await detector.init()
    
    logger.info("Starting weekly reconciliation...")
    result = await detector.run_reconciliation(period_days=7)
    
    logger.info(f"Weekly reconciliation complete: {result}")
    
    await detector.close()
    return result


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

async def cli():
    """CLI for drift detection."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backtest vs Live drift detection")
    parser.add_argument("--stats", action="store_true", help="Show drift stats")
    parser.add_argument("--reconcile", action="store_true", help="Run weekly reconciliation")
    parser.add_argument("--days", type=int, default=30, help="Stats period days")
    args = parser.parse_args()
    
    detector = DriftDetector()
    await detector.init()
    
    if args.stats:
        stats = await detector.get_drift_stats(days=args.days)
        print(json.dumps(stats, indent=2, default=str))
    
    if args.reconcile:
        result = await detector.run_reconciliation()
        print(json.dumps(result, indent=2, default=str))
    
    await detector.close()


if __name__ == "__main__":
    import asyncio
    import json
    asyncio.run(cli())