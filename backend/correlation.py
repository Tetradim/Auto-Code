"""Full Correlation Engine for Sentinel Edge"""
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx

from metrics import correlation_clusters_total

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Minimal signal container — mirrors the analyst.signals.base.Signal interface."""
    action: str          # "BUY" | "SELL" | "STOP_BUYING" | "EMERGENCY_EXIT"
    confidence: float = 1.0


# Actions treated as bullish
_BULLISH_ACTIONS = {"BUY"}
# Actions treated as bearish
_BEARISH_ACTIONS = {"SELL", "STOP_BUYING", "EMERGENCY_EXIT"}


class CorrelationEngine:
    """
    Detect correlation clusters across multiple symbols.

    Maintains a per-symbol rolling window of signal events.  When ≥ min_symbols
    break out in the same direction within the window, a cluster is emitted,
    persisted to MongoDB, a Prometheus counter is incremented, and an optional
    Pulse override is fired.

    All public methods that touch the network are *async*.
    """

    def __init__(
        self,
        db=None,                                        # Motor async DB (optional)
        pulse_base_url: str = "http://pulse:8001",
        window_sec: int = 120,                          # 2-minute look-back
        min_symbols: int = 3,
        cooldown_sec: int = 300,                        # 5-min per-direction cooldown
    ):
        self.db = db
        self.pulse_base_url = pulse_base_url

        self.window_sec = window_sec
        self.min_symbols = min_symbols
        self.cooldown_sec = cooldown_sec

        # symbol → deque of (timestamp, action, confidence)
        self.events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Per-direction cooldown timestamps
        self.last_alert_time: Dict[str, datetime] = {}

        # In-memory cache for the REST API (newest first)
        self._recent_clusters: List[Dict] = []

        logger.info(
            "CorrelationEngine ready (window=%ds, min=%d, cooldown=%ds)",
            window_sec, min_symbols, cooldown_sec,
        )

    # ── Public API ───────────────────────────────────────────────────────

    async def record_signal(
        self,
        symbol: str,
        action: str,
        confidence: float = 1.0,
        timestamp: Optional[datetime] = None,
    ) -> Optional[Dict]:
        """
        Record one signal event.  Returns the cluster dict if a new cluster
        was just detected and handled, otherwise ``None``.

        Compatible with both old call-sites (positional action/confidence) and
        the new Signal-dataclass style via helper below.
        """
        ts = timestamp or datetime.utcnow()
        self.events[symbol].append((ts, action, confidence))
        cluster = self._detect_cluster(ts)
        if cluster:
            await self._handle_cluster(cluster)
        return cluster

    async def record_signal_obj(self, symbol: str, signal: Signal) -> Optional[Dict]:
        """Convenience wrapper accepting a Signal dataclass."""
        return await self.record_signal(symbol, signal.action, signal.confidence)

    def get_recent_clusters(self, limit: int = 10) -> List[Dict]:
        return self._recent_clusters[:limit]

    def get_latest_cluster(self) -> Optional[Dict]:
        return self._recent_clusters[0] if self._recent_clusters else None

    def get_current_breadth(self) -> Dict:
        """Bull / bear / neutral snapshot of the last `window_sec` seconds."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_sec)

        bullish = bearish = neutral = 0
        for history in self.events.values():
            recent = [e for e in history if e[0] >= cutoff]
            if not recent:
                neutral += 1
                continue
            action = recent[-1][1]
            if action in _BULLISH_ACTIONS:
                bullish += 1
            elif action in _BEARISH_ACTIONS:
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

    # ── Internal ─────────────────────────────────────────────────────────

    def _detect_cluster(self, now: datetime) -> Optional[Dict]:
        cutoff = now - timedelta(seconds=self.window_sec)

        bullish_syms: List[tuple] = []
        bearish_syms: List[tuple] = []

        for symbol, history in self.events.items():
            recent = [e for e in history if e[0] >= cutoff]
            if not recent:
                continue
            _, action, conf = recent[-1]
            if action in _BULLISH_ACTIONS:
                bullish_syms.append((symbol, conf))
            elif action in _BEARISH_ACTIONS:
                bearish_syms.append((symbol, conf))

        for direction, sym_list in [("BULLISH", bullish_syms), ("BEARISH", bearish_syms)]:
            if len(sym_list) < self.min_symbols:
                continue

            # Cooldown per direction
            last = self.last_alert_time.get(direction)
            if last and (now - last).total_seconds() < self.cooldown_sec:
                continue

            sym_list.sort(key=lambda x: -x[1])          # sort by confidence desc
            top_symbols = [s[0] for s in sym_list[:6]]
            strength = round(min(1.0, len(sym_list) / 8), 2)   # normalised 0-1

            return {
                "direction": direction,
                "count": len(sym_list),
                "symbols": top_symbols,
                "strength": strength,
                # keep score for backwards compat
                "score": round(len(sym_list) / max(len(self.events), 1), 2),
                "timestamp": now.isoformat(),
            }

        return None

    async def _handle_cluster(self, cluster: Dict) -> None:
        direction = cluster["direction"]
        self.last_alert_time[direction] = datetime.utcnow()

        # In-memory cache
        self._recent_clusters.insert(0, cluster)
        self._recent_clusters = self._recent_clusters[:20]

        # Prometheus
        strength_label = "high" if cluster["strength"] > 0.7 else "medium"
        correlation_clusters_total.labels(
            direction=direction.lower(),
            strength=strength_label,
        ).inc()

        logger.warning(
            "🔗 CORRELATION CLUSTER: %d-symbol %s [%s] strength=%.2f",
            cluster["count"],
            direction,
            ", ".join(cluster["symbols"]),
            cluster["strength"],
        )

        # MongoDB persistence (Motor async)
        await self._persist_cluster(cluster)

        # Auto Pulse override on strong BEARISH cluster
        if direction == "BEARISH" and cluster["strength"] > 0.65:
            await self._trigger_pulse_override(cluster)

    async def _persist_cluster(self, cluster: Dict) -> None:
        if self.db is None:
            return
        try:
            doc = {**cluster, "persisted_at": datetime.utcnow()}
            await self.db.correlation_events.insert_one(doc)
        except Exception as exc:
            logger.error("Failed to persist correlation cluster: %s", exc)

    async def _trigger_pulse_override(self, cluster: Dict) -> None:
        """Tighten trailing stops globally on a strong BEARISH cluster."""
        payload = {
            "action": "tighten_trailing_global",
            "reason": "correlation_bearish_cluster",
            "cluster": {
                "direction": cluster["direction"],
                "count": cluster["count"],
                "symbols": cluster["symbols"],
                "strength": cluster["strength"],
            },
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{self.pulse_base_url}/control/override",
                    json=payload,
                )
                logger.info(
                    "Pulse override response: %s %s",
                    resp.status_code, resp.text[:120],
                )
        except Exception as exc:
            logger.warning("Pulse override skipped (not reachable): %s", exc)
