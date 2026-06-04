# BalanceWheel Quick Start Guide

**Version:** 1.0.9 | **~5 minutes** to first `--account` check

## Prerequisites

- Python 3.9+
- Angel One SmartAPI + [TOTP](https://smartapi.angelbroking.com/enable-totp)
- API key, client code, trading PIN, TOTP secret

## Step 1: Clone & venv (1 min)

```bash
git clone https://github.com/nir351988/Balancewheel.git BalanceWheel
cd BalanceWheel
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

## Step 2: Install (2 min)

```bash
pip install -r requirements-runtime.txt
pip show smartapi-python   # >= 1.5.5
```

## Step 3: Configure (1 min)

```bash
cp .env.example .env
# Edit: ANGEL_API_KEY, ANGEL_CLIENT_CODE, ANGEL_PASSWORD, ANGEL_TOTP_SECRET
# Leave DRY_RUN unset for production
```

## Step 4: Verify & run (1 min)

```bash
python dev_tools.py --test auth
python balance_wheel.py --account    # DMAT snapshot, no orders
python -m pytest tests/ -q           # 20 offline tests

# Full cycle — LIVE by default
python balance_wheel.py
```

Dry-run test only:

```bash
DRY_RUN=true python balance_wheel.py
```

Expected live startup line:

```
LIVE PRODUCTION MODE — real BUY orders will be sent to Angel One when signals fire
```

Portfolio mode log:

```
Portfolio mode: analyzing demat holdings only
```

---

## Verification checklist

- [ ] `requirements-runtime.txt` installed; SmartAPI >= 1.5.5
- [ ] `python balance_wheel.py --account` shows cash + holdings
- [ ] `pytest tests/` — 20 passed
- [ ] `config.json`: `analyze_holdings_only: true` (default)
- [ ] Dry-run tested before first live market day
- [ ] `cooldown_days` set if you want buy spacing (default **0**)

---

## PythonAnywhere

```bash
mkvirtualenv --python=/usr/bin/python3.10 balance_wheel
workon balance_wheel
pip install -r requirements-runtime.txt
```

Scheduled task (example — once daily in market hours):

```
/home/USER/.virtualenvs/balance_wheel/bin/python /home/USER/BalanceWheel/balance_wheel.py
```

Avoid Python **3.11** on PA if `_posixsubprocess` is missing. See [DEPLOYMENT.md](DEPLOYMENT.md).

---

## GCP Ubuntu

See [docs/GCP_VM_BOOTSTRAP.md](docs/GCP_VM_BOOTSTRAP.md). Schedule runs from your infra repo (not installed by bootstrap).

---

## Useful commands

```bash
tail -30 logs/balance_wheel.log
grep -E "Placing LIVE|Order placed|DRY RUN|Execution blocked" logs/balance_wheel.log
sqlite3 data/balance_wheel.db "SELECT * FROM executed_trades ORDER BY id DESC LIMIT 5;"
```

---

## Docs

| Doc | Use |
|-----|-----|
| [README.md](README.md) | Full guide |
| [docs/VERIFICATION.md](docs/VERIFICATION.md) | Go-live checks |
| [docs/TRADING_DIARY.md](docs/TRADING_DIARY.md) | Order history |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Hosting |

**Always test with `DRY_RUN=true` before your first live market run.**
