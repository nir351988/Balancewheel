# BalanceWheel: Complete Deployment Guide

## Deployment Platforms

This guide covers deployment to:
1. **PythonAnywhere** (Recommended - Serverless, easy setup)
2. **AWS Lambda** (Serverless, pay-per-use)
3. **Docker** (Any cloud provider)
4. **Local Server** (VPS/Dedicated server)

---

## Table of Contents
- [PythonAnywhere Deployment](#pythonanywhere-deployment)
- [AWS Lambda Deployment](#aws-lambda-deployment)
- [Docker Deployment](#docker-deployment)
- [Post-Deployment Checks](#post-deployment-checks)
- [Monitoring & Maintenance](#monitoring--maintenance)

---

## PythonAnywhere Deployment

### Why PythonAnywhere?
✅ Pre-configured Python environment  
✅ Built-in scheduler for cron jobs  
✅ Web-based file manager  
✅ Real-time log viewer  
✅ No server management needed  

### Prerequisites
- PythonAnywhere account (free or paid)
- Angel One credentials

### Step-by-Step Setup

#### 1. Upload Files (5 min)

```bash
# On your local machine, zip the project
zip -r BalanceWheel.zip . -x "*.pyc" "__pycache__/*" "venv/*" ".git/*" "logs/*"

# Then upload to PythonAnywhere:
# Web Console -> Files -> Upload file -> BalanceWheel.zip
```

Or upload via terminal:
```bash
# Open PythonAnywhere Bash Console
cd ~
unzip BalanceWheel.zip  # If using zip method
# Or git clone
git clone <your-repo-url> BalanceWheel
cd BalanceWheel
```

#### 2. Create Virtual Environment (2 min)

```bash
# Use 3.10, 3.12, or 3.13 — avoid 3.11 on PythonAnywhere (broken _posixsubprocess on some accounts)
mkvirtualenv --python=/usr/bin/python3.10 balance_wheel
workon balance_wheel
pip install --upgrade pip setuptools wheel
pip install -r requirements-runtime.txt
pip show smartapi-python   # must be >= 1.5.5
```

#### 3. Configure Credentials (2 min)

```bash
# Create .env file with credentials
nano .env
```

Add:
```
ANGEL_API_KEY=your_key
ANGEL_CLIENT_CODE=your_code
ANGEL_PASSWORD=your_password
ANGEL_TOTP=your_totp
# DRY_RUN=true   # omit for production (default: live)
```

Press Ctrl+O to save, Enter, then Ctrl+X to exit.

#### 4. Test auth, then production run (3 min)

```bash
workon balance_wheel
python dev_tools.py --test auth
python balance_wheel.py
```

Expected startup line:
```
LIVE PRODUCTION MODE — real BUY orders will be sent to Angel One when signals fire
```

Optional dry-run:
```bash
DRY_RUN=true python balance_wheel.py
```

#### 5. Set Up Scheduled Task (2 min)

Go to **PythonAnywhere Dashboard > Tasks**:

1. Click "Create new scheduled task"
2. Set the time (e.g., 09:15 for IST):
   - Minute: 15
   - Hour: 9
   - Day of week: * (every day)

3. In the task command field, enter:
   ```bash
   /home/yourusername/.virtualenvs/balance_wheel/bin/python /home/yourusername/BalanceWheel/balance_wheel.py
   ```

4. Save

#### 6. View Logs

```bash
# In PythonAnywhere Bash Console
tail -50 ~/BalanceWheel/logs/balance_wheel.log
# Or use web console -> Files -> logs/balance_wheel.log
```

#### 7. Production is default

Ensure `.env` does **not** set `DRY_RUN=true`. Scheduled tasks run live unless you opt in to dry-run.

### PythonAnywhere Troubleshooting

**Issue: Task not running**
```bash
# Check task output
# Dashboard > Tasks > Click on task > View output

# Check error logs
grep ERROR ~/BalanceWheel/logs/balance_wheel.log

# Verify permissions
chmod +x ~/BalanceWheel/balance_wheel.py
```

**Issue: `ModuleNotFoundError: No module named '_posixsubprocess'`**

**Cause:** Python 3.11 on PythonAnywhere is sometimes symlinked to an incomplete install (`/usr/local/bin/python3.11`).

**Fix:** Delete the venv and recreate with 3.10, 3.12, or 3.13:
```bash
deactivate
rmvirtualenv balance_wheel
# optional: clear virtualenv wheel cache
rm -rf ~/.local/share/virtualenv/wheel/*
mkvirtualenv --python=/usr/bin/python3.10 balance_wheel
workon balance_wheel
python -c "import _posixsubprocess; print('Python OK')"
pip install --upgrade pip
pip install -r requirements.txt
```

**Issue: "Module not found"**
```bash
# Verify virtual environment
workon balance_wheel
pip list | grep smartapi

# Reinstall if needed (>= 1.5.5 required for TOTP login)
pip install --upgrade "smartapi-python>=1.5.5"
pip show smartapi-python
```

**Issue: Authentication fails or `unexpected keyword argument 'totp'`**
```bash
# Upgrade SDK, set TOTP in .env, clear stale cache
pip install --upgrade "smartapi-python>=1.5.5"
rm .credentials.json
python dev_tools.py --test auth
```
See [docs/VERIFICATION.md](docs/VERIFICATION.md) for the full checklist.

---

## AWS Lambda Deployment

### Why AWS Lambda?
✅ Pay-per-use pricing  
✅ Auto-scaling  
✅ Serverless (no server management)  
✅ EventBridge for scheduling  

### Prerequisites
- AWS Account
- AWS CLI configured
- SAM CLI or CloudFormation knowledge

### Setup (Basic)

#### 1. Package Code for Lambda

```bash
# Install dependencies in deployment package
mkdir lambda_package
pip install -r requirements.txt -t lambda_package/
cp balance_wheel.py auth_manager.py lambda_package/
cp config.json lambda_package/

# Create deployment ZIP
cd lambda_package
zip -r ../lambda_function.zip .
```

#### 2. Create Lambda Function

```bash
# Via AWS CLI
aws lambda create-function \
  --function-name balance-wheel-bot \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-role \
  --handler balance_wheel.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables="{ANGEL_API_KEY=your_key,ANGEL_CLIENT_CODE=your_code,ANGEL_PASSWORD=your_password}"
```

#### 3. Schedule with EventBridge

```bash
# Create EventBridge rule for daily execution
aws events put-rule \
  --name balance-wheel-schedule \
  --schedule-expression "cron(15 9 * * ? *)" \
  --state ENABLED

# Add Lambda as target
aws events put-targets \
  --rule balance-wheel-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:region:account:function:balance-wheel-bot"

# Grant EventBridge permission
aws lambda add-permission \
  --function-name balance-wheel-bot \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:region:account:rule/balance-wheel-schedule
```

#### 4. Add Lambda Handler

Update `balance_wheel.py`:
```python
def lambda_handler(event, context):
    """AWS Lambda entry point."""
    bot = BalanceWheelBot(config_file="config.json")
    try:
        if not bot.startup():
            return {
                'statusCode': 500,
                'body': 'Startup failed'
            }
        bot.run_cycle()
        bot.shutdown("Lambda execution completed")
        return {
            'statusCode': 200,
            'body': 'Trading cycle executed successfully'
        }
    except Exception as e:
        bot.logger.error(f"Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }
```

### View Lambda Logs

```bash
# Via AWS CLI
aws logs tail /aws/lambda/balance-wheel-bot --follow

# Via AWS Console
CloudWatch > Log Groups > /aws/lambda/balance-wheel-bot
```

---

## Docker Deployment

### Why Docker?
✅ Consistent environment  
✅ Easy migration between platforms  
✅ Kubernetes-ready  
✅ Microservices-friendly  

### Prerequisites
- Docker installed
- Docker Compose (optional)

### Build & Run

#### 1. Build Docker Image

```bash
docker build -t balance-wheel:latest .
```

#### 2. Run Container

**Dry-Run Mode:**
```bash
docker run \
  --name balance-wheel \
  -e DRY_RUN=true \
  -e ANGEL_API_KEY=your_key \
  -e ANGEL_CLIENT_CODE=your_code \
  -e ANGEL_PASSWORD=your_password \
  -e ANGEL_TOTP=your_totp \
  -v $(pwd)/logs:/app/BalanceWheel/logs \
  -v $(pwd)/data:/app/BalanceWheel/data \
  balance-wheel:latest
```

**Live Mode:**
```bash
docker run \
  --name balance-wheel \
  -e DRY_RUN=false \
  -e ANGEL_API_KEY=your_key \
  -e ANGEL_CLIENT_CODE=your_code \
  -e ANGEL_PASSWORD=your_password \
  -e ANGEL_TOTP=your_totp \
  -v $(pwd)/logs:/app/BalanceWheel/logs \
  -v $(pwd)/data:/app/BalanceWheel/data \
  -v $(pwd)/config.json:/app/BalanceWheel/config.json \
  balance-wheel:latest
```

#### 3. Using Docker Compose

```bash
# Copy .env.example to .env and fill credentials
cp .env.example .env

# Start container
docker-compose up -d

# View logs
docker-compose logs -f balance-wheel

# Stop container
docker-compose down
```

#### 4. Schedule with Cron (Local Server)

```bash
# Add to crontab
crontab -e

# Add line:
15 9 * * * docker run --rm -e DRY_RUN=false [...] balance-wheel:latest >> /var/log/balance-wheel.log 2>&1
```

### Docker Troubleshooting

```bash
# View container logs
docker logs balance-wheel -f

# Access container shell
docker exec -it balance-wheel bash

# Check volumes
docker inspect balance-wheel | grep -A 5 Mounts

# Remove and rebuild
docker rm balance-wheel
docker build --no-cache -t balance-wheel:latest .
```

---

## Post-Deployment Checks

### Verification Checklist

- [ ] Bot initializes without errors
- [ ] Authentication successful
- [ ] Stock list loaded correctly
- [ ] Database tables created
- [ ] Logs being written
- [ ] Dry-run produces expected output
- [ ] Scheduled task/cron job is active
- [ ] Alerts/notifications configured (if applicable)

### Test Commands

```bash
# 1. Test configuration
python dev_tools.py --test config

# 2. Test environment
python dev_tools.py --test environment

# 3. Test authentication
python dev_tools.py --test auth

# 4. Run dry-run
python dev_tools.py --test dry-run

# 5. Check database
python dev_tools.py --test database
```

### Manual Test Run

```bash
# From project directory
python balance_wheel.py

# Expected sequence:
# 1. Bot initializes
# 2. Authentication successful
# 3. Connects to Angel One API
# 4. Fetches market data
# 5. Analyzes stocks
# 6. Logs observations
# 7. Executes dry-run trades (if triggered)
```

---

## Monitoring & Maintenance

### Daily Monitoring

```bash
# Check logs for errors
tail -20 logs/balance_wheel.log | grep ERROR

# Verify task execution
sqlite3 data/balance_wheel.db \
  "SELECT COUNT(*) FROM observations WHERE DATE(timestamp) = DATE('now');"

# Check available balance
# Log into Angel One web/app directly
```

### Weekly Maintenance

```bash
# Rotate old logs (automated, but verify)
ls -lah logs/

# Backup database
cp data/balance_wheel.db data/balance_wheel.db.backup

# Review database size
du -sh data/balance_wheel.db

# Generate summary report
python -c "from utils import generate_daily_report; \
print(generate_daily_report('data/balance_wheel.db'))"
```

### Monthly Maintenance

```bash
# Archive old observations
sqlite3 data/balance_wheel.db << EOF
CREATE TABLE observations_archive_2026_04 AS
SELECT * FROM observations 
WHERE DATE(timestamp) < '2026-05-01';

DELETE FROM observations 
WHERE DATE(timestamp) < '2026-05-01';
EOF

# Backup entire database
tar czf data/backup_$(date +%Y%m%d).tar.gz data/

# Check for configuration drift
git diff config.json  # If using version control

# Update dependencies (test in dry-run first)
pip install --upgrade -r requirements.txt
python dev_tools.py --test environment
```

### Emergency Procedures

**If bot stops running:**

```bash
# 1. Check logs
tail -100 logs/balance_wheel.log

# 2. Verify connectivity
ping google.com

# 3. Test authentication
python -c "from balance_wheel import BalanceWheelBot; \
bot = BalanceWheelBot(); bot.startup()"

# 4. Check scheduled task
# PythonAnywhere: Dashboard > Tasks
# Cron: sudo systemctl status cron

# 5. Restart manually
python balance_wheel.py
```

**If trading goes wrong:**

```bash
# 1. Immediately set DRY_RUN=true
nano config.json  # Set "dry_run": true

# 2. Stop scheduled execution
# PythonAnywhere: Disable task
# Cron: Comment out the line

# 3. Review recent trades
sqlite3 data/balance_wheel.db \
  "SELECT * FROM executed_trades ORDER BY timestamp DESC LIMIT 10;"

# 4. Contact Angel One support with order IDs
```

---

## Scaling Considerations

### For Multiple Bots

```bash
# Run different bot instances for different stock lists
python balance_wheel.py --config config_aggressive.json &
python balance_wheel.py --config config_conservative.json &

# Use Docker:
docker run --name balance-wheel-aggressive -e CONFIG=config_aggressive.json ...
docker run --name balance-wheel-conservative -e CONFIG=config_conservative.json ...
```

### Performance Optimization

```bash
# Reduce stocks for faster execution
config.json: Reduce target_stocks array

# Increase cycle interval
Adjust scheduler: Instead of every 15 min, run every 30 min

# Batch API calls
Modify MarketDataManager to fetch multiple quotes at once
```

### Cost Management

**PythonAnywhere:**
- Free tier: Limited to low-traffic
- Paid: $5-20/month depending on usage

**AWS Lambda:**
- Free tier: 1 million requests/month
- Estimated: $1-5/month for daily runs

**Docker (Self-hosted):**
- VPS: $5-20/month (Linode, DigitalOcean)
- Full control, higher responsibility

---

## Best Practices

1. **Always test in DRY-RUN first**
2. **Monitor logs daily**
3. **Use version control (git)**
4. **Backup database weekly**
5. **Keep credentials in environment variables**
6. **Set up alerts for errors**
7. **Document any configuration changes**
8. **Review trades weekly**
9. **Update dependencies monthly**
10. **Never hardcode credentials**

---

## Support Resources

- **Angel One API Docs:** https://www.angelbroking.com/api-docs/
- **SmartAPI Python:** https://github.com/angelbroking/smartapi-python
- **PythonAnywhere Help:** https://www.pythonanywhere.com/help/
- **AWS Lambda Docs:** https://docs.aws.amazon.com/lambda/
- **Docker Docs:** https://docs.docker.com/

---

**Last Updated:** May 10, 2026  
**Status:** Production Ready
