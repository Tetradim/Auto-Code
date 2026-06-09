# Price Fetch Failures

## What Fired

`PriceFetchFailures` means market-data fetch errors are occurring at more than 0.5 failures per second over 5 minutes:

```promql
rate(price_fetch_failures_total[5m]) > 0.5
```

`price_fetch_failures_total` is labeled by `symbol` and `source`, so first determine whether the issue is one ticker, one provider, or the whole data path.

## Impact

Failed price fetches can cause the scheduler to skip ticker evaluation. That can delay entries, exits, stop tightening, and risk decisions. Treat this as a data freshness problem before tuning strategy parameters.

## First Checks

Check automation state before changing ticker or provider settings:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/automation
```

Pause automation if failures overlap with stale data, emergency exits, or active positions:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/control/pause
```

Find the failing providers:

```promql
sum by (source) (rate(price_fetch_failures_total[5m]))
```

Find the affected symbols:

```promql
topk(20, sum by (symbol) (rate(price_fetch_failures_total[5m])))
```

Check whether failures are isolated to a provider-symbol pair:

```promql
topk(20, sum by (source, symbol) (rate(price_fetch_failures_total[5m])))
```

## Triage

1. If one `source` dominates, inspect that provider's API key, rate limits, service status, and configured provider order.
2. If one `symbol` dominates across sources, confirm the ticker format, market session, splits/halts, and whether the instrument is supported by each provider.
3. If all sources fail, check network connectivity, DNS, API credentials, and the backend process environment.
4. Review `backend/price_fetcher.py` for provider fallback behavior and cache use.
5. Review `backend/scheduler.py` because `evaluate_ticker` returns early when `get_price_with_volume` has no result.
6. If failures correlate with slow evaluation, follow `docs/runbooks/slow-evaluation.md` after stabilizing data fetches.

## Resolution

The incident is resolved when:

- `rate(price_fetch_failures_total[5m])` falls below the alert threshold.
- Provider/source failures have been isolated or recovered.
- Affected symbols are receiving fresh prices again.
- Automation is resumed deliberately if it was paused.

## Escalation

Escalate if the primary provider is down during live trading, if multiple providers fail together, if stale data alerts fire at the same time, or if active positions cannot be evaluated with fresh prices.
