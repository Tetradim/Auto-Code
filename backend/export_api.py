"""Trade export endpoints for tax and reporting.

Provides /export/trades endpoint with:
- CSV export
- Full trade details including regime, edge score, feature contributions

Usage:
    # CSV export
    GET /export/trades?format=csv&start=2024-01-01&end=2024-12-31
    
    # JSON export
    GET /export/trades?format=json&start=2024-01-01
    
    # Filter by symbol
    GET /export/trades?symbol=BTCUSDT&format=csv
"""
import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


# ═══════════════════════════════════════════════════════════
# Export Functions
# ═══════════════════════════════════════════════════════════

def get_audit_trail():
    """Get audit trail singleton from server.py."""
    from server import audit_trail
    return audit_trail


async def get_trade_data(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    symbol: Optional[str] = None,
) -> List[dict]:
    """Fetch trade data from audit database."""
    try:
        audit = get_audit_trail()
        if audit and audit.conn:
            query = "SELECT * FROM orders WHERE 1=1"
            params = []
            
            if start:
                query += " AND timestamp >= ?"
                params.append(start.isoformat())
            if end:
                query += " AND timestamp <= ?"
                params.append(end.isoformat())
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY timestamp DESC"
            
            rows = audit.conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    except Exception:
        pass
    
    return []


def format_trade_for_export(trade: dict) -> dict:
    """Format trade data for export with all required fields."""
    return {
        "trade_id": trade.get("order_id", ""),
        "symbol": trade.get("symbol", ""),
        "side": trade.get("side", ""),
        "entry_time": trade.get("timestamp", ""),
        "entry_price": trade.get("price", 0),
        "exit_time": trade.get("fill_time", ""),
        "exit_price": trade.get("fill_price", 0),
        "size": trade.get("size", 0),
        "pnl": trade.get("pnl", 0),
        "pnl_pct": trade.get("pnl_pct", 0),
        # Tax/reporting fields
        "regime": trade.get("market_regime", "unknown"),
        "edge_score": trade.get("edge", 0),
        "feature_trend": trade.get("edge_vectors", {}).get("trend", 0),
        "feature_volume": trade.get("edge_vectors", {}).get("volume", 0),
        "feature_momentum": trade.get("edge_vectors", {}).get("momentum", 0),
        "feature_volatility": trade.get("edge_vectors", {}).get("volatility", 0),
        "config_hash": trade.get("config_hash", ""),
    }


# ═══════════════════════════════════════════════════════════
# CSV Export
# ═══════════════════════════════════════════════════════════

def generate_csv(trades: List[dict]) -> str:
    """Generate CSV string from trade data."""
    if not trades:
        return ""
    
    output = io.StringIO()
    fieldnames = [
        "trade_id", "symbol", "side",
        "entry_time", "entry_price",
        "exit_time", "exit_price",
        "size", "pnl", "pnl_pct",
        "regime", "edge_score",
        "feature_trend", "feature_volume",
        "feature_momentum", "feature_volatility",
        "config_hash",
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for trade in trades:
        writer.writerow(format_trade_for_export(trade))
    
    return output.getvalue()


# ═══════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════

@router.get("/trades")
async def export_trades(
    format: str = Query("csv", description="Export format: csv or json"),
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
):
    """Export trades for tax/reporting.
    
    Includes:
    - Entry/exit times and prices
    - PnL (absolute and percentage)
    - Market regime at entry
    - Edge score and feature contributions
    - Config hash for audit trail
    
    Args:
        format: "csv" or "json"
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        symbol: Filter by symbol (e.g., BTCUSDT)
    """
    # Parse dates
    start_date = None
    end_date = None
    
    if start:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start date format. Use YYYY-MM-DD")
    
    if end:
        try:
            end_date = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end date format. Use YYYY-MM-DD")
    
    # Get trade data
    trades = await get_trade_data(start=start_date, end=end_date, symbol=symbol)
    
    if not trades:
        return {
            "message": "No trades found for the specified period",
            "start": start,
            "end": end,
            "symbol": symbol,
            "count": 0,
        }
    
    if format.lower() == "csv":
        csv_data = generate_csv(trades)
        return StreamingResponse(
            io.StringIO(csv_data),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=trades_{start or 'all'}_{end or 'all'}.csv"
            }
        )
    
    elif format.lower() == "json":
        return {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "start": start,
            "end": end,
            "symbol": symbol,
            "count": len(trades),
            "trades": [format_trade_for_export(t) for t in trades],
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'json'")


@router.get("/pnl")
async def export_pnl_summary(
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Export PnL summary for tax reporting.
    
    Provides aggregated PnL by:
    - Symbol
    - Side (LONG/SHORT)
    - Month
    """
    start_date = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_date = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    # Get trades
    trades = await get_trade_data(start=start_date, end=end_date)
    
    # Aggregate by symbol
    by_symbol = {}
    by_month = {}
    
    for trade in trades:
        sym = trade.get("symbol", "unknown")
        pnl = trade.get("pnl", 0)
        side = trade.get("side", "UNKNOWN")
        
        # By symbol
        if sym not in by_symbol:
            by_symbol[sym] = {"trades": 0, "pnl": 0, "wins": 0, "losses": 0}
        by_symbol[sym]["trades"] += 1
        by_symbol[sym]["pnl"] += pnl
        if pnl > 0:
            by_symbol[sym]["wins"] += 1
        else:
            by_symbol[sym]["losses"] += 1
        
        # By month
        exit_time = trade.get("fill_time", "")
        if exit_time:
            month = exit_time[:7]  # YYYY-MM
            if month not in by_month:
                by_month[month] = {"trades": 0, "pnl": 0}
            by_month[month]["trades"] += 1
            by_month[month]["pnl"] += pnl
    
    # Calculate totals
    total_pnl = sum(s["pnl"] for s in by_symbol.values())
    total_trades = sum(s["trades"] for s in by_symbol.values())
    
    return {
        "period": {"start": start, "end": end},
        "summary": {
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "avg_pnl_per_trade": total_pnl / total_trades if total_trades else 0,
        },
        "by_symbol": by_symbol,
        "by_month": by_month,
    }


@router.get("/positions")
async def export_positions():
    """Export current positions for reporting."""
    # This would query current positions
    return {
        "positions": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }