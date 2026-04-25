"""
Enhanced Analytics Service

Interactive analytics with real-time chart callbacks:
- Click handlers for drill-down
- Hover tooltips with details
- Selection state management
- Cross-chart interaction
- Export capabilities
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class AnalyticsEvent(Enum):
    """Analytics interaction events"""
    HOVER = "hover"
    CLICK = "click"
    SELECT = "select"
    BRUSH = "brush"  # Range selection
    ZOOM = "zoom"
    RESET = "reset"


class ChartContext(Enum):
    """Chart context for callbacks"""
    PORTFOLIO = "portfolio"
    GREEKS = "greeks"
    SIGNALS = "signals"
    POSITIONS = "positions"
    BACKTEST = "backtest"
    CORRELATION = "correlation"


@dataclass
class AnalyticsInteraction:
    """Represents an interaction event"""
    event: AnalyticsEvent
    context: ChartContext
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Data
    symbol: Optional[str] = None
    value: Optional[float] = None
    timestamp_val: Optional[datetime] = None
    
    # Selection state
    selected_symbols: List[str] = field(default_factory=list)
    is_multi: bool = False
    
    # Metadata
    data_point: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartCallback:
    """Callback for chart interactions"""
    on_hover: Optional[Callable] = None
    on_click: Optional[Callable] = None
    on_select: Optional[Callable] = None
    on_brush: Optional[Callable] = None
    
    # Filters
    enabled_events: List[AnalyticsEvent] = field(default_factory=lambda: [
        AnalyticsEvent.HOVER, 
        AnalyticsEvent.CLICK
    ])


# Analytics state
class AnalyticsState:
    """Manages analytics state and interactions"""
    
    def __init__(self):
        self._callbacks: Dict[ChartContext, ChartCallback] = {}
        self._selected: Dict[ChartContext, Set[str]] = {}
        self._hovered: Optional[str] = None
        self._history: List[AnalyticsInteraction] = []
        self._max_history = 100
    
    def register_callback(
        self, 
        context: ChartContext, 
        callback: ChartCallback
    ):
        """Register callback for context"""
        self._callbacks[context] = callback
    
    def trigger(
        self,
        context: ChartContext,
        event: AnalyticsEvent,
        **kwargs
    ) -> Optional[AnalyticsInteraction]:
        """Trigger an interaction event"""
        interaction = AnalyticsInteraction(
            event=event,
            context=context,
            **kwargs
        )
        
        # Add to history
        self._history.append(interaction)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        # Execute callback
        callback = self._callbacks.get(context)
        if callback:
            handler = {
                AnalyticsEvent.HOVER: callback.on_hover,
                AnalyticsEvent.CLICK: callback.on_click,
                AnalyticsEvent.SELECT: callback.on_select,
                AnalyticsEvent.BRUSH: callback.on_brush,
            }.get(event)
            
            if handler:
                handler(interaction)
        
        return interaction
    
    def select(self, context: ChartContext, symbols: List[str]):
        """Update selection"""
        if context not in self._selected:
            self._selected[context] = set()
        self._selected[context].update(symbols)
    
    def deselect(self, context: ChartContext, symbol: str):
        """Deselect a symbol"""
        if context in self._selected and symbol in self._selected[context]:
            self._selected[context].remove(symbol)
    
    def get_selected(self, context: ChartContext) -> Set[str]:
        """Get selected symbols"""
        return self._selected.get(context, set())
    
    def clear_selection(self, context: ChartContext):
        """Clear selection"""
        self._selected[context] = set()
    
    def get_history(
        self, 
        context: Optional[ChartContext] = None,
        limit: int = 10
    ) -> List[AnalyticsInteraction]:
        """Get interaction history"""
        history = self._history
        if context:
            history = [h for h in history if h.context == context]
        return history[-limit:]


# Cross-chart sync
class CrossChartSync:
    """Synchronize selections across charts"""
    
    def __init__(self):
        self._sources: Dict[str, Set[str]] = {}  # chart_id -> selected symbols
        self._listeners: List[Callable] = []
    
    def set_source(self, chart_id: str, symbols: Set[str]):
        """Set selection source"""
        self._sources[chart_id] = symbols
        
        # Notify all listeners
        for listener in self._listeners:
            listener(chart_id, symbols)
    
    def add_listener(self, listener: Callable):
        """Add sync listener"""
        self._listeners.append(listener)
    
    def get_all_selected(self) -> Set[str]:
        """Get union of all selections"""
        all_sel = set()
        for symbols in self._sources.values():
            all_sel.update(symbols)
        return all_sel
    
    def get_intersection(self) -> Set[str]:
        """Get intersection of selections"""
        result = None
        for symbols in self._sources.values():
            if result is None:
                result = symbols.copy()
            else:
                result &= symbols
        return result or set()


# Analytics Engine
class AnalyticsEngine:
    """Main analytics engine"""
    
    def __init__(self):
        self.state = AnalyticsState()
        self.sync = CrossChartSync()
        self._dashboards: Dict[str, Dict[str, Any]] = {}
    
    def create_dashboard(
        self,
        name: str,
        charts: List[Dict[str, Any]]
    ) -> str:
        """Create a dashboard config"""
        dashboard_id = f"dash_{name}_{len(self._dashboards)}"
        self._dashboards[dashboard_id] = {
            "name": name,
            "charts": charts,
            "created_at": datetime.utcnow()
        }
        return dashboard_id
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dict]:
        """Get dashboard config"""
        return self._dashboards.get(dashboard_id)
    
    def list_dashboards(self) -> List[Dict]:
        """List all dashboards"""
        return [
            {**d, "id": id}
            for id, d in self._dashboards.items()
        ]


# Global instance
_analytics_engine = AnalyticsEngine()


def get_analytics_engine() -> AnalyticsEngine:
    """Get the analytics engine singleton"""
    return _analytics_engine