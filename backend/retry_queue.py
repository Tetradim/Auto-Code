"""Priority retry queue for deferred Pulse decisions."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(order=True)
class QueuedDecision:
    priority: int
    sequence: int
    symbol: str = field(compare=False)
    decision: str = field(compare=False)
    payload: Dict[str, Any] = field(compare=False)
    endpoint: str = field(compare=False)
    queued_at: float = field(compare=False)
    queued_at_iso: str = field(compare=False)
    ttl_seconds: float = field(compare=False)


class DecisionQueue:
    """In-memory priority queue with stale-drop and shutdown flush."""

    def __init__(
        self,
        log_dir: Path | str,
        default_ttl_seconds: float = 60.0,
        emergency_ttl_seconds: float = 300.0,
    ) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self.emergency_ttl_seconds = emergency_ttl_seconds
        self.log_dir = Path(log_dir)
        self.log_path = self.log_dir / "pulse_retry_queue_shutdown.jsonl"

        self._queue: asyncio.PriorityQueue[QueuedDecision] = asyncio.PriorityQueue()
        self._sequence = 0
        self._wakeup = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._stopped = False

    def _ttl_seconds(self, decision: str) -> float:
        if decision.lower() in {"emergency_exit", "emergency_stop"}:
            return self.emergency_ttl_seconds
        return self.default_ttl_seconds

    def _priority(self, decision: str) -> int:
        return 0 if decision.lower() in {"emergency_exit", "emergency_stop"} else 1

    async def enqueue(
        self,
        symbol: str,
        decision: str,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> None:
        now = time.time()
        item = QueuedDecision(
            priority=self._priority(decision),
            sequence=self._sequence,
            symbol=symbol,
            decision=decision,
            payload=dict(payload),
            endpoint=endpoint,
            queued_at=now,
            queued_at_iso=datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            ttl_seconds=self._ttl_seconds(decision),
        )
        self._sequence += 1
        await self._queue.put(item)
        logger.warning(
            "retry_queue enqueue symbol=%s decision=%s priority=%d ttl_seconds=%.0f queue_size=%d",
            symbol,
            decision,
            item.priority,
            item.ttl_seconds,
            self._queue.qsize(),
        )

    def start(
        self,
        *,
        can_send: Callable[[], bool],
        send_func: Callable[[str, Dict[str, Any]], Awaitable[bool]],
    ) -> None:
        if self._task and not self._task.done():
            return
        self._stopped = False
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._drain_loop(can_send=can_send, send_func=send_func))

    def notify_circuit_closed(self) -> None:
        self._wakeup.set()

    async def _drain_loop(
        self,
        *,
        can_send: Callable[[], bool],
        send_func: Callable[[str, Dict[str, Any]], Awaitable[bool]],
    ) -> None:
        while not self._stopped:
            await self._wakeup.wait()
            self._wakeup.clear()

            while can_send() and not self._queue.empty():
                item = await self._queue.get()
                age = time.time() - item.queued_at
                if age > item.ttl_seconds:
                    logger.info(
                        "retry_queue drop_stale symbol=%s decision=%s age_seconds=%.1f ttl_seconds=%.1f",
                        item.symbol,
                        item.decision,
                        age,
                        item.ttl_seconds,
                    )
                    continue

                sent = await send_func(item.endpoint, item.payload)
                if sent:
                    logger.info(
                        "retry_queue replayed symbol=%s decision=%s queued_at=%s",
                        item.symbol,
                        item.decision,
                        item.queued_at_iso,
                    )
                    continue

                await self._queue.put(item)
                break

    async def flush_to_file(self) -> int:
        if self._queue.empty():
            return 0
        shutdown_at = datetime.now(timezone.utc).isoformat()
        self.log_dir.mkdir(parents=True, exist_ok=True)

        pending: List[QueuedDecision] = []
        while not self._queue.empty():
            pending.append(await self._queue.get())

        with self.log_path.open("a", encoding="utf-8") as handle:
            for item in pending:
                handle.write(
                    json.dumps(
                        {
                            "symbol": item.symbol,
                            "decision": item.decision,
                            "endpoint": item.endpoint,
                            "payload": item.payload,
                            "priority": item.priority,
                            "queued_at": item.queued_at_iso,
                            "shutdown_at": shutdown_at,
                        }
                    )
                    + "\n"
                )
        logger.warning(
            "retry_queue flushed_to_file count=%d path=%s",
            len(pending),
            self.log_path,
        )
        return len(pending)

    async def stop(self) -> None:
        self._stopped = True
        self._wakeup.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def stats(self) -> Dict[str, Any]:
        return {
            "queue_size": self._queue.qsize(),
            "default_ttl_seconds": self.default_ttl_seconds,
            "emergency_ttl_seconds": self.emergency_ttl_seconds,
            "log_path": str(self.log_path),
        }

    async def snapshot(self, limit: int = 100) -> List[Dict[str, Any]]:
        items: List[QueuedDecision] = []
        while not self._queue.empty() and len(items) < limit:
            items.append(await self._queue.get())
        for item in items:
            await self._queue.put(item)
        items.sort()
        return [
            {
                "symbol": item.symbol,
                "decision": item.decision,
                "priority": item.priority,
                "queued_at": item.queued_at_iso,
                "ttl_seconds": item.ttl_seconds,
                "endpoint": item.endpoint,
            }
            for item in items
        ]
