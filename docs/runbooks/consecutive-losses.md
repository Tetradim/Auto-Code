# Consecutive Losses

## What Fired

`ConsecutiveLossesWarning` means a ticker has reached 3 or more consecutive losses for at least 1 minute:

```promql
edge_consecutive_losses >= 3
```

`ConsecutiveLossesCritical` means a ticker has reached 5 or more consecutive losses:

```promql
edge_consecutive_losses >= 5
```

`HighConsecutiveLosses` is the legacy rule for the same risk family:

```promql
edge_consecutive_losses > 3
```

## Impact

A repeated loss streak can mean the current strategy is out of regime, the symbol is unusually volatile, or a recent configuration change is too aggressive. Treat critical alerts as a stop-and-review condition before allowing new entries.

## First Checks

Pause automation if the critical alert is active or if the affected ticker is still entering new positions:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/control/pause
```

Check automation state and latest handoff details:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/automation
```

Confirm the current loss streak in Prometheus:

```promql
edge_consecutive_losses
```

Compare the affected ticker against other symbols:

```promql
sort_desc(edge_consecutive_losses)
```

## Triage

1. Identify the affected symbol from the alert labels.
2. Check whether losses are isolated to one ticker or broad across correlated tickers.
3. Review recent fills, slippage, spread, and position size before changing strategy settings.
4. Inspect `max_consecutive_losses` for the affected ticker in `frontend/src/components/TickerConfigModal.tsx`.
5. Compare the configured threshold with recent backtest and Monte Carlo results before loosening it.
6. If the loss streak produced an `EMERGENCY_EXIT`, follow `docs/runbooks/auto-stop-triggered.md` as the controlling incident runbook.

## Resolution

The incident is resolved when:

- `edge_consecutive_losses` has reset or fallen below the active alert threshold.
- The affected ticker's `max_consecutive_losses` setting has been reviewed.
- Any strategy, sizing, or market-regime explanation has been recorded.
- Automation has been deliberately resumed only after broker state and open orders are understood.

## Escalation

Escalate if multiple symbols hit critical loss streaks together, if a symbol keeps re-entering immediately after exits, if Pulse delivery is degraded, or if live broker state differs from Edge's position state.
