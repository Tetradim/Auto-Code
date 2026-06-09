# Engine Paused

## What Fired

`EdgeEnginePaused` means the scheduler has reported a paused state for more than 10 minutes:

```promql
edge_engine_paused == 1
```

This is different from `EngineNotRunning`. A paused scheduler may be intentional, but it stops new scheduled analysis cycles until it is resumed.

## Impact

Recommendations, protection signals, and automation handoffs can become stale while the scheduler is paused. Do not assume the pause is safe just because the API and UI are still reachable.

## First Checks

Check scheduler status:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/stats
```

Check automation state before resuming:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/automation
```

Confirm the metric state:

```promql
edge_engine_paused
```

Resume only after confirming the pause was not intentional:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/control/resume
```

## Triage

1. Confirm whether an operator, runbook, or safety incident intentionally paused the scheduler.
2. If the pause followed an emergency exit, drawdown alert, stale data alert, or price-fetch failure, resolve that incident before resuming.
3. If the pause was accidental, review recent UI actions in Protection or Asset Command and confirm automation handoff mode.
4. Inspect `backend/scheduler.py` if the scheduler immediately pauses again after resume.
5. If `/api/stats` reports the scheduler is not running after resume, follow `docs/runbooks/engine-not-running.md`.

## Resolution

The incident is resolved when:

- The pause is confirmed intentional, or `edge_engine_paused == 0` after a deliberate resume.
- `/api/stats` shows the scheduler is running and not paused.
- Automation state has been reviewed before live handoff is enabled.
- Any related risk incident has been closed or explicitly handed off.

## Escalation

Escalate if the scheduler re-pauses without operator action, if automation remains enabled while analysis is paused, or if live positions depend on stale protection signals.
