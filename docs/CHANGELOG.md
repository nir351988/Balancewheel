# Changelog

All notable changes to this project should be documented in this file. Follow Semantic Versioning where possible.

## [Unreleased]

## [1.0.8] - 2026-05-30

### Fixed
- Live `placeOrder`: correct Angel One fields (`ordertype`, `DELIVERY`, `NORMAL`, `exchange`, `tradingsymbol`).
- Prefer `HCLTECH-EQ` (not IQ/RL) via holdings token or strict EQ search.
- Use `placeOrderFullResponse` for clear broker error messages.

## [1.0.7] - 2026-05-30

### Fixed
- `dev_tools.py` now loads `.env` and applies the same overrides as `BalanceWheelBot` (fixes auth test using `YOUR_*` placeholders).

## [1.0.6] - 2026-05-30

### Changed
- **Production default:** `dry_run: false` in `config.json`; real orders unless `DRY_RUN=true` or `PAPER_TRADING=true` in `.env`.
- Startup logs clearly show LIVE vs DRY RUN mode.

## [1.0.5] - 2026-05-30

### Fixed
- Added `logzero`, `six`, and `websocket-client` to `requirements-runtime.txt` (SmartAPI import on Python 3.13 / PythonAnywhere).

## [1.0.4] - 2026-05-30

### Changed
- **Portfolio-first mode:** `analyze_holdings_only: true` scans all demat holdings; `target_stocks` supplies metadata when symbols match.
- Holdings API called once per cycle (cache); fewer rate-limit errors.
- Added [TARGET_STOCKS.md](TARGET_STOCKS.md) explaining the 13-name watchlist.

## [1.0.3] - 2026-05-30

### Fixed
- **PythonAnywhere auth:** Removed top-level `smartapi/` folder that shadowed the official SDK; added `smartapi_client.py` for reliable imports.
- Login error `unexpected keyword argument 'clientCode'` no longer occurs when `smartapi-python` is installed.

## [1.0.2] - 2026-05-30

### Fixed
- Python 3.13 / PythonAnywhere: removed unused `pandas` import; added `requirements-runtime.txt` without pandas/numpy build issues.
- `dev_tools` environment check uses runtime deps (`requests`, `SmartApi`, `pyotp`).

### Changed
- `requirements.txt` includes runtime file; pandas/numpy optional with flexible pins for dev only.

## [1.0.1] - 2026-05-30

### Changed
- Default `dry_run` set to `true` in `config.json` for safer out-of-the-box runs.
- `smartapi-python` minimum version raised to **1.5.5** (Angel One TOTP login).
- Added `pyotp` to `requirements.txt` (required for TOTP generation).

### Documentation
- Added [VERIFICATION.md](VERIFICATION.md) — verification checklist, known issues, go-live steps.
- Updated README, QUICKSTART, PROJECT_SUMMARY, DEPLOYMENT, PROJECT_DOCUMENTATION, REPO_METADATA, and `.env.example` for SDK/TOTP, dry-run safety, and API rate limits.
- Documented local `smartapi/` test shim vs production SDK usage.

### Verified (2026-05-30)
- Unit tests: 14 passed.
- Angel One authentication, holdings, and balance APIs operational with SDK 1.5.5+.
- Dry-run trading cycle completed successfully.

## [1.0.0] - 2026-05-19

- Initial release: core bot, logging, GitHub log push, documentation baseline.
- Created initial documentation files and CHANGELOG.
