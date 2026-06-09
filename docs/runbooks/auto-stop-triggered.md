# Auto-Stop Triggered

## What Fired

`AutoStopTriggered` means Edge emitted at least one emergency-exit decision during the last 5 minutes:

```promql
increase(edge_decision_total{decision="emergency_exit"}[5m]) > 0
```

`EMERGENCY_EXIT` is a protective trading decision. It may be produced by drawdown, consecutive losses, risk overrides, or another safety rule.

## Impact

Automation may have attempted to flatten or reduce exposure. Treat this as a trading safety incident until the trigger condition, broker/Pulse delivery, and current position state are reviewed.

## First Checks

Pause automation before investigating:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/control/pause
```

Confirm the automation state:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/automation
```

Check whether Pulse is reachable and healthy:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/pulse/health
```

Confirm recent emergency exits in Prometheus:

```promql
increase(edge_decision_total{decision="emergency_exit"}[15m])
```

## Triage

1. Verify the affected `symbol` from Alertmanager, Grafana, or the `edge_decision_total` label set.
2. Review current broker positions and open orders outside Edge before resuming automation.
3. Check whether the trigger came from drawdown, consecutive losses, market-hours gating, or a manual risk override.
4. Inspect `backend/engine.py` for the decision path and `backend/pulse_client.py` for broker/Pulse delivery failures or retries.
5. If Pulse is degraded, follow `docs/runbooks/pulse-circuit-breaker.md` and `docs/runbooks/automation-handoff-failures.md`.
6. If losses triggered the exit, follow `docs/runbooks/drawdown-risk.md` before enabling new entries.

## Recovery

Resume only after positions, open orders, Pulse health, and the triggering risk metric are understood.

1. Keep automation paused while reconciling broker state.
2. Cancel or resolve stale orders manually if needed.
3. Confirm no repeated emergency exits are firing:

```promql
increase(edge_decision_total{decision="emergency_exit"}[5m])
```

4. Restart or resume automation using the normal operator workflow.
5. Watch the affected symbol for at least one full strategy cycle after recovery.

## Escalation

Escalate if emergency exits repeat, if broker state differs from Edge state, if Pulse health is failing, or if the strategy attempts new entries before the incident is resolved.
