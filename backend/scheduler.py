"""Async Evaluation Scheduler — the heartbeat of Sentinel Edge.

EvaluationScheduler runs an asyncio loop that evaluates every active ticker
concurrently every EVAL_INTERVAL seconds.

For each ticker it:
  1. Fetches price + volume (yfinance, 30 s shared cache)
  2. Updates ORB tracker (5m / 15m / 30m ranges, ET-anchored)
  3. Updates ATR calculator (14-period true range)
  4. Scores the signal (5-layer ±10 with volume Z-score)
  5. Reads live position state from PositionTracker (change stream or self-sovereign)
  6. Updates self-sovereign PnL from live price (SELF_SOVEREIGN mode only)
  7. Passes ALL risk parameters to DecisionEngine.decide()
  8. Sends the decision to Pulse — silently suppressed in standalone mode
  9. Notifies PositionTracker of the decision (entry/exit bookkeeping)
 10. Updates enriched ticker_state for the REST API
 11. Records the decision in the 50-entry decision feed
 12. Runs BaseSignal plugins
 13. Persists ORB levels to MongoDB
"""
import logging
import asyncio
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

from atr import ATRCalculator
from correlation import CorrelationEngine
from engine import DecisionEngine, Decision
from market_hours import MarketHours
from metrics import (
    analyst_plugin_signals_total,
    edge_engine_paused,
    edge_engine_running,
    edge_eval_duration,
    ticker_active_count,
    ticker_evaluation_total,
)
from orb import ORBTracker, ORBLevel
from position_tracker import PositionTracker
from price_fetcher import PriceFetcher
from pulse_client import PulseClient
from signals import SignalEngine, TrendDirection

logger = logging.getLogger(__name__)


