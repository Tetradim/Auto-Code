# Pulse API SLO Burn

## What Fired

`PulseApiSloFastBurn` and `PulseApiSloSlowBurn` mean Sentinel Edge is spending the Pulse API 99% availability error budget faster than expected.

The alerts are based on `edge_api_calls_total`:

- `status="success"` counts healthy Pulse API calls.
- Any other status counts against the availability SLO.
- The recording rules divide the observed error ratio by the 1% error budget.

## Impact

Pulse API degradation can delay or block position reads, account status reads, signal handoff, and risk-control commands. During a fast burn, verify trading safety before investigating lower-priority dashboard symptoms.

## First Checks

1. Open the Grafana `Broker Health` dashboard.
2. Check `Pulse API SLO Burn Rate`, `API Success vs Failure Rate`, `API Latency Percentiles`, and `Circuit Breaker State`.
3. Confirm whether failures are isolated to one endpoint or system-wide:

   ```promql
   sum by (endpoint, status) (increase(edge_api_calls_total[15m]))
   ```

4. Check whether requests are timing out:

   ```promql
   sum by (endpoint) (rate(edge_api_calls_total{status="timeout"}[5m]))
   ```

5. Check Pulse and Edge service health:

   ```promql
   up{job=~"pulse|sentinel-edge"}
   ```

## Triage

If the circuit breaker is open, inspect Pulse availability and recent network or credential changes before restarting Edge. Restarting Edge alone can clear local state but will not fix a downstream Pulse outage.

If only one endpoint fails, map the endpoint to the Edge workflow that calls it and decide whether to pause only the affected workflow. Account, position, and decision endpoints are safety-critical.

If failures are timeouts with rising latency, check Pulse saturation, network latency, and retry pressure before increasing timeouts. Longer timeouts can hide overload and delay risk actions.

If failures started after a deploy, roll back the smallest recent change that touched Pulse client behavior, credentials, routing, or Alertmanager webhook delivery.

## Mitigation

For `PulseApiSloFastBurn`, prioritize trading safety:

1. Confirm kill switch and dry-run status.
2. Pause autonomous handoff if Pulse cannot accept or verify risk actions.
3. Keep Alertmanager notifications active until the burn rate returns below threshold.

For `PulseApiSloSlowBurn`, investigate during normal operations:

1. Identify the failing endpoint and status.
2. Check for recurring retry queue growth.
3. Add a follow-up issue if the cause is intermittent or capacity-related.

## Resolution

The incident is resolved when both paired burn-rate windows are below their alert thresholds and `edge_api_calls_total{status!="success"}` is no longer increasing unexpectedly.
