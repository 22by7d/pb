from datetime import datetime, timezone

from bot.db import upsert_market, get_recent_market_ids


def load_logged_market_ids() -> set[str]:
    """Return set of recently-logged market IDs (for restart dedupe)."""
    return get_recent_market_ids()


def log_entry(entry: dict):
    """Persist a market entry to SQLite and print a summary line."""
    upsert_market(entry)
    _print_summary(entry)


def _print_summary(entry: dict):
    """Print a one-line summary to stdout (visible in Railway logs)."""
    decision = entry.get("decision", "?")
    market_slug = entry.get("market_slug", "unknown")
    beat = entry.get("beat_price", 0)
    dist = entry.get("distance_at_decision", 0)

    if decision == "SKIP":
        reason = entry.get("skip_reason", "")
        print(f"[{_now_str()}] {market_slug} | Beat: ${beat:,.2f} | Dist: {dist:.0f} | SKIP ({reason})")
    elif decision == "ACTIVE":
        side = entry.get("would_buy", "?")
        outcome = entry.get("actual_outcome", "?")
        won = entry.get("would_have_won", None)
        result_str = "WIN" if won else ("LOSS" if won is False else "UNKNOWN")
        print(
            f"[{_now_str()}] {market_slug} | Beat: ${beat:,.2f} | Dist: {dist:.0f} | "
            f"ACTIVE | Side: {side} | Outcome: {outcome} | {result_str}"
        )
    else:
        print(f"[{_now_str()}] {market_slug} | {decision}")


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
