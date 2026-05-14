# BalanceWheel Enhancements & Professional Strategy Recommendations

This document captures the latest architecture and strategy improvements for BalanceWheel, along with recommended enhancements for higher reliability and better NSE performance.

## 1. Current Strategy Behavior

BalanceWheel now operates as a **portfolio averaging tool**:

- It evaluates only stocks that already exist in the portfolio.
- It uses the actual current quantity and average price from Angel One holdings.
- It calculates how many shares are needed to bring the portfolio average within a target buffer above the current LTP.
- It does not create new positions for stocks that are not currently held.

This makes the bot more conservative and aligned with the original goal of balancing and averaging existing holdings.

## 2. Core Logic Update

### Average-Down Calculation
The current trade quantity is derived from:

- `current_qty` = current holdings quantity
- `portfolio_avg_price` = average buy price in the portfolio
- `ltp` = latest market price
- `target_avg` = `ltp × (1 + target_average_buffer_percent / 100)`

The bot now calculates

```python
shares_to_buy = floor((Q * A - Q * T) / (T - P))
```

where:
- `Q` = current_qty
- `A` = portfolio_avg_price
- `P` = ltp
- `T` = target_avg

This ensures the trade size is directly proportional to the existing position and the deviation from the target average.

## 3. What changed in the code

### New or updated components

- `MarketDataManager.get_portfolio_position(symbol)`
  - Returns actual quantity and average price from Angel One holdings.

- `BalanceWheelBot.run_cycle()`
  - Skips stocks without current holdings.
  - Uses the real portfolio position when analyzing buy signals.

- `BalanceWheelEngine.analyze_stock()`
  - Accepts `current_qty` as input.
  - Generates `BUY` only when actual holdings are present.

- `_calculate_smart_average()`
  - No longer uses a placeholder 100 shares.
  - Now uses real current quantity for precise averaging.

## 4. Professional enhancement recommendations

These recommendations are based on mean reversion best practices and industry-standard risk controls.

### 4.1 Tune parameters with backtesting

The fixed rules in the code are strong heuristics, but not universal.

- Test the `price_dip_threshold_percent` and `target_average_buffer_percent` with historical NSE data.
- Consider sector-specific values: IT, banking, FMCG, and utilities behave differently.

### 4.2 Add a trend filter

Mean reversion often fails in strong trending markets.

- Example filter: only execute buys when the 20-day moving average is flat or slightly rising.
- This avoids averaging into a stock that is still in a strong downtrend.

### 4.3 Add volatility normalization

A flat 15% dip is not equally meaningful across all stocks.

- Use historical volatility or a Z-score computed from price history.
- A Z-score of -1.5 to -2 is often a more robust mean-reversion signal than a raw percent drop.

### 4.4 Improve position sizing

The current buy size is based on the average target only.

- Add a second cap using portfolio exposure or cash allocation.
- Example: limit any single buy to 5-10% of total portfolio value.
- This avoids overloading a single stock during large dips.

### 4.5 Strengthen market regime controls

The `Nifty >3% down` lock is good, but more can be added.

- Use daily market breadth or volatility proxies.
- Add a second lock when multiple sectors are declining simultaneously.
- Keep buy activity limited during macro news events or earnings windows.

### 4.6 PythonAnywhere deployment tips

Because this app will run once or twice daily:

- Schedule runs during NSE trading hours (09:30–15:30 IST).
- Recommended windows: 10:30–11:30 and 13:30–14:30 IST.
- Avoid running near open or close if the market is volatile.
- Use dry-run first for at least one full week before switching live.

## 5. What to monitor

- `logs/balance_wheel.log` for buy-block reasons such as cooldown or sentiment lock.
- `data/balance_wheel.db` for actual observation records.
- `config.json` to tune thresholds and risk parameters.

## 6. Next improvement ideas

1. Add a historical price database for Z-score calculation.
2. Add RSI or Bollinger Band confirmation.
3. Add a trailing stop or profit booking module.
4. Add position rebalancing to equalize sector weights.
5. Add a “new position” mode separately from the averaging mode.

---

This document is intended to help you keep BalanceWheel conservative, portfolio-focused, and ready for PythonAnywhere deployment.