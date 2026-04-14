"""
Multi-Source Data Fetching + Paper Trading Simulator

Features:
- Multiple data sources (yfinance, mock, Alpaca-ready)
- Paper trading with mock execution (no real broker needed)
- Realistic order simulation with fills, slippage, latency
- Supports crypto (Binance, Coinbase) - mock mode
- Rate limiting built-in

Usage:
    from data_feeder import DataSource, DataFetcher, PaperBroker
    
    # Use mock data (no API keys needed)
    fetcher = DataFetcher(DataSource.MOCK)
    data = await fetcher.fetch("AAPL", "2023-01-01", "2024-01-01")
    
    # Paper trading
    broker = PaperBroker(initial_cash=100000)
    order = await broker.submit_order("NVDA", "BUY", 100)
    fill = await broker.execute_order(order)
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from collections import deque
import random
import hashlib

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ============================================================================
# Enums & Config
# ============================================================================

class DataSource(str, Enum):
    """Available data sources"""
    YFINANCE = "yfinance"
    MOCK = "mock"  # Synthetic data, no API needed
    ALPACA = "alpaca"  # Requires API key
    BINANCE = "binance"  # Crypto - mock
    COINBASE = "coinbase"  # Crypto - mock


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Order representation"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None  # For limit orders
    stop_price: Optional[float] = None  # For stop orders
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


@dataclass
class Fill:
    """Execution fill"""
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    timestamp: datetime
    slippage: float = 0.0


@dataclass
class Position:
    """Current position"""
    symbol: str
    quantity: float = 0.0
    avg_cost: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class AccountState:
    """Account state snapshot"""
    cash: float
    equity: float
    buying_power: float
    positions: Dict[str, Position]
    pending_orders: List[Order]
    timestamp: datetime


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_second: float = 10.0
    requests_per_minute: float = 100.0
    requests_per_hour: float = 1000.0
    max_retries: int = 3
    base_delay: float = 1.0  # Seconds for exponential backoff
    max_delay: float = 60.0


# ============================================================================
# Rate Limiter
# ============================================================================

class RateLimiter:
    """Token bucket rate limiter with exponential backoff"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._tokens = self.config.requests_per_second
        self._last_update = datetime.utcnow()
        self._request_times: deque = deque(maxlen=int(self.config.requests_per_hour))
        self._backoff_until: Optional[datetime] = None
    
    async def acquire(self):
        """Acquire permission to make a request"""
        # Check backoff
        if self._backoff_until and datetime.utcnow() < self._backoff_until:
            wait = (self._backoff_until - datetime.utcnow()).total_seconds()
            logger.warning(f"Rate limit backoff: waiting {wait:.1f}s")
            await asyncio.sleep(wait)
        
        # Token bucket refill
        now = datetime.utcnow()
        elapsed = (now - self._last_update).total_seconds()
        self._tokens = min(
            self.config.requests_per_second,
            self._tokens + elapsed * (self.config.requests_per_second / 1.0)
        )
        self._last_update = now
        
        # Check per-minute and per-hour limits
        self._clean_old_requests()
        if len(self._request_times) >= self.config.requests_per_minute:
            wait = 60 - elapsed
            logger.warning(f"Minute rate limit: waiting {wait:.1f}s")
            await asyncio.sleep(wait)
        
        # Acquire token or wait
        if self._tokens < 1:
            wait = 1.0 / self.config.requests_per_second
            await asyncio.sleep(wait)
            self._tokens -= 1
        else:
            self._tokens -= 1
        
        self._request_times.append(now)
    
    def _clean_old_requests(self):
        """Remove requests outside the window"""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()
    
    def trigger_backoff(self, retry_count: int):
        """Trigger exponential backoff"""
        delay = min(
            self.config.base_delay * (2 ** retry_count),
            self.config.max_delay
        )
        self._backoff_until = datetime.utcnow() + timedelta(seconds=delay)
        logger.warning(f"Triggering backoff: {delay:.1f}s")
    
    def reset_backoff(self):
        """Reset backoff after success"""
        self._backoff_until = None


