#!/usr/bin/env python
"""
Development & Testing Script for BalanceWheel Bot
Run tests, check configuration, and perform diagnostics.

Usage:
    python dev_tools.py --help
    python dev_tools.py --test auth
    python dev_tools.py --validate-config
    python dev_tools.py --check-db
"""

import os
import sys
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

from dotenv import load_dotenv

# Load .env from project root (same as balance_wheel.py)
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DevTools:
    """Development and testing tools for BalanceWheel."""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = None
        self.load_config()
    
    def load_config(self) -> bool:
        """Load configuration file and merge .env overrides (same as BalanceWheelBot)."""
        try:
            with open(self.config_file, 'r') as f:
                raw = json.load(f)
            from balance_wheel import BalanceWheelBot

            self.config = BalanceWheelBot.__new__(BalanceWheelBot)._apply_env_overrides(raw)
            logger.info(f"✓ Config loaded: {self.config_file} (with .env overrides)")
            return True
        except FileNotFoundError:
            logger.error(f"✗ Config file not found: {self.config_file}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"✗ Invalid JSON in config: {str(e)}")
            return False
    
    def validate_config(self) -> bool:
        """Validate configuration completeness."""
        logger.info("\n" + "="*60)
        logger.info("VALIDATING CONFIGURATION")
        logger.info("="*60)
        
        if not self.config:
            logger.error("Config not loaded")
            return False
        
        errors = []
        
        # Check app metadata
        logger.info("\n[1] App Metadata:")
        if "app_name" in self.config:
            logger.info(f"  ✓ App: {self.config['app_name']}")
        else:
            errors.append("Missing app_name")
        
        if "version" in self.config:
            logger.info(f"  ✓ Version: {self.config['version']}")
        
        # Check broker config
        logger.info("\n[2] Broker Configuration:")
        if "broker" in self.config:
            broker = self.config["broker"]
            for key in ["api_key", "client_code", "password"]:
                if key in broker:
                    value = broker[key]
                    if not value or str(value).startswith("YOUR_"):
                        errors.append(f"Broker {key} not configured (.env or config.json)")
                        logger.warning(f"  ⚠ {key}: NOT SET")
                    else:
                        logger.info(f"  ✓ {key}: configured (via .env or config)")
            if os.getenv("ANGEL_TOTP_SECRET") or os.getenv("ANGEL_TOTP"):
                logger.info("  ✓ TOTP: configured via .env")
            elif broker.get("totp", "000000") == "000000":
                errors.append("TOTP not configured")
                logger.warning("  ⚠ totp: NOT SET")
        
        # Check trading rules
        logger.info("\n[3] Trading Rules:")
        if "trading_rules" in self.config:
            rules = self.config["trading_rules"]
            required_rules = [
                "price_dip_threshold_percent",
                "target_average_buffer_percent",
                "minimum_balance_required_inr",
                "cooldown_days"
            ]
            for rule in required_rules:
                if rule in rules:
                    value = rules[rule]
                    logger.info(f"  ✓ {rule}: {value}")
                else:
                    errors.append(f"Missing rule: {rule}")
        
        # Check target stocks
        logger.info("\n[4] Target Stocks:")
        if "target_stocks" in self.config:
            stocks = self.config["target_stocks"]
            logger.info(f"  ✓ Stocks defined: {len(stocks)}")
            
            sectors = set()
            for stock in stocks:
                sectors.add(stock.get("sector", "Unknown"))
            
            logger.info(f"  ✓ Sectors: {', '.join(sorted(sectors))}")
            
            if len(stocks) < 5:
                logger.warning(f"  ⚠ Only {len(stocks)} stocks defined (recommend >= 5)")
        else:
            errors.append("No target stocks configured")
        
        # Summary
        logger.info("\n" + "="*60)
        if errors:
            logger.error(f"✗ VALIDATION FAILED ({len(errors)} errors)")
            for i, error in enumerate(errors, 1):
                logger.error(f"  {i}. {error}")
            return False
        else:
            logger.info("✓ VALIDATION PASSED")
            return True
    
    def test_account(self) -> bool:
        """Show demat balance and holdings (works outside market hours)."""
        logger.info("\n" + "=" * 60)
        logger.info("DMAT ACCOUNT CHECK")
        logger.info("=" * 60)

        try:
            from balance_wheel import BalanceWheelBot

            bot = BalanceWheelBot(self.config_file)
            if not bot.startup():
                logger.error("Startup failed — cannot fetch account")
                return False
            ok = bot.log_dmat_account_summary()
            bot.shutdown("Account check done")
            return ok
        except Exception as e:
            logger.error(f"Account check failed: {e}")
            return False

    def test_auth(self) -> bool:
        """Test Angel One authentication."""
        logger.info("\n" + "="*60)
        logger.info("TESTING AUTHENTICATION")
        logger.info("="*60)
        
        if not self.config:
            logger.error("Config not loaded")
            return False
        
        try:
            from auth_manager import AngelOneAuthManager
            
            broker = self.config["broker"]
            if broker.get("api_key", "").startswith("YOUR_") or broker.get("client_code", "").startswith("YOUR_"):
                logger.error(
                    "Broker credentials still placeholders — check .env in ~/BalanceWheel "
                    "(ANGEL_API_KEY, ANGEL_CLIENT_CODE, ANGEL_PIN, ANGEL_TOTP_SECRET)"
                )
                return False

            logger.info("\nAttempting authentication...")
            logger.info(f"  Client: {broker['client_code'][:2]}*** (from .env)")

            auth = AngelOneAuthManager(
                api_key=broker["api_key"],
                client_code=broker["client_code"],
                password=broker["password"],
                totp=broker.get("totp", "000000")
            )
            
            success, msg = auth.authenticate()
            
            if success:
                logger.info(f"\n✓ AUTHENTICATION SUCCESSFUL")
                logger.info(f"  Message: {msg}")
                logger.info(f"  Token valid until: {auth.token_expiry}")
                return True
            else:
                logger.error(f"\n✗ AUTHENTICATION FAILED")
                logger.error(f"  Error: {msg}")
                return False
        
        except ImportError:
            logger.error("✗ Could not import auth_manager")
            return False
        except Exception as e:
            logger.error(f"✗ Exception: {str(e)}")
            return False
    
    def check_environment(self) -> bool:
        """Check Python environment and dependencies."""
        logger.info("\n" + "="*60)
        logger.info("CHECKING ENVIRONMENT")
        logger.info("="*60)
        
        # Python version
        import platform
        logger.info(f"\nPython: {platform.python_version()}")
        
        # Required packages
        logger.info("\nChecking dependencies:")
        required = [
            "requests",
            "pyotp",
        ]
        optional = [
            "pandas",
        ]
        
        missing = []
        for package in required:
            try:
                __import__(package)
                logger.info(f"  ✓ {package}")
            except ImportError:
                logger.warning(f"  ✗ {package} - NOT INSTALLED")
                missing.append(package)

        try:
            from smartapi_client import SmartConnect
            import inspect
            sig = str(inspect.signature(SmartConnect.generateSession))
            if "totp" in sig:
                logger.info(f"  ✓ SmartApi SDK (generateSession{sig})")
            else:
                logger.warning("  ✗ SmartApi SDK looks like a stub (no totp param)")
                missing.append("smartapi-python")
        except ImportError as e:
            logger.warning(f"  ✗ SmartApi SDK - {e}")
            missing.append("smartapi-python")

        for package in optional:
            try:
                __import__(package)
                logger.info(f"  ✓ {package} (optional)")
            except ImportError:
                logger.info(f"  ○ {package} (optional, not installed)")
        
        # Directories
        logger.info("\nChecking directories:")
        dirs = ["logs", "data", "tests"]
        for dir_name in dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                logger.info(f"  ✓ {dir_name}/")
            else:
                logger.warning(f"  ⚠ {dir_name}/ - MISSING (will create)")
                dir_path.mkdir(exist_ok=True)
        
        if missing:
            logger.warning(f"\n⚠ Missing packages: {', '.join(missing)}")
            logger.info("  Run: pip install -r requirements-runtime.txt")
            return False
        
        logger.info("\n✓ ENVIRONMENT OK")
        return True
    
    def check_database(self) -> bool:
        """Check database status."""
        logger.info("\n" + "="*60)
        logger.info("CHECKING DATABASE")
        logger.info("="*60)
        
        db_file = self.config.get("database", {}).get("file", "data/balance_wheel.db")
        logger.info(f"\nDatabase file: {db_file}")
        
        db_path = Path(db_file)
        if not db_path.exists():
            logger.warning(f"  ⚠ Database does not exist (will be created)")
            return True
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
            """)
            
            tables = cursor.fetchall()
            logger.info(f"\n  Tables: {len(tables)}")
            for table in tables:
                logger.info(f"    • {table[0]}")
            
            # Check observations
            if any(t[0] == "observations" for t in tables):
                cursor.execute("SELECT COUNT(*) FROM observations")
                obs_count = cursor.fetchone()[0]
                logger.info(f"\n  Observations: {obs_count}")
                
                if obs_count > 0:
                    cursor.execute("""
                        SELECT MIN(timestamp), MAX(timestamp) FROM observations
                    """)
                    min_ts, max_ts = cursor.fetchone()
                    logger.info(f"    • First: {min_ts}")
                    logger.info(f"    • Latest: {max_ts}")
            
            # Check trades
            if any(t[0] == "executed_trades" for t in tables):
                cursor.execute("SELECT COUNT(*) FROM executed_trades")
                trade_count = cursor.fetchone()[0]
                logger.info(f"\n  Executed Trades: {trade_count}")
            
            conn.close()
            logger.info("\n✓ DATABASE OK")
            return True
        
        except Exception as e:
            logger.error(f"✗ Database error: {str(e)}")
            return False
    
    def check_logs(self) -> bool:
        """Check log files."""
        logger.info("\n" + "="*60)
        logger.info("CHECKING LOGS")
        logger.info("="*60)
        
        log_dir = Path("logs")
        if not log_dir.exists():
            logger.warning("  ⚠ logs/ directory not found")
            return False
        
        log_files = list(log_dir.glob("balance_wheel.log*"))
        
        if not log_files:
            logger.warning("  ⚠ No log files found")
            return False
        
        logger.info(f"\nFound {len(log_files)} log files:")
        for log_file in sorted(log_files):
            size_mb = log_file.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            logger.info(f"  • {log_file.name} ({size_mb:.2f} MB, {mtime})")
        
        # Show recent entries
        main_log = log_dir / "balance_wheel.log"
        if main_log.exists():
            logger.info("\nRecent log entries:")
            with open(main_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    logger.info(f"  {line.rstrip()}")
        
        logger.info("\n✓ LOGS OK")
        return True
    
    def test_dry_run(self) -> bool:
        """Run bot in dry-run mode."""
        logger.info("\n" + "="*60)
        logger.info("TESTING DRY RUN")
        logger.info("="*60)
        
        try:
            # Ensure dry_run is true
            self.config["dry_run"] = True
            
            from balance_wheel import BalanceWheelBot
            
            logger.info("\nInitializing bot in dry-run mode...")
            bot = BalanceWheelBot(self.config_file)
            
            if not bot.startup():
                logger.error("✗ Startup failed")
                return False
            
            logger.info("\n✓ Bot startup successful")
            logger.info("\nRunning single cycle...")
            bot.run_cycle()
            
            bot.shutdown("Dry-run test completed")
            logger.info("\n✓ DRY RUN TEST PASSED")
            return True
        
        except Exception as e:
            logger.error(f"✗ Dry-run failed: {str(e)}")
            return False
    
    def run_tests(self, test_name: str = "all") -> bool:
        """Run all tests."""
        logger.info("\n" + "="*70)
        logger.info("BALANCEWHEEL DEVELOPMENT TEST SUITE")
        logger.info("="*70)
        
        tests = {
            "environment": self.check_environment,
            "config": self.validate_config,
            "database": self.check_database,
            "logs": self.check_logs,
            "auth": self.test_auth,
            "dry-run": self.test_dry_run,
            "account": self.test_account,
        }
        
        if test_name == "all":
            test_keys = ["environment", "config", "database", "logs", "auth", "account"]
        else:
            test_keys = [test_name] if test_name in tests else []
        
        if not test_keys:
            logger.error(f"Unknown test: {test_name}")
            return False
        
        results = {}
        for test_key in test_keys:
            try:
                results[test_key] = tests[test_key]()
            except Exception as e:
                logger.error(f"Error in {test_key}: {str(e)}")
                results[test_key] = False
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_key, passed_flag in results.items():
            status = "✓ PASS" if passed_flag else "✗ FAIL"
            logger.info(f"{status}: {test_key}")
        
        logger.info(f"\nResult: {passed}/{total} tests passed")
        logger.info("="*70)
        
        return all(results.values())


def main():
    parser = argparse.ArgumentParser(
        description="BalanceWheel Development & Testing Tools"
    )
    
    parser.add_argument(
        "--test",
        choices=["all", "environment", "config", "database", "logs", "auth", "account", "dry-run"],
        default="all",
        help="Test to run (default: all)"
    )
    
    parser.add_argument(
        "--config",
        default="config.json",
        help="Configuration file (default: config.json)"
    )
    
    args = parser.parse_args()
    
    # Run development tools
    dev = DevTools(config_file=args.config)
    success = dev.run_tests(test_name=args.test)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
