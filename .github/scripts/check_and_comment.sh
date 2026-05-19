#!/usr/bin/env bash
set -euo pipefail

# This script runs the changelog check and posts a PR comment if the check fails.
# It expects to run inside a GitHub Action with these env vars set:
# - GITHUB_EVENT_PATH, GITHUB_REPOSITORY, GITHUB_TOKEN

EVENT_PATH=${GITHUB_EVENT_PATH:-}
REPO=${GITHUB_REPOSITORY:-}
TOKEN=${GITHUB_TOKEN:-}

if [ -z "$EVENT_PATH" ] || [ -z "$REPO" ] || [ -z "$TOKEN" ]; then
  echo "Missing required environment variables: GITHUB_EVENT_PATH, GITHUB_REPOSITORY, or GITHUB_TOKEN"
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found; installing jq"
  sudo apt-get update && sudo apt-get install -y jq
fi

PR_NUMBER=$(jq -r '.pull_request.number // .issue.number // empty' "$EVENT_PATH")
if [ -z "$PR_NUMBER" ]; then
  echo "No pull request number found in event; exiting with success to avoid blocking runs on non-PR events."
  exit 0
fi

echo "Running changelog check for PR #$PR_NUMBER"

set +e
.github/scripts/check_changelog.sh
CHECK_RC=$?
set -e

if [ $CHECK_RC -eq 0 ]; then
  echo "Changelog check passed."
  exit 0
fi

echo "Changelog check failed. Posting a comment to PR #$PR_NUMBER"
COMMENT_BODY="Documentation check failed: core code changed but docs/CHANGELOG.md or docs/PROJECT_DOCUMENTATION.md not updated. Please add an entry under [Unreleased] or update docs and push to this PR."

API_URL="https://api.github.com/repos/$REPO/issues/$PR_NUMBER/comments"

curl -s -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
  -d "{\"body\": $(jq -Rn --arg b "$COMMENT_BODY" '$b') }" \
  "$API_URL" >/dev/null

exit 1
