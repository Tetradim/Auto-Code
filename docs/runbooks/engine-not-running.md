# Engine Not Running

## What Fired

`EngineNotRunning` means the Edge evaluation scheduler reported that the main engine loop is not running for at least 1 minute:

```promql
edge_engine_running == 0
```

This differs from `SidecarDown`: the API process can still be reachable while ticker analysis has stopped.

## Impact

Edge may continue serving dashboards and status endpoints, but new ticker analysis cycles are not running. Recommendations, protection signals, and automation handoffs can become stale. Keep live automation paused until the scheduler is confirmed active.

## First Checks

1. Confirm the metric state:

   ```promql
   edge_engine_running
   ```

2. Check runtime readiness:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/ready
   ```

3. Check scheduler stats:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/stats
   ```

4. If the scheduler is only paused and dependencies are ready, resume it deliberately:

   ```powershell
   Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/control/resume
   ```

## Triage

If `/api/ready` reports `scheduler_running`, `scheduler_task_alive`, or `scheduler_initialized` as false, use `docs/runbooks/edge-runtime-not-ready.md` before trying to resume automation.

If `/api/stats` shows `paused` as true, confirm the pause was not intentional, then resume the scheduler and watch `edge_engine_running`.

If the scheduler is not paused but `edge_engine_running` remains `0`, inspect backend logs around `Scheduler fatal error`, recent strategy changes, market-data provider failures, and `backend/scheduler.py`.

If this started after a strategy or automation change, keep automation disabled while checking the latest plugin import or evaluation exception.

## Resolution

The incident is resolved when:

- `edge_engine_running == 1`.
- `/api/ready` reports ready.
- `/api/stats` shows the scheduler is not paused and has recent evaluation activity.
- Automation has been deliberately re-enabled, if it was paused during triage.
