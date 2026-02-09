import asyncio
import logging
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from aiohttp import web

from bot.config import DASHBOARD_PORT, LOG_DIR
from bot.dashboard import create_dashboard_app
from bot.db import init_db
from bot.logger import load_logged_market_ids, log_entry
from bot.market_discovery import discover_markets, fetch_market_outcome, poll_markets_loop
from bot.price_feed import ChainlinkPriceFeed
from bot.strategy import run_market

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 60)
    logger.info("PolyBot Phase 1 — Read-Only Monitor starting")
    logger.info(f"Log directory: {LOG_DIR}")
    logger.info("=" * 60)

    # Initialize SQLite database
    init_db()
    logger.info("Database initialized")

    # Load already-processed markets for restart dedupe
    seen_ids = load_logged_market_ids()
    if seen_ids:
        logger.info(f"Loaded {len(seen_ids)} already-processed markets from today's log")

    # Start Chainlink price feed
    price_feed = ChainlinkPriceFeed()
    asyncio.create_task(price_feed.run())

    # Wait for first price
    logger.info("Waiting for Chainlink BTC/USD price feed...")
    for _ in range(30):
        if price_feed.is_available:
            break
        await asyncio.sleep(1)

    if price_feed.is_available:
        logger.info(f"Price feed connected. BTC/USD: ${price_feed.price:,.2f}")
    else:
        logger.warning("Price feed not available yet. Will retry during market monitoring.")

    # Track active market tasks
    active_tasks: dict[str, asyncio.Task] = {}

    # Start web dashboard
    dashboard_app = create_dashboard_app(price_feed, active_tasks)
    runner = web.AppRunner(dashboard_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", DASHBOARD_PORT)
    await site.start()
    logger.info(f"Dashboard running on http://0.0.0.0:{DASHBOARD_PORT}")

    async def on_new_market(market: dict):
        """Called when a new BTC 15-min market is discovered."""
        market_id = market["id"]
        slug = market["slug"]

        if market_id in active_tasks:
            return

        # Capture beat_price from Chainlink at market start
        # If the market has already started, capture current price
        now = datetime.now(timezone.utc)
        start_time = market["start_time"]

        if market["beat_price"] is None:
            if price_feed.is_available:
                if now >= start_time:
                    # Market already started — use current Chainlink price as approximate beat_price
                    # This is imprecise for markets we discover mid-session
                    market["beat_price"] = price_feed.price
                    if market["beat_price"] is None:
                        logger.warning(f"[{slug}] No Chainlink price available. Logging as SKIP.")
                        log_entry({
                            "market_id": market_id,
                            "market_slug": slug,
                            "end_time": market["end_time"].isoformat(),
                            "decision": "SKIP",
                            "skip_reason": "chainlink_unavailable_at_open",
                        })
                        return
                    logger.warning(
                        f"[{slug}] Market already started. Using current price "
                        f"${market['beat_price']:,.2f} as approximate beat_price"
                    )
                else:
                    # Capture prices at T-1s, T+0 (beat_price), T+1s
                    wait_secs = (start_time - now).total_seconds()
                    if wait_secs > 1:
                        await asyncio.sleep(wait_secs - 1)
                    market["price_before_beat"] = price_feed.price
                    await asyncio.sleep(1)
                    market["beat_price"] = price_feed.price
                    await asyncio.sleep(1)
                    market["price_after_beat"] = price_feed.price
                    if None in (market["price_before_beat"], market["beat_price"], market["price_after_beat"]):
                        logger.warning(f"[{slug}] Price feed died during beat capture. Logging as SKIP.")
                        log_entry({
                            "market_id": market_id,
                            "market_slug": slug,
                            "end_time": market["end_time"].isoformat(),
                            "decision": "SKIP",
                            "skip_reason": "chainlink_lost_during_beat_capture",
                        })
                        return
                    logger.info(
                        f"[{slug}] Beat: ${market['beat_price']:,.2f} "
                        f"(T-1: ${market['price_before_beat']:,.2f}, "
                        f"T+1: ${market['price_after_beat']:,.2f})"
                    )
            else:
                logger.warning(f"[{slug}] No Chainlink price available. Logging as SKIP.")
                log_entry({
                    "market_id": market_id,
                    "market_slug": slug,
                    "end_time": market["end_time"].isoformat(),
                    "decision": "SKIP",
                    "skip_reason": "chainlink_unavailable_at_open",
                })
                return

        # Launch market strategy as a concurrent task
        task = asyncio.create_task(
            _run_market_safe(market, price_feed)
        )
        active_tasks[market_id] = task

        def cleanup(t, mid=market_id):
            active_tasks.pop(mid, None)

        task.add_done_callback(cleanup)

    # Start market discovery loop
    logger.info("Starting market discovery loop...")
    await poll_markets_loop(seen_ids, on_new_market)


async def _run_market_safe(market: dict, price_feed: ChainlinkPriceFeed):
    """Wrapper to catch and log errors from market strategy."""
    try:
        await run_market(market, price_feed, fetch_market_outcome)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"[{market.get('slug', '?')}] Strategy error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
