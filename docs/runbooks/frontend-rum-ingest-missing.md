# Frontend RUM Ingest Missing

## What Fired

`FrontendRumIngestMissing` means Edge has stopped receiving browser real-user monitoring snapshots, or the latest received snapshot is older than the freshness threshold:

```promql
absent_over_time(edge_frontend_rum_samples_total[30m]) or edge_frontend_rum:freshness_seconds > 1800
```

This alert does not mean the trading backend is down. It means the frontend experience telemetry is blind, so Core Web Vitals, slow interaction, and browser error visibility may be stale.

## Impact

Operators can still use Edge, but Grafana frontend panels and frontend experience alerts may no longer represent current user experience. Do not assume the UI is healthy until RUM ingestion resumes.

## First Checks

1. Open Edge in a browser and confirm the app loads without console errors.
2. Confirm the backend can accept RUM snapshots:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/frontend/rum/status
   ```

3. Inspect the freshness metric:

   ```promql
   edge_frontend_rum:freshness_seconds
   ```

4. Confirm samples are arriving:

   ```promql
   sum by (route) (rate(edge_frontend_rum_samples_total[5m]))
   ```

5. Check whether the backend is dropping samples:

   ```promql
   increase(edge_frontend_rum_dropped_metrics_total[15m])
   ```

## Triage

If `/api/frontend/rum/status` is unavailable, check backend logs and `/api/ready` before debugging the browser instrumentation.

If `edge_frontend_rum_dropped_metrics_total` is increasing, compare the frontend metric names in `frontend/src/lib/webVitals.ts` with the backend allow list in `backend/frontend_rum.py`.

If samples arrive for one route but not another, open the affected route directly and check for a JavaScript error before `initWebVitals` sends the beacon.

If no browser sends samples, verify the frontend build includes the RUM bootstrap and that the app can reach the configured backend origin.

## Resolution

The incident is resolved when:

- `/api/frontend/rum/status` returns successfully.
- `edge_frontend_rum:freshness_seconds` is below `1800`.
- `sum(rate(edge_frontend_rum_samples_total[5m]))` is greater than `0`.
- `edge_frontend_rum_dropped_metrics_total` is not increasing unexpectedly.
