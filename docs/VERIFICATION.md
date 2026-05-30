# BalanceWheel — Verification & Operations Guide

**Last verified:** 2026-05-30  
**Python:** 3.11+  
**SmartAPI package:** `smartapi-python` >= 1.5.5 (TOTP login required)

This guide documents how to verify that credentials, APIs, and the trading engine work before enabling live orders.

---

## Prerequisites

1. Angel One account with SmartAPI enabled and [TOTP activated](https://smartapi.angelbroking.com/enable-totp).
2. `.env` created from `.env.example` (never commit `.env`).
3. Dependencies installed: `pip install -r requirements.txt`
4. Confirm SDK version: `pip show smartapi-python` → version **1.5.5 or higher**.

---

## Quick verification commands

```bash
# 1. Unit tests (offline; uses local SmartAPI shim)
python -m pytest tests/ -q

# 2. Environment and config (needs real .env for auth test)
python dev_tools.py --test environment
python dev_tools.py --test config
python dev_tools.py --test auth

# 3. Full dry-run cycle (recommended before live trading)
# Set DRY_RUN=true in .env or "dry_run": true in config.json
python balance_wheel.py
```

---

## What to expect when healthy

| Check | Expected result |
|-------|-----------------|
| Authentication | `Authentication successful` in logs |
| Holdings API | Returns positions you hold in demat |
| RMS / balance | Available cash or margin in INR |
| Dry-run cycle | `[DRY RUN] Would place order` for BUY signals only |
| Database | Rows in `observations` after each cycle |
| Logs | `logs/balance_wheel.log` updated with timezone |

Stocks **not** in your demat are skipped with: `Skipping SYMBOL: missing market data or no current holding`.

---

## Verification checklist (2026-05-30)

- [x] `pytest tests/` — 14 tests passed
- [x] Angel One login with TOTP (SDK >= 1.5.5)
- [x] Holdings and available balance fetched
- [x] Dry-run cycle completed without live orders
- [x] GitHub log push (when `GITHUB_TOKEN` and `GITHUB_REPO` set)
- [ ] Align `target_stocks` in `config.json` with symbols you actually hold
- [ ] Re-enable `cooldown_days` (e.g. 7) before production if desired

---

## Known issues and fixes

### `generateSession() got an unexpected keyword argument 'totp'`

**Cause:** `smartapi-python` 1.3.x or older; Angel One requires TOTP on login.  
**Fix:** `pip install --upgrade "smartapi-python>=1.5.5"`

### `SmartApi` import fails or uses stub `smartConnect`

**Cause:** Local test shim in `smartapi/` can shadow the official package when the SDK is missing or outdated.  
**Fix:** Upgrade SDK (above). The app prefers `from SmartApi import SmartConnect` when installed.

### `Access denied because of exceeding access rate`

**Cause:** Too many Angel One API calls in one cycle (e.g. repeated `holding()` per symbol).  
**Fix:** Run once or twice per trading session; reduce `target_stocks`; add delay between manual API scripts.

### Yahoo Finance `429 Too Many Requests` (Nifty sentiment)

**Cause:** Free Yahoo quote API rate limit.  
**Impact:** Nifty circuit-breaker check may be skipped for that run; other logic still runs.  
**Fix:** Run less frequently; optional paid quote source for production.

### Cached token `Invalid Token` (AG8001)

**Fix:** Delete `.credentials.json` and re-run; bot will perform fresh login.

### Live orders when you meant to test

**Cause:** `config.json` has `"dry_run": false` and `DRY_RUN` not set in `.env`.  
**Fix:** Set `"dry_run": true` in `config.json` **or** `DRY_RUN=true` in `.env` (env overrides config).

---

## Portfolio snapshot (manual)

Use dry-run only; do not commit credentials. Example flow after auth:

1. Run `python dev_tools.py --test auth`
2. Inspect latest log lines for balance and `[BUY]` / `Skipping` per symbol
3. Query SQLite: `sqlite3 data/balance_wheel.db "SELECT symbol, action, dip_percentage, reason FROM observations ORDER BY id DESC LIMIT 20;"`

---

## Going live

Only after dry-run behaves as expected on a **market day**:

1. Set `"dry_run": false` in `config.json` **and** remove or set `DRY_RUN=false` in `.env`.
2. Confirm sufficient demat cash for computed order sizes.
3. Schedule one run during market hours (e.g. 10:30–11:30 IST), not a tight loop.
4. Monitor `logs/balance_wheel.log` after each run.

---

## Related docs

- [README.md](../README.md) — full user guide
- [QUICKSTART.md](../QUICKSTART.md) — 5-minute setup
- [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) — architecture reference
- [CHANGELOG.md](CHANGELOG.md) — version history
