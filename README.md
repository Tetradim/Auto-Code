# Sentinel Edge

Sentinel Edge is a Blink-powered control plane for monitoring Opening Range Breakout (ORB) activity and coordinating actions with a companion trading service ("Sentinel Pulse").

It includes:
- a **React + Vite dashboard** for operators,
- a **Hono edge API** for analysis/webhooks,
- and a set of **Python deployment assets** in `src/extracted/` for production-style bot execution and monitoring.

---

## What Sentinel Edge Does

- Tracks configured tickers and evaluates ORB conditions.
- Surfaces breakout activity and bot logs in a UI.
- Stores runtime state (settings, ranges, logs, breakouts) in Blink tables.
- Optionally sends control updates to Sentinel Pulse when breakout criteria are met.

> ⚠️ Current backend analysis logic in `backend/index.ts` includes placeholder/demo values (for example, mock current price handling). Treat it as a scaffold that should be connected to a real market data source before live trading use.

---

## Repository Layout

```text
.
├── backend/
│   └── index.ts                  # Hono edge API (/analyze, /pulse/webhook)
├── src/
│   ├── App.tsx                   # Router + authenticated shell
│   ├── pages/
│   │   ├── Dashboard.tsx         # Command center view
│   │   ├── Tickers.tsx           # Ticker analytics/monitoring
│   │   ├── Logs.tsx              # Alert + log stream
│   │   └── Settings.tsx          # Runtime configuration
│   ├── hooks/useSentinelData.ts  # UI data-loading hook(s)
│   └── extracted/                # Python bot and ops assets
├── package.json
└── README.md
```

---

## Tech Stack

- **Frontend:** React, TypeScript, Vite, TanStack Router, Blink UI
- **Backend (edge):** Hono + Blink SDK
- **Data/Auth:** Blink (`@blinkdotnew/react`, `@blinkdotnew/sdk`)
- **Ops assets:** Python sidecar, Prometheus/Grafana compose + configs

---

## Prerequisites

- Node.js 20+
- npm (or Bun if you prefer Bun-based scripts)
- A Blink project with valid keys
- A reachable Sentinel Pulse API (optional for local UI-only work)

---

## Environment Variables

Set the variables required by your runtime (local, deploy target, or edge host):

- `VITE_BLINK_PROJECT_ID` — Blink project identifier
- `BLINK_SECRET_KEY` — Blink server secret for backend access

If Sentinel Pulse integration is enabled, configure these values in the app settings table/UI:

- `pulse_api_url`
- `pulse_api_key` (optional)
- `auto_control_enabled`

---

## Local Development

Install dependencies:

```bash
npm install
```

Run the frontend:

```bash
npm run dev
```

Build for production:

```bash
npm run build
```

Run the full lint/check bundle (uses Bun in current scripts):

```bash
bun run lint
```

---

## Backend API Overview

### `POST /analyze`

- Reads runtime settings from Blink tables.
- Pulls ticker data from Sentinel Pulse (`/api/tickers`).
- Evaluates ORB range rows (currently 15m example key pattern: `${symbol}_15`).
- Writes breakout + bot log records.
- Optionally pushes ticker risk-control updates to Pulse.

### `POST /pulse/webhook`

- Receives trade execution notifications.
- Persists readable trade log events to `bot_logs`.

---

## Python/Ops Assets (`src/extracted/`)

The `src/extracted/` directory contains deploy-oriented assets from the Python monitoring/bot workflow, including:

- `sentinel_edge_v2.py`
- `Dockerfile`
- `docker-compose.monitoring.yml`
- `prometheus.yml`
- architecture and monitoring notes

These are useful for production packaging and observability, while the TypeScript app provides the control UI and edge endpoints.

---

## Safety Notes

This project interacts with trading infrastructure. Before any live deployment:

- validate price feed integrity,
- replace placeholder analysis logic,
- add robust auth/authorization for backend endpoints,
- implement circuit breakers and strict risk limits,
- paper-trade and stage test extensively.

---

## Scripts

- `npm run dev` — start Vite dev server
- `npm run build` — production frontend build
- `npm run preview` — preview build output
- `npm run lint:js` — ESLint
- `npm run lint:types` — TypeScript no-emit check
- `npm run lint:css` — Stylelint + autofix
- `npm run check:css-vars` — CSS variable validation
- `npm run check:css-classes` — CSS class validation
- `npm run lint` — full lint/check pipeline (via Bun)

