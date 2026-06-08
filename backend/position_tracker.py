"""Position Tracker — dual-mode PnL and position state manager.

Tracking modes
──────────────
CHANGE_STREAM (primary)
    Watches the MongoDB `positions` collection for changes written by Sentinel
    Pulse. Each insert/update/replace yields an exact position snapshot with
    real PnL, trailing-stop state, and fill prices from the execution engine.
    On position close events it calls DecisionEngine.record_trade_result() with
    the real PnL so consecutive-loss tracking and win-rate metrics are accurate.

SELF_SOVEREIGN (fallback)
    When the change stream cannot be established (Pulse not writing to Mongo,
    no replica set, or DB unavailable), the tracker maintains its own position
    state. Entry price is recorded when a BUY decision is sent. PnL is computed
    each evaluation cycle from the live yfinance price vs entry price.
    Exit decisions (EMERGENCY_EXIT, STOP_BUYING) finalise and record the trade.

Mode transitions
────────────────
- On startup: tries change stream → falls back to SELF_SOVEREIGN on failure.
- Periodic upgrade probe (every UPGRADE_PROBE_INTERVAL seconds): SELF_SOVEREIGN
  mode silently attempts to re-establish the change stream. If successful,
  switches back to CHANGE_STREAM and discards self-sovereign state.
- Manual fallback can be forced by calling switch_to_fallback().

Schema expected from Pulse in the `positions` collection
──────────────────────────────────────────────────────────
{
  "symbol":           "SPY",
  "status":           "open" | "closed",   ← required
  "has_position":     true,
  "pnl":              125.50,
  "pnl_pct":          1.20,
  "trailing_enabled": false,
  "trailing_percent": null,
  "entry_price":      440.00,
  "current_price":    445.28,
  "drawdown_pct":     0.0                  ← optional; derived locally if absent
}

All fields except `symbol` and `status` are optional — the tracker normalises
and applies safe defaults so partial documents don't crash the risk guards.

Command Bus (Pulse → Edge feedback loop)
─────────────────────────────────────────
The tracker also watches the `commands` collection for Pulse → Edge messages.
This enables the feedback loop where Pulse reports:
- ORDER_FILLED: Order fill confirmation with real PnL
- POSITION_UPDATE: Current position state
- ACCOUNT_UPDATE: Account-level metrics
- ORDER_REJECTED: Failed order notification

When these commands arrive, DecisionEngine methods are called to update
risk state, close the feedback loop, and enable advanced risk logic.
"""
import asyncio
import logging
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from engine import DecisionEngine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

UPGRADE_PROBE_INTERVAL = 60   # seconds between SELF_SOVEREIGN → change stream probes
CHANGE_STREAM_RETRY    = 15   # seconds between change stream reconnect attempts


# ─────────────────────────────────────────────────────────────────────────────
# Mode enum
# ─────────────────────────────────────────────────────────────────────────────

class TrackingMode(Enum):
    CHANGE_STREAM  = auto()   # authoritative data from MongoDB / Pulse
    SELF_SOVEREIGN = auto()   # local price-based approximate tracking


# ─────────────────────────────────────────────────────────────────────────────
# Position state shape
# ─────────────────────────────────────────────────────────────────────────────

def _empty_pos() -> Dict:
    return {
        "has_position":     False,
        "pnl":              0.0,
        "pnl_pct":          0.0,
        "trailing_enabled": False,
        "trailing_percent": None,
        "peak_pnl_pct":     0.0,
        "drawdown_pct":     0.0,
        # Self-sovereign fields (ignored in CHANGE_STREAM mode)
        "entry_price":      None,
        "entry_time":       None,
        "source":           "empty",
    }


# ─────────────────────────────────────────────────────────────────────────────
# PositionTracker
# ─────────────────────────────────────────────────────────────────────────────

