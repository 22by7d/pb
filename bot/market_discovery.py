import asyncio
import json
import logging
import ssl
from datetime import datetime, timezone, timedelta

import httpx

from bot.config import GAMMA_API_BASE, MARKET_POLL_INTERVAL

logger = logging.getLogger(__name__)

# Disable SSL verification for local dev (macOS cert issues)
# Railway's environment has proper certs
SSL_VERIFY = False


def _next_market_times(now: datetime | None = None) -> list[tuple[datetime, datetime, str]]:
    """
    Calculate the next few expected 15-min market windows.
    Returns list of (start_time, end_time, slug) tuples.
    Markets run every 15 minutes aligned to :00, :15, :30, :45.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Round down to current 15-min boundary
    minute = now.minute
    boundary_minute = (minute // 15) * 15
    current_boundary = now.replace(minute=boundary_minute, second=0, microsecond=0)

    results = []
    for offset in range(4):  # Current + next 3 markets
        start = current_boundary + timedelta(minutes=15 * offset)
        end = start + timedelta(minutes=15)
        unix_ts = int(start.timestamp())
        slug = f"btc-updown-15m-{unix_ts}"
        results.append((start, end, slug))

    return results


async def discover_markets(seen_ids: set[str]) -> list[dict]:
    """
    Discover active BTC 15-min markets by predicting slugs and checking Gamma API.
    """
    candidates = _next_market_times()
    new_markets = []

    async with httpx.AsyncClient(timeout=10, verify=SSL_VERIFY) as client:
        for start_time, end_time, slug in candidates:
            if slug in seen_ids:
                continue

            try:
                resp = await client.get(
                    f"{GAMMA_API_BASE}/events",
                    params={"slug": slug},
                )
                resp.raise_for_status()
                events = resp.json()

                if not events:
                    continue

                event = events[0]
                markets = event.get("markets", [])
                if not markets:
                    continue

                market = markets[0]
                market_id = market.get("id")
                if not market_id or market_id in seen_ids:
                    continue

                # Validate outcomes
                outcomes = market.get("outcomes", "")
                if '"Up"' not in outcomes or '"Down"' not in outcomes:
                    continue

                # Parse actual times from API
                event_start = _parse_dt(market.get("eventStartTime"))
                end_date = _parse_dt(market.get("endDate"))

                normalized = {
                    "id": market_id,
                    "condition_id": market.get("conditionId", ""),
                    "slug": slug,
                    "title": market.get("question", event.get("title", "")),
                    "start_time": event_start or start_time,
                    "end_time": end_date or end_time,
                    "beat_price": None,  # Captured from Chainlink at event start
                    "outcomes": outcomes,
                    "clob_token_ids": market.get("clobTokenIds", ""),
                    "accepting_orders": market.get("acceptingOrders", False),
                    "closed": market.get("closed", False),
                }
                new_markets.append(normalized)
                seen_ids.add(market_id)
                seen_ids.add(slug)  # Also track by slug to avoid re-fetching
                logger.info(
                    f"Discovered: {slug} | "
                    f"{(event_start or start_time).strftime('%H:%M')}-"
                    f"{(end_date or end_time).strftime('%H:%M')} UTC | "
                    f"accepting={market.get('acceptingOrders')}"
                )

            except httpx.HTTPStatusError as e:
                logger.debug(f"No market at {slug}: {e.response.status_code}")
            except Exception as e:
                logger.warning(f"Error checking {slug}: {e}")

    return new_markets


async def fetch_market_outcome(market_id: str) -> str | None:
    """
    Check if a market has resolved. Returns 'Up', 'Down', or None if not yet resolved.
    """
    try:
        async with httpx.AsyncClient(timeout=10, verify=SSL_VERIFY) as client:
            resp = await client.get(f"{GAMMA_API_BASE}/markets/{market_id}")
            resp.raise_for_status()
            market = resp.json()

            if not market.get("closed", False):
                return None

            # Check outcome prices — winning side price goes to ~1.0
            prices_str = market.get("outcomePrices", "[]")
            try:
                prices = json.loads(prices_str)
                if len(prices) >= 2:
                    up_price = float(prices[0])
                    down_price = float(prices[1])
                    if up_price > 0.9:
                        return "Up"
                    elif down_price > 0.9:
                        return "Down"
            except (ValueError, IndexError):
                pass

            return None
    except Exception as e:
        logger.warning(f"Error fetching outcome for market {market_id}: {e}")
        return None


async def poll_markets_loop(seen_ids: set[str], on_new_market):
    """Continuously poll for new markets and call on_new_market for each."""
    while True:
        new_markets = await discover_markets(seen_ids)
        for market in new_markets:
            asyncio.create_task(on_new_market(market))
        await asyncio.sleep(MARKET_POLL_INTERVAL)


def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        s = str(val).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
