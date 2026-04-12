"""Backtesting & Dry-Run Engine - Phase 5"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd


logger = logging.getLogger(__name__)


class BacktestEngine:
    """Engine for historical backtesting and dry-run simulations."""
    
    def __init__(self, price_fetcher, decision_engine):
        self.price_fetcher = price_fetcher
        self.decision_engine = decision_engine
        self.orb = {}  # symbol -> ORB levels
        self.atr = {}  # symbol -> ATR values
        self.signal_scores = {}  # symbol -> signal scores
        logger.info("BacktestEngine initialized")


    async def run_backtest(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 10000.0
    ):
        """Run historical backtest for a symbol."""
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")

        # Fetch historical data
        try:
            df = await self.price_fetcher.get_ohlcv(symbol, period="60d", interval="5m")
            if df is None or df.empty:
                return {"error": "No data available for backtest"}
        except Exception as e:
            logger.error(f"Backtest data fetch error: {e}")
            return {"error": str(e)}

        # Filter date range
        try:
            df = df.loc[start_date:end_date].copy()
        except Exception:
            # If date filtering fails, use all data
            pass

        if df.empty:
            return {"error": "No data in specified date range"}

        results = {
            "symbol": symbol,
            "trades": [],
            "final_capital": initial_capital,
            "win_rate": 0.0,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "equity_curve": [],
            "trade_points": []
        }

        position = None
        equity = initial_capital
        equity_curve = []
        max_equity = initial_capital
        drawdown = 0.0
        max_drawdown = 0.0

        for idx, row in df.iterrows():
            timestamp = idx.isoformat() if hasattr(idx, 'isoformat') else str(idx)
            price = float(row['Close'])
            volume = float(row.get('Volume', 0))

            # Simulate signal calculation (simplified)
            signal_score = self._calculate_signal_score(df, idx, price)
            
            # Simulate decision (simplified for backtest)
            decision = self._simulate_decision(
                symbol=symbol,
                price=price,
                signal_score=signal_score,
                has_position=position is not None
            )

            trade_marker = None
            if decision == "BUY" and not position:
                position = {
                    "entry_price": price,
                    "entry_time": timestamp,
                    "size": initial_capital * 0.1 / price  # 10% position
                }
                trade_marker = {"time": timestamp, "price": price, "type": "buy"}
                
            elif decision == "SELL" and position:
                pnl_pct = (price - position["entry_price"]) / position["entry_price"]
                equity += equity * pnl_pct * 0.1  # 10% position sizing
                
                results["trades"].append({
                    "entry_time": position["entry_time"],
                    "exit_time": timestamp,
                    "entry_price": position["entry_price"],
                    "exit_price": price,
                    "pnl_pct": round(pnl_pct * 100, 2)
                })
                
                trade_marker = {"time": timestamp, "price": price, "type": "sell"}
                position = None

            # Track equity
            equity_curve.append({"time": timestamp, "equity": round(equity, 2)})
            max_equity = max(max_equity, equity)
            drawdown = (max_equity - equity) / max_equity * 100 if max_equity > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

            if trade_marker:
                results["trade_points"].append(trade_marker)

        # Calculate final stats
        if results["trades"]:
            wins = sum(1 for t in results["trades"] if t["pnl_pct"] > 0)
            results["win_rate"] = round(wins / len(results["trades"]) * 100, 1)
            results["total_return_pct"] = round(
                (equity - initial_capital) / initial_capital * 100, 2
            )
            results["max_drawdown_pct"] = round(max_drawdown, 2)
        else:
            results["win_rate"] = 0.0
            results["total_return_pct"] = 0.0
            results["max_drawdown_pct"] = round(max_drawdown, 2)

        results["equity_curve"] = equity_curve
        results["final_capital"] = round(equity, 2)

        logger.info(
            f"✅ Backtest complete: {len(results['trades'])} trades | "
            f"Return: {results['total_return_pct']}%"
        )
        return results


    def _calculate_signal_score(
        self,
        df: pd.DataFrame,
        idx,
        price: float
    ) -> float:
        """Calculate simplified signal score for backtest."""
        # Simple momentum signal
        if len(df) < 20:
            return 0.0
        
        recent = df.loc[:idx].iloc[-20:]
        if recent.empty:
            return 0.0
            
        ma20 = recent['Close'].mean()
        return (price - ma20) / ma20 * 100 if ma20 > 0 else 0.0


    def _simulate_decision(
        self,
        symbol: str,
        price: float,
        signal_score: float,
        has_position: bool
    ) -> str:
        """Simulate decision logic for backtest."""
        # Simple rules for backtest
        if has_position:
            return "HOLD"  # Simplified
        
        # Entry signals
        if signal_score > 1.0:
            return "BUY"
        elif signal_score < -1.0:
            return "SELL"
        return "HOLD"


    def is_dry_run_enabled(self) -> bool:
        """Check if dry-run mode is enabled."""
        import os
        return os.getenv("DRY_RUN", "true").lower() == "true"