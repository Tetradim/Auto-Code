# Sentinel Edge - Quick Reference

## Project Overview
**Sentinel Edge** = Market data brain that analyzes patterns & signals  
**Sentinel Pulse** = Trade bot that executes buy/sell on brokerage streams  
**Integration**: Edge → Pulse (via API)

---

## Architecture

### Backend (Python FastAPI)
| File | Purpose |
|------|---------|
| `server.py` | Main FastAPI app, routes |
| `scheduler.py` | Orchestrates analysis cycle, DecisionEngine integration |
| `engine.py` | **DecisionEngine** - buy/hold/sell logic + confidence gating |
| `signals_enhanced.py` | **SignalEngineEnhanced** - pattern detection, ConfidenceScore |
| `pulse_client.py` | HTTP client to Pulse API |
| `alert_handler.py` | Webhook receiver for Alertmanager → Pulse actions |
| `price_fetcher.py` | Live OHLCV/quote fetcher and provider fallback pipeline |

### Frontend (TypeScript Vite+React)
- `frontend/` - Standard Vite+React+TypeScript app
- Runs separately on port 3000

---

## Key Integrations

### 1. Confidence Gating
```python
# scheduler.py → DecisionEngine
pattern_confidence = analysis.confidence.overall  # 0.0-1.0
decision = decisions.decide(symbol, trend, signal_strength, confidence=pattern_confidence, ...)

# engine.py - decide() logic
MIN_CONFIDENCE = 0.6
if confidence < MIN_CONFIDENCE:
    return Decision.HOLD  # Gate: reject low-quality signals
confidence_factor = 0.6 if confidence < 1.0 else 1.0
effective_signal = signal_strength * confidence_factor
```

### 2. Pattern Signals
```python
# scheduler.py - pattern detection flow
analysis = await pattern_engine.analyze(symbol, ohlcv_data, timeframe="15m")
# analysis.patterns → PatternObservation → add_observation() → apply_observation_adjustment()
```

### 3. Alert Handler
```
POST /alerts → alert_handler.py → Pulse API (POST /actions)
```
Routes Alertmanager webhooks to Pulse action endpoints.

---

## Current Branch & State
- **Branch**: `consolidated` (mainline)
- **Latest commit**: `9124da7` - "fix: Remove duplicate root frontend + extracted artifacts"
- **Status**: Clean, all artifacts removed

---

## Pending / Known Issues
- Push token occasionally fails (use `$GITHUB_TOKEN` env var)
- Pulse API URL: `http://pulse:8080` (via Docker Compose)

---

## Common Commands
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Frontend  
cd frontend
npm install
npm run dev -- --port 3000

# Docker
docker-compose up -d
docker-compose logs -f edge pulse
```
