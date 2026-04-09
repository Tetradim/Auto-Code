"""Signal primitives and drop-in strategy plugin base — Sentinel Edge"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Core signal payload ───────────────────────────────────────────────────────

@dataclass
class Signal:
    action: str               # "BUY" | "SELL" | "HOLD"
    symbol: str
    confidence: float
    reason: str               # human-readable explanation
    timeframe: str = "5m"
    price: float = 0.0
    atr: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # ── Convenience constructors ──────────────────────────────────────────

    @classmethod
    def buy(cls, symbol: str, confidence: float, reason: str = "", **kwargs) -> "Signal":
        return cls(action="BUY", symbol=symbol, confidence=confidence, reason=reason, **kwargs)

    @classmethod
    def sell(cls, symbol: str, confidence: float, reason: str = "", **kwargs) -> "Signal":
        return cls(action="SELL", symbol=symbol, confidence=confidence, reason=reason, **kwargs)

    @classmethod
    def hold(cls, symbol: str, reason: str = "", **kwargs) -> "Signal":
        return cls(action="HOLD", symbol=symbol, confidence=0.0, reason=reason, **kwargs)


# ── Plugin config schema ──────────────────────────────────────────────────────

class SignalConfig(BaseModel):
    """Base config model for pluggable signal strategies."""

    class Config:
        extra = "forbid"


# ── Drop-in strategy plugin base ──────────────────────────────────────────────

class BaseSignal(ABC):
    """
    Abstract base for pluggable signal strategies.
    Drop a subclass into analyst/signals/custom/ and it will be
    auto-discovered by the engine.  Mirrors the Pulse strategy interface.

    Example
    ───────
        class VWAPSignal(BaseSignal):
            name = "vwap_breakout"
            description = "VWAP cross with volume confirmation"

            async def generate(self, symbol, market_data) -> Optional[Signal]:
                ...
    """

    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = "Community"
    tags: List[str] = []
    requires_history_bars: int = 100
    default_config: Dict[str, Any] = {}

    @abstractmethod
    async def generate(
        self,
        symbol: str,
        market_data: Dict[str, Any],
    ) -> Optional[Signal]:
        """
        Evaluate market data and return a Signal or None.

        Parameters
        ──────────
        symbol      : ticker symbol
        market_data : dict with keys like "ohlcv", "price", "volume", "atr"
        """

    def get_config_schema(self) -> dict:
        """Return the config schema for this strategy (Pydantic v2 compatible)."""
        config_cls = getattr(self, "Config", None)
        if config_cls and hasattr(config_cls, "model_json_schema"):
            return config_cls.model_json_schema()
        return self.default_config
