# @0x8dxd Algo — Core Logic Observed

Based on analysis of 8 markets on February 4, 2026 (BTC "Up or Down" 15-min binary markets on Polymarket).

---

## The 6-Phase Playbook

### Phase 1 — OPEN (T+0 to T+10 seconds)

- Algo enters within **5-17 seconds** of market open
- First trade reveals directional bias
- Opens with **limit orders** (100% round prices, fractional fill sizes)
- Initial position: ~$80-560 USDC
- Observed opening directions:
  - **Bullish open**: 6 out of 8 markets
  - **Bearish open**: 2 out of 8 markets (1:15PM, 2:45PM)

### Phase 2 — HEDGE (T+10s to T+2 minutes)

- Buys the **opposite side** within 10-120 seconds of opening trade
- Hedge size: ~30-50% of opening position
- Combined price of Up + Down typically $0.93-0.97 (built-in $0.03-0.07 spread profit)
- This is **automatic** — happens every single market, no exceptions
- Purpose: cap maximum loss while waiting for price confirmation

### Phase 3 — MONITOR (T+2min to T+3min)

- Activity drops sharply — sometimes just 1-5 trades per minute
- Algo is watching BTC/ETH spot price movement
- Watching Polymarket Up/Down price movement
- This is the **decision window** — algo gathering signal

### Phase 4 — CONFIRM or FLIP (T+2min to T+5min)

The critical moment. Two paths:

**Path A — Direction Confirmed (no flip needed):**
- Opening direction is correct
- Algo sells hedge side or lets it ride
- Adds more to winning side at higher prices
- Observed in: 11:45AM, 12:00PM, 1:30PM, 2:30PM

**Path B — Direction Wrong (flip):**
- Opening direction is wrong — prices moving against
- Algo starts **selling** the losing side
- Simultaneously **buying** the winning side aggressively
- Flip typically takes 2-4 minutes of heavy trading
- Sell prices deteriorate as algo races to exit
- Observed in: 12:45PM (successful flip, +$1,336), 1:15PM (partial flip, -$576), 2:15PM (late flip, -$775)

### Phase 5 — LOTTO TICKETS (T+5min to T+12min)

- Buys cheap shares ($0.05-0.15) on the **abandoned side**
- Very low cost: $50-200 total spend
- Payout if surprise reversal: shares pay $1 each
- Risk/reward: spend $0.10 per share, win $1.00 = 10x
- Observed in every single market

### Phase 6 — HOLD TO SETTLEMENT (T+12min to T+15min)

- Minimal or no trading in final minutes
- Position is locked
- Winning side shares pay $1.00 each
- Losing side shares pay $0.00

---

## Order Execution Style

| Characteristic | Observed |
|---|---|
| Order type | 100% limit orders (maker) |
| Price precision | Round prices: $0.45, $0.50, $0.57 (never $0.4537) |
| Fill sizes | Fractional: 5.87, 63.83, 553.39 (partial fills of resting orders) |
| Recurring sizes | 5, 10, 15, 24, 100, 602 shares (standard order sizes) |
| Multi-fill transactions | Single tx fills at multiple price levels (sweeping book) |
| Speed | 2-second intervals between trade clusters |

The algo is a **directional market maker** — it provides liquidity via resting limit orders, but with deliberate inventory tilt toward its predicted direction.

---

## Timing Patterns

| Event | Typical Timing |
|---|---|
| First trade after market open | T+5 to T+17 seconds |
| Hedge starts | T+10s to T+2min |
| Monitor/quiet period | T+2min to T+3min |
| Flip decision | T+2min to T+5min |
| Lotto ticket buying | T+5min to T+12min |
| Last trade | T+12min to T+14min |

---

## Position Sizing

| Parameter | Typical Range |
|---|---|
| Total capital per market | $4,600 - $30,000 |
| Opening side allocation | 60-75% of capital |
| Hedge side allocation | 25-40% of capital |
| Lotto ticket spend | $30-200 (< 2% of capital) |
| Number of fills per market | 100-1,500 |

---

## Flip Mechanics

When the algo flips, the sell-off follows a pattern:

1. **First sell** — tests liquidity, small batch (1-3 fills)
2. **Heavy dump** — rapid selling over 30-60 seconds, prices deteriorating
3. **Simultaneous load** — while selling losing side, buying winning side
4. **Tail sells** — smaller batches cleaning up remaining position

