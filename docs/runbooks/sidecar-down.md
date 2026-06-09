# Sidecar Down

## What Fired

`SidecarDown` means Prometheus could not scrape the Sentinel Edge target for at least 1 minute:

```promql
up{job="sentinel-edge"} == 0
```

This is an availability alert. It usually means the Edge process, container, port binding, scrape target, or local network path is unavailable.

## Impact

Prometheus cannot collect Edge metrics. Trading automation might still be running briefly, but observability is blind until scrape health returns. Do not enable or expand automation while this alert is active.

## First Checks

1. Check Prometheus scrape state:

   ```promql
   up{job="sentinel-edge"}
   ```

2. Check the dependency-free liveness endpoint:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/live
   ```

3. Check runtime readiness:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/ready
   ```

4. Check local containers and service status:

   ```powershell
   docker compose ps
   ```

5. Confirm the scrape target in `prometheus/prometheus.yml` still points at the Edge backend port.

## Triage

If `/api/live` fails, Edge is not reachable at the process or port level. Check backend logs, container health checks, and whether port `8001` is bound.

If `/api/live` works but `up{job="sentinel-edge"}` is `0`, inspect Prometheus networking, scrape configuration, Docker service names, and firewall or host networking changes.

If `/api/live` works but `/api/ready` fails, use `docs/runbooks/edge-runtime-not-ready.md`; the process is alive but a dependency is not ready.

If this started after local edits, rerun `Launch-Sentinel-Edge-Local.ps1` and confirm the launcher waits for `/api/ready` before opening the UI.

## Resolution

The incident is resolved when:

- `up{job="sentinel-edge"} == 1`.
- `/api/live` returns successfully.
- `/api/ready` returns ready, or any readiness failure has a separate active incident.
- Prometheus resumes scraping Edge metrics and downstream alerts have current data.
