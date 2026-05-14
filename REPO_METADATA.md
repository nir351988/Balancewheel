# Repository Metadata

This file documents the project repository and secure-local storage guidance.

## Repository
- GitHub repository: https://github.com/nir351988/Balancewheel.git

## Notes
- Do not store real GitHub personal access tokens in repository files.
- Use a local `.env` file or secret manager for sensitive credentials.
- Ensure `.env` is added to `.gitignore` so tokens are not committed.

## Recommended secure storage
1. Create a `.env` file in the project root.
2. Add the following variables without actual values:
   ```bash
   ANGEL_API_KEY=
   ANGEL_CLIENT_CODE=
   ANGEL_PASSWORD=
   ANGEL_TOTP=
   GITHUB_TOKEN=
   ```
3. Keep `.env` private.
4. Use `git status` to verify the file is not tracked.

## Reminder
This file contains metadata only. Sensitive tokens must never be saved in plain text in the repository.