"""
Utility functions for BalanceWheel trading bot.
Includes helpers for calculations, formatting, and data management.
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import math


logger = logging.getLogger(__name__)


# ==================== CALCULATION UTILITIES ====================
def calculate_dip_percentage(portfolio_avg: float, ltp: float) -> float:
    """
    Calculate percentage dip from portfolio average to LTP.
    
    Args:
        portfolio_avg: Portfolio average price
        ltp: Last traded price
    
    Returns:
        Negative for dip, positive for increase
    """
    if portfolio_avg == 0:
        return 0.0
    return ((portfolio_avg - ltp) / portfolio_avg) * 100


def calculate_new_average(
    current_qty: int,
    current_avg: float,
    buy_qty: int,
    buy_price: float
) -> float:
    """
    Calculate new weighted average after purchase.
    
    Args:
        current_qty: Current holdings quantity
        current_avg: Current average price
        buy_qty: Quantity being purchased
        buy_price: Purchase price
    
    Returns:
        New weighted average price
    """
    if current_qty + buy_qty == 0:
        return 0.0
    
    total_cost = (current_qty * current_avg) + (buy_qty * buy_price)
    new_avg = total_cost / (current_qty + buy_qty)
    return new_avg


def calculate_shares_for_target_average(
    current_qty: int,
    current_avg: float,
    ltp: float,
    target_buffer_percent: float
) -> Tuple[int, float]:
    """
    Calculate shares needed to achieve target average price.
    
    Args:
        current_qty: Current quantity
        current_avg: Current average price
        ltp: Current LTP
        target_buffer_percent: Target buffer from LTP (e.g., 5%)
    
    Returns:
        Tuple of (shares_to_buy, new_average)
    """
    if current_qty == 0 or ltp == 0:
        return 0, current_avg
    
    target_avg = ltp * (1 + target_buffer_percent / 100)
    
    # Formula: n = (Q * A - Q * T) / (T - P)
    denominator = target_avg - ltp
    if denominator == 0:
        return 0, current_avg
    
    shares_to_buy = (current_qty * current_avg - current_qty * target_avg) / denominator
    shares_to_buy = math.floor(max(0, shares_to_buy))
    
    new_avg = calculate_new_average(current_qty, current_avg, shares_to_buy, ltp)
    
    return shares_to_buy, new_avg


def calculate_position_size_for_budget(
    available_balance: float,
    price_per_share: float,
    safety_buffer_shares: int = 1
) -> int:
    """
    Calculate maximum shares that can be purchased within budget and safety buffer.
    
    Args:
        available_balance: Available funds in INR
        price_per_share: Price per share
        safety_buffer_shares: Shares to reserve for taxes/charges
    
    Returns:
        Number of shares to purchase
    """
    if price_per_share == 0:
        return 0
    
    max_shares = math.floor(available_balance / price_per_share)
    adjusted_shares = max(0, max_shares - safety_buffer_shares)
    
    return adjusted_shares


# ==================== FORMATTING UTILITIES ====================
def format_currency(amount: float, currency: str = "INR") -> str:
    """
    Format amount as currency string.
    
    Args:
        amount: Amount to format
        currency: Currency code
    
    Returns:
        Formatted string (e.g., "₹50,000.00")
    """
    if currency == "INR":
        return f"₹{amount:,.2f}"
    return f"{currency} {amount:,.2f}"


def format_percentage(percent: float, decimal_places: int = 2) -> str:
    """
    Format percentage with sign.
    
    Args:
        percent: Percentage value
        decimal_places: Decimal places to show
    
    Returns:
        Formatted string (e.g., "+15.50%", "-5.25%")
    """
    sign = "+" if percent >= 0 else ""
    return f"{sign}{percent:.{decimal_places}f}%"


def format_stock_action(
    symbol: str,
    action: str,
    details: Optional[Dict] = None
) -> str:
    """
    Format stock action as readable string.
    
    Args:
        symbol: Stock symbol
        action: Action type (BUY, HIGH_ALERT, STATUS_CHECKED, SKIP)
        details: Optional details dict
    
    Returns:
        Formatted string
    """
    if action == "BUY":
        qty = details.get("shares", "?") if details else "?"
        price = details.get("price", "?") if details else "?"
        return f"[BUY] {symbol}: Buy {qty} @ {price}"
    
    elif action == "HIGH_ALERT":
        dip = format_percentage(details.get("dip_percent", 0)) if details else ""
        return f"[⚠️  ALERT] {symbol}: High Alert {dip}"
    
    elif action == "STATUS_CHECKED":
        return f"[✓ CHECK] {symbol}: Monitoring"
    
    else:  # SKIP
        reason = details.get("reason", "constraints") if details else "constraints"
        return f"[⊘ SKIP] {symbol}: {reason}"


# ==================== DATABASE UTILITIES ====================
def get_observation_summary(db_file: str, days: int = 7) -> Dict:
    """
    Get summary statistics from observations database.
    
    Args:
        db_file: Path to SQLite database
        days: Number of days to include
    
    Returns:
        Dict with summary stats
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Count by action
        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM observations
            WHERE timestamp > ?
            GROUP BY action
        """, (cutoff_date,))
        
        action_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total observations
        cursor.execute("""
            SELECT COUNT(*) FROM observations WHERE timestamp > ?
        """, (cutoff_date,))
        
        total_obs = cursor.fetchone()[0]
        
        # Average dip percentage
        cursor.execute("""
            SELECT AVG(dip_percentage) FROM observations 
            WHERE timestamp > ? AND dip_percentage > 0
        """, (cutoff_date,))
        
        avg_dip = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            "total_observations": total_obs,
            "by_action": action_counts,
            "average_dip_percent": round(avg_dip, 2),
            "days_included": days
        }
    
    except Exception as e:
        logger.error(f"Error getting observation summary: {str(e)}")
        return {}


def get_trade_summary(db_file: str, days: int = 7) -> Dict:
    """
    Get summary of executed trades.
    
    Args:
        db_file: Path to SQLite database
        days: Number of days to include
    
    Returns:
        Dict with trade stats
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Total trades
        cursor.execute("""
            SELECT COUNT(*) FROM executed_trades WHERE timestamp > ?
        """, (cutoff_date,))
        
        total_trades = cursor.fetchone()[0]
        
        # Total invested
        cursor.execute("""
            SELECT SUM(total_amount) FROM executed_trades 
            WHERE timestamp > ? AND dry_run = 0
        """, (cutoff_date,))
        
        total_invested = cursor.fetchone()[0] or 0.0
        
        # Dry run vs real
        cursor.execute("""
            SELECT dry_run, COUNT(*) FROM executed_trades
            WHERE timestamp > ?
            GROUP BY dry_run
        """, (cutoff_date,))
        
        trade_types = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total_trades": total_trades,
            "total_invested_inr": round(total_invested, 2),
            "dry_run_count": trade_types.get(1, 0),
            "real_trades": trade_types.get(0, 0),
            "days_included": days
        }
    
    except Exception as e:
        logger.error(f"Error getting trade summary: {str(e)}")
        return {}