class RequestQueue:
    """Queue for managing pending requests with priority"""
    
    def __init__(self, max_size: int = 100):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self._running = False
    
    async def enqueue(self, priority: int, coro):
        """Add request to queue"""
        await self._queue.put((priority, random.random(), coro))
    
    async def dequeue(self) -> Any:
        """Get next request"""
        return await self._queue.get()
    
    @property
    def size(self) -> int:
        return self._queue.qsize()


# ============================================================================
# Data Fetchers
# ============================================================================

class BaseDataFetcher(ABC):
    """Base class for data fetchers"""
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter()
    
    @abstractmethod
    async def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data"""
        pass
    
    async def _throttle(self):
        """Apply rate limiting"""
        await self.rate_limiter.acquire()


class MockDataFetcher(BaseDataFetcher):
    """Generate synthetic market data - no API needed"""
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        volatility: float = 0.02,
        trend: float = 0.0001,
        volume_base: float = 1_000_000
    ):
        super().__init__(rate_limiter)
        self.volatility = volatility
        self.trend = trend
        self.volume_base = volume_base
        
        # Symbol-specific parameters
        self._symbol_params: Dict[str, dict] = {}
    
    def _get_symbol_params(self, symbol: str) -> dict:
        """Get or generate params for symbol"""
        if symbol not in self._symbol_params:
            # Generate deterministic but varied params
            seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
            random.seed(seed)
            
            self._symbol_params[symbol] = {
                "base_price": random.uniform(50, 500),
                "volatility": random.uniform(0.01, 0.04),
                "trend": random.uniform(-0.0002, 0.0005),
                "volume_base": random.uniform(500000, 5000000),
                "spike_prob": random.uniform(0.02, 0.08)
            }
            random.seed()  # Reset
        
        return self._symbol_params[symbol]
    
    async def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Generate synthetic OHLCV data"""
        await self._throttle()
        
        # Parse dates
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        
        # Generate timestamps
        freq_map = {
            "1m": "1min", "5m": "5min", "15m": "15min",
            "1h": "1h", "1d": "1D"
        }
        freq = freq_map.get(interval, "1D")
        
        dates = pd.date_range(start=start_dt, end=end_dt, freq=freq)
        
        # Get symbol params
        params = self._get_symbol_params(symbol)
        
        n = len(dates)
        base = params["base_price"]
        vol = params["volatility"]
        trend = params["trend"]
        
        # Generate returns with trend and volatility
        random.seed(hash(symbol + start + end) % (2**32))
        returns = np.random.normal(trend, vol, n)
        
        # Add occasional spikes
        if random.random() < params["spike_prob"]:
            spike_idx = random.randint(0, n-1)
            returns[spike_idx] += random.uniform(0.05, 0.15) * (1 if random.random() > 0.5 else -1)
        
        # Calculate prices
        prices = base * np.cumprod(1 + returns)
        
        # Generate OHLC
        spread = prices * vol * 0.5
        open_prices = prices + np.random.uniform(-spread * 0.3, spread * 0.3, n)
        high = np.maximum(prices, open_prices) + np.random.uniform(0, spread * 0.5, n)
        low = np.minimum(prices, open_prices) - np.random.uniform(0, spread * 0.5, n)
        close = prices
        
        # Generate volume
        base_vol = params["volume_base"]
        volume = np.random.lognormal(0, 0.5, n) * base_vol
        
        random.seed()
        
        df = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume.astype(int)
        }, index=dates)
        
        logger.info(f"Generated {len(df)} bars for {symbol} (mock)")
        
        return df


