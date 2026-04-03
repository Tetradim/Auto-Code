# Prometheus and Grafana Monitoring Bot Architecture

## Overview
The monitoring system will be implemented as a **sidecar service** that integrates with the existing `Set-Trader` backend. It will consist of two main components:
1.  **Prometheus Exporter & O.R.B. Analyzer**: A Python-based service that connects to the `Set-Trader` MongoDB database and price feeds to generate metrics and detect Opening Range Breakout (O.R.B.) patterns.
2.  **Monitoring Stack**: A Docker Compose setup including Prometheus for data collection and Grafana for visualization.

## Components

### 1. Prometheus Exporter & O.R.B. Analyzer (The "Bot")
-   **Data Source**: Connects to the same MongoDB instance used by `Set-Trader` to read trade history, positions, and ticker configurations.
-   **O.R.B. Detection**:
    -   Monitors the first 5, 15, or 30 minutes of the market session (configurable).
    -   Calculates the high and low of the opening range.
    -   Detects breakouts when the current price crosses these levels.
    -   Exposes these events as Prometheus metrics.
-   **Metrics Exposed**:
    -   `trading_bot_balance`: Current account balance.
    -   `trading_bot_total_pnl`: Total profit and loss.
    -   `trading_bot_active_positions`: Number of open positions.
    -   `trading_bot_orb_breakout_total`: Counter for detected O.R.B. breakouts per ticker.
    -   `trading_bot_trade_count_total`: Total number of trades executed.
-   **Implementation**: A FastAPI service (to match the existing backend style) with a `/metrics` endpoint.

### 2. Prometheus
-   **Configuration**: Scrapes the `/metrics` endpoint of the analyzer bot.
-   **Storage**: Time-series database for all trading and detection metrics.

### 3. Grafana
-   **Dashboards**:
    -   **Trading Overview**: Balance, PnL, active positions, and trade history.
    -   **O.R.B. Analysis**: Real-time breakout alerts, ticker-specific opening ranges, and breakout frequency.
-   **Data Source**: Prometheus.

## Integration Points
-   **Database**: Shared MongoDB (`mongodb://mongodb:27017`).
-   **Network**: All services will run in the same Docker network as `Set-Trader`.
-   **Environment**: Uses the same `.env` variables for database and broker access if needed.

## Deployment
-   A new `docker-compose.monitoring.yml` file will be provided to extend the existing setup.
-   A `monitoring/` directory will contain the analyzer code, Prometheus config, and Grafana dashboard definitions.