class PositionTracker:
    """Dual-mode position and PnL tracker.

    Usage in scheduler
    ──────────────────
        self.position_tracker = PositionTracker(db=db, decision_engine=engine)
        asyncio.create_task(self.position_tracker.run())

        # In evaluate_ticker():
        pos = self.position_tracker.get(symbol)

        # After sending a decision:
        self.position_tracker.on_decision(symbol, decision, entry_price=price)
    """

    def __init__(
        self,
        db: Optional[Any] = None,
        decision_engine: Optional["DecisionEngine"] = None,
    ) -> None:
        self.db              = db
        self.decision_engine = decision_engine

        self.mode: TrackingMode = TrackingMode.SELF_SOVEREIGN

        # symbol → position dict
        self._state: Dict[str, Dict] = {}

        self._running  = False
        self._bg_task: Optional[asyncio.Task] = None

        logger.info("PositionTracker initialised (mode: SELF_SOVEREIGN pending probe)")

    # ─────────────────────────────────────────────────────────────────────────
    # Public read / write interface (called from scheduler)
    # ─────────────────────────────────────────────────────────────────────────

    def get(self, symbol: str) -> Dict:
        """Return current position state for *symbol*, defaulting to empty."""
        return self._state.get(symbol, _empty_pos())

    def on_decision(
        self,
        symbol:      str,
        decision:    Any,             # Decision enum from engine.py
        entry_price: Optional[float] = None,
    ) -> None:
        """Notify the tracker that a decision was sent to Pulse.

        In SELF_SOVEREIGN mode this maintains position state locally:
        - BUY → record entry price, mark has_position=True
        - EMERGENCY_EXIT / STOP_BUYING → finalise trade, record result
        - ENABLE/TIGHTEN_TRAILING_STOP → update trailing flag

        In CHANGE_STREAM mode this is mostly a no-op because the authoritative
        state comes from MongoDB, but we still update local tracking immediately
        so the next evaluate_ticker() cycle sees coherent state before the
        change stream event arrives.
        """
        from engine import Decision  # local import avoids circular at module level

        ps = self._state.setdefault(symbol, _empty_pos())

        if decision == Decision.BUY:
            if entry_price is not None and not ps["has_position"]:
                ps["has_position"] = True
                ps["entry_price"]  = entry_price
                ps["entry_time"]   = datetime.utcnow().isoformat()
                ps["pnl"]          = 0.0
                ps["pnl_pct"]      = 0.0
                ps["peak_pnl_pct"] = 0.0
                ps["drawdown_pct"] = 0.0
                ps["source"]       = "optimistic"
                logger.debug("PositionTracker: BUY %s @ %.4f", symbol, entry_price)

        elif decision in (Decision.EMERGENCY_EXIT, Decision.STOP_BUYING):
            pnl = ps.get("pnl", 0.0)
            if self.decision_engine and ps.get("has_position"):
                self.decision_engine.record_trade_result_legacy(symbol, pnl)
                logger.info(
                    "record_trade_result(%s, %.2f) via on_decision", symbol, pnl
                )
            self._state[symbol] = _empty_pos()

        elif decision == Decision.ENABLE_TRAILING_STOP:
            ps["trailing_enabled"] = True

        elif decision == Decision.TIGHTEN_TRAILING_STOP:
            ps["trailing_enabled"]  = True
            ps["trailing_percent"]  = 0.5

    def update_price(self, symbol: str, current_price: float) -> None:
        """Recompute self-sovereign PnL for *symbol* using the live price.

        Called every evaluation tick only when mode == SELF_SOVEREIGN.
        In CHANGE_STREAM mode the MongoDB event provides the authoritative PnL
        so local recomputation would overwrite real data with an approximation.
        """
        if self.mode != TrackingMode.SELF_SOVEREIGN:
            return

        ps = self._state.get(symbol)
        if not ps or not ps.get("has_position") or ps.get("entry_price") is None:
            return

        entry = ps["entry_price"]
        if entry <= 0:
            return

        pnl_pct = ((current_price - entry) / entry) * 100.0
        pnl     = current_price - entry  # per-share; multiply by qty if available

        peak       = max(ps.get("peak_pnl_pct", 0.0), pnl_pct)
        drawdown   = max(0.0, peak - pnl_pct)

        ps["pnl"]          = round(pnl,     4)
        ps["pnl_pct"]      = round(pnl_pct, 4)
        ps["peak_pnl_pct"] = round(peak,    4)
        ps["drawdown_pct"] = round(drawdown, 4)
        ps["source"]       = "self_sovereign"

    def remove(self, symbol: str) -> None:
        self._state.pop(symbol, None)

    @property
    def mode_name(self) -> str:
        return self.mode.name

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    def start(self) -> asyncio.Task:
        """Launch the background task and return it."""
        self._running  = True
        self._bg_task  = asyncio.create_task(self._run(), name="position-tracker")
        return self._bg_task

    def stop(self) -> None:
        self._running = False
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()

    async def _run(self) -> None:
        """Main background loop: attempt CHANGE_STREAM, probe for upgrade.
        
        Also runs the Command Bus change stream to listen for Pulse → Edge messages.
        """
        if self.db is None:
            logger.warning(
                "PositionTracker: no DB — running in SELF_SOVEREIGN mode permanently"
            )
            return

        # Initial probe - positions and commands
        await asyncio.gather(
            self._try_change_stream(),
            self._try_command_stream(),
        )

        # If still SELF_SOVEREIGN, schedule periodic upgrade probes
        while self._running:
            await asyncio.sleep(UPGRADE_PROBE_INTERVAL)
            if self.mode == TrackingMode.SELF_SOVEREIGN:
                logger.debug("PositionTracker: probing for change stream upgrade...")
                await self._try_change_stream()
            
            # Always probe for command stream too
            await self._try_command_stream()

    # ─────────────────────────────────────────────────────────────────────────
    # Change stream (primary mode)
    # ─────────────────────────────────────────────────────────────────────────

    async def _try_change_stream(self) -> None:
        """Attempt to open the change stream and hold it.

        Returns when the stream closes (error or intentional stop).
        Switches to SELF_SOVEREIGN on any failure.
        """
        try:
            pipeline = [{"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}}]
            async with self.db.positions.watch(
                pipeline,
                full_document="updateLookup",
            ) as stream:
                self.mode = TrackingMode.CHANGE_STREAM
                logger.info("✅ PositionTracker: CHANGE_STREAM active (watching positions)")

                async for change in stream:
                    if not self._running:
                        break
                    try:
                        await self._handle_change(change)
                    except Exception as exc:
                        logger.error("PositionTracker: error handling change: %s", exc)

        except Exception as exc:
            if self.mode == TrackingMode.CHANGE_STREAM:
                logger.warning(
                    "PositionTracker: change stream lost (%s) → SELF_SOVEREIGN", exc
                )
            else:
                logger.debug(
                    "PositionTracker: change stream unavailable (%s) — staying SELF_SOVEREIGN", exc
                )
            self.mode = TrackingMode.SELF_SOVEREIGN

    async def _handle_change(self, change: dict) -> None:
        """Process a MongoDB change stream event from the positions collection."""
        doc = change.get("fullDocument") or change.get("updateDescription", {})
        if not doc:
            return

        symbol = doc.get("symbol", "").upper()
        if not symbol:
            return

        status = doc.get("status", "open").lower()
        prev   = self._state.get(symbol, _empty_pos())

        # Normalise field names — Pulse may use different keys across versions
        has_pos  = bool(doc.get("has_position", doc.get("active", status == "open")))
        pnl      = float(doc.get("pnl",      doc.get("unrealized_pnl",     0.0)))
        pnl_pct  = float(doc.get("pnl_pct",  doc.get("unrealized_pnl_pct", 0.0)))
        trail_en = bool(doc.get("trailing_enabled", doc.get("trailing_stop_enabled", False)))
        trail_pct = doc.get("trailing_percent")
        entry    = doc.get("entry_price")
        drawdown = float(doc.get("drawdown_pct", 0.0))

        # High-water mark — carry forward so drawdown survives partial updates
        peak = max(prev.get("peak_pnl_pct", 0.0), pnl_pct)
        if drawdown == 0.0:
            drawdown = max(0.0, peak - pnl_pct)

        self._state[symbol] = {
            "has_position":     has_pos,
            "pnl":              pnl,
            "pnl_pct":          pnl_pct,
            "trailing_enabled": trail_en,
            "trailing_percent": trail_pct,
            "peak_pnl_pct":     peak,
            "drawdown_pct":     drawdown,
            "entry_price":      entry,
            "entry_time":       prev.get("entry_time"),
            "source":           "change_stream",
        }

        # Position close event — record the final result in DecisionEngine
        was_open  = prev.get("has_position", False)
        now_closed = status == "closed" or (was_open and not has_pos)

        if now_closed and was_open:
            final_pnl = float(doc.get("realized_pnl", doc.get("pnl", pnl)))
            if self.decision_engine:
                self.decision_engine.record_trade_result_legacy(symbol, final_pnl)
                logger.info(
                    "record_trade_result(%s, %.2f) via change stream (status=%s)",
                    symbol, final_pnl, status,
                )
            self._state[symbol] = _empty_pos()

    # ─────────────────────────────────────────────────────────────────────────
    # Command Bus Change Stream (Pulse → Edge feedback loop)
    # ─────────────────────────────────────────────────────────────────────────

    async def _try_command_stream(self) -> None:
        """Watch the commands collection for Pulse → Edge messages.
        
        This implements the feedback loop where Pulse reports:
        - ORDER_FILLED: Order fill confirmation
        - POSITION_UPDATE: Current position state  
        - ACCOUNT_UPDATE: Account-level metrics
        - ORDER_REJECTED: Failed orders
        """
        if not hasattr(self, '_command_stream_running'):
            self._command_stream_running = False
        
        if self._command_stream_running:
            return
            
        try:
            # Import command types for handling
            from shared.commands import (
                CommandType, command_from_dict, COMMANDS_COLLECTION
            )
            
            pipeline = [
                {"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}}
            ]
            
            async with self.db[COMMANDS_COLLECTION].watch(
                pipeline,
                full_document="updateLookup",
            ) as stream:
                self._command_stream_running = True
                logger.info("✅ CommandBus: watching commands collection")
                
                async for change in stream:
                    if not self._running:
                        break
                    try:
                        await self._handle_command(change)
                    except Exception as exc:
                        logger.error("CommandBus: error handling command: %s", exc)
                        
        except Exception as exc:
            logger.debug("CommandBus: change stream unavailable (%s)", exc)
        finally:
            self._command_stream_running = False

    async def _handle_command(self, change: dict) -> None:
        """Process a command from Pulse.
        
        When ORDER_FILLED arrives, we call decision_engine.record_trade_result()
        with real fill data, activating the advanced risk logic.
        
        When POSITION_UPDATE arrives, we call decision_engine.update_position_state()
        with real position data.
        """
        from shared.commands import CommandType, command_from_dict
        
        doc = change.get("fullDocument") or {}
        if not doc:
            return
        
        cmd_type = doc.get("command_type")
        if not cmd_type:
            return
        
        try:
            # Parse into typed command object
            cmd = command_from_dict(doc)
            
            # Handle each command type
            if cmd_type == CommandType.ORDER_FILLED:
                await self._handle_order_filled(cmd)
            elif cmd_type == CommandType.POSITION_UPDATE:
                await self._handle_position_update(cmd)
            elif cmd_type == CommandType.ACCOUNT_UPDATE:
                await self._handle_account_update(cmd)
            elif cmd_type == CommandType.ORDER_REJECTED:
                await self._handle_order_rejected(cmd)
            else:
                logger.debug("CommandBus: unhandled command type: %s", cmd_type)
                
        except Exception as exc:
            logger.error("CommandBus: failed to process command: %s", exc)

    async def _handle_order_filled(self, cmd) -> None:
        """Handle ORDER_FILLED command - close the feedback loop."""
        if not self.decision_engine:
            return
            
        # Record the trade result with real fill data
        await self.decision_engine.record_trade_result(
            symbol=cmd.symbol,
            fill_price=cmd.fill_price,
            quantity=cmd.quantity,
            side=cmd.side,
            realized_pnl=cmd.pnl_realized,
            order_id=cmd.order_id,
        )
        
        logger.info(
            "✅ CommandBus: ORDER_FILLED %s @ %.2f (pnl=%.2f)",
            cmd.symbol, cmd.fill_price, cmd.pnl_realized or 0
        )

    async def _handle_position_update(self, cmd) -> None:
        """Handle POSITION_UPDATE command - update position state."""
        if not self.decision_engine:
            return
            
        # Update position state in decision engine
        self.decision_engine.update_position_state(
            symbol=cmd.symbol,
            position_size=cmd.position_size,
            entry_price=cmd.entry_price,
            pnl_pct=cmd.current_pnl_pct,
            pnl_dollar=cmd.current_pnl_dollar,
        )
        
        logger.info(
            "📍 CommandBus: POSITION_UPDATE %s size=%.4f pnl=%.2f%%",
            cmd.symbol, cmd.position_size, cmd.current_pnl_pct
        )

    async def _handle_account_update(self, cmd) -> None:
        """Handle ACCOUNT_UPDATE command - update account metrics."""
        if not self.decision_engine:
            return
            
        # Update account state in decision engine
        self.decision_engine.update_account_state(
            total_equity=cmd.total_equity,
            available_balance=cmd.available_balance,
            margin_used=cmd.total_margin_used,
            unrealized_pnl=cmd.unrealized_pnl,
        )
        
        logger.info(
            "💰 CommandBus: ACCOUNT_UPDATE equity=%.2f pnl=%.2f",
            cmd.total_equity, cmd.unrealized_pnl
        )

    async def _handle_order_rejected(self, cmd) -> None:
        """Handle ORDER_REJECTED command - log the failure."""
        if not self.decision_engine:
            return
            
        # Record the rejection for risk tracking
        self.decision_engine.record_order_rejected(
            symbol=cmd.symbol,
            order_id=cmd.order_id,
            reason=cmd.reason,
        )
        
        logger.warning(
            "❌ CommandBus: ORDER_REJECTED %s reason=%s",
            cmd.symbol, cmd.reason
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Force-fallback (callable from tests or alert handler)
    # ─────────────────────────────────────────────────────────────────────────

    def switch_to_fallback(self, reason: str = "manual") -> None:
        """Force SELF_SOVEREIGN mode — useful in tests or emergency overrides."""
        if self.mode != TrackingMode.SELF_SOVEREIGN:
            logger.warning("PositionTracker: forced to SELF_SOVEREIGN (%s)", reason)
            self.mode = TrackingMode.SELF_SOVEREIGN
