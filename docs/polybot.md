# PolyBot — Read-Only Monitor (Phase 1)

## Goal

A Python bot running 24/7 on Railway that monitors every 15-minute BTC "Up or Down" market on Polymarket, tracks the Chainlink BTC/USD price, and logs what trade it WOULD have taken — without placing any real orders. After 2-3 days of data, we analyze results and decide whether to go live.

---

## Strategy Rules

```
Every 15-minute market:

1. Get "price to beat" from Polymarket at market open
2. Monitor Chainlink BTC/USD price throughout
3. At T+14:30 (30 seconds before close):

   distance = abs(current_btc - beat_price)

   if distance > 125  → SKIP (clear outcome, no fills available)
   if distance < 15   → SKIP (too close, flip risk)
   if 15 ≤ distance ≤ 125 → ACTIVE

4. If ACTIVE, track price every second until T+14:59:
   → if btc > beat_price + 15  → WOULD BUY "Up" at $0.99
   → if btc < beat_price - 15  → WOULD BUY "Down" at $0.99
   → if flips below ±15 threshold at any point → SKIP (unstable)

5. Log everything. Record actual outcome at settlement.
```

---

## What We Record (Per Market)

Each 15-minute market generates one log entry:

```json
{
  "market_id": "0x...",
  "market_slug": "btc-up-or-down-feb-9-1-115am-et",
  "start_time": "2026-02-09T01:00:00Z",
  "end_time": "2026-02-09T01:15:00Z",
  "beat_price": 70979.15,

  "price_at_T14_30": 70951.22,
  "price_at_T14_45": 70948.10,
  "price_at_T14_55": 70952.80,
  "price_at_T14_58": 70950.91,
  "price_at_T14_59": 70950.44,
  "price_at_close": 70950.91,

  "distance_at_T14_30": 27.93,
  "distance_at_T14_59": 28.71,

  "decision": "ACTIVE",
  "skip_reason": null,
  "would_buy": "Down",
  "side_at_T14_59": "Down",
  "actual_outcome": "Down",
  "would_have_won": true,
  "theoretical_pnl_per_share": 0.01,

  "notes": "Stable Down signal from T+14:30 through close. No flip."
}
```

For SKIP markets, we still log the prices and reason:

```json
{
  "market_id": "...",
  "decision": "SKIP",
  "skip_reason": "distance_too_large",
  "distance_at_T14_30": 340.50,
  "beat_price": 71000.00,
  "price_at_T14_30": 70659.50
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Railway (Python)                    │
│                                                       │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────┐ │
│  │   Market     │   │  Chainlink   │   │  Decision  │ │
│  │  Discovery   │   │  Price Feed  │   │   Engine   │ │
│  │  (REST poll) │   │  (WebSocket) │   │            │ │
│  └──────┬───────┘   └──────┬───────┘   └─────┬──────┘ │
│         │                  │                  │        │
│         └──────────┬───────┘                  │        │
│                    ▼                          │        │
│            ┌──────────────┐                   │        │
│            │  Market Loop │◄──────────────────┘        │
│            │  (per 15min) │                            │
│            └──────┬───────┘                            │
│                   │                                    │
│                   ▼                                    │
│         ┌──────────────────┐    ┌──────────────────┐  │
│         │   JSON Logger    │    │  Telegram Alerts  │  │
│         │  (file per day)  │    │   (optional)      │  │
│         └──────────────────┘    └──────────────────────┘
└─────────────────────────────────────────────────────┘

External APIs:
  → Polymarket Gamma API (market discovery)
  → Polymarket RTDS WebSocket (Chainlink BTC/USD price)
  → Polymarket CLOB WebSocket (orderbook state — optional for Phase 1)
```

---

## Components

### 1. Market Discovery

**What:** Find new BTC "Up or Down" 15-min markets as they open (96 per day).

**How:** Poll Polymarket Gamma API every 60 seconds:
```
GET https://gamma-api.polymarket.com/markets
  ?tag=btc
  &closed=false
  &active=true
```

**Extract:**
- `conditionId` / `questionId` — market identifier
- `startDate` / `endDate` — 15-minute window
- `outcomes` — ["Up", "Down"]
- `outcomePrices` — current prices
- Market description → parse "price to beat" from title/description

**CRITICAL — beat_price source (must resolve before anything else):**
The "price to beat" is the Chainlink BTC/USD price at market open. Our entire win-rate analysis depends on using the EXACT same value Polymarket uses for settlement. Incorrect beat_price = corrupted data.

