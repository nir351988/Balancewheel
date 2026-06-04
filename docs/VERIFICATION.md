# BalanceWheel — Verification & Operations Guide

**Last verified:** 2026-06-04  
**App version:** 1.0.9  
**Python:** 3.9–3.13  
**SmartAPI:** `smartapi-python` >= 1.5.5 (TOTP required)

Use this guide before and after go-live to confirm credentials, APIs, and trading behavior.

---

## Prerequisites

1. Angel One account with SmartAPI and [TOTP enabled](https://smartapi.angelbroking.com/enable-totp).
2. `.env` from `.env.example` (never commit `.env`).
3. `pip install -r requirements-runtime.txt` (production) or `requirements.txt` (dev).
4. `pip show smartapi-python` → version **>= 1.5.5**.

**PythonAnywhere:** Use Python **3.10, 3.12, or 3.13** for `mkvirtualenv`. Avoid **3.11** if you see `No module named '_posixsubprocess'`.

**GCP:** See [GCP_VM_BOOTSTRAP.md](GCP_VM_BOOTSTRAP.md).

---

## Quick verification commands

```bash
# 1. Unit tests (offline; 20 tests)
python -m pytest tests/ -q

# 2. Environment and config
python dev_tools.py --test environment
python dev_tools.py --test config
python dev_tools.py --test auth

# 3. DMAT snapshot (any time — best connection check)
python dev_tools.py --test account
python balance_wheel.py --account

# 4. Full trading cycle
python balance_wheel.py

# Dry-run only when testing
DRY_RUN=true python balance_wheel.py
```

---

## What to expect when healthy

| Check | Expected result |
|-------|-----------------|
| Authentication | `Authentication successful` |
| Account mode | `LIVE PRODUCTION MODE` or explicit `DRY RUN MODE` |
| Holdings | Demat positions listed in startup snapshot |
| Portfolio mode | Log: `analyzing demat holdings only` |
| Dry-run | `[DRY RUN] Would place order` — no broker order ID |
| Live BUY | `Placing LIVE order` → `Order placed successfully` + numeric `orderid` |
| Blocked buy | `Execution blocked: …` (balance, cooldown, sentiment) |
| Database | Rows in `observations` after each cycle |
| Logs | `logs/balance_wheel.log` updated with timezone |

Holdings **not** in demat are not analyzed in portfolio mode (watchlist names without positions are ignored).

---

## Verification checklist

- [x] `pytest tests/` — 20 passed (2026-06-04)
- [x] Angel One login with TOTP (SDK >= 1.5.5)
- [x] `--account` shows cash and holdings
- [x] Portfolio-first mode (`analyze_holdings_only: true`)
- [x] Live order path logged (see [TRADING_DIARY.md](TRADING_DIARY.md))
- [ ] `cooldown_days` set as desired (default **0** in `config.json`; use **7** to enable weekly cooldown)
- [ ] GCP static IP registered for live orders (if using GCP)
- [ ] Review whether GitHub log push is appropriate for repo visibility

---

## Known issues and fixes

### `generateSession() got an unexpected keyword argument 'totp'`

**Fix:** `pip install --upgrade "smartapi-python>=1.5.5"`

### Local `smartapi/` shadowing SDK

**Fix:** Use current repo (imports via `smartapi_client.py`); upgrade SDK.

### `Access denied because of exceeding access rate`

**Cause:** Too many Angel API calls in one session.  
**Fix:** One run per trading window; avoid multiple cycles within minutes.

### Yahoo Finance `429` (Nifty sentiment)

**Impact:** Nifty circuit-breaker may be skipped; other logic continues.

### Cached token `Invalid Token` (AG8001)

**Fix:** `rm .credentials.json` and re-run.

### Unintended live orders

**Fix:** Set `DRY_RUN=true` or `PAPER_TRADING=true` in `.env` for testing.

### `No response from broker` / empty JSON on placeOrder

**Cause:** Broker rejection, wrong symbol token, or rate limits.  
**Fix:** Confirm `-EQ` symbol, DELIVERY product, sufficient cash; see logs and Angel order book.

---

## Going live

1. Logs show **LIVE PRODUCTION MODE** (not DRY RUN).
2. Remove `DRY_RUN=true` from `.env` if present.
3. Sufficient demat cash for sized orders (bot may reduce qty vs signal).
4. Schedule **once** per market day (e.g. 10:30 IST), not a tight loop.
5. Record order IDs in [TRADING_DIARY.md](TRADING_DIARY.md).

---

## Related docs

- [README.md](../README.md)
- [QUICKSTART.md](../QUICKSTART.md)
- [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)
- [TRADING_DIARY.md](TRADING_DIARY.md)
- [CHANGELOG.md](CHANGELOG.md)
