# BalanceWheel Quick Start Guide

## 5-Minute Setup

### Prerequisites
- Python 3.9+
- Angel One account with SmartAPI enabled
- API credentials (Key, Client Code, Password, TOTP)

### Step 1: Clone & Setup (1 min)
```bash
cd ~/projects
git clone <your-repo-url> BalanceWheel
cd BalanceWheel
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies (2 min)
```bash
pip install -r requirements.txt
pip show smartapi-python   # must be >= 1.5.5 (TOTP login)
```

### Step 3: Configure Credentials (1 min)
```bash
cp .env.example .env
# Edit .env with your Angel One credentials:
# ANGEL_API_KEY=your_key
# ANGEL_CLIENT_CODE=your_code
# ANGEL_PASSWORD=your_trading_pin
# ANGEL_TOTP=your_totp_secret   # from enable-totp page
# Leave DRY_RUN unset for production (default)
nano .env
```

### Step 4: Verify auth, then run (1 min)
```bash
python dev_tools.py --test auth
python balance_wheel.py   # LIVE by default — places real orders when BUY fires
```

Optional dry-run test:
```bash
DRY_RUN=true python balance_wheel.py
```

Expected output:
```
BalanceWheel Bot Initialized
Authentication successful
[BUY] TCS: Price dip 16.50%...
[DRY RUN] Would place order: TCS x150 @ 3400
```

### Step 5: Production scheduling
```bash
# Default is live. Confirm .env does NOT have DRY_RUN=true
grep -E "DRY_RUN|PAPER" .env || true
python balance_wheel.py
```

---

## Verification Checklist

- [ ] All dependencies installed: `pip list`
- [ ] Config file properly formatted: `python -c "import json; json.load(open('config.json'))"`
- [ ] Credentials working: Dry-run mode runs successfully
- [ ] Logs being created: `ls -la logs/`
- [ ] Database initialized: `sqlite3 data/balance_wheel.db ".tables"`
- [ ] All 13 stocks in target list
- [ ] Dry-run tested with at least 1 cycle
- [ ] Ready for live trading

---

## Running on PythonAnywhere

### Deploy Steps

1. **Upload Files to PythonAnywhere Web Console**
   ```
   /home/yourusername/BalanceWheel/
   ```

2. **Create Virtual Environment**
   ```
   mkvirtualenv --python=/usr/bin/python3.10 balance_wheel
   pip install -r requirements.txt
   ```

3. **Create Scheduled Task**
   - Go to: PythonAnywhere > Tasks
   - Add task:
     ```
     /home/yourusername/.virtualenvs/balance_wheel/bin/python \
     /home/yourusername/BalanceWheel/balance_wheel.py
     ```
   - Schedule: Daily @ 09:15 (before market opens at 9:30)
   - Or: Every 15 minutes during market hours

4. **Monitor Logs**
   ```
   tail -f /home/yourusername/BalanceWheel/logs/balance_wheel.log
   ```

---

## Common First Steps

### 1. Check Authentication
```bash
python -c "
from balance_wheel import BalanceWheelBot
bot = BalanceWheelBot()
success, msg = bot.auth_manager.authenticate()
print(f'Auth: {success} - {msg}')
"
```

### 2. Fetch Stock Prices
```bash
python -c "
from balance_wheel import BalanceWheelBot
bot = BalanceWheelBot()
bot.startup()
ltp = bot.market_data_manager.get_ltp('TCS')
print(f'TCS LTP: {ltp}')
"
```

### 3. Inspect Database
```bash
# View all observations
sqlite3 data/balance_wheel.db "SELECT * FROM observations LIMIT 10;"

# View all trades
sqlite3 data/balance_wheel.db "SELECT * FROM executed_trades LIMIT 10;"

# Count by action
sqlite3 data/balance_wheel.db \
  "SELECT action, COUNT(*) FROM observations GROUP BY action;"
```

### 4. Check Recent Logs
```bash
# Last 20 lines
tail -20 logs/balance_wheel.log

# Filter by log level
grep ERROR logs/balance_wheel.log
grep -i "buy\|alert" logs/balance_wheel.log
```

---

## Troubleshooting First Issues

### "ModuleNotFoundError: No module named 'SmartApi'"
```bash
# Reinstall requirements
pip install --upgrade -r requirements.txt
```

### "Connection refused" or "Timeout"
```bash
# Check internet connection
ping google.com

# Try auth manually
python -c "from auth_manager import AngelOneAuthManager; \
auth = AngelOneAuthManager('KEY', 'CODE', 'PASS'); \
success, msg = auth.authenticate(); print(msg)"
```

### "Invalid credentials"
```bash
# Verify in Angel One website first
# Then re-check .env file
# Ensure no extra spaces:
cat .env | grep ANGEL
```

### No trades executing
```bash
# 1. Check if dry_run is enabled
grep dry_run config.json

# 2. Check if any BUY signals in logs
grep "\[BUY\]" logs/balance_wheel.log

# 3. Run single cycle in verbose mode
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from balance_wheel import BalanceWheelBot
bot = BalanceWheelBot()
bot.startup()
bot.run_cycle()
"
```

---

## Development

### Running Tests
```bash
pytest tests/ -v
pytest tests/test_engine.py::TestBalanceWheelEngine::test_analyze_stock_buy_signal -v
```

### Code Quality
```bash
# Format code
black balance_wheel.py auth_manager.py

# Check lint
flake8 balance_wheel.py auth_manager.py

# Type checking
mypy balance_wheel.py
```

### Manual Testing
```bash
# Enter Python REPL
python

# Then in REPL:
from balance_wheel import *
config = json.load(open('config.json'))
bot = BalanceWheelBot()
bot.startup()

# Test analysis
stock = config['target_stocks'][0]
analysis = bot.engine.analyze_stock(stock, ltp=3400, portfolio_avg_price=4000)
print(analysis)
```

---

## Next Steps

1. **Customize Stock List**
   - Edit `config.json` `target_stocks` array
   - Add/remove stocks based on your portfolio

2. **Adjust Rules**
   - Modify thresholds in `trading_rules`
   - Test different dip percentages in dry-run

3. **Monitor Daily**
   - Set phone alerts for errors
   - Review logs for patterns

4. **Optimize Scheduling**
   - Start with single daily run
   - Expand to multiple runs if comfortable

---

## Support

- **Logs:** `logs/balance_wheel.log`
- **Database:** `data/balance_wheel.db`
- **Config:** `config.json`
- **Documentation:** `README.md`

---

**Happy Trading! Remember: Always test in dry-run first! 🚀**
