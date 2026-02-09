# Polymarket Binary Outcome Trading Bot — Infrastructure Plan

## Overview

Replicate the algo observed on @0x8dxd's Polymarket activity across BTC/ETH "Up or Down" 15-minute prediction markets. The algo opens a directional position, hedges immediately, monitors price, flips if wrong, and buys lotto tickets on the abandoned side.

---

## 1. Price Feed (The Signal)

- Real-time BTC/ETH price stream via WebSocket (Binance, Coinbase, or both)
- Sub-second latency — the algo decides direction within the first few seconds of market open
- Possibly multiple feeds for cross-validation / redundancy
- Need: spot price, short-term momentum (5s/15s/30s candles), order flow if available

**Key question:** What signal determines the opening direction? Could be:
- Short-term momentum (price delta over last N seconds)
- Order flow imbalance on spot exchanges
- Polymarket orderbook imbalance itself
- External data (funding rates, liquidation levels)

---

## 2. Polymarket CLOB Integration

- Polymarket runs a Central Limit Order Book (off-chain matching, on-chain settlement)
- REST API + WebSocket for real-time orderbook and fill updates
- Docs: `docs.polymarket.com`
- Key operations:
  - Place limit orders (maker — the algo uses 100% limit orders)
  - Cancel orders
  - Monitor fills
  - Query orderbook state
- Official Python SDK: `py-clob-client`

---

## 3. Wallet / On-Chain

- Polygon wallet with USDC balance
- Orders signed with wallet private key
- Settlement is on-chain (Polygon), but order matching is off-chain
- Need USDC approval for Polymarket's CTF Exchange contract
- Capital per market: ~$20-30K USDC based on observed activity
- Total capital for running multiple markets simultaneously: $50-100K USDC

---

## 4. Strategy Engine

The core algo observed across 5+ markets:

```
PHASE 1 — OPEN (0-10 seconds after market opens)
  → Read BTC/ETH price signal
  → Place limit orders on the directional side (e.g., BUY Up at ~0.45-0.50)
  → Size: ~$500-1000 initial

PHASE 2 — HEDGE (10-30 seconds)
  → Place limit orders on the opposite side (e.g., BUY Down at ~0.50-0.55)
  → Size: ~$200-600
  → Purpose: cap downside while waiting for confirmation

PHASE 3 — MONITOR (30 seconds - 3 minutes)
  → Watch BTC/ETH spot price movement
  → Watch Polymarket price movement (Up/Down share prices)
  → Decision point: is opening direction confirmed or wrong?

PHASE 4 — CONFIRM or FLIP (2-4 minutes in)
  → If CONFIRMED: sell hedge side, add to winning side
  → If WRONG: sell opening side, load opposite side aggressively
  → This is the critical decision — costs ~$500-2000 in slippage when flipping

PHASE 5 — LOTTO TICKETS (5-12 minutes in)
  → Buy cheap shares ($0.05-0.15) on the abandoned side
  → Low cost, high payout if last-second reversal
  → Typical spend: $50-200

PHASE 6 — HOLD TO SETTLEMENT (final minutes)
  → No action, wait for market resolution
  → Shares on winning side pay $1 each
  → Shares on losing side pay $0
```

---

## 5. Order Management

- Place/cancel limit orders rapidly (observed: 300-1400 fills per 15-min market)
- All limit orders, round prices (e.g., 0.45, 0.50, not 0.4537)
- Standard order sizes observed: 5, 10, 15, 24, 100, 602 shares
- Track in real-time:
  - Net shares per side (Up / Down)
  - Average entry price per side
  - Total USDC deployed
  - Unrealized P&L based on current market prices
- Handle partial fills (fractional sizes from orderbook matching)

---

## 6. Risk Management

Based on observed behavior:

| Parameter | Observed Value |
|---|---|
| Max capital per market | ~$30K |
| Hedge ratio | ~30-50% of opening position |
| Flip threshold | ~2-3 minutes, price move confirmation |
| Max loss tolerance | ~$500-800 per market (1:15PM lost $576) |
| Win rate | 4/5 = 80% on BTC markets observed |
| Avg win | ~$1,000-1,300 |
| Avg loss | ~$576 |

**Spread capture:** When buying both sides (Up at 0.45 + Down at 0.50 = 0.95), the combined cost is < $1.00, guaranteeing a $0.05 profit per share pair regardless of outcome. The directional tilt adds profit on top.

---

## 7. Tech Stack

| Component | Tool | Notes |
|---|---|---|
| Language | Python 3.10+ (asyncio) | Fast enough for 2-second reaction times |
| Price feed | Binance WebSocket (`websockets` lib) | BTC/ETH spot, sub-second updates |
| Polymarket API | `py-clob-client` | Official SDK for CLOB operations |
| Wallet | `eth-account` + Polygon RPC | Sign orders, manage approvals |
| Hosting | AWS/GCP VM (us-east-1) | Low latency to Polymarket servers |
| State | In-memory dict | Each market only lasts 15 min, no DB needed |
| Monitoring | Telegram bot (`python-telegram-bot`) | Real-time alerts on fills, flips, P&L |
| Logging | File-based per market | Post-session analysis |

---

## 8. Market Discovery

- Polymarket lists new 15-min markets every 15 minutes
- Need to auto-discover new BTC/ETH "Up or Down" markets as they appear
- Query Polymarket API for active markets matching pattern
- Extract conditionId and token IDs for each new market
- Start strategy engine automatically when market opens

---

## 9. Observed P&L Across Markets

| Market | Direction Opened | BTC Result | Algo P&L | Flipped? |
|---|---|---|---|---|
| 11:45AM-12:00PM | Bullish | Up | ~+$1,100 | No |
| 12:00PM-12:15PM | Bullish | Up | ~+$900 | No |
| 12:15PM-12:30PM | — | — | (limited data) | — |
| 12:45PM-1:00PM | Bullish | Down | +$1,336 | Yes |
| 1:15PM-1:30PM | Bearish | Up | -$576 | Yes (partial) |
| 1:30PM-1:45PM | Bullish | Up | ~+$1,600 | No |

**Net across 5 markets: ~+$4,360**

---

## 10. Development Phases

### Phase 1 — Data & Simulation
- Build price feed ingestion (Binance WS)
- Build Polymarket market discovery
- Paper trade: run the strategy logic against live data without placing real orders
- Backtest against historical 15-min BTC candles + Polymarket orderbook snapshots

### Phase 2 — Execution
- Integrate `py-clob-client` for live order placement
- Implement order management (place, cancel, track fills)
- Start with small size ($500 per market) to validate

### Phase 3 — Tuning
- Optimize opening direction signal
- Tune hedge ratio, flip timing, position sizing
- Run across both BTC and ETH markets simultaneously

### Phase 4 — Scale
- Increase capital per market
- Add more assets if Polymarket lists them (SOL, etc.)
- Add monitoring dashboard
