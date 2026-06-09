# API Rate Limit Rejections

## What Fired

`ApiRateLimitRejections` means Edge returned one or more HTTP 429 responses from the API rate limiter:

```promql
edge_rate_limit_rejections:rate5m{scope="api"} > 0
```

This alert is about active user-visible rejection. It is different from `ApiRateLimitBucketPressure`, which tracks how many client buckets are being retained.

## Impact

Requests are being denied until the caller's fixed-window budget resets. Dashboard refreshes, frontend RUM uploads, local scripts, or automation clients may see `429` responses with `Retry-After`, `RateLimit-Limit`, `RateLimit-Remaining`, and `RateLimit-Reset` headers.

## First Checks

1. Check the current caller budget and aggregate pressure:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/rate-limit/status
   ```

2. Confirm rejection rate by scope:

   ```promql
   edge_rate_limit_rejections:rate5m
   ```

3. Check bucket pressure to distinguish a single noisy caller from broad scan traffic:

   ```promql
   edge_rate_limit_tracked_clients:max5m
   ```

4. Inspect the `API Rate Limit Rejections` panel in Grafana `Broker Health`.

## Triage

If rejection rate is low and `Retry-After` values are small, the caller may simply be over-refreshing. Let the fixed window reset and avoid restarting Edge.

If the frontend is the likely caller, inspect `frontend/src/lib/api.ts` and dashboard polling intervals before raising API limits. A UI loop can generate steady 429s without a backend failure.

If automation is the likely caller, pause nonessential automation and check whether repeated health, status, or backtest calls are ignoring `Retry-After`.

If rejection rate and bucket pressure are both high, use `docs/runbooks/api-rate-limit-bucket-pressure.md` to check for scan traffic, proxy identity churn, or stale bucket pruning.

## Resolution

The incident is resolved when:

- `edge_rate_limit_rejections:rate5m{scope="api"}` returns to `0`.
- `/api/rate-limit/status` reports available `remaining_requests` for normal callers.
- Any caller that triggered 429s honors `Retry-After` and reduces request frequency.
- The `API Rate Limit Rejections` Grafana panel stays flat after the next request window.
