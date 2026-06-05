# BalanceWheel: Mean-Reversion & Smart Averaging Trading Bot

**Version:** 1.0.9  
**Platform:** Angel One (SmartAPI) — requires `smartapi-python` >= 1.5.5 (TOTP)  
**Status:** Production ready (default: **live trading**; dry-run opt-in via `DRY_RUN=true`)

---

## Table of Contents

1. [Overview](#overview)
2. [Strategy Explanation](#strategy-explanation)
3. [Latest Enhancement Notes](#latest-enhancement-notes)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [Safety & Risk Management](#safety--risk-management)
8. [Log Interpretation](#log-interpretation)
9. [Centralized Logging & Analysis](#centralized-logging--analysis)
10. [Troubleshooting](#troubleshooting)
11. [Architecture](#architecture)

---

## Overview

**BalanceWheel** is an intelligent, automated mean-reversion trading bot designed for Angel One's SmartAPI platform. It targets "Diamond" dividend and sector-leading stocks, leveraging the principle of **smart cost-averaging** to lower your portfolio's average purchase price during market dips.

### Key Features

✅ **Automated Precision Buying** – Calculates exact shares needed to hit target average price  
✅ **15/5 Rule Engine** – Data-driven entry signals with multiple alert levels  
✅ **Configurable Cool-Down** – Optional per-symbol buy spacing (`cooldown_days`; default 0)  
✅ **Sector Diversification** – Max 1 buy per sector per 24 hours  
✅ **Market Sentiment Lock** – Pauses all buying if Nifty 50 drops >3%  
✅ **DRY-RUN Mode** – Test strategies before live execution  
✅ **Persistent Logging** – 10-day rotating logs with SQLite database  
✅ **Centralized Log Analysis** – Automatic GitHub log pushing for multi-environment tracking  
✅ **DevSecOps Ready** – Error handling, graceful shutdown, secure credential management  
✅ **Buy-Only Strategy** – No selling or position liquidation; focuses on accumulation during dips  

---

## Strategy Explanation

### The "BalanceWheel" Philosophy

The bot implements a **mean-reversion strategy** based on the principle that quality stocks temporarily dip below their long-term value. Instead of panic-selling during downturns, BalanceWheel **systematically accumulates** during dips, lowering your average cost basis.

**Important:** BalanceWheel is a **buy-only bot**. It never sells or liquidates positions. The strategy focuses exclusively on cost-averaging existing holdings during market dips, building long-term wealth through disciplined accumulation.

### The 15/5 Rule

The core decision logic:

| Scenario | Condition | Action | Rationale |
|----------|-----------|--------|-----------|
| **Strong Dip** | LTP ≤ 15% below Avg | **BUY** | Strong mean-reversion opportunity |
| **Medium Dip** | 12% < LTP < 15% | **HIGH_ALERT** | Monitor closely, potential entry tomorrow |
| **Normal Range** | LTP > Avg or < 12% below | **STATUS_CHECKED** | Routine monitoring, no action |

**Mathematical Formula:**

When a buy signal triggers:
```
Target Avg Price = LTP × (1 + 5%)
Required Shares = (Q × Avg_Price - Q × Target) / (Target - LTP)

Where:
  Q = Current Quantity
  Avg_Price = Portfolio Average
  LTP = Current Market Price
```

**Example:**
```
Current Holdings: 100 shares @ ₹500 avg
Current Price (LTP): ₹400 (20% dip)
Target New Avg: ₹420 (LTP + 5%)

Shares to Buy = (100 × 500 - 100 × 420) / (420 - 400)
              = (50,000 - 42,000) / 20
              = 8,000 / 20
              = 400 shares

New Portfolio:
  Total: 500 shares
  New Average: (100 × 500 + 400 × 400) / 500 = ₹420
```

### Latest Update: Portfolio-first mode
With **`analyze_holdings_only": true`** (default in `config.json`), each run analyzes **every stock in your demat**. The **`target_stocks`** watchlist is kept for sector labels and strategy reference—not as the scan list.

- Buy signals use your real quantity and average price from Angel One.
- Holdings **not** on the watchlist (e.g. BAJAJFINSV) are still analyzed.
- Watchlist rationale: [docs/TARGET_STOCKS.md](docs/TARGET_STOCKS.md).

For a longer discussion of strategy tuning and professional improvement ideas, see [ENHANCEMENTS.md](ENHANCEMENTS.md).

### Why this matters
- Angel One holdings and portfolio average are the source of truth for cost-basis decisions.
- Buying only when the stock is already in your portfolio reduces exposure to new, untested positions.
- It prevents the bot from acting like a generic signal scanner and instead keeps it aligned with your long-term portfolio structure.

### Professional enhancement suggestions
Based on mean reversion principles and common market practice, the current 15% dip / 5% target buffer should be treated as a strong starting point, not a fixed rule.

1. **Backtest before locking values**
   - Use historical NSE price data to test the 15% / 5% thresholds on your selected stocks.
   - Different sectors and market regimes may need different thresholds.

2. **Prefer range-bound large caps**
   - Mean reversion works best in stocks that are not in a strong trending move.
   - For NSE large caps, lower dip thresholds (10-18%) and smaller buffers (3-7%) are often more effective than extreme values.

3. **Add a trend filter**
   - Avoid buying during strong downtrends by checking a simple moving average or slope.
   - Example: only execute buys when the 20-day moving average is flat or gently rising.

4. **Use volatility or Z-score instead of raw percent alone**
   - A 15% dip in one stock may be much more or less significant than 15% in another.
   - Use historical standard deviation / Z-score to normalize dips.

5. **Market condition limits**
   - The current Nifty stop-loss threshold (>3% down) is good.
   - Consider adding a broader market breadth filter or a second indicator like VIX-equivalent sentiment.

6. **Position sizing relative to portfolio value**
   - Today the buy size is calculated to achieve a target average.
   - You can further cap buy size at a percentage of total portfolio or cash, especially on PythonAnywhere when running once or twice daily.

7. **PythonAnywhere scheduling**
   - Run the bot once or twice during market hours, not outside trading windows.
   - Recommended times: 10:30–11:30 and 13:30–14:30 IST on NSE trading days.
   - Use PythonAnywhere scheduled tasks, not a constant loop.

---

## Installation

### Prerequisites

- **Python 3.9+**
- **Angel One Account** with SmartAPI enabled
- **API Key & Credentials** from Angel One dashboard
- **Host:** PythonAnywhere, GCP Ubuntu VM, Docker, or local machine

### Step 1: Clone/Setup Project

```bash
# Create project directory
mkdir ~/BalanceWheel
cd ~/BalanceWheel

# Download project files (or clone from git)
# Copy all files to this directory
```

### Step 2: Create Virtual Environment

```bash
# On Linux/macOS
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Production (PythonAnywhere, GCP, live VPS)
pip install -r requirements-runtime.txt

# Full dev environment
pip install -r requirements.txt

pip show smartapi-python   # must be 1.5.5 or higher for TOTP login
```

**GCP Ubuntu:** See [docs/GCP_VM_BOOTSTRAP.md](docs/GCP_VM_BOOTSTRAP.md) and [DEPLOYMENT.md](DEPLOYMENT.md#gcp-ubuntu--linux-vps).

### Step 4: PythonAnywhere Specific Setup

If deploying on PythonAnywhere:

```bash
# 1. Upload project files to PythonAnywhere file system
# 2. Create web app with custom Python path:
#    /home/yourusername/BalanceWheel/venv/bin/python
#
# 3. Set up scheduled task (PythonAnywhere -> Tasks):
Task: python ~/BalanceWheel/balance_wheel.py
Schedule: Every 15 minutes (market hours)
```

---

## Configuration

### `config.json` – Main Configuration File

```json
{
  "version": "1.0.9",
  "dry_run": false,
  "analyze_holdings_only": true,
  "startup_show_account": true,
  "order_settings": {
    "variety": "NORMAL",
    "ordertype": "LIMIT",
    "producttype": "DELIVERY",
    "duration": "DAY",
    "exchange": "NSE"
  },
  "trading_rules": {
    "price_dip_threshold_percent": 15,
    "target_average_buffer_percent": 5,
    "minimum_balance_required_inr": 2000,
    "cooldown_days": 0,
    "market_sentiment_nifty_down_percent": 3,
    "safety_buffer_subtract_shares": 1
  }
}
```

Watchlist symbols live in `target_stocks` (13 names) — see [docs/TARGET_STOCKS.md](docs/TARGET_STOCKS.md). Credentials belong in `.env`, not `config.json`.

### Setting Up Credentials Securely

**Option 1: Environment Variables (Recommended)**

```bash
# Create .env file (add to .gitignore)
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_CODE=your_client_code
ANGEL_PASSWORD=your_trading_pin
# Or: ANGEL_PIN= / ANGELONE_PIN=
ANGEL_TOTP_SECRET=your_totp_secret
# Or: ANGEL_TOTP= (pyotp generates 6-digit codes from secret)
# DRY_RUN=true   # Uncomment only for manual dry-run tests
MIN_WALLET_BALANCE=500
```

The bot loads `.env` automatically (`python-dotenv`). `BalanceWheelBot._apply_env_overrides()` merges env into config at runtime.

**Option 2: Encrypted Credentials (Advanced)**

Use Python's `cryptography` library to encrypt sensitive data.

---

## Usage

### Running the Bot

**Account snapshot only (no trading cycle)**

```bash
python balance_wheel.py --account
# Alias: --status
```

**Dry-Run Mode (manual / agent testing only)**

```bash
# One-off test: DRY_RUN=true python balance_wheel.py
# Or set "dry_run": true in config.json temporarily
DRY_RUN=true python balance_wheel.py
```

Expected output:
```
2026-05-10 09:30:00 - BalanceWheel - INFO - Authentication successful
2026-05-10 09:30:05 - BalanceWheel - INFO - [BUY] TCS: Price dip 16.50% >= 15%...
2026-05-10 09:30:05 - BalanceWheel - INFO - [DRY RUN] Would place order: TCS x150 @ 3400 = 510000.00 INR
```

**Production mode (default)**

```bash
# Ensure DRY_RUN is not set to true in .env
python balance_wheel.py
```

Logs must show: `LIVE PRODUCTION MODE — real BUY orders will be sent to Angel One`.

### Scheduling on PythonAnywhere

1. Go to **PythonAnywhere Dashboard > Tasks**
2. Add new scheduled task:
   - **Command:** `python /home/yourusername/BalanceWheel/balance_wheel.py`
   - **Schedule:** Every 15 minutes (or your preferred interval)
   - **Time zone:** IST

---

## Safety & Risk Management

### Critical Safety Rules

⚠️ **ALWAYS test in DRY-RUN mode first**

⚠️ **Start with small allocations** (e.g., 5% of portfolio)

⚠️ **Monitor logs daily** – never ignore errors

⚠️ **Never share your API key or credentials**

### Built-in Safety Mechanisms

| Safeguard | Details |
|-----------|---------|
| **Minimum Balance Check** | Bot won't execute if DMAT < ₹2,000 |
| **Cool-Down Period** | When `cooldown_days` > 0, blocks repeat buys per symbol |
| **Safety Buffer** | Reduces shares by 1 to cover taxes/brokerage |
| **Market Circuit Break** | Stops all buys if Nifty 50 drops >3% |
| **Sector Lock** | Max 1 buy per sector per 24 hours |
| **Fractional Share Prevention** | Uses `math.floor()` to avoid decimal shares |

### Risk Warnings

⚠️ **This is a leveraged strategy** – You're using margin to increase holdings  
⚠️ **Market risk remains** – No strategy prevents all losses  
⚠️ **API failures** – Network issues can delay or miss orders  
⚠️ **Liquidity risk** – Some stocks may not have sufficient volume at limit prices  
⚠️ **Regulatory risk** – Angel One or market regulations may change  

### Recommended Position Limits

- **Max allocation per stock:** 15% of portfolio
- **Max sector allocation:** 30% of portfolio
- **Max portfolio usage:** 50% (keep 50% cash for opportunities)
- **Max order size:** 10% of daily volume

---

## Log Interpretation

### Log File Location

```
logs/balance_wheel.log
```

### Log Levels

| Level | Meaning | Example |
|-------|---------|---------|
| **DEBUG** | Detailed execution flow | Token refresh, API calls |
| **INFO** | Important events | Stock analysis results |
| **WARNING** | Non-critical issues | Insufficient balance |
| **ERROR** | Critical failures | API timeout, authentication failed |

### Sample Log Walkthrough

```
2026-05-10 09:30:00 - BalanceWheel - INFO - ================================================================================
2026-06-04 10:36:37 - BalanceWheel - INFO - BalanceWheel Bot Initialized - BalanceWheel v1.0.9
2026-06-04 10:36:37 - BalanceWheel - WARNING - LIVE PRODUCTION MODE — real BUY orders will be sent to Angel One when signals fire
2026-05-10 09:30:00 - BalanceWheel - INFO - ================================================================================

// Authentication
2026-05-10 09:30:02 - BalanceWheel - INFO - Starting up BalanceWheel bot...
2026-05-10 09:30:03 - BalanceWheel - INFO - Authentication successful: Fresh authentication successful

// Trading Cycle Start
2026-05-10 09:30:05 - BalanceWheel - INFO - --------------------------------------------------------------------------------
2026-05-10 09:30:05 - BalanceWheel - INFO - Starting trading cycle at 2026-05-10 09:30:05.123456

// Stock Analysis
2026-05-10 09:30:06 - BalanceWheel - DEBUG - Analyzing TCS...
2026-05-10 09:30:07 - BalanceWheel - DEBUG - Fetched LTP for TCS: 3400.50
2026-05-10 09:30:08 - BalanceWheel - DEBUG - Portfolio avg price for TCS: 4050.00
2026-05-10 09:30:09 - BalanceWheel - INFO - [BUY] TCS: Price dip 16.10% >= 15%. Buy 150 shares.

// Constraint Checks
2026-05-10 09:30:09 - BalanceWheel - DEBUG - Available balance: 50000.00 INR
2026-05-10 09:30:10 - BalanceWheel - INFO - Execution result: [DRY RUN] TCS x150 @ 3400.50 = 510075.00 INR

// Cycle End
2026-06-04 10:36:38 - BalanceWheel - INFO - Placing LIVE order: HDFCBANK-EQ x10 LIMIT @ 747.6 (DELIVERY)
2026-06-04 10:36:38 - BalanceWheel - INFO - Order placed successfully: HDFCBANK-EQ x10 @ 747.6. Order ID: 260604000384963
2026-06-04 10:36:39 - BalanceWheel - INFO - Trading cycle completed. Processed 2 holding(s).
2026-05-10 09:30:15 - BalanceWheel - INFO - --------------------------------------------------------------------------------
```

### Database Observations Table

Query observations:
```bash
sqlite3 data/balance_wheel.db "SELECT * FROM observations ORDER BY timestamp DESC LIMIT 10;"
```

Output:
```
| symbol | ltp    | portfolio_avg_price | dip_percentage | action       | reason                  |
|--------|--------|---------------------|----------------|--------------|-------------------------|
| TCS    | 3400.5 | 4050.0              | 16.1           | BUY          | Price dip 16.1% >= 15%  |
| HCLTECH| 1200.0 | 1350.0              | 11.1           | STATUS_CHECK | Normal monitoring       |
```

---

## Centralized Logging & Analysis

BalanceWheel automatically pushes all execution logs to GitHub after each run, enabling comprehensive analysis across all deployment environments.

### Automatic Log Pushing

- **Trigger**: After every app execution (local or cloud)
- **Destination**: `logs/` folder in GitHub repository
- **Authentication**: Uses `GITHUB_TOKEN` from environment
- **Timezone**: Captures local system timezone in all timestamps

### Log Structure with Timezone

```
2026-05-14 10:25:53 IST - BalanceWheel - INFO - [startup:923] - Authentication successful
2026-05-14 10:26:12 EDT - BalanceWheel - INFO - [run_cycle:986] - [BUY] HCLTECH: Price dip 25.49%
```

### Analysis Benefits

- **Multi-Environment Tracking**: Compare performance across local dev, PythonAnywhere, etc.
- **Historical Performance**: Track buy signals, success rates, and market conditions
- **Debugging**: Centralized log access for troubleshooting deployment issues
- **Statistics**: Extract metrics for strategy optimization

### Accessing Logs on GitHub

1. Visit: https://github.com/nir351988/Balancewheel/tree/master/logs
2. Download latest `balance_wheel.log` for analysis
3. Use GitHub search for specific events or time periods

### Detailed Documentation

See [LOGGING.md](LOGGING.md) for complete log management guide, including:
- Log format specifications
- Analysis tools and techniques
- Multi-environment deployment considerations
- Troubleshooting log push issues

---

## Troubleshooting

### Issue: "Authentication failed" or `unexpected keyword argument 'totp'`

**Cause:** Invalid credentials, expired TOTP, or outdated `smartapi-python` (< 1.5.5)  
**Solution:**
```bash
pip install --upgrade "smartapi-python>=1.5.5"
# Verify .env (preferred) or config.json credentials
# Enable TOTP: https://smartapi.angelbroking.com/enable-totp
# Clear cached credentials:
rm .credentials.json   # Windows: del .credentials.json
python dev_tools.py --test auth
```

### Issue: `unexpected keyword argument 'clientCode'` on login

**Cause:** Repo used to ship a `smartapi/` test folder that shadowed the real SDK when run from `~/BalanceWheel`.  
**Fix:** `git pull` latest code, `pip install -r requirements-runtime.txt`, then verify:
```bash
python -c "from SmartApi.smartConnect import SmartConnect; import inspect; print(inspect.signature(SmartConnect.generateSession))"
# Should show: (self, clientCode, password, totp)
```

### Issue: "Insufficient Funds"

**Cause:** DMAT balance < ₹2,000  
**Solution:**
- Add funds to Angel One account
- Reduce order size in config.json
- Lower `minimum_balance_required_inr` threshold (not recommended)

### Issue: No orders executing

**Cause:** Could be multiple  
**Solution:**
```bash
# 1. Check dry_run mode
cat config.json | grep dry_run

# 2. Verify market data
python -c "from balance_wheel import *; bot = BalanceWheelBot(); bot.startup(); \
    market = bot.market_data_manager; print(market.get_ltp('TCS'))"

# 3. Check database for observations
sqlite3 data/balance_wheel.db "SELECT * FROM observations LIMIT 5;"

# 4. Review latest logs
tail -50 logs/balance_wheel.log
```

### Issue: API Rate Limiting

**Cause:** Too many API calls  
**Solution:**
- Increase cycle interval (e.g., 30 minutes instead of 15)
- Reduce number of stocks in `target_stocks`
- Contact Angel One support for higher limits

### Issue: Orders not matching expected price

**Cause:** Using LIMIT order at market price or slippage  
**Solution:**
- Use MARKET order type (higher price but guaranteed fill)
- Adjust order price dynamically based on market depth
- Set more conservative price limits

---

## Architecture

### Module Breakdown

```
BalanceWheel/
├── balance_wheel.py          # Main bot engine
├── auth_manager.py           # Angel One authentication
├── config.json               # Configuration & stock list
├── smartapi_client.py        # Official SDK import wrapper
├── requirements-runtime.txt  # Production dependencies
├── requirements.txt          # Full dev dependencies
├── README.md                 # This file
├── logs/
│   └── balance_wheel.log     # Rotating log file (10 days)
├── data/
│   └── balance_wheel.db      # SQLite observations & trades
└── tests/
    ├── test_auth.py          # Authentication tests
    ├── test_engine.py        # Trading logic tests
    └── test_market_data.py   # Market data tests
```

### Class Hierarchy

```
BalanceWheelBot (Orchestrator)
├── AngelOneAuthManager (API Auth)
├── MarketDataManager (Quote Fetching)
├── ObservationDatabase (SQLite Persistence)
└── BalanceWheelEngine (Trading Logic)
    ├── analyze_stock()
    ├── _calculate_smart_average()
    ├── check_execution_constraints()
    └── execute_buy_order()
```

### Data Flow

```
1. Load Config
    ↓
2. Authenticate → Angel One API
    ↓
3. Fetch Market Data (LTP, Holdings, Balance)
    ↓
4. Analyze Each Stock (15/5 Rule)
    ↓
5. Check Constraints (Balance, Cool-down, Sentiment)
    ↓
6. Execute Order (or DRY RUN)
    ↓
7. Log Observation & Trade
    ↓
8. Repeat
```

---

## Advanced Customization

### Modifying the 15/5 Rule

Edit `config.json`:
```json
"trading_rules": {
  "price_dip_threshold_percent": 20,       // Change from 15% to 20%
  "target_average_buffer_percent": 3,      // Change from 5% to 3%
  "high_alert_lower_threshold_percent": 15,
  "high_alert_upper_threshold_percent": 20
}
```

### Adding New Stocks

Edit `config.json` `target_stocks`:
```json
{
  "symbol": "INFY",
  "exchange": "NSE",
  "sector": "IT",
  "category": "Dividend",
  "priority": 1
}
```

### Custom Scheduling with APScheduler

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(bot.run_cycle, 'interval', minutes=15)
scheduler.start()
```

---

## Support & Contributions

For issues, feature requests, or contributions:

1. Review logs thoroughly
2. Isolate the problem with dry-run mode
3. Check Angel One API documentation
4. Contact Angel One support for API issues

---

## License

This bot is provided as-is for educational and trading purposes. Use at your own risk.

---

**Disclaimer:** BalanceWheel is an automated trading tool. While it implements multiple safety mechanisms, **no algorithm can guarantee profits or prevent losses**. Past performance is not indicative of future results. Always understand your risk tolerance and investment goals before using automated trading systems.

**Last Updated:** June 4, 2026  
**Maintained By:** Senior Python Developer & FinTech Engineer

---

## Documentation

This repository includes a dedicated `docs/` folder with authoritative references and maintenance guidance. Keep these documents up to date whenever you change code, configuration, or logging behavior.

- Project documentation: [docs/PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md)
- Verification & go-live: [docs/VERIFICATION.md](docs/VERIFICATION.md)
- Trading diary (orders & run history): [docs/TRADING_DIARY.md](docs/TRADING_DIARY.md)
- GCP VM bootstrap: [docs/GCP_VM_BOOTSTRAP.md](docs/GCP_VM_BOOTSTRAP.md)
- GCP teardown (keep secrets + static IP): [docs/GCP_TEARDOWN.md](docs/GCP_TEARDOWN.md)
- Changelog: [docs/CHANGELOG.md](docs/CHANGELOG.md)
- Docs maintenance: [docs/DOCS_MAINTENANCE.md](docs/DOCS_MAINTENANCE.md)
- Target watchlist: [docs/TARGET_STOCKS.md](docs/TARGET_STOCKS.md)

CI & PR checks
- The repository includes a Pull Request template and a lightweight GitHub Action that runs on PRs to help ensure the changelog or documentation is updated when core files change. See `.github/` for details.