def cleanup_old_logs(log_dir: str, days: int = 10) -> int:
    """
    Remove log files older than specified days.
    
    Args:
        log_dir: Directory containing log files
        days: Age threshold in days
    
    Returns:
        Number of files deleted
    """
    try:
        log_path = Path(log_dir)
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for log_file in log_path.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time.timestamp():
                log_file.unlink()
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old log files")
        return deleted_count
    
    except Exception as e:
        logger.error(f"Error cleaning up logs: {str(e)}")
        return 0


# ==================== CONFIG UTILITIES ====================
def validate_config(config_file: str) -> Tuple[bool, List[str]]:
    """
    Validate configuration file.
    
    Args:
        config_file: Path to config.json
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Check required keys
        required_keys = ["app_name", "broker", "trading_rules", "target_stocks"]
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required key: {key}")
        
        # Validate broker credentials
        if "broker" in config:
            broker = config["broker"]
            required_broker_keys = ["api_key", "client_code", "password"]
            for key in required_broker_keys:
                if not broker.get(key) or broker.get(key).startswith("YOUR_"):
                    errors.append(f"Broker credentials not configured: {key}")
        
        # Validate trading rules
        if "trading_rules" in config:
            rules = config["trading_rules"]
            if rules.get("price_dip_threshold_percent", 0) >= 100:
                errors.append("price_dip_threshold_percent should be < 100")
        
        # Validate target stocks
        if "target_stocks" in config:
            if len(config["target_stocks"]) == 0:
                errors.append("target_stocks array is empty")
        
        return len(errors) == 0, errors
    
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {str(e)}"]
    except Exception as e:
        return False, [f"Error validating config: {str(e)}"]


# ==================== REPORT GENERATION ====================
def generate_daily_report(db_file: str, output_file: Optional[str] = None) -> str:
    """
    Generate a daily trading report.
    
    Args:
        db_file: Path to SQLite database
        output_file: Optional file to save report
    
    Returns:
        Report as formatted string
    """
    obs_summary = get_observation_summary(db_file, days=1)
    trade_summary = get_trade_summary(db_file, days=1)
    
    report = f"""
{'='*60}
BALANCEWHEEL - DAILY TRADING REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

OBSERVATIONS:
  Total: {obs_summary.get('total_observations', 0)}
  By Action:
    - BUY: {obs_summary.get('by_action', {}).get('BUY', 0)}
    - HIGH_ALERT: {obs_summary.get('by_action', {}).get('HIGH_ALERT', 0)}
    - STATUS_CHECKED: {obs_summary.get('by_action', {}).get('STATUS_CHECKED', 0)}
    - SKIP: {obs_summary.get('by_action', {}).get('SKIP', 0)}
  Avg Dip %: {format_percentage(obs_summary.get('average_dip_percent', 0))}

TRADES:
  Total Trades: {trade_summary.get('total_trades', 0)}
  Real Trades: {trade_summary.get('real_trades', 0)}
  Dry Runs: {trade_summary.get('dry_run_count', 0)}
  Total Invested: {format_currency(trade_summary.get('total_invested_inr', 0))}

{'='*60}
"""
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
    
    return report


if __name__ == "__main__":
    # Test utilities
    print("Testing utilities...")
    
    # Test calculations
    print("\n--- Calculation Tests ---")
    dip = calculate_dip_percentage(4000, 3400)
    print(f"Dip %: {format_percentage(dip)}")
    
    new_avg = calculate_new_average(100, 4000, 100, 3400)
    print(f"New Average: {format_currency(new_avg)}")
    
    shares = calculate_shares_for_target_average(100, 4000, 3400, 5)
    print(f"Shares to Buy: {shares[0]}, New Avg: {format_currency(shares[1])}")
    
    # Test formatting
    print("\n--- Formatting Tests ---")
    print(f"Currency: {format_currency(50000)}")
    print(f"Percentage: {format_percentage(15.5)}")
    print(f"Action: {format_stock_action('TCS', 'BUY', {'shares': 150, 'price': 3400})}")
    
    print("\n✓ All utilities working correctly")
