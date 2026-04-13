"""Rate limiter with exponential backoff for exchange API calls.

Handles 429 (rate limit) responses from exchanges like Binance.
Uses exponential backoff with jitter to prevent thundering herd
while respecting rate limits.

Usage:
    from rate_limit import RateLimiter
    
    limiter = RateLimiter(max_calls=10, period=1.0)  # 10 calls/second
    async with limiter:
        result = await exchange.fetch_ticker(symbol)

    # Or for CCXT specifically:
    from rate_limit import CCTXRateLimiter
    
    ccxt_limiter = CCTXRateLimiter(exchange)  #Wraps ccxt exchange
    await ccxt_limiter.fetch_with_limit('ticker', symbol)
"""
import asyncio
import logging
import random
import time
from collections import deque
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Token bucket rate limiter
# ─────────────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Token bucket rate limiter for API calls.
    
    Usage:
        limiter = RateLimiter(max_calls=10, period=1.0)  # 10/sec
        async with limiter:
            await make_api_call()
    """
    
    def __init__(
        self,
        max_calls: int = 10,
        period: float = 1.0,
        backoff_base: float = 1.0,
        backoff_max: float = 60.0,
        backoff_factor: float = 2.0,
    ) -> None:
        self.max_calls = max_calls
        self.period = period
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.backoff_factor = backoff_factor
        
        self._tokens = deque(maxlen=max_calls)
        self._lock = asyncio.Lock()
        self._consecutive_429s = 0
        
    async def __aenter__(self) -> None:
        """Wait for rate limit slot."""
        async with self._lock:
            now = time.time()
            
            # Remove expired tokens
            while self._tokens and self._tokens[0] < now - self.period:
                self._tokens.popleft()
            
            # If at limit, wait for oldest token to expire
            if len(self._tokens) >= self.max_calls:
                wait_time = self._tokens[0] + self.period - now
                if wait_time > 0:
                    logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    
            # Add new token
            self._tokens.append(now)
            self._consecutive_429s = 0
            
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Handle rate limit responses."""
        return False  # Don't suppress exceptions
    
    def on_429(self, retry_after: Optional[int] = None) -> float:
        """Handle 429 response, return wait time.
        
        Called when a 429 is received. Tracks consecutive failures
        and calculates backoff with jitter.
        """
        self._consecutive_429s += 1
        
        # Exponential backoff: base * factor^n + jitter
        base = retry_after if retry_after else self.backoff_base
        delay = min(
            base * (self.backoff_factor ** self._consecutive_429s),
            self.backoff_max
        )
        # Add jitter (±25%)
        jitter = delay * 0.25 * random.uniform(-1, 1)
        delay = max(0.1, delay + jitter)
        
        logger.warning(f"429 received, backing off {delay:.1f}s (attempt {self._consecutive_429s})")
        return delay


# ─────────────────────────────────────────────────────────────────────────────
# Exponential backoff decorator
# ─────────────────────────────────────────────────────────────────────────────

