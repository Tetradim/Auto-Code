"""
Alert Handler - Receives Prometheus Alertmanager webhooks and triggers Pulse actions.

This bridges the gap between Prometheus alerts (like BearishClusterOverride) 
and the Pulse trading API.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
PULSE_URL = "http://localhost:8001"  # Pulse API base URL
DEFAULT_POWER = 1000  # Default position size for new tickers


class AlertPayload(BaseModel):
    """Alertmanager webhook payload"""
    alerts: list[Dict[str, Any]] = []


class PulseClient:
    """HTTP client for Pulse API"""
    
    def __init__(self, base_url: str = PULSE_URL):
        self.base_url = base_url
        self._session: Optional[asyncio.ClientSession] = None
    
    async def _get_session(self) -> asyncio.ClientSession:
        if self._session is None or self._session.is_closed:
            self._session = asyncio.ClientSession(
                base_url=self.base_url,
                timeout=asyncio.ClientTimeout(total=10.0)
            )
        return self._session
    
    async def post(self, path: str, json: Dict = None) -> bool:
        """POST to Pulse API"""
        try:
            session = await self._get_session()
            async with session.post(path, json=json) as resp:
                if resp.status >= 400:
                    logger.error(f"Pulse API error: {resp.status} {await resp.text()}")
                    return False
                logger.info(f"✓ Pulse API: POST {path} -> {resp.status}")
                return True
        except Exception as e:
            logger.error(f"Failed to call Pulse API: {e}")
            return False
    
    async def close(self):
        if self._session and not self._session.is_closed:
            await self._session.close()


# Global client instance
pulse_client = PulseClient()


async def handle_global_risk_reduction():
    """Trigger global risk reduction - tighten all trailing stops"""
    logger.warning("🚨 ALERT: Global risk reduction triggered")
    await pulse_client.post(
        "/control/override",
        json={"action": "tighten_trailing_global"}
    )


async def handle_bearish_cluster(symbol: str):
    """Handle bearish cluster override - stop buying, tighten stops"""
    logger.warning(f"🚨 ALERT: Bearish cluster override for {symbol}")
    await pulse_client.post(
        f"/api/tickers/{symbol}/override",
        json={
            "action": "stop_buying",
            "reason": "BearishClusterOverride alert"
        }
    )


async def handle_add_ticker(symbol: str, base_power: int = DEFAULT_POWER):
    """Add new ticker to Pulse"""
    logger.info(f"➕ ALERT: Adding ticker {symbol} to Pulse")
    await pulse_client.post(
        "/api/tickers",
        json={
            "symbol": symbol,
            "base_power": base_power
        }
    )


async def handle_remove_ticker(symbol: str):
    """Remove ticker from Pulse"""
    logger.info(f"➖ ALERT: Removing ticker {symbol} from Pulse")
    await pulse_client.post(
        f"/api/tickers/{symbol}",
        json={
            "action": "remove"
        }
    )


@router.post("/alerts")
async def handle_alertmanager_webhook(payload: AlertPayload):
    """
    Receive Prometheus Alertmanager webhook and trigger Pulse actions.
    
    Expected labels:
    - action: global_risk_reduction | add_ticker | remove_ticker | bearish_cluster
    - symbol: ticker symbol (for add/remove/cluster actions)
    
    Expected annotations:
    - summary: human-readable alert description
    - symbol: optional override for symbol
    """
    processed = 0
    
    for alert in payload.alerts:
        # Only process firing alerts
        if alert.get("status") != "firing":
            continue
        
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        
        action = labels.get("action")
        symbol = annotations.get("symbol") or labels.get("symbol")
        
        logger.info(
            f"📥 Alert webhook: {labels.get('alertname')} | "
            f"action={action} symbol={symbol}"
        )
        
        if action == "global_risk_reduction":
            await handle_global_risk_reduction()
            processed += 1
            
        elif action == "bearish_cluster":
            if symbol:
                await handle_bearish_cluster(symbol)
                processed += 1
            else:
                logger.warning("⚠️ BearishCluster alert missing symbol")
                
        elif action == "add_ticker":
            if symbol:
                base_power = int(labels.get("base_power", DEFAULT_POWER))
                await handle_add_ticker(symbol, base_power)
                processed += 1
            else:
                logger.warning("⚠️ AddTicker alert missing symbol")
                
        elif action == "remove_ticker":
            if symbol:
                await handle_remove_ticker(symbol)
                processed += 1
            else:
                logger.warning("⚠️ RemoveTicker alert missing symbol")
                
        else:
            logger.debug(f"Unknown alert action: {action}")
    
    return {"status": "processed", "count": processed}


@router.get("/health")
async def health_check():
    """Health endpoint for webhook receiver"""
    return {"status": "healthy", "service": "alert-handler"}


async def shutdown():
    """Cleanup on shutdown"""
    await pulse_client.close()