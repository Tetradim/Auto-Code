"""Provider health monitoring for market-data sources."""
import logging
from typing import Dict, Iterable, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class ProviderHealth:
    """Monitor health status of price providers.

    Providers are initialized with the common Edge sources, but new provider
    names are registered lazily so experimental/free feeds can be added without
    changing this class first.
    """

    PROVIDERS = [
        "polygon",
        "finnhub",
        "alpaca",
        "yfinance",
        "stooq",
        "alpha_vantage",
        "twelve_data",
        "financial_modeling_prep",
        "marketstack",
        "tiingo",
        "eodhd",
        "nasdaq_data_link",
    ]

    def __init__(self, providers: Optional[Iterable[str]] = None):
        names = list(providers or self.PROVIDERS)
        self.status: Dict[str, dict] = {}
        self.last_check: Dict[str, datetime] = {}
        for provider in names:
            self._ensure_provider(provider)

    def _ensure_provider(self, provider: str) -> None:
        if provider not in self.status:
            self.status[provider] = {
                "healthy": True,
                "last_success": None,
                "error_count": 0,
            }

    def record_success(self, provider: str):
        """Record a successful call to a provider."""
        self._ensure_provider(provider)
        self.status[provider]["healthy"] = True
        self.status[provider]["last_success"] = datetime.utcnow()
        self.status[provider]["error_count"] = 0
        logger.debug("Provider %s - success recorded", provider)

    def record_failure(self, provider: str):
        """Record a failed call to a provider."""
        self._ensure_provider(provider)
        self.status[provider]["error_count"] += 1
        if self.status[provider]["error_count"] >= 5:
            self.status[provider]["healthy"] = False
            logger.warning(
                "Provider %s degraded (errors: %s)",
                provider,
                self.status[provider]["error_count"],
            )
        else:
            logger.debug(
                "Provider %s failed (errors: %s)",
                provider,
                self.status[provider]["error_count"],
            )

    def get_health(self) -> dict:
        """Get health status for all providers."""
        return {
            "providers": {
                name: {
                    "healthy": data["healthy"],
                    "last_success": data["last_success"].isoformat()
                    if data["last_success"]
                    else None,
                    "error_count": data["error_count"],
                }
                for name, data in self.status.items()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    def is_healthy(self, provider: str) -> bool:
        """Check if a provider is healthy."""
        self._ensure_provider(provider)
        return self.status.get(provider, {}).get("healthy", False)

    def get_best_provider(self) -> str:
        """Get the best first available healthy provider."""
        for provider in self.PROVIDERS:
            if self.is_healthy(provider):
                return provider
        return "yfinance"
