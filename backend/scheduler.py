"""Async Scheduler for Continuous Evaluation"""
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

from orb import ORBTracker, ORBLevel
from atr import ATRCalculator
from signals import SignalEngine, TrendDirection
from engine import DecisionEngine, Decision
from pulse_client import PulseClient
from price_fetcher import PriceFetcher
from market_hours import MarketHours
from correlation import CorrelationEngine
from metrics import (
    edge_engine_running,
    edge_engine_paused,
    ticker_evaluation_total,
    ticker_active_count,
    edge_eval_duration,
)

logger = logging.getLogger(__name__)


class EvaluationScheduler:
    """Continuously evaluate tickers and make decisions"""

    DEFAULT_TICKERS = ["SPY", "QQQ", "NVDA", "AAPL"]
    EVAL_INTERVAL = 1  # seconds

    def __init__(
        self,
        pulse_client: PulseClient,
        price_fetcher: PriceFetcher,
        orb_tracker: ORBTracker,
        atr_calculator: ATRCalculator,
        signal_engine: SignalEngine,
        decision_engine: DecisionEngine,
        market_hours: MarketHours,
        db=None,  # Motor MongoDB database (optional)
    ):
        self.pulse = pulse_client
        self.prices = price_fetcher
        self.orb = orb_tracker
        self.atr = atr_calculator
        self.signals = signal_engine
        self.decisions = decision_engine
        self.market_hours = market_hours
        self.db = db

        self.active_tickers: List[str] = self.DEFAULT_TICKERS.copy()
        self.running = False
        self.paused = False

        # Track previous prices for momentum calculation
        self.prev_prices: Dict[str, float] = {}

        # Track metric toggles per ticker
        self.ticker_configs: Dict[str, Dict] = {}

        # Enriched per-ticker state for the API
        self.ticker_state: Dict[str, Dict] = {}

        # Recent non-HOLD decisions for the decision feed (newest first)
        self.recent_decisions: list = []

        # Correlation engine (async, Motor-backed)
        import os
        self.correlation = CorrelationEngine(
            db=self.db,
            pulse_base_url=os.getenv("PULSE_API_URL", "http://pulse:8001"),
            window_sec=120,
            min_symbols=3,
            cooldown_sec=300,
        )

        logger.info(f"Scheduler initialized with {len(self.active_tickers)} tickers")

    # ─────────────────────────────────────────────────────────────────────
    # Evaluation
    # ─────────────────────────────────────────────────────────────────────

    async def evaluate_ticker(self, symbol: str):
        """Evaluate a single ticker"""
        start_time = time.time()

        try:
            # Fetch current price and volume
            result = await self.prices.get_price_with_volume(symbol)
            if not result:
                logger.warning(f"Could not fetch data for {symbol}")
                return

            price, volume = result
            now = datetime.now()

            # ── ORB update ──────────────────────────────────────────────
            orb_levels = self.orb.update(symbol, price, now)

            # Detect breakouts
            breakouts = self.orb.check_breakout(symbol, price)
            for bo in breakouts:
                logger.warning(
                    f"🚨 BREAKOUT: {symbol} {bo['direction'].upper()} on {bo['timeframe']}m"
                )

            # ── ATR ─────────────────────────────────────────────────────
            ohlcv_data = await self.prices.get_ohlcv(symbol)
            atr = 0.0
            if ohlcv_data is not None and not ohlcv_data.empty:
                latest = ohlcv_data.iloc[-1]
                atr = self.atr.update(
                    symbol,
                    float(latest["High"]),
                    float(latest["Low"]),
                    float(latest["Close"]),
                )

            # ── Price momentum ──────────────────────────────────────────
            price_change_pct = 0.0
            if symbol in self.prev_prices and self.prev_prices[symbol] > 0:
                price_change_pct = (
                    (price - self.prev_prices[symbol]) / self.prev_prices[symbol]
                ) * 100
            self.prev_prices[symbol] = price

            # ── Volume & signal ─────────────────────────────────────────
            self.signals.update_avg_volume(symbol, volume)
            volume_ratio = self.signals.get_volume_ratio(symbol, volume)

            orb_high: Optional[float] = None
            orb_low: Optional[float] = None
            if 15 in orb_levels and orb_levels[15].is_valid:
                orb_high = orb_levels[15].high
                orb_low = orb_levels[15].low

            trend, signal_strength = self.signals.evaluate_signal(
                symbol=symbol,
                price=price,
                orb_high=orb_high,
                orb_low=orb_low,
                volume_ratio=volume_ratio,
                atr=atr,
                price_change_pct=price_change_pct,
            )

            # ── Decision ─────────────────────────────────────────────────
            decision = self.decisions.decide(
                symbol=symbol,
                trend=trend,
                signal_strength=signal_strength,
                pnl=0.0,
                pnl_pct=0.0,
                current_drawdown=0.0,
                has_position=False,
                trailing_enabled=False,
            )

            # ── Send to Pulse ────────────────────────────────────────────
            if decision == Decision.BUY:
                logger.info(f"🚀 {symbol}: Sending BUY signal to Pulse")
                await self.pulse.send_decision(symbol, "buy")

            elif decision == Decision.STOP_BUYING:
                logger.warning(f"⛔ {symbol}: Sending STOP_BUYING signal to Pulse")
                await self.pulse.stop_buying(symbol)

            elif decision == Decision.ENABLE_TRAILING_STOP:
                trailing_pct = min(2.0, max(0.5, (atr / price) * 100 * 2)) if price > 0 else 1.5
                logger.info(f"🎯 {symbol}: Enabling trailing stop ({trailing_pct:.2f}%)")
                await self.pulse.enable_trailing_stop(symbol, trailing_pct)

            elif decision == Decision.TIGHTEN_TRAILING_STOP:
                logger.info(f"🎯 {symbol}: AUTO-TIGHTENING trailing stop → 0.5%")
                await self.pulse.enable_trailing_stop(symbol, 0.5)

            elif decision == Decision.EMERGENCY_EXIT:
                logger.error(f"🚨 {symbol}: EMERGENCY EXIT triggered")
                await self.pulse.emergency_stop(symbol)

            # ── Correlation tracking (async) ─────────────────────────────
            if decision == Decision.BUY:
                await self.correlation.record_signal(
                    symbol, "BUY", min(abs(signal_strength) / 10.0, 1.0)
                )
            elif decision in (Decision.STOP_BUYING, Decision.EMERGENCY_EXIT):
                # Map to "SELL" so the engine recognises it as a bearish signal
                await self.correlation.record_signal(
                    symbol, "SELL", min(abs(signal_strength) / 10.0, 1.0)
                )

            # ── Record decision for feed (skip HOLD) ─────────────────────
            if decision != Decision.HOLD:
                entry = {
                    "symbol": symbol,
                    "decision": decision.value,
                    "signal_strength": round(signal_strength, 2),
                    "trend": trend.name.lower(),
                    "confidence": round(min(abs(signal_strength) / 10.0, 1.0), 3),
                    "price": round(price, 4),
                    "timestamp": now.isoformat(),
                }
                self.recent_decisions.insert(0, entry)
                self.recent_decisions = self.recent_decisions[:50]

            # ── Store enriched ticker state (for /api/tickers) ────────────
            orb_data: Dict[str, Dict] = {}
            for tf, level in orb_levels.items():
                safe_low = level.low if level.low != float("inf") else 0.0
                orb_data[f"{tf}m"] = {
                    "high": round(level.high, 4),
                    "low": round(safe_low, 4),
                    "locked": level.locked,
                    "range_width": round(level.range_width, 4),
                    "is_valid": level.is_valid,
                }

            confidence = min(abs(signal_strength) / 10.0, 1.0)
            self.ticker_state[symbol] = {
                "symbol": symbol,
                "enabled": True,
                "current_price": round(price, 4),
                "orb_levels": orb_data,
                "signal_strength": round(signal_strength, 2),
                "trend": trend.name.lower(),
                "atr": round(atr, 4),
                "volume_ratio": round(volume_ratio, 4),
                "last_decision": decision.value,
                "confidence": round(confidence, 3),
                "last_updated": now.isoformat(),
            }

            # ── MongoDB ORB persistence ───────────────────────────────────
            await self._persist_orb(symbol, orb_levels, now)

            # ── Prometheus ────────────────────────────────────────────────
            ticker_evaluation_total.labels(symbol=symbol).inc()

        except Exception as e:
            logger.error(f"Error evaluating {symbol}: {e}", exc_info=True)

        finally:
            duration = time.time() - start_time
            edge_eval_duration.labels(symbol=symbol).observe(duration)

    async def evaluate_all(self):
        """Evaluate all active tickers"""
        if self.paused:
            return

        self.market_hours.update_metrics()
        ticker_active_count.set(len(self.active_tickers))

        tasks = [self.evaluate_ticker(s) for s in self.active_tickers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run(self):
        """Main evaluation loop"""
        self.running = True
        edge_engine_running.set(1)

        logger.info(f"🚀 Sentinel Edge scheduler started (interval: {self.EVAL_INTERVAL}s)")

        # Restore ORB levels from MongoDB on startup
        await self._load_orb_from_db()

        try:
            while self.running:
                await self.evaluate_all()
                await asyncio.sleep(self.EVAL_INTERVAL)
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
        finally:
            self.running = False
            edge_engine_running.set(0)
            logger.info("⏸️ Sentinel Edge scheduler stopped")

    # ─────────────────────────────────────────────────────────────────────
    # MongoDB helpers
    # ─────────────────────────────────────────────────────────────────────

    async def _persist_orb(self, symbol: str, orb_levels: Dict, now: datetime):
        """Save ORB levels to MongoDB (upsert per symbol per day)."""
        if self.db is None:
            return
        try:
            levels_doc: Dict[str, Dict] = {}
            for tf, level in orb_levels.items():
                if level.is_valid:
                    safe_low = level.low if level.low != float("inf") else 0.0
                    levels_doc[str(tf)] = {
                        "high": level.high,
                        "low": safe_low,
                        "locked": level.locked,
                        "is_valid": True,
                    }
            if levels_doc:
                await self.db.orb_levels.update_one(
                    {"symbol": symbol, "date": now.strftime("%Y-%m-%d")},
                    {
                        "$set": {
                            "symbol": symbol,
                            "date": now.strftime("%Y-%m-%d"),
                            "levels": levels_doc,
                            "updated_at": now,
                        }
                    },
                    upsert=True,
                )
        except Exception as e:
            logger.error(f"Failed to persist ORB for {symbol}: {e}")

    async def _load_orb_from_db(self):
        """Restore ORB levels from MongoDB for today."""
        if self.db is None:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            cursor = self.db.orb_levels.find({"date": today}, {"_id": 0})
            count = 0
            async for doc in cursor:
                symbol = doc["symbol"]
                if symbol not in self.orb.orb_levels:
                    self.orb.orb_levels[symbol] = {}
                for tf_str, level_data in doc.get("levels", {}).items():
                    tf = int(tf_str)
                    if tf in [5, 15, 30] and level_data.get("is_valid"):
                        orb = ORBLevel(
                            high=level_data["high"],
                            low=level_data["low"],
                            locked=level_data["locked"],
                            start_time=datetime.now(),
                        )
                        self.orb.orb_levels[symbol][tf] = orb
                        count += 1
            if count:
                logger.info(f"✅ Restored {count} ORB levels from MongoDB")
        except Exception as e:
            logger.error(f"Failed to load ORB from DB: {e}")

    # ─────────────────────────────────────────────────────────────────────
    # Control
    # ─────────────────────────────────────────────────────────────────────

    def pause(self):
        self.paused = True
        edge_engine_paused.set(1)
        logger.info("⏸️ Scheduler paused")

    def resume(self):
        self.paused = False
        edge_engine_paused.set(0)
        logger.info("▶️ Scheduler resumed")

    def stop(self):
        self.running = False
        logger.info("⏹️ Stopping scheduler...")

    def add_ticker(self, symbol: str):
        if symbol not in self.active_tickers:
            self.active_tickers.append(symbol)
            logger.info(f"➕ Added {symbol} to watch list")

    def remove_ticker(self, symbol: str):
        if symbol in self.active_tickers:
            self.active_tickers.remove(symbol)
            self.ticker_state.pop(symbol, None)
            logger.info(f"➖ Removed {symbol} from watch list")
