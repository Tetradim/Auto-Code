# OpenClaw Handoff: P1 Fixes

Date: 2026-06-07
Branch: OC-Iteration

## Fixed

- Scheduler now only updates `PositionTracker` after `_handoff_to_pulse()` returns success. This prevents local optimistic positions after blocked, disabled, or failed Pulse handoffs.
- Daily loss guard no longer returns a constant `0.0`. It reads Pulse account status when available, falls back to `DecisionEngine.account_state`, then falls back to realized daily PnL accumulated by `DecisionEngine`.
- Trade-result feedback paths now feed daily realized PnL reliably:
  - synchronous `PositionTracker` close paths call `record_trade_result_legacy()`;
  - async WebSocket/command handlers await `record_trade_result()`;
  - `DecisionEngine` stores account snapshots and exposes `get_daily_pnl_pct()`.
- Ticker config GET/PUT now works when MongoDB is disabled. Demo/no-Mongo mode stores configs in `_memory_ticker_configs`.
- Ticker config now persists and returns `price_providers`, and the scheduler passes per-ticker provider order into `PriceFetcher`.
- Removed the frontend's dead `/api/tickers/{symbol}/price-providers` client method. Provider order is saved through the existing `/api/tickers/{symbol}/config` route.
- Settings no longer posts to missing `/api/config`; it uses `/api/config/validate` when the backend is available.
- Alpaca is no longer shown in the provider modal or metadata catalog until runtime fetcher support exists.

## Regression Coverage

- Added `backend/tests/test_p1_regression_static.py` to lock the P1 contracts without importing the full FastAPI app.

## Verification

- `python -m unittest backend.tests.test_p1_regression_static`
- `python -m py_compile backend\server.py backend\scheduler.py backend\engine.py backend\position_tracker.py backend\analyst\core.py backend\price_fetcher.py backend\providers\catalog.py`
- `npm.cmd run build` from `frontend`

All three commands passed. The frontend build still reports existing Vite warnings about a mixed static/dynamic `mockData.ts` import and chunk size over 500 kB.
