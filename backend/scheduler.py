"""Async Scheduler for Continuous Evaluation"""
import logging
import asyncio
import time
from datetime import datetime
from typing import List
from orb import ORBTracker
from atr import ATRCalculator
from signals import SignalEngine, TrendDirection
from engine import DecisionEngine, Decision
from pulse_client import PulseClient
from price_fetcher import PriceFetcher
from market_hours import MarketHours
from metrics import (
    edge_engine_running,
    edge_engine_paused,
    ticker_evaluation_total,
    ticker_active_count,
    edge_eval_duration
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
        market_hours: MarketHours
    ):
        self.pulse = pulse_client
        self.prices = price_fetcher
        self.orb = orb_tracker
        self.atr = atr_calculator
        self.signals = signal_engine
        self.decisions = decision_engine
        self.market_hours = market_hours
        
        self.active_tickers: List[str] = self.DEFAULT_TICKERS.copy()
        self.running = False
        self.paused = False
        
        # Track previous prices for momentum calculation
        self.prev_prices = {}
        
        logger.info(f"Scheduler initialized with {len(self.active_tickers)} tickers")
    
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
            
            # Update ORB levels
            orb_levels = self.orb.update(symbol, price, now)
            
            # Check for breakouts
            breakouts = self.orb.check_breakout(symbol, price)
            if breakouts:
                for breakout in breakouts:
                    logger.warning(
                        f"🚨 BREAKOUT: {symbol} {breakout['direction'].upper()} on {breakout['timeframe']}m timeframe"
                    )
            
            # Fetch OHLCV for ATR
            ohlcv_data = await self.prices.get_ohlcv(symbol)
            if ohlcv_data is not None and not ohlcv_data.empty:
                # Update ATR with latest bar
                latest = ohlcv_data.iloc[-1]
                atr = self.atr.update(
                    symbol,
                    float(latest['High']),
                    float(latest['Low']),
                    float(latest['Close'])
                )
            else:
                atr = 0.0
            
            # Calculate price change percentage
            price_change_pct = 0.0
            if symbol in self.prev_prices:
                price_change_pct = ((price - self.prev_prices[symbol]) / self.prev_prices[symbol]) * 100
            self.prev_prices[symbol] = price
            
            # Update volume tracking
            self.signals.update_avg_volume(symbol, volume)
            volume_ratio = self.signals.get_volume_ratio(symbol, volume)
            
            # Get ORB levels for primary timeframe (15m)
            orb_high = None
            orb_low = None
            if 15 in orb_levels and orb_levels[15].is_valid:
                orb_high = orb_levels[15].high
                orb_low = orb_levels[15].low
            
            # Evaluate signal
            trend, signal_strength = self.signals.evaluate_signal(
                symbol=symbol,
                price=price,
                orb_high=orb_high,
                orb_low=orb_low,
                volume_ratio=volume_ratio,
                atr=atr,
                price_change_pct=price_change_pct
            )
            
            # Make decision (using mock P&L data for now)
            decision = self.decisions.decide(
                symbol=symbol,
                trend=trend,
                signal_strength=signal_strength,
                pnl=0.0,  # Would come from Pulse
                pnl_pct=0.0,
                current_drawdown=0.0,
                has_position=False,  # Would come from Pulse
                trailing_enabled=False
            )
            
            # Send decision to Pulse based on decision type
            if decision == Decision.BUY:
                logger.info(f"🚀 {symbol}: Sending BUY signal to Pulse")
                await self.pulse.send_decision(symbol, "buy")
            
            elif decision == Decision.STOP_BUYING:
                logger.warning(f"⛔ {symbol}: Sending STOP_BUYING signal to Pulse")
                await self.pulse.stop_buying(symbol)
            
            elif decision == Decision.ENABLE_TRAILING_STOP:
                # Calculate trailing stop based on ATR
                trailing_pct = min(2.0, max(0.5, (atr / price) * 100 * 2))
                logger.info(f"🎯 {symbol}: Enabling trailing stop ({trailing_pct:.2f}%)")
                await self.pulse.enable_trailing_stop(symbol, trailing_pct)
            
            elif decision == Decision.EMERGENCY_EXIT:
                logger.error(f"🚨 {symbol}: EMERGENCY EXIT triggered")
                await self.pulse.emergency_stop(symbol)
            
            # Update metrics
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
        
        # Update market hours
        self.market_hours.update_metrics()
        
        # Update active ticker count
        ticker_active_count.set(len(self.active_tickers))
        
        # Evaluate all tickers concurrently
        tasks = [self.evaluate_ticker(symbol) for symbol in self.active_tickers]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run(self):
        """Main evaluation loop"""
        
        self.running = True
        edge_engine_running.set(1)
        
        logger.info(f"🚀 Sentinel Edge scheduler started (interval: {self.EVAL_INTERVAL}s)")
        
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
    
    def pause(self):
        """Pause evaluations"""
        self.paused = True
        edge_engine_paused.set(1)
        logger.info("⏸️ Scheduler paused")
    
    def resume(self):
        """Resume evaluations"""
        self.paused = False
        edge_engine_paused.set(0)
        logger.info("▶️ Scheduler resumed")
    
    def stop(self):
        """Stop scheduler"""
        self.running = False
        logger.info("⏹️ Stopping scheduler...")
    
    def add_ticker(self, symbol: str):
        """Add ticker to watch list"""
        if symbol not in self.active_tickers:
            self.active_tickers.append(symbol)
            logger.info(f"➕ Added {symbol} to watch list")
    
    def remove_ticker(self, symbol: str):
        """Remove ticker from watch list"""
        if symbol in self.active_tickers:
            self.active_tickers.remove(symbol)
            logger.info(f"➖ Removed {symbol} from watch list")