Observed sell price deterioration during flips:
- 12:45PM: Sold Down at $0.40-0.45 (orderly)
- 1:15PM: Sold Down from $0.44 down to $0.32 (30% slippage)
- 2:15PM: Sold Up from $0.38 down to $0.16 (58% slippage — too late)

**Key insight:** Early flips (within 3 min) preserve value. Late flips (5+ min) are costly because prices have already moved significantly.

---

## When the Algo Loses

Two losing markets observed:

**1:15PM-1:30PM (Lost $576):**
- Opened bearish (rare) — heavy Down buying at $0.46
- BTC reversed upward
- Flipped but too much capital committed to Down ($22K in buys)
- Sold 35K of 53K Down shares, recovered $12,771
- Remaining 18K Down shares → $0 at settlement

**2:15PM-2:30PM (Lost ~$775):**
- Opened bullish at $0.54
- BTC dropped — Up crashed from $0.57 to $0.16
- Flip started at T+6min (too late)
- Only sold 1,768 of 14,014 Up shares — recovered $413 of $6,653
- Had to buy Down at $0.80-0.93 (near certainty, thin margin)

**Loss pattern:** The algo loses when:
1. Opening direction is wrong AND
2. It commits too much capital before confirming AND/OR
3. The flip comes too late (after prices have moved >50%)

---

## Chaotic Markets

Two markets showed much higher activity (1,400+ trades): 1:15PM and 2:45PM. Both:
- Opened bearish
- Had sells on BOTH sides (active market making / inventory rotation)
- Much more volatile price action
- The algo appeared to be providing liquidity on both sides simultaneously rather than taking a clean directional bet

This suggests the algo has **two modes**:
1. **Directional mode** (clean): open → hedge → hold/flip → done (~100-300 trades)
2. **Market making mode** (chaotic): continuous buying and selling both sides (~1,400+ trades)

The trigger for which mode may be related to market volatility or orderbook conditions at open.

---

## P&L Summary

| Market (Feb 4) | Opened | BTC Result | Flipped? | P&L |
|---|---|---|---|---|
| 11:45AM-12:00PM | Bullish | Up | No | ~+$1,100 |
| 12:00PM-12:15PM | Bullish | Up | No | ~+$900 |
| 12:45PM-1:00PM | Bullish | Down | Yes | +$1,336 |
| 1:15PM-1:30PM | Bearish | Up | Yes (failed) | -$576 |
| 1:30PM-1:45PM | Bullish | Up | No | ~+$1,600 |
| 2:15PM-2:30PM | Bullish | Down | Yes (late) | ~-$775 |
| 2:30PM-2:45PM | Bullish | Up | No | +$936 |
| 2:45PM-3:00PM | Bearish | TBD | Active | TBD |

**Running total (7 settled markets): ~+$4,521**
**Win rate: 5/7 = 71%**
**Avg win: +$1,174 | Avg loss: -$676**

---

## The Edge

The algo's profitability comes from three layers:

1. **Spread capture (guaranteed):** Buying Up + Down combined < $1.00. Even if direction is wrong, the hedge limits loss.

2. **Directional signal (the alpha):** Whatever determines the opening direction is right ~71% of the time. This is the secret sauce — could be BTC momentum, order flow, or external data.

3. **Flip mechanism (loss mitigation):** When wrong, the algo limits damage by selling the losing side and loading the winning side. Even the losing markets only lost $576-775, not the full position value.

The combination means: wins are $900-1,600, losses are $500-800. With a 71% win rate, the expected value per market is strongly positive.

---

## Open Questions

1. **What signal determines the opening direction?** This is the core alpha. Could be:
   - BTC spot price momentum in the seconds before market open
   - Polymarket orderbook imbalance at open
   - Broader market data (funding rates, liquidation levels, order flow)

2. **Why does it sometimes open bearish?** Only 2/8 markets opened bearish. Is this signal-driven or does the algo alternate?

3. **What triggers the flip timing?** Early flips (T+3min) are profitable, late flips (T+6min) are lossy. What threshold determines when to flip?

4. **Does it run the same algo on ETH?** We saw ETH trades with identical patterns but smaller size (~$2-3K vs $5-30K per market). Same logic, same wallet.

5. **Two modes — why?** The chaotic markets (1:15PM, 2:45PM) both opened bearish and had 5-10x more trades. Is high activity a sign of uncertainty in the signal?
