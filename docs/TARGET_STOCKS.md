# BalanceWheel — Target Stocks Watchlist

The **`target_stocks`** list in `config.json` is a **curated watchlist**, not the list of symbols the bot scans each run.

With **`analyze_holdings_only": true`** (default), the bot:

1. Loads **every stock in your Angel One demat**
2. Applies the 15/5 trading rules to each holding
3. Uses `target_stocks` only for **extra metadata** (sector, category) when the symbol matches

Holdings **not** on the watchlist (e.g. BAJAJFINSV) are still analyzed, with sector `Portfolio`.

To revert to the old behaviour (only scan watchlist names you hold), set `"analyze_holdings_only": false` in `config.json`.

---

## Watchlist (13 symbols)

| Symbol | Sector | Category | Why it is on the list |
|--------|--------|----------|------------------------|
| **ITC** | FMCG | Dividend | Large-cap consumer staple; long history of dividends and relatively stable cash flows. Fits “quality + income” averaging during dips. |
| **TCS** | IT | Dividend | India's leading IT services name; strong balance sheet, institutional core holding, often recovers after sector-wide IT selloffs. |
| **HCLTECH** | IT | Dividend | Diversified IT player with dividend profile; similar dip-averaging logic to TCS with different volatility. |
| **POWERGRID** | Utilities | Dividend | Regulated utility / transmission; bond-like equity with yield focus—mean reversion often works in range-bound phases. |
| **COALINDIA** | Mining | Dividend | High-dividend PSU miner; cyclical but popular for income portfolios; deep dips can be averaged for long-term holders. |
| **RECLTD** | Finance | Dividend | PSU lender; government-linked, yield-oriented name often held for dividends rather than growth. |
| **PFC** | Finance | Dividend | Power finance PSU; paired mentally with RECLTD for infra/finance income exposure. |
| **ASIANPAINT** | Paints | Sector leader | Category leader with pricing power; quality consumer/industrial franchise—classic “buy the leader on correction” candidate. |
| **LT** | Infrastructure | Sector leader | EPC and infra conglomerate; bellwether for capex cycles; holders often average on macro scares. |
| **HDFCBANK** | Banking | Sector leader | Largest private bank; core portfolio stock for many Indian investors; sharp corrections invite averaging (with sector risk). |
| **TITAN** | Consumer | Sector leader | Jewellery and consumer story; high-quality retail exposure; corrections tied to consumption sentiment. |
| **BAJAJ-AUTO** | Auto | Dividend/Leader | Premium two-wheeler/export story; dividend plus leadership in auto—defensive quality within cyclical sector. |
| **RELIANCE** | Energy | Sector leader | Index heavyweight, diversified energy/retail/digital; default “India portfolio” stock for long-term accumulation on dips. |

**Priority** in config (`1` vs `2`) is reserved for future use (e.g. scan order or size bias). Today all holdings are processed equally in portfolio mode.

---

## Design philosophy (from BalanceWheel strategy)

The watchlist reflects two buckets:

1. **Dividend / “diamond” names** — ITC, TCS, HCLTECH, POWERGRID, COALINDIA, RECLTD, PFC  
   Focus: income, PSUs, defensives where averaging down on large dips is a common long-term habit.

2. **Sector leaders** — ASIANPAINT, LT, HDFCBANK, TITAN, BAJAJ-AUTO, RELIANCE  
   Focus: high-quality franchises where you may already hold or plan to hold; mean reversion on sharp drawdowns.

The bot does **not** open new positions in symbols you do not hold. The watchlist documents **intent and sector labels** for names aligned with that strategy.

---

## Your portfolio vs this list (example)

Typical demat holdings might include symbols **not** on the watchlist (e.g. **BAJAJFINSV**). Those are still processed in portfolio mode; add them to `target_stocks` only if you want a proper **sector** label for logs and future sector limits.

---

## Related config

```json
"analyze_holdings_only": true
```

See [README.md](../README.md) and [VERIFICATION.md](VERIFICATION.md).
