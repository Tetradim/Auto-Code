import asyncio

from backend.retry_queue import DecisionQueue


def test_emergency_exit_queued_with_higher_priority(tmp_path):
    async def _run():
        queue = DecisionQueue(log_dir=tmp_path)
        await queue.enqueue("AAPL", "buy", "/api/tickers/AAPL/decision", {"decision": "buy"})
        await queue.enqueue(
            "MSFT",
            "emergency_stop",
            "/api/tickers/MSFT/decision",
            {"decision": "emergency_stop"},
        )

        first = await queue._queue.get()
        second = await queue._queue.get()

        assert first.decision == "emergency_stop"
        assert second.decision == "buy"

    asyncio.run(_run())


def test_stale_retries_are_dropped_during_drain(tmp_path):
    async def _run():
        queue = DecisionQueue(log_dir=tmp_path, default_ttl_seconds=0.01)
        await queue.enqueue("AAPL", "buy", "/api/tickers/AAPL/decision", {"decision": "buy"})

        stale_item = await queue._queue.get()
        stale_item.queued_at -= 120
        await queue._queue.put(stale_item)

        replayed = []

        async def fake_send(endpoint, payload):
            replayed.append((endpoint, payload))
            return True

        queue.start(can_send=lambda: True, send_func=fake_send)
        queue.notify_circuit_closed()
        await asyncio.sleep(0.05)

        assert replayed == []
        assert queue._queue.empty()

        await queue.stop()

    asyncio.run(_run())


def test_flush_to_file_writes_shutdown_timestamps(tmp_path):
    async def _run():
        queue = DecisionQueue(log_dir=tmp_path)
        await queue.enqueue("TSLA", "buy", "/api/tickers/TSLA/decision", {"decision": "buy"})

        written = await queue.flush_to_file()

        assert written == 1
        content = queue.log_path.read_text(encoding="utf-8")
        assert '"queued_at"' in content
        assert '"shutdown_at"' in content

    asyncio.run(_run())
