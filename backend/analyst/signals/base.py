"""Signal base types for Sentinel Edge"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Signal:
    """
    Universal signal representation.
    action: "BUY" | "SELL" | "STOP_BUYING" | "EMERGENCY_EXIT" | "HOLD"
    """
    action: str
    confidence: float = 1.0
    symbol: Optional[str] = None
    price: Optional[float] = None
    signal_strength: float = 0.0
    atr: Optional[float] = None
    volume_ratio: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def buy(cls, symbol: str, confidence: float = 1.0, **kwargs) -> "Signal":
        return cls(action="BUY", symbol=symbol, confidence=confidence, **kwargs)

    @classmethod
    def sell(cls, symbol: str, confidence: float = 1.0, **kwargs) -> "Signal":
        return cls(action="SELL", symbol=symbol, confidence=confidence, **kwargs)

    @classmethod
    def hold(cls, symbol: Optional[str] = None, **kwargs) -> "Signal":
        return cls(action="HOLD", symbol=symbol, **kwargs)
