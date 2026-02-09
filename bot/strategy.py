import asyncio
import logging
from datetime import datetime, timezone

from bot.config import (
    DISTANCE_MIN,
    DISTANCE_MAX,
    TRACKING_START_SECS,
    BUY_PRICE,
    SIMULATED_SHARES,
    SETTLEMENT_POLL_INTERVAL,
    SETTLEMENT_POLL_TIMEOUT,
)
from bot.logger import log_entry
from bot.price_feed import ChainlinkPriceFeed

logger = logging.getLogger(__name__)


async def run_market(market: dict, price_feed: ChainlinkPriceFeed, fetch_outcome_fn):
    """
    Run the full strategy lifecycle for a single 15-minute market.
    Logs a single entry to SQLite after settlement outcome is known.
    """
    market_id = market["id"]
    market_slug = market.get("slug", "unknown")
    beat_price = market["beat_price"]
    end_time = market["end_time"]  # datetime (UTC)

    end_ts = end_time.timestamp()
    tracking_start_ts = end_ts - TRACKING_START_SECS

    logger.info(f"[{market_slug}] Monitoring. Beat: ${beat_price:,.2f} | Ends: {end_time.isoformat()}")

    # Phase: IDLE — wait until 30 seconds before close
    now_ts = datetime.now(timezone.utc).timestamp()
    if now_ts < tracking_start_ts:
        await asyncio.sleep(tracking_start_ts - now_ts)

    # Phase: EVALUATE — check if opportunity exists
    if not price_feed.is_available:
        _log_skip(market, beat_price, "chainlink_unavailable", 0)
        return

    price = price_feed.price
    distance = abs(price - beat_price)

    if distance > DISTANCE_MAX:
        _log_skip(market, beat_price, "distance_too_large", distance, price)
        return
    if distance < DISTANCE_MIN:
        _log_skip(market, beat_price, "distance_too_small", distance, price)
        return

    logger.info(f"[{market_slug}] ACTIVE — distance ${distance:.2f}, tracking for {TRACKING_START_SECS - 1}s")

    # Phase: ACTIVE — track price every second (wall-clock aligned)
    # 29 samples: T+14:31 through T+14:59
    prices = []
    for tick in range(29):
        target_ts = tracking_start_ts + tick + 1
        now_ts = datetime.now(timezone.utc).timestamp()
        if now_ts < target_ts:
            await asyncio.sleep(target_ts - now_ts)

        if not price_feed.is_available:
            _log_skip(market, beat_price, "chainlink_lost_during_tracking", distance)
            return

        price = price_feed.price
        distance = abs(price - beat_price)
        side = "Up" if price > beat_price else "Down"
        prices.append({
            "t": tick,
            "ts": datetime.now(timezone.utc).isoformat(),
            "price": price,
            "distance": round(distance, 2),
            "side": side,
        })

        # Safety: abort if distance drops below minimum
        if distance < DISTANCE_MIN:
            _log_skip(market, beat_price, "unstable_during_tracking", distance, price)
            return

    # Phase: DECISION — last sample before close
    final = prices[-1]
    final_side = final["side"]
    final_price = final["price"]
    final_distance = final["distance"]

    logger.info(
        f"[{market_slug}] DECISION — Would buy {final_side} at ${BUY_PRICE} | "
        f"BTC: ${final_price:,.2f} | Dist: ${final_distance:.2f}"
    )

    # Phase: WAIT FOR SETTLEMENT — poll for outcome
    actual_outcome = await _poll_outcome(market_id, fetch_outcome_fn)

    # Phase: LOG — single complete entry
    would_have_won = (actual_outcome == final_side) if actual_outcome else None
    pnl = (1.0 - BUY_PRICE) * SIMULATED_SHARES if would_have_won else (-BUY_PRICE * SIMULATED_SHARES if would_have_won is False else None)

    entry = {
        "market_id": market_id,
        "market_slug": market_slug,
        "start_time": market.get("start_time", "").isoformat() if hasattr(market.get("start_time", ""), "isoformat") else str(market.get("start_time", "")),
        "end_time": end_time.isoformat(),
        "beat_price": beat_price,
        "price_before_beat": market.get("price_before_beat"),
        "price_after_beat": market.get("price_after_beat"),
        "price_at_T14_31": prices[0]["price"] if prices else None,
        "price_at_T14_45": prices[14]["price"] if len(prices) > 14 else None,
        "price_at_T14_55": prices[24]["price"] if len(prices) > 24 else None,
        "price_at_T14_58": prices[27]["price"] if len(prices) > 27 else None,
        "price_at_T14_59": final_price,
        "distance_at_T14_31": prices[0]["distance"] if prices else None,
        "distance_at_decision": final_distance,
        "decision": "ACTIVE",
        "skip_reason": None,
        "would_buy": final_side,
        "actual_outcome": actual_outcome,
        "would_have_won": would_have_won,
        "theoretical_pnl": round(pnl, 2) if pnl is not None else None,
        "simulated_shares": SIMULATED_SHARES,
        "buy_price": BUY_PRICE,
        "price_samples": prices,
    }
    log_entry(entry)

    result_str = "WIN" if would_have_won else ("LOSS" if would_have_won is False else "UNKNOWN")
    logger.info(f"[{market_slug}] RESULT — {result_str} | Outcome: {actual_outcome} | Side: {final_side}")


async def _poll_outcome(market_id: str, fetch_outcome_fn) -> str | None:
    """Poll for market resolution. Returns 'Up', 'Down', or None if timeout."""
    elapsed = 0
    while elapsed < SETTLEMENT_POLL_TIMEOUT:
        await asyncio.sleep(SETTLEMENT_POLL_INTERVAL)
        elapsed += SETTLEMENT_POLL_INTERVAL
        try:
            outcome = await fetch_outcome_fn(market_id)
            if outcome:
                return outcome
        except Exception as e:
            logger.warning(f"Error polling outcome for {market_id}: {e}")
    logger.warning(f"Timeout waiting for outcome: {market_id}")
    return None


def _log_skip(market: dict, beat_price: float, reason: str, distance: float, current_price: float | None = None):
    """Log a SKIP entry."""
    entry = {
        "market_id": market["id"],
        "market_slug": market.get("slug", "unknown"),
        "end_time": market["end_time"].isoformat(),
        "beat_price": beat_price,
        "decision": "SKIP",
        "skip_reason": reason,
        "distance_at_decision": round(distance, 2),
        "current_price": current_price,
    }
    log_entry(entry)
    logger.info(f"[{market.get('slug', 'unknown')}] SKIP — {reason} (dist: ${distance:.2f})")
