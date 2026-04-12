# Sentinel Edge

Sentinel Edge is an operator dashboard + edge API for managing Opening Range Breakout (ORB) workflows alongside a companion trading engine ("Sentinel Pulse").

This repository currently provides:

- a **React/Vite control UI** for monitoring ORB state, breakouts, and bot logs,
- a **Hono edge service** with analysis + webhook endpoints,
- **extracted Python/ops artifacts** for Docker/monitoring workflows.

## Current Project Status (Important)

Sentinel Edge is **not production-hardened yet**.

Some logic is still scaffold/demo grade (for example, placeholder price handling in `POST /analyze`).
Use this repo as a foundation that still needs:

- real market data ingestion,
- robust authn/authz,
- stricter risk controls,
- deployment hardening and end-to-end validation.

---

## Architecture at a Glance

```text
[Browser UI]
   │
   ├─ Reads/writes Blink tables (settings, orb_ranges, breakouts, bot_logs)
   │
   ▼
[Hono Edge API]  POST /analyze, POST /pulse/webhook
   │
   ├─ Reads runtime settings from Blink
   ├─ Pulls tickers from Sentinel Pulse
   ├─ Evaluates ORB ranges, writes events/logs
   └─ Optionally pushes control updates back to Pulse
```

---

## Repository Layout

```text
.
├── backend/
│   └── index.ts
├── src/
│   ├── App.tsx
│   ├── hooks/useSentinelData.ts
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Tickers.tsx
│   │   ├── Logs.tsx
│   │   └── Settings.tsx
│   └── extracted/
│       ├── sentinel_edge_v2.py
│       ├── Dockerfile
│       ├── docker-compose.monitoring.yml
│       ├── prometheus.yml
│       └── *.md ops/architecture notes
├── package.json
└── README.md
```

---

## Tech Stack

- **Frontend:** React + TypeScript + Vite + TanStack Router + Blink UI
- **Backend:** Hono + Blink SDK
- **Data/Auth layer:** Blink (`@blinkdotnew/react`, `@blinkdotnew/sdk`)
- **Ops artifacts:** Python + Docker + Prometheus/Grafana configs

---

## Prerequisites

- Node.js 20+
- npm
- Blink project credentials
- Reachable Sentinel Pulse API (for integration testing)

> `bun run lint` is configured, but Bun is optional unless you use the aggregate lint script.

---

## Configuration

### Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `VITE_BLINK_PROJECT_ID` | Yes | Blink project id used by client/backend initialization |
| `BLINK_SECRET_KEY` | Yes (backend) | Server credential used by edge API |

### Runtime settings (Blink `settings` table)

| Key | Purpose | Example |
|---|---|---|
| `pulse_api_url` | Base URL of Sentinel Pulse | `https://pulse.example.com` |
| `pulse_api_key` | Optional Pulse API key header (`X-API-KEY`) | `secret_value` |
| `orb_minutes` | Preferred ORB timeframe in UI/settings | `15` |
| `auto_control_enabled` | Enables automatic control actions (`1` / `0`) | `1` |
| `pulse_engine_status` | UI status indicator for pulse engine | `running` |

---

## Quick Start (Operator Flow)

1. Start the UI (`npm run dev`).
2. Authenticate with Blink in the app.
3. Open **Configuration** and set `pulse_api_url`, `pulse_api_key` (if required), and ORB settings.
4. Confirm Pulse connectivity/status in the dashboard.
5. Trigger/observe analysis events and verify `breakouts` + `bot_logs` updates.

---

## Local Development

Install dependencies:

```bash
npm install
```

Run frontend dev server:

```bash
npm run dev
```

Create production build:

```bash
npm run build
```

Optional lint/check flows:

```bash
npm run lint:types
npm run lint:js
npm run lint:css
bun run lint
```

---

## Edge API

### `POST /analyze`

High-level behavior:

1. Load runtime settings (`pulse_api_url`, `pulse_api_key`, `auto_control_enabled`).
2. Fetch enabled tickers from Pulse (`GET {pulse_api_url}/api/tickers`).
3. Load ORB range records (currently keyed like `${symbol}_15`).
4. Evaluate breakout logic.
5. Write `breakouts` + `bot_logs` records.
6. Optionally send control updates to Pulse (`PUT /api/tickers/{symbol}`).

### `POST /pulse/webhook`

Accepts trade event payloads from Pulse and appends readable entries to `bot_logs`.

---

## Data Surfaces Used by the UI

- `orb_ranges` (range values displayed/queried)
- `breakouts` (event feed)
- `bot_logs` (alert + audit stream)
- `settings` (integration and runtime controls)

---

## Troubleshooting

- **"Pulse API URL not configured"**: add `pulse_api_url` in the settings table/UI before calling `/analyze`.
- **No breakout rows visible**: verify `orb_ranges` has current-day records and symbol keys that match runtime expectations.
- **Pulse status looks stale**: refresh from the dashboard and ensure `pulse_engine_status` is updated by backend or control actions.
- **Build warnings about exports/chunk size**: currently non-fatal in this repo; build artifacts are still produced.

---

## Known Gaps Before Live Trading Use

- Replace placeholder/mock pricing in analysis path.
- Add authenticated user context and real JWT/API verification.
- Protect backend endpoints with stricter authorization rules.
- Add retries/timeouts/circuit-breakers for Pulse calls.
- Add deterministic test coverage for breakout and risk-control paths.
- Run paper-trading + staging drills before any capital exposure.

---

## Scripts

- `npm run dev` — start Vite dev server
- `npm run build` — build frontend artifacts
- `npm run preview` — preview build output
- `npm run lint:types` — type-check with `tsc --noEmit`
- `npm run lint:js` — ESLint
- `npm run lint:css` — Stylelint
- `npm run check:css-vars` — validate CSS variable usage
- `npm run check:css-classes` — validate CSS class references
- `npm run lint` — aggregate lint/check script (Bun)
