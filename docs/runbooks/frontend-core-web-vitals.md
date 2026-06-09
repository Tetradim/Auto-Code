# Frontend Core Web Vitals

## What Fired

One of the frontend experience alerts fired from browser real-user monitoring:

- `FrontendINPPoor`: `edge_frontend_web_vital_value{metric="inp"} > 500`
- `FrontendLCPPoor`: `edge_frontend_web_vital_value{metric="lcp"} > 4000`
- `FrontendCLSPoor`: `edge_frontend_web_vital_value{metric="cls"} > 0.25`
- `FrontendSlowInteractionP95High`: `edge_frontend_slow_interaction:p95_ms > 500`

These alerts are route-scoped. Use the alert's `route` label as the first page to inspect.

## Impact

Edge may be functionally available while the browser UI feels slow, unstable, or delayed. Poor responsiveness can make trading controls feel unreliable, especially when operators are switching dashboards during active monitoring.

## First Checks

1. Open Grafana `Frontend Experience` and inspect the affected route.
2. Check backend RUM freshness:

   ```promql
   edge_frontend_rum:freshness_seconds
   ```

3. Check current route-level values:

   ```promql
   edge_frontend_web_vital_value
   ```

4. Inspect slow interaction samples:

   ```promql
   edge_frontend_slow_interaction:p95_ms
   ```

5. Confirm the frontend dashboard can still reach the backend RUM status endpoint:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/frontend/rum/status
   ```

## Triage

If `FrontendINPPoor` or `FrontendSlowInteractionP95High` fired, start with the route's slow-interaction list in the Experience dashboard. Check recent changes to `frontend/src/lib/webVitals.ts`, heavy dashboard tables, chart rendering, and polling intervals.

If `FrontendLCPPoor` fired, check whether the route is blocked on large assets, slow backend calls, or chart bundle work before the main content appears.

If `FrontendCLSPoor` fired, look for unstable containers, images without dimensions, late-loading chart panels, or rows that resize after data arrives.

If RUM freshness is stale, use `docs/runbooks/frontend-rum-ingest-missing.md` before optimizing the UI; stale telemetry can point at old route data.

## Resolution

The incident is resolved when:

- The affected alert no longer fires for the route.
- `grafana/dashboards/frontend-experience.json` shows current RUM samples for that route.
- The Experience dashboard slow-interaction list no longer shows repeated high-duration controls.
- Any UI fix has a focused test or static guard for the component that regressed.
