import os

# --- Strategy thresholds ---
DISTANCE_MIN = 15       # skip if BTC within ±$15 of beat price (too risky)
DISTANCE_MAX = 125      # skip if BTC beyond ±$125 of beat price (no opportunity)
TRACKING_START_SECS = 30  # start active tracking N seconds before market close
BUY_PRICE = 0.99        # simulated limit order price
SIMULATED_SHARES = 10000  # for theoretical P&L calculation

# --- Polymarket APIs ---
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
GAMMA_MARKETS_URL = f"{GAMMA_API_BASE}/markets"
GAMMA_EVENTS_URL = f"{GAMMA_API_BASE}/events"

# RTDS WebSocket for Chainlink prices
# Docs: https://docs.polymarket.com/developers/RTDS/RTDS-overview
RTDS_WS_URL = "wss://ws-live-data.polymarket.com"

# --- Timing ---
MARKET_POLL_INTERVAL = 60       # seconds between market discovery polls
CHAINLINK_STALE_THRESHOLD = 5   # seconds — if no update for this long, mark feed unavailable
TICK_BUFFER_SECS = 90           # deque retention window (90s to give 60s of clean data with margin)
SETTLEMENT_POLL_INTERVAL = 15   # seconds between outcome checks
SETTLEMENT_POLL_TIMEOUT = 300   # max seconds to wait for resolution

# --- Logging ---
LOG_DIR = os.environ.get("LOG_DIR", "./data")
DB_PATH = os.path.join(LOG_DIR, "polybot.db")

# --- Telegram (optional) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Dashboard ---
DASHBOARD_PORT = int(os.environ.get("PORT", 8080))
