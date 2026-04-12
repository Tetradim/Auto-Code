import asyncio

import pytest

from backend.pulse_client import CircuitState, PulseClient


@pytest.mark.asyncio
async def test_emergency_exit_queued_with_higher_priority():
    client = PulseClient()
    client.pulse_available = True
    client.state = CircuitState.OPEN

    await client.send_decision("AAPL", "buy")
    await client.send_decision("MSFT", "emergency_stop")

    first = await client._retry_queue.get()
    second = await client._retry_queue.get()

    assert first.decision == "emergency_stop"
    assert second.decision == "buy"

    await client.aclose()


@pytest.mark.asyncio
async def test_stale_retries_are_dropped_during_drain(monkeypatch):
    client = PulseClient()
    client.pulse_available = True
    client.state = CircuitState.OPEN
    client.DEFAULT_RETRY_TTL_SECONDS = 0.01

    await client.send_decision("AAPL", "buy")
    queued = await client._retry_queue.get()
    queued.queued_at -= 120
    await client._retry_queue.put(queued)

    replayed = []

    async def fake_post(endpoint, payload):
        replayed.append((endpoint, payload))
        return True

    monkeypatch.setattr(client, "_post", fake_post)
    client.state = CircuitState.CLOSED
    drain_task = asyncio.create_task(client._drain_queue())
    client._queue_wakeup.set()
    await asyncio.sleep(0.05)
    drain_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await drain_task

    assert replayed == []
    assert client._retry_queue.empty()

    await client.aclose()
