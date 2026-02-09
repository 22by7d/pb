# @0x8dxd Trading Summary — February 4, 2026

Wallet: `0x63ce342161250d705dc0b16df89036c8e5f9ba9a`
Platform: Polymarket CLOB (BTC/ETH "Up or Down" 15-min binary markets)

---

## Market-by-Market Breakdown

### 1. BTC 11:45AM-12:00PM ET (22:15-22:30 IST)

- **Opened:** Bullish
- **BTC Result:** Up
- **Flipped:** No
- **Trades:** ~180
- **P&L:** ~+$1,100
- **Notes:** Clean bullish run. No flip needed. One of the simpler markets — opened Up, hedged Down, held to settlement.

---

### 2. BTC 12:00PM-12:15PM ET (22:30-22:45 IST)

- **Opened:** Bullish
- **BTC Result:** Up
- **Flipped:** No
- **Trades:** ~190
- **P&L:** ~+$900
- **Notes:** Same playbook as 11:45AM. Opened bullish, hedged, BTC cooperated. No drama.

---

### 3. BTC 12:15PM-12:30PM ET (22:45-23:00 IST)

- **Opened:** Unknown (limited data)
- **BTC Result:** Unknown
- **Flipped:** Unknown
- **Trades:** 15 (only partial data — beyond API pagination limit)
- **P&L:** Insufficient data
- **Notes:** API pagination limit hit. Only 15 trades recovered for this market. Unable to do full analysis.

---

### 4. BTC 12:45PM-1:00PM ET (23:15-23:30 IST)

- **Opened:** Bullish (BUY Up at ~$0.53 within first 9 seconds)
- **BTC Result:** Down
- **Flipped:** Yes — successful flip at 12:48:33 ET
- **Trades:** 335
- **Capital Deployed:** $11,717 total buys, $1,032 from sells
- **P&L:** +$1,336 (+11.4% ROI)
- **Timeline:**
  - 12:45:09 — Opens bullish, BUY Up @0.53
  - 12:45:25 — Hedge starts, BUY Down @0.44
  - 12:48:33 — **FLIP** — starts selling Up, loading Down
  - 12:49:55 — Lotto tickets on Up @0.05-0.10
  - 12:57:51 — Last significant trade
- **Notes:** The algo's most impressive performance. Opened wrong (bullish), detected BTC going down within 3 minutes, flipped to bearish, and still profited $1,336. The early flip timing was key — sold Up shares at decent prices before they collapsed.

---

### 5. BTC 1:15PM-1:30PM ET (23:45-00:00 IST)

- **Opened:** Bearish (first time — BUY Down at $0.46)
- **BTC Result:** Up
- **Flipped:** Yes — partial, couldn't fully recover
- **Trades:** 1,445 (chaotic market-making mode)
- **Capital:** $30,563 total buys, $15,164 from sells
- **P&L:** -$576 (per Polymarket summary)
- **Polymarket Summary:**
  - Won: 17,237 Up at 49¢ → $15,916.50 return (+$7,528)
  - Lost: 53,290 Down at 39¢ → $12,771.43 return (-$8,105)
- **Sell-off detail:** Dumped 35,179 Down shares between 13:18-13:22. Prices deteriorated from $0.44 to $0.32 during the sell-off. Couldn't sell remaining ~18,000 Down shares — went to $0 at settlement.
- **Notes:** First losing market. Opened bearish (rare), BTC reversed upward. The $12,771 return on the losing Down side came entirely from selling shares before settlement. Had committed too much capital ($22K on Down) before confirming direction.

---

### 6. BTC 1:30PM-1:45PM ET (00:00-00:15 IST)

- **Opened:** Bullish (BUY Up at ~$0.45-0.46 in first 30 seconds)
- **BTC Result:** Up
- **Flipped:** No
- **Trades:** 870 (partial — API cap)
- **Capital:** $13,944 buys, $0 sells (no Up sells at all)
- **P&L:** ~+$1,600
- **Notes:** Opened bullish, never sold a single Up share. Most confident bullish hold of all markets. Up price climbed from $0.45 to $0.87. Down collapsed from $0.54 to $0.07. Heavy Down lotto buying at $0.07-0.13 in final minutes.

---

### 7. BTC 2:15PM-2:30PM ET (00:45-01:00 IST)

- **Opened:** Bullish (BUY Up at $0.51-0.57)
- **BTC Result:** Down
- **Flipped:** Yes — late flip, too slow
- **Trades:** 200
- **Capital:** $13,944 buys, $413 from sells
- **P&L:** ~-$775
- **Timeline (IST):**
  - 00:45 — Opens bullish, BUY Up @0.54
  - 00:46 — Loading Up @0.56, first hedge Down @0.43
  - 00:47 — Massive minute, 67 trades both sides
  - 00:48-00:49 — Quiet, then buying cheap Down @0.25-0.32
  - 00:50 — Last Up buy @0.44 (price dropping)
  - 00:51 — **First SELL Up @0.38** — flip begins
  - 00:52 — BUY Down @0.93 — near certainty, expensive
  - 00:54 — Heavy Down @0.80 + Up lotto @0.08-0.13
  - 00:55 — Final Up dump @0.16-0.17
