# Set-Trader Monitoring with Prometheus and Grafana

This document outlines the setup and usage of a monitoring solution for the `Set-Trader` trading bot, leveraging Prometheus for metrics collection and Grafana for visualization. The solution includes a custom Python-based sidecar service that acts as a Prometheus exporter and an Opening Range Breakout (O.R.B.) analyzer.

## Architecture Overview

The monitoring system is designed as a sidecar service that integrates seamlessly with the existing `Set-Trader` backend. It comprises the following key components:

*   **Prometheus Exporter & O.R.B. Analyzer**: A Python application that connects to the `Set-Trader` MongoDB database and utilizes `yfinance` to fetch real-time price data. It exposes various trading metrics and detects O.R.B. patterns, making them available for Prometheus to scrape.
*   **Prometheus**: A robust open-source monitoring system that collects and stores time-series data from the O.R.B. Analyzer.
*   **Grafana**: An open-source platform for data visualization and analytics. It connects to Prometheus to display the collected metrics through interactive dashboards.

## Components and Functionality

### Prometheus Exporter & O.R.B. Analyzer (`analyzer` service)

This Python service performs the following functions:

*   **Data Source Integration**: Connects to the same MongoDB instance used by `Set-Trader` to retrieve critical trading data, including account balance, profit and loss (PnL), and active positions.
*   **O.R.B. Detection**: Monitors stock tickers traded by `Set-Trader` for Opening Range Breakout patterns. The detection logic is configurable for the first 5, 15, or 30 minutes of the market session. It calculates the high and low of the opening range and identifies breakouts when the current price crosses these levels.
*   **Metrics Exposure**: Exposes the following metrics via a `/metrics` endpoint for Prometheus to scrape:

    | Metric Name                       | Description                                   |
    | :-------------------------------- | :-------------------------------------------- |
    | `trading_bot_balance`             | Current account balance                       |
    | `trading_bot_total_pnl`           | Total profit and loss                         |
    | `trading_bot_active_positions`    | Number of open trading positions              |
    | `trading_bot_orb_breakout_total`  | Counter for detected O.R.B. breakouts per ticker and direction (up/down) |
    | `trading_bot_trade_count_total`   | Total number of trades executed               |
    | `trading_bot_current_price`       | Current price of tracked tickers              |
    | `trading_bot_orb_high`            | Opening Range High for a given ticker         |
    | `trading_bot_orb_low`             | Opening Range Low for a given ticker          |

### Prometheus (`prometheus` service)

*   **Configuration**: Configured to scrape metrics from the `analyzer` service at regular intervals.
*   **Storage**: Stores all collected trading and O.R.B. detection metrics as time-series data.

### Grafana (`grafana` service)

*   **Dashboards**: Provides pre-configured dashboards for visualizing key trading performance indicators and O.R.B. analysis results. These include:
    *   **Trading Overview**: Displays current account balance, total PnL, and active positions.
    *   **O.R.B. Analysis**: Visualizes real-time ticker prices against their calculated opening ranges, and tracks O.R.B. breakout events.
*   **Data Source**: Uses Prometheus as its data source.

## Setup Instructions

To integrate this monitoring solution with your existing `Set-Trader` setup, follow these steps:

1.  **Navigate to the `monitoring` directory**:

    ```bash
    cd /home/ubuntu/monitoring
    ```

2.  **Ensure `set-trader_default` network exists**: The `Set-Trader` application typically creates a Docker network named `set-trader_default`. Verify its existence or create it if necessary:

    ```bash
    docker network create set-trader_default || true
    ```

3.  **Start the monitoring services**: Use Docker Compose to bring up the `analyzer`, `prometheus`, and `grafana` services:

    ```bash
    docker-compose -f docker-compose.monitoring.yml up -d
    ```

    This command will:
    *   Build and run the `analyzer` service, which will start collecting metrics and detecting O.R.B.s.
    *   Start the Prometheus server, configured to scrape metrics from the `analyzer`.
    *   Start the Grafana server, pre-configured with Prometheus as a data source and a basic trading dashboard.

4.  **Access Grafana**: Open your web browser and navigate to `http://localhost:3001`.

    *   **Login**: Use `admin` for both username and password (you will be prompted to change it on first login).
    *   **Dashboard**: The "Set-Trader Monitoring" dashboard should be automatically provisioned and visible.

## Configuration

You can customize the `analyzer` service by setting the following environment variables in `docker-compose.monitoring.yml`:

*   `MONGO_URL`: MongoDB connection string (default: `mongodb://mongodb:27017`)
*   `DB_NAME`: MongoDB database name (default: `bracket_bot`)
*   `METRICS_PORT`: Port for the Prometheus exporter (default: `8002`)
*   `ORB_MINUTES`: Duration of the opening range in minutes (e.g., `5`, `15`, `30`; default: `15`)

## O.R.B. Detection Logic

The O.R.B. detection in the `analyzer` service works as follows:

1.  **Market Hours Check**: The analyzer first verifies if the market is open (9:30 AM to 4:00 PM ET, weekdays).
2.  **Opening Range Calculation**: During the first `ORB_MINUTES` of the market session, the highest high and lowest low are recorded for each active ticker. These define the opening range.
3.  **Breakout Detection**: After the opening range is established, the current price of each ticker is continuously monitored. A breakout is detected when the price moves above the opening range high (breakout up) or below the opening range low (breakout down). Each breakout event is recorded as a Prometheus counter metric.

## Files Provided

*   `monitoring/analyzer/main.py`: The Python script for the Prometheus exporter and O.R.B. analyzer.
*   `monitoring/analyzer/requirements.txt`: Python dependencies for the analyzer.
*   `monitoring/analyzer/Dockerfile`: Dockerfile for building the analyzer service image.
*   `monitoring/prometheus/prometheus.yml`: Prometheus configuration file.
*   `monitoring/grafana/datasources.yml`: Grafana data source provisioning file.
*   `monitoring/grafana/dashboards/trading_dashboard.json`: Grafana dashboard definition.
*   `monitoring/docker-compose.monitoring.yml`: Docker Compose file to deploy the monitoring stack.
*   `monitoring/README.md`: This documentation file.

## Next Steps

After setting up the monitoring solution, you can further enhance it by:

*   **Customizing Grafana Dashboards**: Add more panels, alerts, and visualizations to suit your specific monitoring needs.
*   **Adding More Metrics**: Extend `main.py` to expose additional metrics from `Set-Trader`'s internal state or trade events.
*   **Alerting**: Configure Prometheus Alertmanager or Grafana alerts to notify you of significant trading events or O.R.B. breakouts.
