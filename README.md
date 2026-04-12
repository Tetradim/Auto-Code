# Sentinel Edge

Sentinel Edge is an advanced trading assistant bot that integrates with the Set Trader (Sentinel Pulse) repository. It intelligently monitors and manages trading strategies for volatile stocks (SPY, QQQ, NVDA, AAPL) by leveraging real-time metrics and O.R.B. (Opening Range Breakout) detection.

## 🚀 Key Features

- **Multi-Timeframe O.R.B. Detection**: Monitors 5m, 15m, and 30m opening ranges with volume-confirmed breakouts.
- **Dynamic Risk Management**: Automatically adjusts trailing stops based on ATR (Average True Range) volatility and deactivates regular stop-losses during breakouts.
- **Autonomous Pulse Control**: Remote API integration to stop buying or exit positions fast when a bearish breakout is detected.
- **Real-time Monitoring Dashboard**: Built with `@blinkdotnew/ui` for live breakout alerts, ORB level tracking, and emergency Pulse control.
- **Robust Python Sidecar**: Improved `sentinel_edge_v2.py` with better error handling, `httpx` for Pulse API, and volume confirmation logic.

## 🛠 Setup & Integration

### 1. Configure Sentinel Pulse
Ensure your Sentinel Pulse instance (FastAPI) is reachable. You can use Cloudflare Tunnel if running locally.

### 2. Configure Blink Settings
In the **Sentinel Edge Dashboard** (Blink App), go to **Configuration** and set:
- **Sentinel Pulse API URL**: The URL of your Pulse instance.
- **Pulse API Secret**: Your Pulse API key (if configured).
- **O.R.B. Minutes**: Your preferred breakout window duration.

### 3. Deploy the Edge Bot
Use the provided `src/extracted/sentinel_edge_v2.py` in your Docker environment. It will connect to the same MongoDB as Sentinel Pulse and report metrics to Prometheus.

### 4. Monitor & Control
Access the Blink Dashboard to:
- See live ORB High/Low levels.
- Get instant breakout alerts with volume confirmation.
- Trigger an **EMERGENCY STOP** to kill all active trades in Pulse.

## 📈 Trading Edge

The bot uses **ATR-based dynamic stops** to give your trades room to breathe during high-volatility breakouts while protecting profits with a trailing exit that tightens as the breakout cools down.

---
Built with Blink — The #1 AI Fullstack Engineer.
