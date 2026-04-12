"""Provider Health Monitoring - Phase 4"""
import logging
from typing import Dict
from datetime import datetime


logger = logging.getLogger(__name__)

# Note: We'll import metrics after creating the health module
# from metrics import price_fetch_failures_total, price_fetch_latency


class ProviderHealth:
    """Monitor health status of price providers."""
    
    # Known providers
    PROVIDERS = ["yfinance", "alpaca", "polygon", "finnhub"]
    
    def __init__(self):
        self.status: Dict[str, dict] = {
            provider: {
                "healthy": True, 
                "last_success": None, 
                "error_count": 0
            }
            for provider in self.PROVIDERS
        }
        self.last_check: Dict[str, datetime] = {}


    def record_success(self, provider: str):
        """Record a successful call to a provider."""
        if provider in self.status:
            self.status[provider]["healthy"] = True
            self.status[provider]["last_success"] = datetime.utcnow()
            self.status[provider]["error_count"] = 0
            logger.debug(f"Provider {provider} - success recorded")


    def record_failure(self, provider: str):
        """Record a failed call to a provider."""
        if provider in self.status:
            self.status[provider]["error_count"] += 1
            if self.status[provider]["error_count"] >= 5:
                self.status[provider]["healthy"] = False
                logger.warning(f"Provider {provider} degraded (errors: {self.status[provider]['error_count']})")
            else:
                logger.debug(f"Provider {provider} failed (errors: {self.status[provider]['error_count']})")


    def get_health(self) -> dict:
        """Get health status for all providers."""
        return {
            "providers": {
                name: {
                    "healthy": data["healthy"],
                    "last_success": data["last_success"].isoformat() if data["last_success"] else None,
                    "error_count": data["error_count"]
                }
                for name, data in self.status.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }


    def is_healthy(self, provider: str) -> bool:
        """Check if a provider is healthy."""
        return self.status.get(provider, {}).get("healthy", False)


    def get_best_provider(self) -> str:
        """Get the best (first available) healthy provider."""
        for provider in self.PROVIDERS:
            if self.is_healthy(provider):
                return provider
        return "yfinance"  # Fallback