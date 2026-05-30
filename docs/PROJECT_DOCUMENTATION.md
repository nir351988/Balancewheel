BalanceWheel — Project Documentation
=================================

Version: 1.0.1
Last Updated: 2026-05-30

Purpose
- Full project reference, architecture, operation, and maintenance guide for BalanceWheel trading bot.

Contents
- Overview
- Architecture & file map
- Configuration & secrets
- Running the bot (local / cloud)
- Logging & centralized log push
- Troubleshooting common issues
- Development and documentation workflow

Overview
- BalanceWheel is a Python trading bot designed to run on local machines or cloud hosts (e.g., PythonAnywhere). It analyzes configured universe stocks and places buy orders via Angel One (SmartAPI). The project includes an automated mechanism to push runtime logs into a GitHub repository for centralized analysis.

Architecture & File Map
- Top-level files and directories (primary files to inspect):
  - balance_wheel.py — Main bot entrypoint and cycle orchestration.
  - auth_manager.py — Authentication wrapper for Angel One SmartAPI.
  - market_data_manager.py — Market data helpers; LTP, symbol token lookup, Yahoo fallback.
  - config.json — Runtime configuration and trading rules (dry_run, cooldown_days, thresholds).
  - data/ — SQLite DB directory (data/balance_wheel.db).
  - logs/ — Runtime logs (RotatingFileHandler). NOTE: logs are sensitive and should be excluded from commits unless sanitized.
  - tests/ — Unit tests.
  - smartapi/ and SmartApi/ — Local test shims for offline unit testing.
  - .env — Local environment secrets (never commit to remote).
  - docs/ — Project documentation (this folder).

Test Shim Note
- The repository includes a lightweight local shim in `smartapi/` (see `smartapi/smartConnect.py`).
- Unit tests and CI can import a minimal `SmartConnect` without network access.
- **Production:** install `smartapi-python>=1.5.5` from `requirements.txt`. The app imports `from SmartApi import SmartConnect` when available.
- Angel One login requires **TOTP** (SDK 1.3.x will fail with unexpected keyword `totp`). See [VERIFICATION.md](VERIFICATION.md).

Documentation index
- [VERIFICATION.md](VERIFICATION.md) — pre-flight checks and known issues
- [CHANGELOG.md](CHANGELOG.md) — release notes

Configuration & Secrets
- Secrets and credentials are stored in `.env` for local runs. Recommended deployment practices:
  - Do NOT commit `.env` or `logs/` to Git. Add them to `.gitignore`.
  - Rotate any tokens that were accidentally exposed.
  - For hosted deployments, set environment variables in the host UI (PythonAnywhere env settings, CI secrets, etc.).

Running the bot
- Local (development):
  1. Create a Python virtual environment and install requirements (`pip install -r requirements.txt`).
  2. Populate `.env` with Angel One credentials and a GitHub token only if needed for log pushes.
  3. Configure `config.json` (set `dry_run` true for tests).
  4. Run: `python balance_wheel.py`

- Production / Hosted:
  - Use platform environment variables instead of `.env`.
  - Ensure `GITHUB_TOKEN` has minimal permissions (repo contents only if private, or a scoped token for log pushes). Rotate tokens regularly.

Logging & Centralized Log Push
- Logs are written locally to `logs/balance_wheel.log` using a timezone-aware formatter.
- On shutdown the bot attempts to commit and push logs to the configured `GITHUB_REPO` using `GITHUB_TOKEN`. Safeguards:
  - `_push_logs_to_github()` sanitizes commit messages and avoids including raw secrets.
  - Logs should still be treated as sensitive — sanitize before pushing.

Troubleshooting — Common Issues
- **Authentication / TOTP:** Upgrade `pip install "smartapi-python>=1.5.5"`. Set `ANGEL_TOTP` or `ANGEL_TOTP_SECRET` in `.env`. Clear stale tokens: delete `.credentials.json`.
- **SDK / shim conflict:** If login uses a stub, upgrade the official package; do not rely on `smartapi/smartConnect.py` for live trading.
- **Angel One rate limit:** Reduce `target_stocks` or run fewer cycles per day; avoid hammering `holding()` in tight loops.
- **Yahoo 429 (Too Many Requests):** Throttle runs; Nifty sentiment check may fail without blocking other logic.
- **SmartAPI `placeOrder()` returns `None`:** Verify credentials, product type (CNC/MIS), `symboltoken` mapping, and account permissions.
- **Accidental secret commit:** Rotate tokens immediately; remove from git history if needed.
- **Live orders unintentionally:** Ensure `dry_run: true` in `config.json` or `DRY_RUN=true` in `.env`.

Development & Documentation Workflow
- Update `docs/CHANGELOG.md` for every meaningful change. Keep `docs/PROJECT_DOCUMENTATION.md` and `README.md` in sync.
- Documentation policy: update docs on every PR/commit that changes behavior, config, or public interfaces.

Contact & Ownership
- Owner: repo owner (see GitHub remote configured in `.env` / `GITHUB_REPO`).
