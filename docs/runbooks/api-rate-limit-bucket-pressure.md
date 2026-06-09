# API Rate Limit Bucket Pressure

## What Fired

`ApiRateLimitBucketPressure` means the in-memory API rate limiter tracked more than 500 client buckets for at least 5 minutes:

```promql
edge_rate_limit_tracked_clients:max5m > 500
```

This alert is about limiter state growth, not a single rejected request. It can indicate scan traffic, runaway automation, a frontend polling loop, or a stale bucket pruning regression.

## Impact

Edge may still serve requests, but excessive bucket growth can add memory pressure and make legitimate users hit rate limits more often. If the growth is caused by automation or a polling loop, it can also hide more important API failures behind rate-limit noise.

## First Checks

1. Check the current aggregate limiter state:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/rate-limit/status
   ```

2. Confirm the alerting series:

   ```promql
   edge_rate_limit_tracked_clients:max5m
   ```

3. Check whether users are being rejected:

   ```promql
   sum by (scope) (rate(edge_rate_limit_rejections_total[5m]))
   ```

4. Compare API call volume with frontend telemetry and automation changes:

   ```promql
   sum by (endpoint, status) (rate(edge_api_calls_total[5m]))
   ```

## Triage

If tracked buckets are high but rejection rate is low, look for scan traffic, health-check fanout, proxy header churn, or a bucket pruning regression in `backend/rate_limit.py` and the middleware helpers in `backend/server.py`.

If tracked buckets and rejections are both high, pause nonessential automation, reduce dashboard refresh frequency, and check recent frontend polling changes.

If the pressure started after a release, inspect changes touching `frontend/src/lib/api.ts`, dashboard polling intervals, or backend request identity handling.

If this is local development, stop duplicate browser tabs and restart the backend only after checking whether bucket count falls naturally within the configured window.

## Resolution

The incident is resolved when:

- `/api/rate-limit/status` reports `pressure` as `normal`.
- `edge_rate_limit_tracked_clients:max5m` is below `500`.
- `edge_rate_limit_rejections_total` is not increasing unexpectedly.
- Any runaway caller, scan traffic source, or pruning regression has a follow-up fix or block in place.
