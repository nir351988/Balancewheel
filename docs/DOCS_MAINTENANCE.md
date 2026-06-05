# Docs Maintenance & Update Guidelines

## When to update docs

Update relevant files whenever you change:

- Public behavior, CLI flags (`--account`), or config keys
- Default modes (`dry_run`, `analyze_holdings_only`, `order_settings`)
- Deployment targets (PythonAnywhere, GCP, Docker)
- Logging, GitHub push, or security practices
- Verified live trades → add entry to [TRADING_DIARY.md](TRADING_DIARY.md)

## Files to keep in sync

| File | Purpose |
|------|---------|
| [README.md](../README.md) | Primary user guide |
| [QUICKSTART.md](../QUICKSTART.md) | Short setup path |
| [DEPLOYMENT.md](../DEPLOYMENT.md) | Hosting platforms |
| [docs/PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) | Architecture reference |
| [docs/VERIFICATION.md](VERIFICATION.md) | Pre-flight & known issues |
| [docs/CHANGELOG.md](CHANGELOG.md) | Version history |
| [docs/TARGET_STOCKS.md](TARGET_STOCKS.md) | Watchlist rationale |
| [docs/TRADING_DIARY.md](TRADING_DIARY.md) | Order/run diary |
| [docs/GCP_VM_BOOTSTRAP.md](GCP_VM_BOOTSTRAP.md) | GCP VM create/bootstrap |
| [docs/GCP_TEARDOWN.md](GCP_TEARDOWN.md) | GCP destroy + billing verification |

## Workflow

1. Edit the affected doc(s).
2. Add an entry under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md).
3. Bump version in `config.json` only for releases you tag.
4. Commit: `docs: <short description>`.

## Accuracy checks

```bash
# Version in config
python -c "import json; print(json.load(open('config.json'))['version'])"

# Tests count
python -m pytest tests/ -q

# Grep for stale version strings
rg "1\.0\.0|1\.0\.1|dry-run default|cooldown_days.: 7" --glob '*.md'
```

## Log push policy

- Treat `logs/` as sensitive; `.gitignore` excludes them locally but the bot may push them if `GITHUB_TOKEN` is set.
- Document incidents in TRADING_DIARY; do not paste live tokens into markdown.

## CI

PR template and `.github/workflows/docs-check.yml` may require changelog updates when core files change — see `.github/`.