class EvaluationScheduler:
    """Continuously evaluate tickers and make decisions."""

    DEFAULT_TICKERS = ["SPY", "QQQ", "NVDA", "AAPL"]
    EVAL_INTERVAL   = 1   # seconds between full evaluation sweeps

    def __init__(
        self,
        pulse_client:    PulseClient,
        price_fetcher:   PriceFetcher,
        orb_tracker:     ORBTracker,
        atr_calculator:  ATRCalculator,
        signal_engine:   SignalEngine,
        decision_engine: DecisionEngine,
        market_hours:    MarketHours,
        db=None,
    ):
        self.pulse    = pulse_client
        self.prices   = price_fetcher
        self.orb      = orb_tracker
        self.atr      = atr_calculator
        self.signals  = signal_engine
        self.decisions = decision_engine
        self.market_hours = market_hours
        self.db       = db

        self.active_tickers: List[str] = self.DEFAULT_TICKERS.copy()
        self.running = False
        self.paused  = False

        self.prev_prices:    Dict[str, float] = {}
        self.ticker_configs: Dict[str, Dict]  = {}
        self.ticker_state:   Dict[str, Dict]  = {}
        self.recent_decisions: list           = []
        self.signal_plugins:   list           = []

        # Dual-mode position tracker (change stream primary, self-sovereign fallback)
        self.position_tracker = PositionTracker(
            db=db,
            decision_engine=decision_engine,
        )

        self.correlation = CorrelationEngine(
            db=self.db,
            pulse_base_url=os.getenv("PULSE_API_URL", "http://pulse:8001"),
            window_sec=120,
            min_symbols=3,
            cooldown_sec=300,
        )

        logger.info("Scheduler initialised with %d tickers", len(self.active_tickers))

    # ─────────────────────────────────────────────────────────────────────────
    # Evaluation
    # ─────────────────────────────────────────────────────────────────────────

    async def evaluate_ticker(self, symbol: str):
        """Full evaluation pipeline for a single ticker (see module docstring)."""
        start_time = time.time()

        try:
            # ── 1. Price + volume ────────────────────────────────────────────
            result = await self.prices.get_price_with_volume(symbol)
            if not result:
                logger.warning("Could not fetch data for %s", symbol)
                return
            price, volume = result
            now = datetime.now()

            # ── 2. ORB update + breakout detection ───────────────────────────
            orb_levels = self.orb.update(symbol, price, now)
            for bo in self.orb.check_breakout(symbol, price):
                logger.warning(
                    "🚨 BREAKOUT: %s %s on %dm",
                    symbol, bo["direction"].upper(), bo["timeframe"],
                )

            # ── 3. ATR ───────────────────────────────────────────────────────
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

            # ── 4. Price momentum ────────────────────────────────────────────
            price_change_pct = 0.0
            if symbol in self.prev_prices and self.prev_prices[symbol] > 0:
                price_change_pct = (
                    (price - self.prev_prices[symbol]) / self.prev_prices[symbol]
                ) * 100
            self.prev_prices[symbol] = price

            # ── 5. Volume & signal scoring ───────────────────────────────────
            self.signals.update_avg_volume(symbol, volume)
            volume_ratio  = self.signals.get_volume_ratio(symbol, volume)
            volume_zscore = self.signals.compute_volume_zscore(symbol, volume)

            orb_high: Optional[float] = None
            orb_low:  Optional[float] = None
            if 15 in orb_levels and orb_levels[15].is_valid:
                orb_high = orb_levels[15].high
                orb_low  = orb_levels[15].low

            trend, signal_strength = self.signals.evaluate_signal(
                symbol=symbol,
                price=price,
                orb_high=orb_high,
                orb_low=orb_low,
                volume_ratio=volume_ratio,
                atr=atr,
                price_change_pct=price_change_pct,
                volume_zscore=volume_zscore,
            )

            # ── 6. Position state (PositionTracker: change stream or self-sovereign)
            # In SELF_SOVEREIGN mode, update local PnL from live price before
            # passing it to DecisionEngine so all risk guards fire correctly.
            self.position_tracker.update_price(symbol, price)
            pos = self.position_tracker.get(symbol)

            # ── 7. Decision — all risk parameters populated ──────────────────
            decision = self.decisions.decide(
                symbol=symbol,
                trend=trend,
                signal_strength=signal_strength,
                pnl=pos["pnl"],
                pnl_pct=pos["pnl_pct"],
                current_drawdown=pos["drawdown_pct"],
                has_position=pos["has_position"],
                trailing_enabled=pos["trailing_enabled"],
            )

            # ── 8. Send decision to Pulse ────────────────────────────────────
            if decision == Decision.BUY:
                logger.info("🚀 %s: BUY signal → Pulse", symbol)
                await self.pulse.send_decision(symbol, "buy")

            elif decision == Decision.STOP_BUYING:
                logger.warning("⛔ %s: STOP_BUYING → Pulse", symbol)
                await self.pulse.stop_buying(symbol)

            elif decision == Decision.ENABLE_TRAILING_STOP:
                trailing_pct = (
                    min(2.0, max(0.5, (atr / price) * 100 * 2))
                    if price > 0 else 1.5
                )
                logger.info("🎯 %s: ENABLE trailing stop %.2f%% → Pulse", symbol, trailing_pct)
                await self.pulse.enable_trailing_stop(symbol, trailing_pct)

            elif decision == Decision.TIGHTEN_TRAILING_STOP:
                logger.info("🎯 %s: TIGHTEN trailing stop → 0.5%% → Pulse", symbol)
                await self.pulse.enable_trailing_stop(symbol, 0.5)

            elif decision == Decision.TIGHTEN_STOP:
                logger.warning("⚠️ %s: TIGHTEN_STOP → Pulse", symbol)
                await self.pulse.send_decision(symbol, "tighten_stop")

            elif decision == Decision.EMERGENCY_EXIT:
                logger.error("🚨 %s: EMERGENCY EXIT → Pulse", symbol)
                await self.pulse.emergency_stop(symbol)

            # ── 9a. Notify PositionTracker of decision taken ─────────────────
            # Keeps optimistic state coherent while waiting for change stream
            # confirmation; also finalises trade in SELF_SOVEREIGN mode.
            self.position_tracker.on_decision(symbol, decision, entry_price=price)

            # ── 9. Correlation tracking ──────────────────────────────────────
            confidence = min(abs(signal_strength) / 10.0, 1.0)
            if decision == Decision.BUY:
                await self.correlation.record_signal(symbol, "BUY", confidence)
            elif decision in (Decision.STOP_BUYING, Decision.EMERGENCY_EXIT):
                await self.correlation.record_signal(symbol, "SELL", confidence)

            # ── 10. Decision feed (skip HOLD) ─────────────────────────────────
            if decision != Decision.HOLD:
                self.recent_decisions.insert(0, {
                    "symbol":          symbol,
                    "decision":        decision.value,
                    "signal_strength": round(signal_strength, 2),
                    "trend":           trend.name.lower(),
                    "confidence":      round(confidence, 3),
                    "price":           round(price, 4),
                    "pnl_pct":         round(pos["pnl_pct"], 3),
                    "has_position":    pos["has_position"],
                    "timestamp":       now.isoformat(),
                })
                self.recent_decisions = self.recent_decisions[:50]

            # ── 11. Enriched ticker state (GET /api/tickers) ──────────────────
            orb_data: Dict[str, Dict] = {}
            for tf, level in orb_levels.items():
                safe_low = level.low if level.low != float("inf") else 0.0
                orb_data[f"{tf}m"] = {
                    "high":        round(level.high, 4),
                    "low":         round(safe_low, 4),
                    "locked":      level.locked,
                    "range_width": round(level.range_width, 4),
                    "is_valid":    level.is_valid,
                }

            self.ticker_state[symbol] = {
                "symbol":           symbol,
                "enabled":          True,
                "current_price":    round(price, 4),
                "orb_levels":       orb_data,
                "signal_strength":  round(signal_strength, 2),
                "trend":            trend.name.lower(),
                "atr":              round(atr, 4),
                "volume_ratio":     round(volume_ratio, 4),
                "volume_zscore":    round(volume_zscore, 3),
                "last_decision":    decision.value,
                "confidence":       round(confidence, 3),
                # Position context visible in the dashboard
                "has_position":     pos["has_position"],
                "pnl":              round(pos["pnl"], 2),
                "pnl_pct":          round(pos["pnl_pct"], 3),
                "trailing_enabled": pos["trailing_enabled"],
                "drawdown_pct":     round(pos["drawdown_pct"], 3),
                "last_updated":     now.isoformat(),
            }

            # ── 12. BaseSignal plugins ─────────────────────────────────────────
            if self.signal_plugins and ohlcv_data is not None and not ohlcv_data.empty:
                market_data = {
                    "ohlcv":           ohlcv_data,
                    "price":           price,
                    "volume":          volume,
                    "atr":             atr,
                    "volume_ratio":    volume_ratio,
                    "volume_zscore":   volume_zscore,
                    "signal_strength": signal_strength,
                    "trend":           trend.name.lower(),
                    "orb_high":        orb_high,
                    "orb_low":         orb_low,
                }
                for plugin in self.signal_plugins:
                    try:
                        plugin_signal = await plugin.generate(symbol, market_data)
                        if plugin_signal and plugin_signal.action in ("BUY", "SELL"):
                            await self.correlation.record_signal(
                                symbol,
                                plugin_signal.action,
                                plugin_signal.confidence,
                            )
                            analyst_plugin_signals_total.labels(
                                plugin=plugin.name,
                                symbol=symbol,
                                action=plugin_signal.action,
                            ).inc()
                            logger.info(
                                "🔌 Plugin [%s] → %s %s conf=%.2f: %s",
                                plugin.name, plugin_signal.action, symbol,
                                plugin_signal.confidence, plugin_signal.reason,
                            )
                    except Exception as pe:
                        logger.debug("Plugin %s error for %s: %s", plugin.name, symbol, pe)

            # ── 13. MongoDB ORB persistence ────────────────────────────────────
            await self._persist_orb(symbol, orb_levels, now)

            ticker_evaluation_total.labels(symbol=symbol).inc()

        except Exception as e:
            logger.error("Error evaluating %s: %s", symbol, e, exc_info=True)

        finally:
            edge_eval_duration.labels(symbol=symbol).observe(time.time() - start_time)

    async def evaluate_all(self):
        """Evaluate all active tickers concurrently."""
        if self.paused:
            return
        self.market_hours.update_metrics()
        ticker_active_count.set(len(self.active_tickers))
        await asyncio.gather(
            *[self.evaluate_ticker(s) for s in self.active_tickers],
            return_exceptions=True,
        )

    async def run(self):
        """Main evaluation loop — runs until stop() is called."""
        self.running = True
        edge_engine_running.set(1)
        logger.info(
            "🚀 Sentinel Edge scheduler started (interval: %ds, position tracking: %s)",
            self.EVAL_INTERVAL, self.position_tracker.mode_name,
        )

        # Start position tracker background task (change stream probe + auto-upgrade)
        self.position_tracker.start()

        await self._load_orb_from_db()

        try:
            while self.running:
                await self.evaluate_all()
                await asyncio.sleep(self.EVAL_INTERVAL)
        except Exception as e:
            logger.error("Scheduler fatal error: %s", e, exc_info=True)
        finally:
            self.running = False
            edge_engine_running.set(0)
            logger.info("⏸️ Sentinel Edge scheduler stopped")

    # ─────────────────────────────────────────────────────────────────────────
    # MongoDB helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _persist_orb(self, symbol: str, orb_levels: Dict, now: datetime):
        """Upsert ORB levels to MongoDB (one document per symbol per trading day)."""
        if self.db is None:
            return
        try:
            levels_doc: Dict[str, Dict] = {}
            for tf, level in orb_levels.items():
                if level.is_valid:
                    safe_low = level.low if level.low != float("inf") else 0.0
                    levels_doc[str(tf)] = {
                        "high":   level.high,
                        "low":    safe_low,
                        "locked": level.locked,
                        "is_valid": True,
                    }
            if levels_doc:
                await self.db.orb_levels.update_one(
                    {"symbol": symbol, "date": now.strftime("%Y-%m-%d")},
                    {"$set": {
                        "symbol":     symbol,
                        "date":       now.strftime("%Y-%m-%d"),
                        "levels":     levels_doc,
                        "updated_at": now,
                    }},
                    upsert=True,
                )
        except Exception as e:
            logger.error("Failed to persist ORB for %s: %s", symbol, e)

    async def _load_orb_from_db(self):
        """Restore today's ORB levels from MongoDB on startup."""
        if self.db is None:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            count = 0
            async for doc in self.db.orb_levels.find({"date": today}, {"_id": 0}):
                symbol = doc["symbol"]
                if symbol not in self.orb.orb_levels:
                    self.orb.orb_levels[symbol] = {}
                for tf_str, level_data in doc.get("levels", {}).items():
                    tf = int(tf_str)
                    if tf in [5, 15, 30] and level_data.get("is_valid"):
                        self.orb.orb_levels[symbol][tf] = ORBLevel(
                            high=level_data["high"],
                            low=level_data["low"],
                            locked=level_data["locked"],
                            start_time=datetime.now(),
                        )
                        count += 1
            if count:
                logger.info("✅ Restored %d ORB levels from MongoDB", count)
        except Exception as e:
            logger.error("Failed to load ORB from DB: %s", e)

    # ─────────────────────────────────────────────────────────────────────────
    # Runtime control
    # ─────────────────────────────────────────────────────────────────────────

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
        self.position_tracker.stop()
        logger.info("⏹️ Stopping scheduler...")

    def add_ticker(self, symbol: str):
        if symbol not in self.active_tickers:
            self.active_tickers.append(symbol)
            logger.info("➕ Added %s to watch list", symbol)

    def remove_ticker(self, symbol: str):
        if symbol in self.active_tickers:
            self.active_tickers.remove(symbol)
            self.ticker_state.pop(symbol, None)
            self.position_tracker.remove(symbol)
            logger.info("➖ Removed %s from watch list", symbol)
