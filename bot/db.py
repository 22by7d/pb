import json
import os
import sqlite3

from bot.config import DB_PATH, LOG_DIR

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS markets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT UNIQUE,
    market_slug TEXT,
    start_time TEXT,
    end_time TEXT,
    beat_price REAL,
    price_before_beat REAL,
    price_after_beat REAL,
    decision TEXT,
    skip_reason TEXT,
    price_at_T14_31 REAL,
    price_at_T14_45 REAL,
    price_at_T14_55 REAL,
    price_at_T14_58 REAL,
    price_at_T14_59 REAL,
    current_price REAL,
    distance_at_T14_31 REAL,
    distance_at_decision REAL,
    would_buy TEXT,
    actual_outcome TEXT,
    would_have_won INTEGER,
    theoretical_pnl REAL,
    simulated_shares INTEGER,
    buy_price REAL,
    price_samples TEXT,
    logged_at TEXT DEFAULT (datetime('now'))
)
"""

_UPSERT = """
INSERT INTO markets (
    market_id, market_slug, start_time, end_time, beat_price,
    price_before_beat, price_after_beat,
    decision, skip_reason,
    price_at_T14_31, price_at_T14_45, price_at_T14_55, price_at_T14_58, price_at_T14_59,
    current_price, distance_at_T14_31, distance_at_decision,
    would_buy, actual_outcome, would_have_won, theoretical_pnl,
    simulated_shares, buy_price, price_samples
) VALUES (
    :market_id, :market_slug, :start_time, :end_time, :beat_price,
    :price_before_beat, :price_after_beat,
    :decision, :skip_reason,
    :price_at_T14_31, :price_at_T14_45, :price_at_T14_55, :price_at_T14_58, :price_at_T14_59,
    :current_price, :distance_at_T14_31, :distance_at_decision,
    :would_buy, :actual_outcome, :would_have_won, :theoretical_pnl,
    :simulated_shares, :buy_price, :price_samples
)
ON CONFLICT(market_id) DO UPDATE SET
    market_slug      = COALESCE(excluded.market_slug, markets.market_slug),
    start_time       = COALESCE(excluded.start_time, markets.start_time),
    end_time         = COALESCE(excluded.end_time, markets.end_time),
    beat_price       = COALESCE(excluded.beat_price, markets.beat_price),
    price_before_beat = COALESCE(excluded.price_before_beat, markets.price_before_beat),
    price_after_beat  = COALESCE(excluded.price_after_beat, markets.price_after_beat),
    decision         = COALESCE(excluded.decision, markets.decision),
    skip_reason      = COALESCE(excluded.skip_reason, markets.skip_reason),
    price_at_T14_31  = COALESCE(excluded.price_at_T14_31, markets.price_at_T14_31),
    price_at_T14_45  = COALESCE(excluded.price_at_T14_45, markets.price_at_T14_45),
    price_at_T14_55  = COALESCE(excluded.price_at_T14_55, markets.price_at_T14_55),
    price_at_T14_58  = COALESCE(excluded.price_at_T14_58, markets.price_at_T14_58),
    price_at_T14_59  = COALESCE(excluded.price_at_T14_59, markets.price_at_T14_59),
    current_price    = COALESCE(excluded.current_price, markets.current_price),
    distance_at_T14_31  = COALESCE(excluded.distance_at_T14_31, markets.distance_at_T14_31),
    distance_at_decision = COALESCE(excluded.distance_at_decision, markets.distance_at_decision),
    would_buy        = COALESCE(excluded.would_buy, markets.would_buy),
    actual_outcome   = COALESCE(excluded.actual_outcome, markets.actual_outcome),
    would_have_won   = COALESCE(excluded.would_have_won, markets.would_have_won),
    theoretical_pnl  = COALESCE(excluded.theoretical_pnl, markets.theoretical_pnl),
    simulated_shares = COALESCE(excluded.simulated_shares, markets.simulated_shares),
    buy_price        = COALESCE(excluded.buy_price, markets.buy_price),
    price_samples    = COALESCE(excluded.price_samples, markets.price_samples)
"""

# Column names expected in the upsert (order must match _UPSERT placeholders)
_COLUMNS = [
    "market_id", "market_slug", "start_time", "end_time", "beat_price",
    "price_before_beat", "price_after_beat",
    "decision", "skip_reason",
    "price_at_T14_31", "price_at_T14_45", "price_at_T14_55", "price_at_T14_58", "price_at_T14_59",
    "current_price", "distance_at_T14_31", "distance_at_decision",
    "would_buy", "actual_outcome", "would_have_won", "theoretical_pnl",
    "simulated_shares", "buy_price", "price_samples",
]


def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the markets table (if needed) and enable WAL mode."""
    os.makedirs(LOG_DIR, exist_ok=True)
    conn = _get_conn()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(_CREATE_TABLE)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_markets_logged_at ON markets(logged_at)")
        conn.commit()
    finally:
        conn.close()


def upsert_market(entry: dict):
    """Insert or update a market row."""
    # Serialize price_samples list to JSON string
    params = {}
    for col in _COLUMNS:
        val = entry.get(col)
        if col == "price_samples" and val is not None and not isinstance(val, str):
            val = json.dumps(val, default=str)
        # Convert booleans to int for would_have_won
        if col == "would_have_won" and isinstance(val, bool):
            val = int(val)
        params[col] = val

    conn = _get_conn()
    try:
        conn.execute(_UPSERT, params)
        conn.commit()
    finally:
        conn.close()


def get_recent_market_ids() -> set[str]:
    """Return market_ids logged in the last 24 hours (for restart dedupe)."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT market_id FROM markets WHERE logged_at > datetime('now', '-1 day')"
        ).fetchall()
        return {row[0] for row in rows}
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return set()
    finally:
        conn.close()