Resolution order:
1. Check Gamma API market object for a canonical `beat_price` or `startPrice` field
2. If not in API, check if it's embedded in the market description/title text
3. Last resort: capture Chainlink RTDS price at exact T+0 ourselves (risky — may drift from Polymarket's snapshot)

**This is the first thing to verify during implementation. Do not proceed until resolved.**

### 2. Chainlink Price Feed

**What:** Real-time BTC/USD price from the same source Polymarket uses for settlement.

**How:** Connect to Polymarket's RTDS WebSocket:
```
wss://ws-subscriptions-clob.polymarket.com/ws/
  Topic: crypto_prices_chainlink
  Symbol: btc/usd
```

**Payload:**
```json
{
  "symbol": "btc/usd",
  "timestamp": 1707440100000,
  "value": 70950.91
}
```

**Frequency:** Sub-second updates. Store latest price in memory.

**If Chainlink feed is unavailable:** Do NOT fall back to Binance or other sources. Settlement is Chainlink-based — using a different price source would corrupt our decision data. If RTDS WebSocket is down or stale (no update for >5 seconds), log all markets as `SKIP` with reason `chainlink_unavailable` until the feed recovers.

### 3. Market Loop (Core Logic)

For each active market, run this lifecycle:

```python
async def run_market(market):
    beat_price = market.beat_price
    end_time = market.end_time

    # Phase: IDLE (T+0 to T+14:30)
    # Just track price, no decisions
    await sleep_until(end_time - 30)

    # Phase: EVALUATE (T+14:30)
    price = get_latest_chainlink_price()
    distance = abs(price - beat_price)

    if distance > 125:
        log_skip(market, "distance_too_large", distance)
        return
    if distance < 15:
        log_skip(market, "distance_too_small", distance)
        return

    # Phase: ACTIVE (T+14:30 to T+14:59)
    # Track price at wall-clock aligned seconds to avoid drift
    # 29 samples: T+14:31 through T+14:59 (last sample is 1 second BEFORE close)
    prices = []
    tracking_start = end_time - 30
    for tick in range(29):
        target_time = tracking_start + tick + 1  # T+14:31, T+14:32, ... T+14:59
        await sleep_until(target_time)           # wall-clock aligned, no cumulative drift
        price = get_latest_chainlink_price()
        distance = abs(price - beat_price)
        side = "Up" if price > beat_price else "Down"
        prices.append({"t": tick, "ts": now(), "price": price, "distance": distance, "side": side})

        # Safety: if distance drops below 15 during tracking, abort
        if distance < 15:
            log_skip(market, "unstable_during_tracking", distance)
            return

    # Phase: DECISION (T+14:59 — last sample before close)
    final_price = prices[-1]["price"]
    final_side = prices[-1]["side"]
    final_distance = prices[-1]["distance"]

    # Phase: WAIT FOR SETTLEMENT
    # Poll for resolution — don't assume fixed delay
    actual_outcome = await poll_market_outcome(market.id, timeout=300, interval=15)

    # Phase: LOG — single complete write after outcome is known
    # Hold all state in memory until here. One NDJSON line with decision + outcome.
    log_market_entry(market, final_side, final_price, final_distance, prices, actual_outcome)
```

### 4. Data Logger

**Storage:** NDJSON (newline-delimited JSON) — one JSON object per line, append-only. Crash-safe, no rewrite overhead, no corruption risk from mid-write failures.

```
/data/
  2026-02-09.ndjson
  2026-02-10.ndjson
  ...
```

Each line is one complete market entry (see "What We Record" above). Append with flush after each write.

**Write model:** Hold all market state in memory during the market lifecycle (decision, prices, timestamps). Only write the NDJSON line AFTER settlement outcome is known — one complete record per market, no partial writes, no enrichment needed. If the process crashes between decision and settlement (~5 min window), that market entry is lost — acceptable for Phase 1.

**Also log:** A running summary printed to stdout (visible in Railway logs):
```
[01:15 ET] Market BTC 1:00-1:15AM | Beat: $70,979 | Close: $70,951 | Dist: 28 | ACTIVE | Would buy: Down | Outcome: Down | WIN
[01:30 ET] Market BTC 1:15-1:30AM | Beat: $70,951 | Close: $71,200 | Dist: 249 | SKIP (too far)
[01:45 ET] Market BTC 1:30-1:45AM | Beat: $71,200 | Close: $71,190 | Dist: 10 | SKIP (too close)
```

### 5. Telegram Alerts (Optional)

Send a message for every ACTIVE market:
```
POLYBOT — WOULD TRADE
Market: BTC 1:00-1:15AM ET
Beat: $70,979.15
Close: $70,950.91 (dist: $28)
Side: Down at $0.99
Outcome: Down — WIN (+$0.01/share)
```

Useful during the 2-3 day monitoring period to follow along in real time.

---

## Tech Stack

| Component | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ | Polymarket SDK ecosystem, asyncio |
| Async runtime | `asyncio` | Multiple concurrent WebSocket + REST |
| WebSocket | `websockets` | Chainlink price feed |
| HTTP | `httpx` (async) | Polymarket Gamma API polling |
| Data storage | NDJSON files on Railway volume | Append-only, crash-safe, no DB needed |
| Telegram | `python-telegram-bot` or raw HTTP | Optional alerts |
| Deployment | Railway (Hobby plan) | $1/mo, persistent process |

---

## Project Structure

```
btc-pricing/
├── docs/
│   └── polybot.md          ← this file
├── bot/
│   ├── __init__.py
│   ├── main.py             ← entry point, starts all loops
│   ├── market_discovery.py ← polls Gamma API for new markets
│   ├── price_feed.py       ← Chainlink WebSocket subscription
│   ├── strategy.py         ← decision engine (15/125 thresholds)
│   ├── logger.py           ← NDJSON file logging + stdout
│   └── config.py           ← thresholds, API URLs, settings
├── data/                   ← logged market data (gitignored)
├── requirements.txt
├── Procfile                ← Railway: `worker: python -m bot.main`
├── railway.toml            ← Railway config
└── .env.example            ← env vars template
```

---

## Railway Deployment

**Procfile:**
```
worker: python -m bot.main
```

**railway.toml:**
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "python -m bot.main"
restartPolicyType = "always"
```

**Volume:** Mount a persistent volume at `/data` for log files.

**Environment variables:**
```
TELEGRAM_BOT_TOKEN=...       # optional
TELEGRAM_CHAT_ID=...         # optional
LOG_DIR=/data                # Railway volume path
```

No wallet keys needed for Phase 1 — read-only, no orders placed.

**Restart / Idempotency:**
Railway restarts on deploys or crashes. On startup:
1. Read today's NDJSON file, build a set of already-logged `market_id`s
2. Skip any market that's already been logged (dedupe)
3. Pick up the next upcoming market from Gamma API
Worst case on restart: miss 1 market (the one in progress during crash). No data corruption with NDJSON append.

---

## API Endpoints Used (Phase 1 — Read Only)

| API | Method | Purpose | Auth needed? |
|---|---|---|---|
| Gamma API `/markets` | GET | Discover new 15-min markets | No |
| Gamma API `/markets/{id}` | GET | Get market details / outcome | No |
| RTDS WebSocket | WSS | Chainlink BTC/USD real-time price | No |

No CLOB API, no wallet, no order placement in Phase 1.

---

## Thresholds (Configurable)

```python
# config.py
DISTANCE_MIN = 15        # skip if BTC within ±$15 of beat price
DISTANCE_MAX = 125       # skip if BTC beyond ±$125 of beat price
TRACKING_START = 30       # start active tracking 30s before close
BUY_PRICE = 0.99          # simulated limit order price
SHARES = 10000            # simulated order size for P&L calc
```

---

## Success Metrics (After 2-3 Days)

After running, analyze the data for:

1. **Opportunity frequency** — How many markets per day fall in the 15-125 sweet spot?
2. **Win rate** — Of ACTIVE markets, how often does the T+14:59 side match the actual outcome?
3. **Stability** — How often does the side flip between T+14:30 and close?
4. **Theoretical P&L** — If we had placed $0.99 orders at 10,000 shares, what's the cumulative result?
5. **Edge case patterns** — Any time-of-day patterns? Volatility patterns?

**Go/No-Go for Phase 2 (live trading):**
- Win rate > 85% on ACTIVE markets → proceed
- Win rate 70-85% → adjust thresholds, run more data
- Win rate < 70% → rethink strategy

---

## Phase 2 Preview (Live Trading — Not Built Yet)

Once Phase 1 data looks good:
- Add Polymarket CLOB client (`py-clob-client`)
- Add wallet/signing (private key in Railway env)
- Replace `log_trade()` with actual `place_order()`
- Add position tracking and settlement verification
- Start with tiny size (100 shares = $99 per trade)
- Scale up based on fill rates and actual P&L

---

## Open Questions to Resolve During Phase 1

1. **Where is "price to beat" in the API?** — BLOCKING. Must resolve before deployment. Check Gamma API market object for canonical field. See Market Discovery section for resolution steps.
2. **Exact `acceptingOrders` cutoff** — When does Polymarket stop accepting orders? Log the transition.
3. **Chainlink update frequency** — How often do we get price updates? Every 100ms? 500ms? 1s?
4. **Market discovery lag** — How quickly do new markets appear in the Gamma API after opening?
5. **Side stability** — In edge cases, how many times does the leading side flip in the last 30 seconds?

## Resolved Design Decisions

- **No Binance fallback** — If Chainlink is unavailable, skip and log. Don't use alternate price sources.
- **NDJSON over JSON arrays** — Append-only, crash-safe logging.
- **Wall-clock aligned timing** — Use `sleep_until(target)` not cumulative `sleep(1)` to avoid drift.
- **Poll for settlement** — Don't assume fixed 60s delay. Poll every 15s with 5-min timeout.
- **Restart dedupe** — On startup, read today's log, skip already-processed markets.
