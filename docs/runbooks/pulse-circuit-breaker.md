# Pulse Circuit Breaker

## What Fired

`CircuitBreakerOpen` means the Pulse broker circuit is blocking handoff calls after repeated failures:

```promql
broker_circuit_state{broker_id="pulse"} == 2
```

`CircuitBreakerHalfOpen` means Edge is allowing limited probe calls to test whether Pulse recovered:

```promql
broker_circuit_state{broker_id="pulse"} == 1
```

## Impact

Edge can continue evaluating markets, but Pulse handoff delivery may be delayed, queued, suppressed, or failed. Do not enable live automation while the circuit is Open, and avoid flooding Pulse while the circuit is Half-Open.

## First Checks

1. Check the breaker state:

   ```promql
   broker_circuit_state{broker_id="pulse"}
   ```

2. Check Pulse health from Edge:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/pulse/health
   ```

3. Check automation status and latest handoff outcome:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/automation
   ```

4. Compare broker API failures and handoff outcomes:

   ```promql
   sum by (endpoint, status) (increase(edge_api_calls_total[15m]))
   ```

   ```promql
   edge_automation_handoffs:rate5m
   ```

## Triage

If the circuit is Open, pause live automation and let the cooldown protect Pulse from repeated failing calls. Check Pulse availability, credentials, base URL, network reachability, and recent broker API errors.

If the circuit is Half-Open, do not trigger manual handoff bursts. Allow the limited probe request to complete, then verify whether the state returns to Closed or reopens.

If handoffs are failing while the circuit is Open, use `docs/runbooks/automation-handoff-failures.md` and inspect the retry queue before retrying commands.

If this started after a local edit, inspect `backend/pulse_client.py`, Pulse configuration, and any changes touching automation handoff paths.

## Resolution

The incident is resolved when:

- `broker_circuit_state{broker_id="pulse"}` returns to Closed.
- `/api/pulse/health` reports healthy or expected standalone behavior.
- `/api/automation` has no fresh failed `last_handoff`.
- The retry queue is draining or empty.
- Automation has been deliberately re-enabled, if it was paused during triage.
