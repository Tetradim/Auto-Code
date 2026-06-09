# Drawdown Risk

## What Fired

`DrawdownWarning` means one ticker's current drawdown exceeded 5% for at least 2 minutes:

```promql
ticker_drawdown_percent > 5
```

`DrawdownCritical` means one ticker's current drawdown exceeded 10% for at least 1 minute:

```promql
ticker_drawdown_percent > 10
```

## Impact

The affected ticker is moving far enough below its recent peak that normal signal logic may no longer be the right decision boundary. Treat critical drawdown as a capital-preservation incident before considering new entries or looser stops.

## First Checks

1. Identify the affected symbol from the alert labels.
2. Check current ticker drawdown:

   ```promql
   ticker_drawdown_percent
   ```

3. Check automation mode and latest handoff outcome:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/automation
   ```

4. Check current stats and position state in the UI Protection dashboard.

## Triage

Pause automation before changing ticker risk settings if `DrawdownCritical` is active.

Review the ticker's configured `max_drawdown_pct` in `frontend/src/components/TickerConfigModal.tsx` and compare it with the current strategy/backtest assumptions. A threshold that is too loose can delay exits; a threshold that is too tight can repeatedly exit normal volatility.

If the drawdown is isolated to one ticker, inspect recent position updates, liquidity, spread, and news before applying global risk reductions.

If multiple tickers are in drawdown together, check market regime and correlation alerts before re-enabling automation.

If a recent strategy change caused the drawdown, compare the ticker's Monte Carlo and backtest drawdown distribution before keeping the change.

## Resolution

The incident is resolved when:

- `ticker_drawdown_percent` returns below the relevant warning or critical threshold.
- The affected ticker's risk configuration has been reviewed.
- Any required exit, stop tightening, or automation pause has been deliberately handled.
- Automation has been deliberately re-enabled, if it was paused during triage.
