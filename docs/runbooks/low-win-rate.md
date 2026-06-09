# Low Win Rate

## What Fired

`LowWinRate` means one symbol's live win rate has stayed below 40% for 30 minutes:

```promql
edge_win_rate < 40
```

## Impact

A low win rate is not automatically a stop condition, because expectancy also depends on average win size, average loss size, fees, and slippage. It is still a signal-quality warning: the strategy may be out of regime, overtrading, using stale parameters, or taking entries that no longer match the tested edge.

## First Checks

Pause automation if low win rate appears alongside drawdown, consecutive-loss, or emergency-exit alerts:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/control/pause
```

Check automation state and latest handoff details:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/automation
```

Confirm live win rate by symbol:

```promql
edge_win_rate
```

Compare related risk signals:

```promql
edge_consecutive_losses
ticker_drawdown_percent
```

## Triage

1. Identify the affected symbol from the alert labels.
2. Check whether the alert is isolated to one ticker or broad across the active universe.
3. Review recent fills for slippage, spread, commissions, rejected orders, and position sizing changes.
4. Compare the live win rate with the latest backtest in `frontend/src/components/BacktestResultsChart.tsx`.
5. Review Monte Carlo results for probability of profit, drawdown distribution, and risk-of-ruin style stress.
6. Do not loosen stops or raise size based on win rate alone; review profit factor, average win/loss, and max drawdown together.
7. If low win rate coincides with consecutive losses, follow `docs/runbooks/consecutive-losses.md`.

## Resolution

The incident is resolved when:

- `edge_win_rate` recovers above the alert threshold or the strategy is deliberately disabled for that symbol.
- Recent live trades have been compared with backtest and Monte Carlo expectations.
- Profit factor, drawdown, and consecutive-loss risk have been reviewed together.
- Any parameter change is tested before automation is resumed at normal size.

## Escalation

Escalate if multiple high-volume symbols fall below threshold together, if the low win rate follows a strategy deployment, if broker fills differ from expected orders, or if the alert overlaps with drawdown or `EMERGENCY_EXIT` activity.
