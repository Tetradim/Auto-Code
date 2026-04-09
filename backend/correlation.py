"""Correlation Detection Engine for Sentinel Edge"""
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from metrics import correlation_clusters_total

logger = logging.getLogger(__name__)


class CorrelationEngine:
    """
    Detect when multiple symbols are breaking out in the same direction
    within a rolling time window — signals a broad market move.
    """

    WINDOW_SECONDS = 90        # Look-back window for signal correlation
    MIN_CLUSTER_SIZE = 3       # Minimum symbols to form a cluster
    ALERT_COOLDOWN_SECONDS = 60  # Minimum gap between cluster alerts

    def __init__(self):
        # symbol -> deque of (timestamp, action, confidence)
        self.events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self._last_alert_time: Optional[datetime] = None
        self._recent_clusters: List[Dict] = []   # In-memory cache for the API
        logger.info("Correlation Engine initialized")

    # ── Public API ──────────────────────────────────────────────────────

    def record_signal(
        self,
        symbol: str,
        action: str,
        confidence: float = 1.0,
        timestamp: Optional[datetime] = None,
    ) -> Optional[Dict]:
        """
        Record a signal event and return a cluster dict if a new cluster
        was just detected, otherwise return None.
        """
        ts = timestamp or datetime.utcnow()
        self.events[symbol].append((ts, action, confidence))
        cluster = self._detect_cluster()
        if cluster:
            self._handle_cluster(cluster)
        return cluster

    def get_recent_clusters(self, limit: int = 10) -> List[Dict]:
        return self._recent_clusters[:limit]

    def get_current_breadth(self) -> Dict:
        """Snapshot of current directional bias across all tracked symbols."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.WINDOW_SECONDS)

        bullish = bearish = neutral = 0
        for history in self.events.values():
            recent = [(ts, act, conf) for ts, act, conf in history if ts >= cutoff]
            if not recent:
                neutral += 1
                continue
            action = recent[-1][1]
            if action == "BUY":
                bullish += 1
            elif action in ("STOP_BUYING", "EMERGENCY_EXIT"):
                bearish += 1
            else:
                neutral += 1

        total = max(bullish + bearish + neutral, 1)
        return {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "total": total,
            "bullish_pct": round(bullish / total * 100, 1),
            "bearish_pct": round(bearish / total * 100, 1),
        }

    # ── Internal ────────────────────────────────────────────────────────

    def _detect_cluster(self) -> Optional[Dict]:
        now = datetime.utcnow()

        # Enforce cooldown
        if (
            self._last_alert_time
            and (now - self._last_alert_time).total_seconds() < self.ALERT_COOLDOWN_SECONDS
        ):
            return None

        cutoff = now - timedelta(seconds=self.WINDOW_SECONDS)
        bullish_symbols: List[tuple] = []
        bearish_symbols: List[tuple] = []

        for symbol, history in self.events.items():
            recent = [(ts, act, conf) for ts, act, conf in history if ts >= cutoff]
            if not recent:
                continue
            ts, action, conf = recent[-1]
            if action == "BUY":
                bullish_symbols.append((symbol, conf))
            elif action in ("STOP_BUYING", "EMERGENCY_EXIT"):
                bearish_symbols.append((symbol, conf))

        for direction, sym_list in [("BULLISH", bullish_symbols), ("BEARISH", bearish_symbols)]:
            if len(sym_list) >= self.MIN_CLUSTER_SIZE:
                total = max(len(self.events), 1)
                score = round(len(sym_list) / total, 2)
                top = [s[0] for s in sorted(sym_list, key=lambda x: -x[1])[:5]]
                return {
                    "direction": direction,
                    "count": len(sym_list),
                    "symbols": top,
                    "score": score,
                    "timestamp": now.isoformat(),
                }

        return None

    def _handle_cluster(self, cluster: Dict) -> None:
        self._last_alert_time = datetime.utcnow()

        # Keep last 20 in memory
        self._recent_clusters.insert(0, cluster)
        self._recent_clusters = self._recent_clusters[:20]

        correlation_clusters_total.labels(direction=cluster["direction"]).inc()

        logger.warning(
            "🔗 CORRELATION CLUSTER: %d symbols %s [%s] score=%.2f",
            cluster["count"],
            cluster["direction"],
            ", ".join(cluster["symbols"]),
            cluster["score"],
        )
