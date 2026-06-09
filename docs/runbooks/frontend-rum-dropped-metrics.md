# Frontend RUM Dropped Metrics

## What Fired

`FrontendRumDroppedMetrics` means Edge received frontend real-user monitoring snapshots, but the backend rejected one or more metric names that are not in the frontend RUM allow list:

```promql
increase(edge_frontend_rum_dropped_metrics_total{reason="unknown_metric"}[15m]) > 0
```

This usually means the browser instrumentation started sending a new metric before the backend allow list was updated, or a malformed payload reached the ingestion endpoint.

## Impact

Frontend telemetry is partially blind. Some Core Web Vitals, long task, or interaction fields may still be recorded, but unknown metric names are not exported to Prometheus. Grafana panels can under-report browser experience problems while this alert is active.

## First Checks

1. Confirm the drop reason and recent rate:

   ```promql
   sum by (reason) (increase(edge_frontend_rum_dropped_metrics_total[15m]))
   ```

2. Confirm frontend snapshots are still arriving:

   ```promql
   sum by (route) (rate(edge_frontend_rum_samples_total[5m]))
   ```

3. Check the current backend RUM status:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/frontend/rum/status
   ```

## Triage

Compare emitted metric names in `frontend/src/lib/webVitals.ts` with the backend allow list in `backend/frontend_rum.py` and the ingestion loop in `backend/server.py`.

If a new browser metric is intentional, update the backend allow list, metric export mapping, Grafana panels, and static tests in the same change.

If the dropped metric is malformed or unexpected, inspect recent browser console output and backend request logs before widening the allow list.

If drops started after a frontend-only change, keep the existing backend allow list strict and revert or rename the frontend metric to an already supported value.

## Resolution

The incident is resolved when:

- `increase(edge_frontend_rum_dropped_metrics_total{reason="unknown_metric"}[15m])` returns no active increase.
- `/api/frontend/rum/status` shows fresh samples.
- Grafana `Dropped RUM Metrics` is flat at zero after a new browser session sends telemetry.
- Any intentional new metric has backend allow-list, Prometheus, Grafana, and static-test coverage.
