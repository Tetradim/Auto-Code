# Slow Evaluation

## What Fired

`SlowEvaluation` means the p99 ticker evaluation latency exceeded 1 second for 3 minutes:

```promql
histogram_quantile(0.99, rate(edge_eval_duration_seconds_bucket[5m])) > 1.0
```

Edge records this latency in `edge_eval_duration_seconds_bucket` from the scheduler evaluation path and analyst Prometheus exporter.

## Impact

Slow evaluation can delay entry, exit, and risk decisions. In live trading, the first question is whether the latency is symbol-specific or broad across the evaluation loop.

## First Checks

Check automation state before changing runtime settings:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/automation
```

Pause automation if evaluation latency overlaps with emergency exits, broker failures, or stale data:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/control/pause
```

Find the slowest symbols:

```promql
topk(10, histogram_quantile(0.99, sum by (le, symbol) (rate(edge_eval_duration_seconds_bucket[5m]))))
```

Check whether the whole engine is slow:

```promql
histogram_quantile(0.99, sum by (le) (rate(edge_eval_duration_seconds_bucket[5m])))
```

## Triage

1. If only one symbol is slow, inspect that symbol's data fetch, spread/liquidity, custom strategy plugins, and recent analyst signal work.
2. If all symbols are slow, check backend CPU, broker/Pulse calls, MongoDB persistence, and price-fetch failure alerts.
3. Review `backend/scheduler.py`, especially the `evaluate_ticker` flow and the final latency observation.
4. Review `backend/analyst/exporters/prometheus.py` if analyst modules are publishing evaluation timings.
5. Compare slow symbols with Puzzle Key Strategy or other custom plugins before disabling global automation.
6. Check whether a large ticker universe or low scheduler interval is causing too much concurrent work.

## Resolution

The incident is resolved when:

- p99 evaluation latency falls below 1 second for the active universe.
- Any symbol-specific plugin, data, or persistence issue has been isolated.
- Automation has been resumed deliberately if it was paused.
- The affected strategy or ticker universe change has a follow-up task if it caused the latency.

## Escalation

Escalate if slow evaluation overlaps with stale data, emergency exits, broker failures, or repeated missed market windows. Treat broad latency across all symbols as an engine reliability incident, not a single-ticker strategy issue.
