"""Backward-compatibility shim.
All code now lives in analyst/correlation/engine.py.
Existing imports (scheduler.py, server.py) continue to work unchanged.
"""
from analyst.correlation.engine import CorrelationEngine, Signal  # noqa: F401

__all__ = ["CorrelationEngine", "Signal"]
