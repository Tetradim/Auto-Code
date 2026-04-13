"""Structured JSON logging for Sentinel Edge.

Provides JSON formatter for Loki compatibility and structured log events.
All logs include: timestamp, level, message, module, function, line.

Usage:
    from json_logging import setup_json_logging
    
    setup_json_logging()
    logger = logging.getLogger(__name__)
    logger.info("Order filled", extra={"order_id": "123", "pnl": 5.50})
    
For Loki/Promtail, logs go to stdout as JSON.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from functools import lru_cache


# ─────────────────────────────────────────────────────────────────────────────
# JSON Formatter
# ─────────────────────────────────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """JSON formatter for Loki-compatible logs.
    
    Output format:
    {
        "timestamp": "2024-01-01T12:00:00.000Z",
        "level": "INFO",
        "message": "Order filled",
        "module": "server",
        "function": "fill_order",
        "line": 123,
        "order_id": "123",
        "pnl": 5.50
    }
    """
    
    def __init__(
        self,
        include_extra: bool = True,
        include_extra_keys: Optional[list] = None,
    ) -> None:
        super().__init__()
        self.include_extra = include_extra
        self.include_extra_keys = include_extra_keys or [
            'order_id', 'symbol', 'side', 'pnl', 'pnl_pct',
            'edge', 'signal_id', 'decision', 'error_type',
        ]
    
    def format(self, record: logging.LogRecord) -> str:
        # Base fields
        log_obj = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields from log dict
        if self.include_extra and hasattr(record, 'extra_fields'):
            for key in self.include_extra_keys:
                if key in record.extra_fields:
                    log_obj[key] = record.extra_fields[key]
        
        # Include ExcInfo if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj, default=str)


class StructuredLogger:
    """Logger with structured logging support.
    
    Usage:
        logger = StructuredLogger(__name__)
        logger.info("Order filled", order_id="123", pnl=5.50)
        
        # Logs as JSON:
        # {"timestamp": "...", "level": "INFO", "message": "Order filled",
        #  "order_id": "123", "pnl": 5.50, ...}
    """
    
    def __init__(self, name: str) -> None:
        self.logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> None:
        """Add contextual fields to all logs from this logger."""
        self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear contextual fields."""
        self._context.clear()
    
    def _log(self, level: int, message: str, **kwargs) -> None:
        """Log with structured fields."""
        extra = {'extra_fields': {**self._context, **kwargs}}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs) -> None:
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        self._log(logging.CRITICAL, message, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Log level detection
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache()
def get_log_level() -> int:
    """Get log level from env or default to INFO."""
    level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    return getattr(logging, level, logging.INFO)


# ─────────────────────────────────────────────────────────────────────────────
# Setup function
# ─────────────────────────────────────────────────────────────────────────────

def setup_json_logging(
    level: Optional[int] = None,
    json_output: bool = True,
) -> None:
    """Setup JSON logging for Loki/Promtail.
    
    Args:
        level: Log level (default from LOG_LEVEL env or INFO)
        json_output: If True, output JSON to stdout (for Loki)
                     If False, output human-readable (for dev)
    """
    level = level or get_log_level()
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    if json_output:
        # JSON output for Loki/Promtail
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        handler.setLevel(level)
        root_logger.addHandler(handler)
        
        # Set specific loggers too
        for logger_name in ['sentinel-edge', 'pulse', 'engine']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
            logger.handlers.clear()
            logger.addHandler(handler)
    else:
        # Human-readable for development
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        ))
        handler.setLevel(level)
        root_logger.addHandler(handler)


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: get structured logger
# ─────────────────────────────────────────────────────────────────────────────

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger."""
    return StructuredLogger(name)


# ─────────────────────────────────────────────────────────────────────────────
# Log event helpers for common patterns
# ─────────────────────────────────────────────────────────────────────────────

def log_order_event(
    logger: StructuredLogger,
    event: str,  # 'created', 'filled', 'cancelled', 'failed'
    order: Dict[str, Any],
) -> None:
    """Log an order event with structured data."""
    logger.info(
        f"Order {event}",
        event=event,
        order_id=order.get('order_id'),
        symbol=order.get('symbol'),
        side=order.get('side'),
        price=order.get('price'),
        quantity=order.get('quantity'),
    )


def log_signal_evaluation(
    logger: StructuredLogger,
    symbol: str,
    decision: str,
    edge: float,
    reasons: list,
) -> None:
    """Log signal evaluation."""
    logger.info(
        f"Signal eval: {decision}",
        symbol=symbol,
        decision=decision,
        edge=edge,
        reasons=reasons,
    )


def log_error_with_context(
    logger: StructuredLogger,
    error: Exception,
    context: Dict[str, Any],
) -> None:
    """Log error with context."""
    logger.error(
        str(error),
        error_type=type(error).__name__,
        error_message=str(error),
        **context
    )