# Automation Handoff Failures

## What Fired

`EdgeAutomationHandoffFailures` means Edge recorded failed Edge-to-Pulse handoff delivery for at least 2 minutes:

```promql
edge_automation_handoffs:rate5m{result="failed"}
```

This is different from `result="suppressed"`, which can be expected when automation is disabled, a ticker is off, confidence is below threshold, cooldown is active, or the market is closed.

## Impact

Edge may still evaluate tickers and produce decisions, but Pulse is not accepting or confirming automation handoff commands. Live or paper automation can drift from operator expectations if failed handoffs are ignored.

## First Checks

1. Pause autonomous handoff before making broker or Pulse changes.
2. Check the current Edge automation state:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/automation
   ```

3. Check Pulse health from Edge:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/pulse/health
   ```

4. Inspect the failing action, mode, and reason labels:

   ```promql
   edge_automation_handoffs:rate5m{result="failed"}
   ```

5. Compare failed delivery with broker API health:

   ```promql
   sum by (endpoint, status) (increase(edge_api_calls_total[15m]))
   ```

## Triage

If `reason="pulse_send_failed"`, check Pulse availability, the configured handoff endpoint, network routing, and Edge backend logs around `Pulse handoff`.

If Pulse health is failing or the Pulse API SLO burn alerts are active, keep handoff paused and use `docs/runbooks/pulse-api-slo-burn.md` before retrying automation.

If handoff is enabled in `/api/automation` but Pulse is unavailable, switch automation back to `recommend_only` until delivery is healthy.

## Resolution

The incident is resolved when:

- `/api/pulse/health` reports healthy or expected standalone behavior.
- `edge_automation_handoffs:rate5m{result="failed"}` returns no active series.
- The latest `/api/automation` status shows no fresh failed `last_handoff`.
- Automation has been deliberately re-enabled, if it was paused during mitigation.
