# BalanceWheel — Project Documentation

**Version:** 1.0.9  
**Last updated:** 2026-06-04

## Purpose

Technical reference for architecture, configuration, deployment, logging, and maintenance of the BalanceWheel trading bot (Angel One SmartAPI).

## Documentation index

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | User guide and strategy |
| [VERIFICATION.md](VERIFICATION.md) | Pre-flight checks and known issues |
| [TRADING_DIARY.md](TRADING_DIARY.md) | Verified orders and run history |
| [TARGET_STOCKS.md](TARGET_STOCKS.md) | Watchlist rationale |
| [GCP_VM_BOOTSTRAP.md](GCP_VM_BOOTSTRAP.md) | GCP Ubuntu VM provisioning (no crontab) |
| [GCP_TEARDOWN.md](GCP_TEARDOWN.md) | Destroy billable GCP resources; keep secrets + static IP |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |
| [DOCS_MAINTENANCE.md](DOCS_MAINTENANCE.md) | How to keep docs in sync |

## Overview

BalanceWheel is a **buy-only**, mean-reversion bot that:

- Authenticates to Angel One via SmartAPI (TOTP, SDK >= 1.5.5)
- By default analyzes **all demat holdings** (`analyze_holdings_only: true`)
- Uses `target_stocks` for sector/metadata when symbols match
- Places **LIMIT DELIVERY** BUY orders on NSE when the 15/5 rule fires (unless dry-run)
- Persists observations and trades in SQLite; rotates logs locally; optionally pushes logs to GitHub

**Production default:** `dry_run: false` in `config.json`. Opt into simulation with `DRY_RUN=true` or `PAPER_TRADING=true` in `.env`.

## Architecture and file map

```
BalanceWheel/
├── balance_wheel.py      # Main entry: bot, market data, engine, DB, GitHub log push
├── auth_manager.py       # Angel One auth + token cache (.credentials.json)
├── smartapi_client.py    # Imports official SmartConnect (avoids local shim)
├── dev_tools.py          # Diagnostics (--test auth, account, config, …)
├── utils.py              # Helpers and trade summaries
├── config.json           # Rules, watchlist, order_settings
├── requirements-runtime.txt  # Production dependencies (PA, GCP)
├── requirements.txt      # Full dev dependencies
├── tests/                # pytest (20 tests)
├── test_shims/           # Offline SmartAPI stub for tests only
├── logs/                 # Runtime logs (gitignored; may be pushed by bot)
└── data/                 # balance_wheel.db (gitignored)
```

**Do not** add a top-level `smartapi/` package — it shadows the official SDK.

### Class responsibilities (in `balance_wheel.py`)

| Class | Role |
|-------|------|
| `BalanceWheelBot` | Startup, `run_cycle()`, `--account`, shutdown, log push |
| `MarketDataManager` | Holdings cache, LTP, symbol token, Yahoo fallback |
| `BalanceWheelEngine` | 15/5 analysis, constraints, `execute_buy_order()` |
| `ObservationDatabase` | SQLite: `observations`, `executed_trades` |

## Configuration

### `config.json` (key fields)

| Key | Default | Meaning |
|-----|---------|---------|
| `version` | 1.0.9 | App version string in logs |
| `dry_run` | false | Live orders unless overridden by env |
| `analyze_holdings_only` | true | Scan all demat holdings each cycle |
| `startup_show_account` | true | DMAT snapshot at startup |
| `order_settings` | LIMIT, DELIVERY, NORMAL, NSE | Angel `placeOrder` fields |
| `trading_rules.cooldown_days` | 0 | Days between buys per symbol (set 7 if desired) |
| `trading_rules.minimum_balance_required_inr` | 2000 | Minimum cash before buys |

### Environment variables (`.env`)

Loaded automatically via `python-dotenv`. Common keys:

- `ANGEL_API_KEY`, `ANGEL_CLIENT_CODE`
- `ANGEL_PASSWORD` or `ANGEL_PIN` or `ANGELONE_PIN`
- `ANGEL_TOTP` or `ANGEL_TOTP_SECRET`
- `DRY_RUN`, `PAPER_TRADING` — force dry-run when set true
- `MIN_WALLET_BALANCE` — overrides minimum balance rule
- `GITHUB_TOKEN`, `GITHUB_REPO` — optional log push after each run

See [.env.example](../.env.example).

## Running the bot

```bash
pip install -r requirements-runtime.txt

# Connection + DMAT snapshot only (no trading cycle)
python balance_wheel.py --account

# Full trading cycle (live unless DRY_RUN=true)
python balance_wheel.py

# Tests
python -m pytest tests/ -q
```

### Hosting

- **PythonAnywhere:** `requirements-runtime.txt`, Python 3.10/3.12/3.13 (avoid broken 3.11 on some accounts)
- **GCP Ubuntu VM:** See [GCP_VM_BOOTSTRAP.md](GCP_VM_BOOTSTRAP.md); schedule runs from your infra repo (e.g. 10:30 IST weekdays)
- **Angel One live orders:** May require a **registered static IPv4** on the SmartAPI dashboard (GCP VM with reserved IP)

## Logging and GitHub log push

- File: `logs/balance_wheel.log` (rotating, timezone-aware)
- On shutdown, if `GITHUB_TOKEN` and `GITHUB_REPO` are set, the bot may commit/push `logs/`
- **Risk:** Logs can contain API errors with token fragments — prefer a private repo or disable push on public repos

## Troubleshooting (quick)

| Issue | Action |
|-------|--------|
| `unexpected keyword argument 'totp'` | `pip install "smartapi-python>=1.5.5"` |
| `Invalid Token` / AG8001 | `rm .credentials.json`, re-run |
| Rate limit on holdings/search | Run once per session; avoid back-to-back cycles |
| Yahoo 429 | Nifty check skipped; reduce run frequency |
| Unintended live orders | Remove `DRY_RUN` from `.env`; confirm log says LIVE PRODUCTION MODE |

Full list: [VERIFICATION.md](VERIFICATION.md).

## Development workflow

1. Change code/config
2. Run `pytest tests/`
3. Update `docs/CHANGELOG.md` and affected docs
4. For behavior changes, add notes to [TRADING_DIARY.md](TRADING_DIARY.md) when verifying live trades
