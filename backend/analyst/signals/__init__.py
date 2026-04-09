"""analyst.signals — exports + plugin auto-discovery"""
import importlib
import logging
import pkgutil
from pathlib import Path
from typing import List, Type

from analyst.signals.base import Signal, BaseSignal, SignalConfig

logger = logging.getLogger(__name__)

__all__ = ["Signal", "BaseSignal", "SignalConfig", "discover_plugins"]


def discover_plugins() -> List[BaseSignal]:
    """
    Auto-discover and instantiate all BaseSignal subclasses inside
    analyst/signals/custom/.

    Drop any .py file containing a BaseSignal subclass into that
    directory — it will be picked up automatically at startup.

    Returns a list of instantiated plugin objects.
    """
    plugins: List[BaseSignal] = []
    custom_dir = Path(__file__).parent / "custom"

    for _, module_name, is_pkg in pkgutil.iter_modules([str(custom_dir)]):
        if is_pkg or module_name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"analyst.signals.custom.{module_name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseSignal)
                    and attr is not BaseSignal
                    and not getattr(attr, "_abstract", False)
                ):
                    instance = attr()
                    plugins.append(instance)
                    logger.info(
                        "Plugin loaded: %s v%s — %s",
                        instance.name, instance.version, instance.description,
                    )
        except Exception as exc:
            logger.warning("Failed to load plugin '%s': %s", module_name, exc)

    if not plugins:
        logger.info("No signal plugins found in analyst/signals/custom/")
    else:
        logger.info("Loaded %d signal plugin(s): %s", len(plugins), [p.name for p in plugins])

    return plugins
