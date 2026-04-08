"""Pulse API Client with Circuit Breaker"""
import logging
import time
from typing import Optional, Dict, Any
from enum import Enum
import httpx
from metrics import edge_api_calls_total, edge_api_latency, broker_circuit_state, broker_failure_rate

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = 0      # Normal operation
    HALF_OPEN = 1   # Testing if service recovered
    OPEN = 2        # Service unavailable

class PulseClient:
    """Client for Pulse API with circuit breaker pattern"""
    
    FAILURE_THRESHOLD = 5
    SUCCESS_THRESHOLD = 2
    TIMEOUT_SECONDS = 5.0
    CIRCUIT_OPEN_DURATION = 60  # seconds
    
    def __init__(self, base_url: str = "http://localhost:8002", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.broker_id = "pulse"
        
        # Circuit breaker state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        
        # Initialize metrics
        broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
        broker_failure_rate.labels(broker_id=self.broker_id).set(0.0)
        
        logger.info(f"Pulse Client initialized: {self.base_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        return headers
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on circuit state"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if we should try half-open
            if time.time() - self.last_failure_time > self.CIRCUIT_OPEN_DURATION:
                logger.info(f"Circuit breaker transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
                return True
            return False
        
        # HALF_OPEN state - allow limited requests
        return True
    
    def _record_success(self):
        """Record successful request"""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.SUCCESS_THRESHOLD:
                logger.info(f"Circuit breaker CLOSED after {self.success_count} successes")
                self.state = CircuitState.CLOSED
                self.success_count = 0
                broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
    
    def _record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        
        if self.failure_count >= self.FAILURE_THRESHOLD:
            logger.error(f"Circuit breaker OPEN after {self.failure_count} failures")
            self.state = CircuitState.OPEN
            broker_circuit_state.labels(broker_id=self.broker_id).set(self.state.value)
        
        # Update failure rate
        total_requests = self.failure_count
        failure_rate = (self.failure_count / max(total_requests, 1)) * 100
        broker_failure_rate.labels(broker_id=self.broker_id).set(failure_rate)
    
    async def get_tickers(self) -> list:
        """Get active tickers from Pulse (MOCKED)"""
        # For now, return mock data
        return [
            {"symbol": "SPY", "enabled": True},
            {"symbol": "QQQ", "enabled": True},
            {"symbol": "NVDA", "enabled": True},
            {"symbol": "AAPL", "enabled": True}
        ]
    
    async def send_decision(self, symbol: str, decision: str, **kwargs) -> bool:
        """Send trading decision to Pulse"""
        
        if not self._should_allow_request():
            logger.warning(f"Circuit breaker {self.state.name} - request blocked")
            return False
        
        endpoint = f"/api/tickers/{symbol}/decision"
        url = f"{self.base_url}{endpoint}"
        
        payload = {
            "symbol": symbol,
            "decision": decision,
            **kwargs
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers()
                )
                
                duration = time.time() - start_time
                edge_api_latency.labels(endpoint=endpoint).observe(duration)
                
                if response.status_code in [200, 201]:
                    edge_api_calls_total.labels(endpoint=endpoint, status="success").inc()
                    self._record_success()
                    logger.info(f"✅ Sent decision to Pulse: {symbol} -> {decision}")
                    return True
                else:
                    edge_api_calls_total.labels(endpoint=endpoint, status="failure").inc()
                    self._record_failure()
                    logger.error(f"❌ Pulse API error: {response.status_code}")
                    return False
        
        except httpx.TimeoutException:
            edge_api_calls_total.labels(endpoint=endpoint, status="timeout").inc()
            self._record_failure()
            logger.error(f"⌛ Pulse API timeout for {symbol}")
            return False
        
        except Exception as e:
            edge_api_calls_total.labels(endpoint=endpoint, status="error").inc()
            self._record_failure()
            logger.error(f"⚠️ Pulse API error: {e}")
            return False
    
    async def enable_trailing_stop(self, symbol: str, trailing_percent: float) -> bool:
        """Enable trailing stop for a symbol"""
        return await self.send_decision(
            symbol,
            "enable_trailing_stop",
            trailing_percent=trailing_percent
        )
    
    async def stop_buying(self, symbol: str) -> bool:
        """Stop buying a symbol"""
        return await self.send_decision(symbol, "stop_buying")
    
    async def emergency_stop(self, symbol: str) -> bool:
        """Emergency stop for a symbol"""
        return await self.send_decision(symbol, "emergency_stop")
