import asyncio
import json
import ssl
import time
import logging

import websockets

from bot.config import RTDS_WS_URL, CHAINLINK_STALE_THRESHOLD

# SSL context for local dev (macOS cert issues)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

logger = logging.getLogger(__name__)


class ChainlinkPriceFeed:
    """Subscribes to Polymarket RTDS WebSocket for Chainlink BTC/USD prices."""

    def __init__(self):
        self._price: float | None = None
        self._timestamp: float = 0  # unix timestamp of last update
        self._connected = False
        self._ws = None

    @property
    def price(self) -> float | None:
        """Latest Chainlink BTC/USD price, or None if stale/unavailable."""
        if self._price is None:
            return None
        if time.time() - self._timestamp > CHAINLINK_STALE_THRESHOLD:
            return None  # stale
        return self._price

    @property
    def last_update_age(self) -> float:
        """Seconds since last price update."""
        if self._timestamp == 0:
            return float("inf")
        return time.time() - self._timestamp

    @property
    def is_available(self) -> bool:
        return self.price is not None

    async def run(self):
        """Connect and subscribe to Chainlink BTC/USD. Reconnects on failure."""
        while True:
            try:
                await self._connect_and_listen()
            except (websockets.ConnectionClosed, ConnectionError, OSError) as e:
                logger.warning(f"WebSocket disconnected: {e}. Reconnecting in 5s...")
                self._connected = False
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected price feed error: {e}. Reconnecting in 10s...")
                self._connected = False
                await asyncio.sleep(10)

    async def _connect_and_listen(self):
        logger.info(f"Connecting to RTDS WebSocket: {RTDS_WS_URL}")
        async with websockets.connect(RTDS_WS_URL, ssl=_ssl_ctx, ping_interval=30, ping_timeout=10) as ws:
            self._ws = ws
            self._connected = True

            # Subscribe to Chainlink BTC/USD
            # Docs: https://docs.polymarket.com/developers/RTDS/RTDS-crypto-prices
            subscribe_msg = {
                "action": "subscribe",
                "subscriptions": [
                    {
                        "topic": "crypto_prices_chainlink",
                        "type": "*",
                        "filters": "",
                    }
                ],
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to crypto_prices_chainlink")

            ping_counter = 0
            async for message in ws:
                # Skip binary or empty messages
                if isinstance(message, bytes) or not message.strip():
                    continue
                try:
                    data = json.loads(message)
                    self._handle_message(data)
                except json.JSONDecodeError:
                    pass  # Ignore non-JSON (pings, etc.)

                # Send periodic pings to keep connection alive
                ping_counter += 1
                if ping_counter % 50 == 0:
                    await ws.send(json.dumps({"action": "ping"}))

    def _handle_message(self, data: dict):
        """
        Process incoming price update.
        Documented format:
        {
            "topic": "crypto_prices_chainlink",
            "type": "update",
            "timestamp": 1753314064237,
            "payload": {"symbol": "btc/usd", "timestamp": 1753314064213, "value": 97000.50}
        }
        """
        topic = data.get("topic", "")
        msg_type = data.get("type", "")

        # Skip non-price messages
        if msg_type in ("ping", "pong", "heartbeat", "subscribed", "connected"):
            if msg_type == "subscribed":
                logger.info(f"Subscription confirmed: {data}")
            return

        # Primary: documented RTDS format with payload
        payload = data.get("payload")
        if payload and isinstance(payload, dict):
            self._extract_price(payload)
            return

        # Fallback: flat format (in case format varies)
        self._extract_price(data)

    def _extract_price(self, data: dict):
        if not isinstance(data, dict):
            return

        symbol = data.get("symbol", data.get("asset", ""))
        if "btc" not in str(symbol).lower():
            return

        value = data.get("value", data.get("price", data.get("p")))
        if value is None:
            return

        try:
            price = float(value)
        except (ValueError, TypeError):
            return

        ts = data.get("timestamp", data.get("t"))
        if ts and ts > 1_000_000_000_000:
            ts = ts / 1000  # ms to seconds

        self._price = price
        self._timestamp = ts if ts else time.time()
        logger.debug(f"BTC/USD: ${price:,.2f} (age: {self.last_update_age:.1f}s)")