def with_exponential_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    factor: float = 2.0,
    jitter: bool = True,
):
    """Decorator for exponential backoff on API calls.
    
    Usage:
        @with_exponential_backoff(max_retries=5)
        async def call_api():
            return await exchange.fetch_ticker(symbol)
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = '429' in error_str or 'rate limit' in error_str
                    
                    if is_rate_limit and attempt < max_retries:
                        # Exponential backoff
                        delay = min(
                            base_delay * (factor ** attempt),
                            max_delay
                        )
                        if jitter:
                            delay = delay * (0.5 + random.random())
                        logger.warning(
                            f"Rate limit hit, retry {attempt + 1}/{max_retries} "
                            f"in {delay:.1f}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        last_exception = e
                        break
            
            if last_exception:
                raise last_exception
            return None
        
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# CCXT exchange wrapper with rate limiting
# ─────────────────────────────────────────────────────────────────────────────

class CCTXRateLimiter:
    """Wrapper around CCXT exchange with automatic rate limiting.
    
    Usage:
        exchange = ccxt.binance({'apiKey': ..., 'secret': ...})
        limiter = CCTXRateLimiter(exchange)
        
        # Replace exchange methods
        limiter.wrap_methods()
        
        # Or use directly
        await limiter.fetch_with_limit('fetch_ticker', 'BTC/USDT')
    
    Supports:
        - fetch_ticker, fetch_ohlcv, fetch_order_book
        - create_order, cancel_order, fetch_orders
        - fetch_balance, fetch_positions
    """
    
    # Default rate limits per exchange
    EXCHANGE_LIMITS = {
        'binance': {'fetch': 120, 'period': 60},  # 120 reads/min
        'coinbase': {'fetch': 10, 'period': 1},     # 10 reads/sec
        'kraken': {'fetch': 15, 'period': 1},     # 15 reads/sec
        'default': {'fetch': 10, 'period': 1},   # 10 reads/sec
    }
    
    def __init__(
        self,
        exchange: Any,
        max_calls: Optional[int] = None,
        period: Optional[float] = None,
    ) -> None:
        self.exchange = exchange
        self.exchange_id = exchange.id if hasattr(exchange, 'id') else 'default'
        
        # Get rate limit from exchange or use default
        limits = self.EXCHANGE_LIMITS.get(
            self.exchange_id,
            self.EXCHANGE_LIMITS['default']
        )
        self.max_calls = max_calls or limits['fetch']
        self.period = period or limits['period']
        
        self._limiter = RateLimiter(
            max_calls=self.max_calls,
            period=self.period,
        )
        self._outbound_limit = RateLimiter(
            max_calls=10,  # 10 orders/sec default
            period=1.0,
        )
        
    async def __aenter__(self) -> None:
        await self._limiter.__aenter__()
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._limiter.__aexit__(exc_type, exc_val, exc_tb)
        
    def wrap_methods(self) -> None:
        """Wrap CCXT methods with rate limiting."""
        methods_to_wrap = [
            'fetch_ticker',
            'fetch_ohlcv', 
            'fetch_order_book',
            'fetch_balance',
            'fetch_positions',
            'fetch_orders',
            'create_order',
            'cancel_order',
        ]
        
        for method_name in methods_to_wrap:
            if hasattr(self.exchange, method_name):
                original = getattr(self.exchange, method_name)
                wrapped = self._wrap_method(original, method_name)
                setattr(self.exchange, method_name, wrapped)
                logger.debug(f"Wrapped {self.exchange_id}.{method_name}")
    
    def _wrap_method(self, method: Callable, name: str) -> Callable:
        """Wrap a single CCXT method with rate limiting."""
        is_write = name in ('create_order', 'cancel_order', 'edit_order')
        limiter = self._outbound_limit if is_write else self._limiter
        
        async def wrapped(*args, **kwargs):
            # Check for 429 in response
            for _ in range(3):  # Max 3 backoff attempts
                try:
                    async with limiter:
                        result = await method(*args, **kwargs)
                    return result
                except Exception as e:
                    error_str = str(e).lower()
                    is_429 = '429' in error_str or 'rate limit' in error_str
                    
                    if is_429:
                        delay = limiter.on_429()
                        logger.warning(
                            f"Rate limit on {name}, waiting {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise
            
            # All retries exhausted
            raise Exception(f"Rate limit exhausted for {name}")
        
        return wrapped
    
    async def fetch_with_limit(self, method: str, *args, **kwargs) -> Any:
        """Fetch with rate limiting shorthand."""
        if not hasattr(self.exchange, method):
            raise AttributeError(f"Exchange has no method {method}")
        
        method_fn = getattr(self.exchange, method)
        return await self._wrap_method(method_fn, method)(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Circuit breaker pattern
# ─────────────────────────────────────────────────────────────────────────────

class CircuitBreaker:
    """Circuit breaker to stop hammering a failing API.
    
    States: CLOSED → OPEN → HALF_OPEN
    
    Usage:
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        
        async with cb:
            await api_call()
    """
    
    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self._state = self.STATE_CLOSED
        self._failures = 0
        self._successes = 0
        self._last_failure_time = 0
        self._lock = asyncio.Lock()
        
    @property
    def state(self) -> str:
        return self._state
    
    async def __aenter__(self) -> None:
        async with self._lock:
            if self._state == self.STATE_OPEN:
                # Check if recovery timeout passed
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = self.STATE_HALF_OPEN
                    self._successes = 0
                    logger.info("Circuit breaker: OPEN -> HALF_OPEN")
                else:
                    raise Exception(
                        f"Circuit breaker OPEN, wait {self.recovery_timeout}s"
                    )
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        async with self._lock:
            if exc_type is None or '429' in str(exc_val).lower():
                # Success
                self._failures = 0
                if self._state == self.STATE_HALF_OPEN:
                    self._successes += 1
                    if self._successes >= self.success_threshold:
                        self._state = self.STATE_CLOSED
                        logger.info("Circuit breaker: HALF_OPEN -> CLOSED")
            else:
                # Failure
                self._failures += 1
                self._last_failure_time = time.time()
                
                if self._failures >= self.failure_threshold:
                    self._state = self.STATE_OPEN
                    logger.warning(
                        f"Circuit breaker: CLOSED -> OPEN "
                        f"({self._failures} failures)"
                    )
        
        return False
    
    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self._state = self.STATE_CLOSED
        self._failures = 0
        self._successes = 0
        logger.info("Circuit breaker reset")