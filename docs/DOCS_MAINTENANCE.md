# Docs Maintenance & Update Guidelines

Purpose
- Explain how to keep documentation current and provide a lightweight workflow for updating docs after code changes.

When to update docs
- Update `docs/PROJECT_DOCUMENTATION.md`, `docs/VERIFICATION.md`, and `docs/CHANGELOG.md` whenever:
  - Public behavior, configuration keys, or runtime semantics change.
  - New files or modules are added that affect the architecture.
  - Logging, deployment, or security behavior changes (e.g., new token handling, log push behavior).

How to update
1. Edit the relevant `docs/` file(s).
2. Add an entry to `docs/CHANGELOG.md` under `[Unreleased]` describing the change.
3. Commit with a descriptive message: `docs: describe changes`.

Optional: simple commit hook (example)
- Place the following script in `.git/hooks/pre-commit` (make executable on Unix).

```bash
# Example pre-commit: ensure changelog updated when docs changed
changed_docs=$(git diff --cached --name-only | grep '^docs/' || true)
if [ -n "$changed_docs" ]; then
  echo "Docs changed: $changed_docs"
  # Ensure changelog has an Unreleased section entry (manual check recommended)
fi
```

Automated doc updates
- For complex projects, consider adding a CI step that validates documentation completeness (links, file existence, format).

Note on pushing logs to GitHub
- Because runtime logs may accidentally contain secrets, treat the automatic log push as optional and gated. If you enable automatic pushes in production, ensure:
  - Tokens used for pushes have minimal scope.
  - Logs are sanitized before commit.
