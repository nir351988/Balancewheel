# BalanceWheel Log Management & Analysis

## Overview

BalanceWheel automatically pushes all execution logs to the GitHub repository after each run, enabling centralized log analysis, performance tracking, and continuous improvement from any deployment environment (local, PythonAnywhere, cloud, etc.).

## Log Structure & Details

### Log Format
```
2026-05-14 10:25:53 IST - BalanceWheel - INFO - [startup:923] - Authentication successful: Fresh authentication successful
```

**Components:**
- **Timestamp**: System local time with timezone (e.g., `2026-05-14 10:25:53 IST`)
- **Logger Name**: `BalanceWheel`
- **Level**: `INFO`, `WARNING`, `ERROR`, `DEBUG`
- **Function:Line**: `[startup:923]` - Source code location
- **Message**: Detailed action/result description

### Timezone Handling
- Logs capture the **local system timezone** where the app runs
- No market hour or timezone assumptions
- Timezone name is appended to timestamps (e.g., `IST`, `UTC`, `EDT`)
- Enables accurate analysis across different deployment environments

### Detailed Logging Events

#### Startup Phase
- Authentication status
- Database initialization
- Configuration loading
- Bot initialization confirmation

#### Trading Cycle
- Cycle start/end timestamps
- Stock-by-stock analysis results
- Buy signal triggers with:
  - Dip percentage
  - Calculated shares to buy
  - Target average price
- Execution constraints checks:
  - Cooldown status
  - Balance verification
  - Sector diversification
  - Market sentiment
- Order execution results (success/failure with order IDs)

#### Shutdown Phase
- Clean exit confirmation
- Error summaries (if any)
- Log push status to GitHub

## GitHub Log Repository

### Automatic Log Pushing
- **Trigger**: After every app run (successful or failed)
- **Location**: `logs/` folder in GitHub repository
- **Method**: Git commit and push using configured GITHUB_TOKEN
- **Files**: All log files including rotated backups

### Repository Structure
```
Balancewheel/
├── logs/
│   ├── balance_wheel.log          # Current log file
│   ├── balance_wheel.log.1        # Previous run
│   ├── balance_wheel.log.2        # Older runs
│   └── ...
├── src/                           # Application code
└── docs/                          # Documentation
```

### Access & Analysis
- Logs are publicly accessible on GitHub
- Enable GitHub Pages for web-based log viewing
- Use GitHub's search and blame features for analysis
- Download logs for local processing

## Configuration

### Environment Variables
```bash
# Required for log pushing
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
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

## Analysis & Statistics

### Key Metrics to Extract
- **Execution Frequency**: Run timestamps and intervals
- **Buy Signal Success Rate**: Triggers vs actual executions
- **Cooldown Effectiveness**: Blocks due to timing
- **Balance Management**: Available funds tracking
- **Stock Performance**: Dip percentages and recovery patterns
- **Error Patterns**: Common failure modes

### Tools for Analysis
- **GitHub Insights**: Commit frequency, file changes
- **Log Parsers**: Custom scripts for metric extraction
- **Dashboards**: Web-based log visualization
- **Alerts**: Automated monitoring for anomalies

## Deployment Considerations

### Multi-Environment Support
- **Local Development**: Logs pushed from developer machines
- **PythonAnywhere**: Automated daily runs with timezone logging
- **Cloud Deployments**: Container logs with system timezone
- **Concurrent Runs**: Timestamp-based conflict resolution

### Security & Privacy
- Sensitive data excluded via .gitignore
- Token-based authentication for GitHub access
- No credentials logged in application logs
- Public repository for transparency

## Troubleshooting

### Log Push Failures
- Check GITHUB_TOKEN validity
- Verify repository access permissions
- Review network connectivity
- Check git installation and configuration

### Timezone Issues
- Ensure system timezone is correctly set
- Verify Python datetime handling
- Check container timezone configuration

### Log Analysis Problems
- Use consistent log parsing tools
- Maintain log format compatibility
- Archive old logs for historical analysis