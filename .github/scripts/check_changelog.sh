#!/usr/bin/env bash
set -euo pipefail

# Simple guard: if core files changed, ensure either CHANGELOG.md or PROJECT_DOCUMENTATION.md changed
# This script is intentionally conservative; customize as needed for your repo.

BASE_REF=${GITHUB_BASE_REF:-}
if [ -z "$BASE_REF" ]; then
  # Not running in PR context; attempt a fuzzy check
  changed_files=$(git diff --name-only HEAD~1..HEAD || true)
else
  git fetch origin "$BASE_REF":"refs/remotes/origin/$BASE_REF" || true
  changed_files=$(git diff --name-only origin/$BASE_REF...HEAD || true)
fi

echo "Changed files:\n$changed_files"

# Define core files that should trigger a docs change when modified
# Match core python files, tests, requirements, and config changes
trigger_pattern='(^balance_wheel.py$|^auth_manager.py$|^market_data_manager.py$|^config.json$|^requirements.txt$|^tests/|^.+\.py$)'

if echo "$changed_files" | grep -E "$trigger_pattern" -q; then
  if echo "$changed_files" | grep -E '(^docs/CHANGELOG.md$|^docs/PROJECT_DOCUMENTATION.md$)' -q; then
    echo "Docs updated alongside code changes. OK."
    exit 0
  else
    echo "ERROR: Core code changed but docs/CHANGELOG.md or docs/PROJECT_DOCUMENTATION.md were not updated."
    echo "Please update docs/CHANGELOG.md or docs/PROJECT_DOCUMENTATION.md with a short note."
    exit 1
  fi
else
  echo "No core files changed; skipping changelog enforcement."
  exit 0
fi