- **Notes:** Second losing market. Opened bullish, BTC went down. Flip started at T+6min — too late. Up had already crashed from $0.57 to $0.38 by the time it started selling. Only sold 1,768 of 14,014 Up shares. Had to buy Down at $0.80-0.93 with thin margin.

---

### 8. BTC 2:30PM-2:45PM ET (01:00-01:15 IST)

- **Opened:** Bullish (BUY Up at $0.57)
- **BTC Result:** Up
- **Flipped:** No
- **Trades:** 182
- **Capital:** $4,623 deployed
- **P&L:** +$936
- **Timeline (IST):**
  - 01:00 — Opens bullish @0.57
  - 01:01 — More Up @0.55
  - 01:02 — Heavy Up loading @0.42 (dip buy) + first hedge Down @0.46
  - 01:03 — 87 trades, massive minute. Up @0.66, Down already falling @0.32
  - 01:05 — Loads Up @0.81, Down lotto @0.16
  - 01:09-01:10 — Final Up buys @0.71-0.82
  - 01:11 — Down lottos @0.05-0.08. Done.
- **Notes:** Clean win. Zero sells the entire market. Got direction right from the start and never wavered. Smallest capital deployment of all markets ($4,623).

---

### 9. BTC 2:45PM-3:00PM ET (01:15-01:30 IST)

- **Opened:** Bearish (first trade BUY Down @0.51)
- **BTC Result:** TBD (leaning Up based on prices)
- **Flipped:** Active market making — sells on both sides from minute 1
- **Trades:** 2,150 (partial — API cap, actual likely much higher)
- **Capital:** $48,060 buys, $17,241 from sells, $30,820 net deployed
- **P&L scenarios:** If Up: +$9,482 / If Down: -$2,721
- **Notes:** Chaotic market-making mode (like 1:15PM). Opened bearish but quickly started buying and selling BOTH sides simultaneously. 2,150 trades in 8 minutes. Ended up leaning heavily bullish (Up net 40,302sh vs Down net 28,098sh). Biggest position of the day — $48K volume.

---

### 10. BTC 3:00PM-3:15PM ET (01:30-01:45 IST)

- **Opened:** Bullish (BUY Up at $0.47-0.51)
- **BTC Result:** In progress
- **Flipped:** Not yet (at T+4min)
- **Trades:** 201 (and counting)
- **Capital:** $6,589 deployed
- **Status at T+4min:** Up @0.67, Down @0.32. Light sells both sides. Leaning bullish.
- **P&L projection:** If Up: +$1,054 / If Down: -$1,170

---

## Aggregate Stats

| Metric | Value |
|---|---|
| Markets analyzed | 9 (7 settled, 1 pending, 1 incomplete) |
| Win rate (settled) | 5/7 = 71% |
| Total profit (7 settled) | ~+$4,521 |
| Average win | +$1,174 |
| Average loss | -$676 |
| Biggest win | +$1,600 (1:30PM) |
| Biggest loss | -$775 (2:15PM) |
| Best flip | +$1,336 (12:45PM — opened wrong, still profited) |
| Most trades in a market | 2,150+ (2:45PM) |
| Fewest trades | 182 (2:30PM) |
| Total capital deployed (all markets) | ~$150,000+ |

---

## Opening Direction Track Record

| Market | Opened | BTC Went | Correct? |
|---|---|---|---|
| 11:45AM | Bullish | Up | Yes |
| 12:00PM | Bullish | Up | Yes |
| 12:45PM | Bullish | Down | No — flipped, still profited |
| 1:15PM | Bearish | Up | No — flipped, lost |
| 1:30PM | Bullish | Up | Yes |
| 2:15PM | Bullish | Down | No — flipped late, lost |
| 2:30PM | Bullish | Up | Yes |

**Opening direction accuracy: 4/7 = 57%**
**Win rate after flips: 5/7 = 71%**

The flip mechanism adds ~14% to the win rate — turning one wrong open (12:45PM) into a profit.

---

## Two Operating Modes Observed

### Mode 1 — Directional (Clean)
- 100-350 trades per market
- Clear open → hedge → monitor → hold/flip → done
- Markets: 11:45AM, 12:00PM, 12:45PM, 1:30PM, 2:15PM, 2:30PM

### Mode 2 — Market Making (Chaotic)
- 1,400-2,150+ trades per market
- Buying AND selling both sides from early on
- Active inventory rotation throughout
- Both observed markets opened bearish
- Markets: 1:15PM, 2:45PM

---

## Key Observations

1. **First trade within 5-17 seconds** of market open, every single time
2. **Hedge within 10-120 seconds** — never skipped
3. **Early flips work, late flips don't** — 12:45PM flipped at T+3min and profited. 2:15PM flipped at T+6min and lost.
4. **Never sold a winning side** — when direction is right, zero sells on that side
5. **Lotto tickets every market** — always buys $30-200 of cheap shares on the abandoned side
6. **Runs on ETH too** — same wallet, same patterns, smaller size (~$2-3K vs $5-30K)
7. **All limit orders** — 100% round prices, fractional fill sizes, maker behavior
8. **Recurring order sizes** — 5, 10, 15, 24, 100, 602 shares appear across all markets
