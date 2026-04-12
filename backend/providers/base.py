"""Base price provider interface."""
from abc import ABC, abstractmethod
from typing import Optional, Tuple
import pandas as pd


class BasePriceProvider(ABC):
    """Abstract base class for price providers."""
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        pass
    
    @abstractmethod
    async def get_price_with_volume(self, symbol: str) -> Optional[Tuple[float, float]]:
        """Get current price and volume."""
        pass
    
    @abstractmethod
    async def get_ohlcv(
        self, 
        symbol: str, 
        period: str = "1d", 
        interval: str = "1m"
    ) -> Optional[pd.DataFrame]:
        """Get OHLCV data."""
        pass