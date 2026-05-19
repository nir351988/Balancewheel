BalanceWheel — Project Documentation
=================================

Version: 1.0.0
Last Updated: 2026-05-19

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
  - .env — Local environment secrets (never commit to remote).
  - docs/ — Project documentation (this folder).

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
- Yahoo 429 (Too Many Requests): Add caching, throttle requests, or use an alternative paid quote API.
- SmartAPI `placeOrder()` returns `None`: Verify credentials, product type (CNC/MIS), `symboltoken` mapping, and account permissions. Use the minimal order test script to print raw responses.
- Accidental secret commit: Immediately rotate exposed tokens, remove file from history (`git filter-branch` or BFG), and force-push cleaned history.

Development & Documentation Workflow
- Update `docs/CHANGELOG.md` for every meaningful change. Keep `docs/PROJECT_DOCUMENTATION.md` and `README.md` in sync.
- Documentation policy: update docs on every PR/commit that changes behavior, config, or public interfaces.

Contact & Ownership
- Owner: repo owner (see GitHub remote configured in `.env` / `GITHUB_REPO`).
