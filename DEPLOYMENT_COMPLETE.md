# BalanceWheel: Deployment Complete with Centralized Logging

> **Note (2026-06-04):** For current setup, defaults (v1.0.9, live mode, portfolio-first), and hosting, use [README.md](README.md), [DEPLOYMENT.md](DEPLOYMENT.md), and [docs/VERIFICATION.md](docs/VERIFICATION.md). This file is a historical completion log from May 2026.

## Summary of Completed Tasks

### ✅ 1. GitHub Repository Setup
- **Initialized git repository** in the project directory
- **Created initial commit** with all source code and configuration
- **Pushed entire project** to GitHub: https://github.com/nir351988/Balancewheel.git

### ✅ 2. Centralized Logging with Timezone Support
- **Implemented timezone-aware logging** that captures system local time
- **Format**: `2026-05-14 10:48:25 India Standard Time - BalanceWheel - INFO - [function:line] - Message`
- **No timezone assumptions** - logs capture whatever timezone the system running the app has
- **Works across environments**: Local (Windows), PythonAnywhere, cloud deployments, etc.

### ✅ 3. Automatic Log Pushing to GitHub
- **After every app run**, logs are automatically committed and pushed to GitHub
- **Log push process**:
  1. `git add logs/ -f` - Stage all log files
  2. `git commit` - Commit with timestamp and system info
  3. `git push` - Push to GitHub repository
- **Secure credential handling** - Uses GITHUB_TOKEN from environment
- **Sanitized error logging** - Tokens are redacted in error messages

### ✅ 4. Comprehensive Documentation
- **LOGGING.md** - Complete guide on log management, analysis, and multi-environment deployment
- **README.md** - Updated with logging features and Centralized Logging section
- **Inline code comments** - Clear documentation of log pushing functionality

## Verification & Testing

### Run Date: May 14, 2026 @ 10:48 AM IST

**Terminal Output:**
```
2026-05-14 10:48:25 India Standard Time - BalanceWheel - INFO - [__init__:839] - BalanceWheel Bot Initialized
2026-05-14 10:48:25 India Standard Time - BalanceWheel - INFO - [startup:931] - Starting up BalanceWheel bot...
2026-05-14 10:48:26 India Standard Time - BalanceWheel - INFO - [_push_logs_to_github:1069] - Git command successful: git config
2026-05-14 10:48:25 India Standard Time - BalanceWheel - INFO - [_push_logs_to_github:1069] - Git command successful: git add
2026-05-14 10:48:26 India Standard Time - BalanceWheel - INFO - [_push_logs_to_github:1069] - Git command successful: git commit
2026-05-14 10:48:28 India Standard Time - BalanceWheel - INFO - [_push_logs_to_github:1069] - Git command successful: git push
```

**Verification:**
- ✅ Timezone captured correctly: "India Standard Time"
- ✅ All git commands executed successfully
- ✅ Logs pushed to GitHub automatically
- ✅ Commit created: "Logs update: 2026-05-14 10:48:25 - Windows"

## Key Features

### Logging Capabilities
- **Detailed Execution Tracking**:
  - Stock analysis results
  - Buy signals (trigger conditions, shares to buy, target averages)
  - Execution blocks (cooldown, balance, sentiment)
  - Order results (success/failure)

- **System Information**:
  - Execution timestamps with timezone
  - System name (Windows, Linux, etc.)
  - Function name and line number
  - Log level (INFO, WARNING, ERROR, DEBUG)

### Multi-Environment Support
| Environment | Timezone Capture | Log Push |
|------------|-----------------|----------|
| Local Dev | System TZ (IST) | ✅ Yes |
| PythonAnywhere | Server TZ (UTC) | ✅ Yes |
| Cloud Deploy | Container TZ | ✅ Yes |

### Data Collection for Analysis
- **Performance Metrics**: Buy success rates, dip frequencies, market conditions
- **Statistical Analysis**: Average dip percentages, cooldown effectiveness, sector performance
- **Debugging**: Centralized access to execution logs from any deployment
- **Historical Tracking**: 10-day log rotation with GitHub archive

## Configuration

### Environment Variables Required
```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO=https://github.com/nir351988/Balancewheel.git
```

### Log Configuration (config.json)
```json
{
  "logging": {
    "log_file": "logs/balance_wheel.log",
    "backup_count": 10,
    "max_bytes": 5242880,
    "level": "INFO"
  }
}
```

## GitHub Repository Structure

```
Balancewheel/
├── balance_wheel.py              # Main bot engine with log pushing
├── config.json                   # Trading rules and logging config
├── auth_manager.py              # Angel One authentication
├── LOGGING.md                   # Logging & analysis guide
├── README.md                    # Updated with logging features
├── logs/
│   ├── balance_wheel.log        # Current run logs
│   ├── balance_wheel.log.1      # Previous runs (rotated)
│   └── ...                      # Backup logs (up to 10 days)
└── .gitignore                   # Excludes sensitive data
```

## Workflow: App Run → Log Push

1. **App Startup**
   - Initializes logging with timezone formatter
   - Connects to Angel One
   - Loads trading rules

2. **Trading Cycle**
   - Analyzes each stock
   - Logs buy signals, blocks, and results
   - Records to SQLite observations table

3. **Graceful Shutdown**
   - Logs shutdown message
   - Triggers `_push_logs_to_github()`
   - Commits and pushes logs with timestamp

4. **GitHub Update**
   - Logs appear in `logs/` folder on GitHub
   - Commit message shows run timestamp and system
   - Available for historical analysis

## Security & Privacy

✅ **Protected Credentials**
- `.env` excluded from git (credentials safe locally)
- Tokens redacted in error logs
- GitHub token used only for authentication

✅ **Data Privacy**
- No personal data in logs
- Only trading actions and market data
- Public repository suitable for transparency

✅ **Safe Error Logging**
- Sensitive URLs sanitized before logging
- Error messages truncated to prevent exposure
- Tokens never appear in committed logs

## Next Steps

### For PythonAnywhere Deployment
1. Set environment variables:
   ```bash
   export GITHUB_TOKEN=your_token_here
   export GITHUB_REPO=your_repo_url
   ```

2. Schedule bot to run during trading hours:
   - 10:30–11:30 AM IST (Market open + 1 hour)
   - 13:30–14:30 PM IST (Post-lunch session)

3. Monitor logs on GitHub for:
   - Buy signal success rates
   - Cooldown pattern effectiveness
   - Market condition analysis

### For Local Analysis
```bash
# View latest logs
tail -f logs/balance_wheel.log

# Analyze from GitHub
git log --grep="Logs update" --oneline

# Download logs for processing
git show origin/master:logs/balance_wheel.log
```

## Troubleshooting

### Issue: "GITHUB_TOKEN not found"
**Solution**: Add to `.env`:
```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

### Issue: Logs not pushing
**Check**:
1. GITHUB_TOKEN validity
2. Repository access permissions
3. Network connectivity
4. Git installation

### Issue: Timezone incorrect
**Solution**:
- Verify system timezone setting
- Set in environment: `TZ=Asia/Kolkata`
- Check log file: Line 1 shows captured timezone

## Success Confirmation

✅ **All tasks completed successfully**:
- [x] Project pushed to GitHub
- [x] Timezone-aware logging implemented
- [x] Automatic log pushing configured
- [x] Documentation created
- [x] Testing verified with successful push

**Last Successful Run**: 2026-05-14 10:48:25 India Standard Time  
**Logs Status**: ✅ Pushed to GitHub repository