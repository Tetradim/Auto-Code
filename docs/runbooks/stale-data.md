# Stale Data

## What Fired

`StaleData` means no fresh tick timestamp has been observed for more than 30 seconds:

```promql
time() - sentinel_last_tick > 30
```

`sentinel_last_tick` is the freshness metric for incoming ticker data. Treat this alert as a market-data freshness problem until proven otherwise.

## Impact

Stale data can make live entries, exits, stop tightening, and risk checks operate on old prices. During market hours, this is a trading safety issue, not just a telemetry issue.

## First Checks

Check automation state before changing ticker or provider settings:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/automation
```

Pause automation if stale data overlaps with active positions, emergency exits, or price-fetch failures:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/control/pause
```

Find symbols with stale ticks:

```promql
time() - sentinel_last_tick
```

Compare with price-fetch failures:

```promql
sum by (source, symbol) (rate(price_fetch_failures_total[5m]))
```

## Triage

1. Confirm whether the alert is firing during market hours. If the market is closed, verify the market-hours guard before treating this as a live incident.
2. If only one symbol is stale, check ticker format, provider support, halts, splits, and whether the symbol was recently added or removed.
3. If many symbols are stale, check the backend scheduler, WebSocket manager, provider credentials, network access, and price-fetch failure alerts.
4. Review `backend/price_fetcher.py` for provider fallback and cache behavior.
5. Review `backend/scheduler.py` for evaluation cadence and whether `evaluate_ticker` is returning before state updates.
6. If stale data overlaps with slow evaluation, follow `docs/runbooks/slow-evaluation.md`.
7. If stale data overlaps with provider failures, follow `docs/runbooks/price-fetch-failures.md`.

## Resolution

The incident is resolved when:

- `time() - sentinel_last_tick` falls below 30 seconds for active symbols during market hours.
- Price-fetch failures have recovered or been isolated to a known provider.
- Affected symbols have fresh current prices in the UI or API.
- Automation is resumed deliberately if it was paused.

## Escalation

Escalate if stale data affects symbols with open positions, if all symbols stop updating during market hours, if provider failures and slow evaluation fire together, or if Edge and broker position state diverge while prices are stale.
