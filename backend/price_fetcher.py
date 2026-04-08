"""Price Data Fetcher using yfinance"""
import logging
import time
from typing import Dict, Optional, Tuple
import yfinance as yf
from datetime import datetime, timedelta
from metrics import price_fetch_latency, price_fetch_failures_total, current_price

logger = logging.getLogger(__name__)

class PriceFetcher:
    """Fetch real-time price data from yfinance"""
    
    def __init__(self):
        self.cache: Dict[str, Tuple[float, datetime]] = {}
        self.cache_duration = timedelta(seconds=5)  # Cache for 5 seconds
        logger.info("Price Fetcher initialized (yfinance)")
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        
        # Check cache
        if symbol in self.cache:
            cached_price, cached_time = self.cache[symbol]
            if datetime.now() - cached_time < self.cache_duration:
                return cached_price
        
        # Fetch from yfinance
        start_time = time.time()
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            
            duration = time.time() - start_time
            price_fetch_latency.labels(source="yfinance").observe(duration)
            
            if data.empty:
                price_fetch_failures_total.labels(symbol=symbol, source="yfinance").inc()
                logger.warning(f"⚠️ No price data for {symbol}")
                return None
            
            price = float(data['Close'].iloc[-1])
            
            # Update cache
            self.cache[symbol] = (price, datetime.now())
            
            # Update metric
            current_price.labels(symbol=symbol).set(price)
            
            return price
        
        except Exception as e:
            price_fetch_failures_total.labels(symbol=symbol, source="yfinance").inc()
            logger.error(f"❌ Error fetching price for {symbol}: {e}")
            return None
    
    async def get_price_with_volume(self, symbol: str) -> Optional[Tuple[float, float]]:
        """Get current price and volume"""
        
        start_time = time.time()
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            
            duration = time.time() - start_time
            price_fetch_latency.labels(source="yfinance").observe(duration)
            
            if data.empty:
                price_fetch_failures_total.labels(symbol=symbol, source="yfinance").inc()
                return None
            
            price = float(data['Close'].iloc[-1])
            volume = float(data['Volume'].iloc[-1])
            
            # Update cache
            self.cache[symbol] = (price, datetime.now())
            
            # Update metric
            current_price.labels(symbol=symbol).set(price)
            
            return price, volume
        
        except Exception as e:
            price_fetch_failures_total.labels(symbol=symbol, source="yfinance").inc()
            logger.error(f"❌ Error fetching price/volume for {symbol}: {e}")
            return None
    
    async def get_ohlcv(self, symbol: str, period: str = "1d", interval: str = "1m"):
        """Get OHLCV data for ATR calculation"""
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                return None
            
            return data
        
        except Exception as e:
            logger.error(f"❌ Error fetching OHLCV for {symbol}: {e}")
            return None
