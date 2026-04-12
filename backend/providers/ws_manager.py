"""WebSocket Manager — real-time price streaming via Alpaca."""

import asyncio
import logging
import os
from typing import Dict, Callable, Optional

import aiohttp

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for live price streaming."""

    def __init__(
        self,
        price_fetcher,
        on_price_update: Callable[[str, float, float],  # symbol, price, volume
    ):
        self.price_fetcher = price_fetcher
        self.on_price_update = on_price_update
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Track which symbols have active WS subscriptions
        self.subscribed_symbols: set = set()

        # Alpaca credentials
        self._api_key = os.getenv("ALPACA_API_KEY", "")
        self._secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self._ws_url = os.getenv(
            "ALPACA_WS_URL",
            "wss://stream.data.alpaca.markets/v2/stream"
        )

        logger.info("WebSocketManager initialized")

    async def start(self):
        """Start the WebSocket connection."""
        if self._running:
            logger.warning("WebSocket already running")
            return

        if not self._api_key or not self._secret_key:
            logger.info("Alpaca credentials not configured - WebSocket disabled")
            return

        self._running = True
        self._session = aiohttp.ClientSession()
        self._task = asyncio.create_task(self._connect())
        logger.info("Alpaca WebSocket started")

    async def _connect(self):
        """Connect to Alpaca WebSocket and subscribe to symbols."""
        try:
            async with self._session.ws_connect(
                self._ws_url,
                headers={
                    "APCA-API-KEY-ID": self._api_key,
                    "APCA-API-SECRET-KEY": self._secret_key,
                },
            ) as ws:
                self._ws = ws
                await self._subscribe()
                await self._listen()
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            self._running = False

    async def _subscribe(self):
        """Subscribe to trade updates for all active tickers."""
        if not self._ws:
            return

        symbols = self.price_fetcher._cache.keys()
        if not symbols:
            # Subscribe to default tickers if none configured
            symbols = ["SPY", "QQQ"]

        for symbol in symbols:
            self.subscribed_symbols.add(symbol)

        msg = {
            "action": "subscribe",
            "trades": list(symbols),
        }
        await self._ws.send_json(msg)
        logger.info(f"Subscribed {', '.join(symbols)} via WebSocket")

    async def _listen(self):
        """Listen for incoming messages."""
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._handle_message(msg.json())
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"WebSocket error: {msg}")
                break

    async def _handle_message(self, data: dict):
        """Process incoming WebSocket message."""
        try:
            # Handle Alpaca streaming format
            # Expected: {"T": "t", "S": "SPY", "p": 500.00, "v": 1000}
            if data.get("T") == "t":
                symbol = data.get("S")
                price = data.get("p")
                volume = data.get("v", 0)

                if symbol and price:
                    # Update price in fetcher cache
                    self.price_fetcher.update_live_price(symbol, price, volume)

                    # Trigger callback
                    if self.on_price_update:
                        await self.on_price_update(symbol, price, volume)

                    logger.debug(f"📡 WS Live Update → {symbol} @ ${price:.2f}")
        except Exception as e:
            logger.debug(f"WS message parse error: {e}")

    async def stop(self):
        """Stop the WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
        if self._task:
            self._task.cancel()
        logger.info("WebSocket stopped")