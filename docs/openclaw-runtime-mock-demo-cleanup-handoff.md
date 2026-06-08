# OpenClaw Handoff: Runtime Mock/Demo Data Cleanup

Date: 2026-06-07
Branch: OC-Iteration

## Removed

- Removed the frontend mock data generator module.
- Removed the top-bar mock data toggle and related Zustand state.
- Replaced Trading Overview's generated ticker/decision flow with live backend-only polling.
- Removed unused runtime dashboards that generated local data:
  - Analytics dashboard
  - Greeks dashboard
  - Short squeeze dashboard
  - Broker health dashboard
  - Paper trading dashboard
- Replaced P&L and portfolio panels with live Pulse account/position views and explicit unavailable states.
- Removed backend paper trading routes and the simulator/data feeder module.
- Removed seeded analyst portfolio positions and seeded correlation returns. These modules now start empty.
- Removed the paper trading settings group.

## Kept

- `DEMO_MODE`/standalone no-Mongo plumbing remains. It does not fabricate market data; it lets Edge run without MongoDB/Pulse while testing real code paths.
- Test-only fakes and mocks remain in test files.

## Regression Coverage

- Added `backend/tests/test_no_runtime_mock_demo_data_static.py` to guard against runtime fake data modules and stale paper/mock UI/API paths returning.

## Verification

- Red phase: `python -m unittest backend.tests.test_no_runtime_mock_demo_data_static` failed before cleanup.
- Green phase: the same command passes after cleanup.
- Python compile check passed for changed backend files.
- `npm.cmd run build` passed from `frontend`; the previous mixed import warning is gone.
