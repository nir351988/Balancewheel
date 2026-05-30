# Changelog

All notable changes to this project should be documented in this file. Follow Semantic Versioning where possible.

## [Unreleased]

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