class YahooDataFetcher(BaseDataFetcher):
    """Yahoo Finance data fetcher"""
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(rate_limiter)
        
        try:
            import yfinance
            self.yf = yfinance
            self._available = True
        except ImportError:
            logger.warning("yfinance not installed")
            self._available = False
    
    async def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        if not self._available:
            raise RuntimeError("yfinance not available")
        
        await self._throttle()
        
        interval_map = {
            "1m": "1m", "5m": "5m", "15m": "15min",
            "1h": "1h", "1d": "1d", "1wk": "1wk"
        }
        yf_interval = interval_map.get(interval, "1d")
        
        ticker = self.yf.download(symbol, start=start, end=end, interval=yf_interval, progress=False)
        
        if ticker.empty:
            raise ValueError(f"No data for {symbol}")
        
        if isinstance(ticker.columns, pd.MultiIndex):
            ticker.columns = ticker.columns.get_level_values(0)
        
        ticker.columns = [c.lower() for c in ticker.columns]
        
        return ticker


class BinanceDataFetcher(BaseDataFetcher):
    """Binance data fetcher - mock mode for now"""
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        api_key: Optional[str] = None,
        mock_mode: bool = True
    ):
        super().__init__(rate_limiter)
        self.api_key = api_key
        self.mock_mode = mock_mode
        
        if not mock_mode:
            # TODO: Implement real Binance client
            logger.warning("Binance real mode not implemented, using mock")
            self.mock_mode = True
    
    async def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch crypto data - mock for now"""
        if self.mock_mode:
            # Use mock with crypto-like behavior (24/7)
            params = {
                "volatility": 0.03,  # Higher volatility for crypto
                "trend": 0.0002,
                "volume_base": 10_000_000  # Higher volume
            }
            
            # Convert symbol to check if crypto
            symbol = symbol.upper()
            if not any(x in symbol for x in ['BTC', 'ETH', 'USDT', 'USD']):
                symbol += 'USD'
            
            mock_fetcher = MockDataFetcher(self.rate_limiter, **params)
            return await mock_fetcher.fetch(symbol, start, end, interval)
        
        raise NotImplementedError("Real Binance API not implemented")


class DataFetcherFactory:
    """Factory for creating data fetchers"""
    
    _fetchers: Dict[DataSource, type] = {
        DataSource.MOCK: MockDataFetcher,
        DataSource.YFINANCE: YahooDataFetcher,
        DataSource.BINANCE: BinanceDataFetcher,
    }
    
    @classmethod
    def create(
        source: DataSource,
        rate_limiter: Optional[RateLimiter] = None,
        **kwargs
    ) -> BaseDataFetcher:
        fetcher_class = cls._fetchers.get(source)
        if not fetcher_class:
            raise ValueError(f"Unknown source: {source}")
        return fetcher_class(rate_limiter, **kwargs)


# ============================================================================
# Paper Trading Broker
# ============================================================================

class PaperBroker:
    """Paper trading broker with realistic simulation
    
    Features:
    - Mock order execution with realistic fills
    - Configurable slippage and latency
    - Position tracking and PnL
    - Cash management
    - Supports crypto 24/7
    
    Usage:
        broker = PaperBroker(initial_cash=100000)
        order = await broker.submit_order("AAPL", "BUY", 100)
        fill = await broker.execute_order(order)
        state = await broker.get_account_state()
    """
    
    def __init__(
        self,
        initial_cash: float = 100000,
        slippage_pct: float = 0.0005,
        commission_pct: float = 0.001,
        latency_ms: int = 100,
        max_slippage_pct: float = 0.01
    ):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        self.latency_ms = latency_ms
        self.max_slippage_pct = max_slippage_pct
        
        # State
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.fills: List[Fill] = []
        self.order_counter = 0
        self.fill_counter = 0
        
        # Price cache (latest prices)
        self._prices: Dict[str, float] = {}
        
        logger.info(f"PaperBroker initialized with ${initial_cash:,.2f}")
    
    def _generate_order_id(self) -> str:
        self.order_counter += 1
        return f"paper_{self.order_counter:06d}"
    
    def _generate_fill_id(self) -> str:
        self.fill_counter += 1
        return f"fill_{self.fill_counter:06d}"
    
    async def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day"
    ) -> Order:
        """Submit an order"""
        symbol = symbol.upper()
        
        # Validate
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and not price:
            raise ValueError(f"{order_type} requires price")
        
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not stop_price:
            raise ValueError(f"{order_type} requires stop_price")
        
        # Check buying power for buys
        if side == OrderSide.BUY:
            required = quantity * (price or 0)
            if self.cash < required * (1 + self.commission_pct):
                logger.warning(f"Insufficient cash: {self.cash} < {required}")
                # Create rejected order
                order = Order(
                    order_id=self._generate_order_id(),
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price,
                    status=OrderStatus.REJECTED
                )
                self.orders[order.order_id] = order
                return order
        
        # Create pending order
        order = Order(
            order_id=self._generate_order_id(),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            expires_at=datetime.utcnow() + timedelta(days=1) if time_in_force == "day" else None
        )
        
        self.orders[order.order_id] = order
        logger.debug(f"Order submitted: {order.order_id} {side.value} {quantity} {symbol}")
        
        return order
    
    async def execute_order(self, order: Order) -> Optional[Fill]:
        """Execute an order (simulate fill)"""
        # Simulate latency
        await asyncio.sleep(self.latency_ms / 1000)
        
        # Get current price (simulated if not set)
        current_price = self._prices.get(order.symbol)
        if not current_price:
            # Use a reasonable default
            current_price = 100.0
        
        # Determine fill price
        fill_price = self._calculate_slippage(current_price, order.side)
        
        # Create fill
        fill = Fill(
            fill_id=self._generate_fill_id(),
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            commission=fill_price * order.quantity * self.commission_pct,
            timestamp=datetime.utcnow(),
            slippage=abs(fill_price - current_price) / current_price * 100
        )
        
        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = fill_price
        order.filled_at = datetime.utcnow()
        
        # Update cash and positions
        if order.side == OrderSide.BUY:
            self.cash -= (fill_price * order.quantity + fill.commission)
            self._update_position_buy(order.symbol, order.quantity, fill_price)
        else:
            self.cash += (fill_price * order.quantity - fill.commission)
            self._update_position_sell(order.symbol, order.quantity, fill_price)
        
        self.fills.append(fill)
        logger.debug(f"Order filled: {order.order_id} @ ${fill_price:.2f}")
        
        return fill
    
    def _calculate_slippage(self, price: float, side: OrderSide) -> float:
        """Calculate fill price with slippage"""
        # Random slippage within bounds
        slip = random.uniform(0, self.max_slippage_pct)
        
        if side == OrderSide.BUY:
            # Buy at higher price
            return price * (1 + self.slippage_pct + slip)
        else:
            # Sell at lower price
            return price * (1 - self.slippage_pct - slip)
    
    def _update_position_buy(self, symbol: str, quantity: float, price: float):
        """Update position after buy"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_cost = pos.avg_cost * pos.quantity + price * quantity
            pos.quantity += quantity
            pos.avg_cost = total_cost / pos.quantity if pos.quantity > 0 else 0
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_cost=price
            )
        
        self._recalculate_position_value(symbol)
    
    def _update_position_sell(self, symbol: str, quantity: float, price: float):
        """Update position after sell"""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        
        # Calculate realized PnL
        if quantity >= pos.quantity:
            realized = (price - pos.avg_cost) * pos.quantity
            pos.realized_pnl += realized
            pos.quantity = 0
            del self.positions[symbol]
        else:
            realized = (price - pos.avg_cost) * quantity
            pos.realized_pnl += realized
            pos.quantity -= quantity
        
        # Recalculate for other positions
        for sym in list(self.positions.keys()):
            self._recalculate_position_value(sym)
    
    def _recalculate_position_value(self, symbol: str):
        """Recalculate position market value and unrealized PnL"""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        current_price = self._prices.get(symbol, pos.avg_cost)
        
        pos.market_value = pos.quantity * current_price
        pos.unrealized_pnl = (current_price - pos.avg_cost) * pos.quantity
    
    def update_price(self, symbol: str, price: float):
        """Update current price for a symbol"""
        self._prices[symbol.upper()] = price
        self._recalculate_position_value(symbol.upper())
    
    async def get_account_state(self) -> AccountState:
        """Get current account state"""
        total_market_value = sum(p.market_value for p in self.positions.values())
        
        return AccountState(
            cash=self.cash,
            equity=self.cash + total_market_value,
            buying_power=self.cash * 2,  # Reg T margin
            positions=self.positions.copy(),
            pending_orders=[o for o in self.orders.values() if o.status == OrderStatus.PENDING],
            timestamp=datetime.utcnow()
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        order = self.orders.get(order_id)
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CANCELLED
            logger.debug(f"Order cancelled: {order_id}")
            return True
        return False
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all positions"""
        return self.positions.copy()
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_fills(self, symbol: Optional[str] = None) -> List[Fill]:
        """Get fills, optionally filtered by symbol"""
        if symbol:
            return [f for f in self.fills if f.symbol == symbol.upper()]
        return self.fills.copy()


# ============================================================================
# Portfolio Analytics
# ============================================================================

class PortfolioAnalytics:
    """Portfolio analytics with risk metrics"""
    
    def __init__(self, broker: PaperBroker):
        self.broker = broker
    
    async def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive portfolio metrics"""
        state = await self.broker.get_account_state()
        
        positions = list(state.positions.values())
        
        if not positions:
            return self._empty_metrics()
        
        # Basic metrics
        total_value = state.equity
        cash_pct = state.cash / total_value * 100 if total_value > 0 else 0
        
        # Position metrics
        positions_data = []
        for pos in positions:
            positions_data.append({
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "market_value": pos.market_value,
                "weight": pos.market_value / total_value * 100 if total_value > 0 else 0,
                "unrealized_pnl": pos.unrealized_pnl,
                "realized_pnl": pos.realized_pnl,
                "total_pnl": pos.unrealized_pnl + pos.realized_pnl
            })
        
        # Sort by value
        positions_data.sort(key=lambda x: x['market_value'], reverse=True)
        
        return {
            "total_equity": total_value,
            "cash": state.cash,
            "cash_pct": cash_pct,
            "buying_power": state.buying_power,
            "positions": positions_data,
            "position_count": len(positions)
        }
    
    def _empty_metrics(self) -> Dict:
        return {
            "total_equity": self.broker.cash,
            "cash": self.broker.cash,
            "cash_pct": 100.0,
            "buying_power": self.broker.cash * 2,
            "positions": [],
            "position_count": 0
        }
    
    def calculate_var(
        self,
        returns: List[float],
        confidence: float = 0.95
    ) -> float:
        """Calculate Value at Risk"""
        if not returns:
            return 0.0
        
        sorted_returns = sorted(returns)
        idx = int((1 - confidence) * len(sorted_returns))
        return abs(sorted_returns[idx]) if idx < len(sorted_returns) else 0.0
    
    def calculate_cvar(
        self,
        returns: List[float],
        confidence: float = 0.95
    ) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        if not returns:
            return 0.0
        
        var = self.calculate_var(returns, confidence)
        tail_returns = [r for r in returns if r <= -var]
        
        if tail_returns:
            return abs(sum(tail_returns) / len(tail_returns))
        return var
    
    def calculate_correlation(
        self,
        returns_history: Dict[str, List[float]]
    ) -> pd.DataFrame:
        """Calculate correlation matrix for positions"""
        if not returns_history:
            return pd.DataFrame()
        
        df = pd.DataFrame(returns_history)
        return df.corr()
    
    def suggest_rebalancing(
        self,
        target_weights: Dict[str, float]
    ) -> List[Dict]:
        """Suggest rebalancing trades to hit target weights"""
        # This would require price data - placeholder
        return []


# ============================================================================
# Convenience Functions
# ============================================================================

async def create_paper_trading_session(
    initial_cash: float = 100000,
    data_source: DataSource = DataSource.MOCK
) -> tuple:
    """Create a complete paper trading session"""
    
    # Create rate limiter
    rate_limiter = RateLimiter()
    
    # Create data fetcher
    data_fetcher = DataFetcherFactory.create(data_source, rate_limiter)
    
    # Create broker
    broker = PaperBroker(initial_cash)
    
    # Create analytics
    analytics = PortfolioAnalytics(broker)
    
    return data_fetcher, broker, analytics