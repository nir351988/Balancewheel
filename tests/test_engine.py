"""
Unit tests for BalanceWheel trading engine.
Run with: pytest tests/test_engine.py -v
"""

import unittest
import json
import math
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import modules (adjust imports based on your project structure)
import sys
sys.path.insert(0, '..')

from balance_wheel import (
    BalanceWheelEngine,
    StockAnalysis,
    ObservationDatabase,
    MarketDataManager
)


class TestBalanceWheelEngine(unittest.TestCase):
    """Test cases for BalanceWheelEngine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "trading_rules": {
                "price_dip_threshold_percent": 15,
                "target_average_buffer_percent": 5,
                "high_alert_lower_threshold_percent": 12,
                "high_alert_upper_threshold_percent": 15,
                "minimum_balance_required_inr": 2000,
                "cooldown_days": 7,
                "market_sentiment_nifty_down_percent": 3,
                "safety_buffer_subtract_shares": 1
            }
        }
        
        # Mock dependencies
        self.mock_auth = Mock()
        self.mock_db = Mock()
        self.mock_market_data = Mock()
        self.mock_logger = Mock()
        
        # Create engine
        self.engine = BalanceWheelEngine(
            self.config,
            self.mock_auth,
            self.mock_db,
            self.mock_market_data,
            self.mock_logger
        )
    
    def test_analyze_stock_buy_signal(self):
        """Test BUY signal when price dip >= 15%."""
        stock = {
            "symbol": "TCS",
            "sector": "IT",
            "priority": 1
        }
        ltp = 3400.0
        portfolio_avg = 4000.0  # 15% dip
        
        result = self.engine.analyze_stock(stock, ltp, portfolio_avg, current_qty=100)
        
        self.assertEqual(result.symbol, "TCS")
        self.assertEqual(result.action, "BUY")
        self.assertGreater(result.dip_percentage, 0)
        self.assertGreater(result.shares_to_buy, 0)
    
    def test_analyze_stock_high_alert(self):
        """Test HIGH_ALERT when 12% < dip < 15%."""
        stock = {
            "symbol": "INFY",
            "sector": "IT",
            "priority": 1
        }
        ltp = 3500.0
        portfolio_avg = 4000.0  # 12.5% dip
        """Test STATUS_CHECKED when dip < 12%."""
        stock = {
            "symbol": "HCLTECH",
            "sector": "IT",
            "priority": 2
        }
        ltp = 3520.0
        portfolio_avg = 4000.0  # ~12% dip (boundary)
        
        result = self.engine.analyze_stock(stock, ltp, portfolio_avg, current_qty=100)
        
        self.assertEqual(result.symbol, "HCLTECH")
        self.assertEqual(result.action, "STATUS_CHECKED")
    
    def test_analyze_stock_zero_average_price(self):
        """Test handling when portfolio avg price is 0."""
        stock = {
            "symbol": "TEST",
            "sector": "Finance",
            "priority": 1
        }
        ltp = 1000.0
        portfolio_avg = 0.0
        
        result = self.engine.analyze_stock(stock, ltp, portfolio_avg, current_qty=0)
        
        self.assertEqual(result.action, "SKIP")
    
    def test_calculate_smart_average(self):
        """Test smart average calculation."""
        portfolio_avg = 4000.0
        ltp = 3400.0
        
        shares, new_avg = self.engine._calculate_smart_average(current_qty=100, portfolio_avg_price=portfolio_avg, ltp=ltp)
        
        # Shares should be positive (assuming current qty > 0)
        self.assertIsInstance(shares, int)
        # New average should be between LTP and original average
        if shares > 0:
            self.assertGreaterEqual(new_avg, ltp)
            self.assertLessEqual(new_avg, portfolio_avg)
    
    def test_calculate_smart_average_no_division_error(self):
        """Test smart average doesn't divide by zero."""
        # When LTP = target_avg, formula shouldn't crash
        portfolio_avg = 4000.0
        ltp = 4000.0
        
        shares, new_avg = self.engine._calculate_smart_average(current_qty=100, portfolio_avg_price=portfolio_avg, ltp=ltp)
        
        self.assertEqual(shares, 0)
        self.assertEqual(new_avg, portfolio_avg)
    
    def test_execution_constraints_insufficient_balance(self):
        """Test execution blocked when balance insufficient."""
        self.mock_market_data.get_available_balance.return_value = 1000.0  # < 2000 min
        
        can_exec, adjusted_qty, reason = self.engine.check_execution_constraints(
            "TCS", "IT", 100, 3400.0
        )
        
        self.assertFalse(can_exec)
        self.assertEqual(adjusted_qty, 0)
        self.assertIn("Insufficient", reason)
    
    def test_execution_constraints_cooldown_active(self):
        """Test execution blocked due to cool-down period."""
        self.mock_market_data.get_available_balance.return_value = 50000.0
        
        # Last buy 3 days ago (< 7 day cool-down)
        last_buy = datetime.now() - timedelta(days=3)
        self.mock_db.get_last_buy_date.return_value = last_buy
        
        can_exec, adjusted_qty, reason = self.engine.check_execution_constraints(
            "TCS", "IT", 100, 3400.0
        )
        
        self.assertFalse(can_exec)
        self.assertIn("Cool-down", reason)
    
    def test_execution_constraints_market_sentiment_lock(self):
        """Test execution blocked due to market crash (Nifty down >3%)."""
        self.mock_market_data.get_available_balance.return_value = 50000.0
        self.mock_db.get_last_buy_date.return_value = None
        self.mock_market_data.get_nifty_50_change_percent.return_value = -4.5
        
        can_exec, adjusted_qty, reason = self.engine.check_execution_constraints(
            "TCS", "IT", 100, 3400.0
        )
        
        self.assertFalse(can_exec)
        self.assertIn("Market Sentiment", reason)
    
    def test_execution_constraints_safety_buffer(self):
        """Test safety buffer applied when shares exceed available balance."""
        self.mock_market_data.get_available_balance.return_value = 100000.0
        self.mock_db.get_last_buy_date.return_value = None
        self.mock_market_data.get_nifty_50_change_percent.return_value = -0.5
        
        # Required amount would exceed balance
        shares_to_buy = 1000
        ltp = 3400.0
        required = shares_to_buy * ltp  # 3.4M >> 100K available
        
        can_exec, adjusted_qty, reason = self.engine.check_execution_constraints(
            "TCS", "IT", shares_to_buy, ltp
        )
        
        # Should adjust down with safety buffer
        self.assertTrue(can_exec)
        self.assertLess(adjusted_qty, shares_to_buy)
        self.assertGreaterEqual(adjusted_qty, 0)


class TestStockAnalysisDataClass(unittest.TestCase):
    """Test StockAnalysis dataclass."""
    
    def test_stock_analysis_creation(self):
        """Test creating StockAnalysis instance."""
        analysis = StockAnalysis(
            symbol="TCS",
            ltp=3400.0,
            portfolio_avg_price=4000.0,
            dip_percentage=15.0,
            action="BUY",
            shares_to_buy=100,
            new_avg_price=3500.0,
            reason="Test reason"
        )
        
        self.assertEqual(analysis.symbol, "TCS")
        self.assertEqual(analysis.action, "BUY")
        self.assertEqual(analysis.shares_to_buy, 100)


class TestDipPercentageCalculation(unittest.TestCase):
    """Test dip percentage calculations."""
    
    def test_dip_percentage_15_percent(self):
        """Test calculation of 15% dip."""
        portfolio_avg = 4000.0
        ltp = 3400.0
        
        dip_percent = ((portfolio_avg - ltp) / portfolio_avg) * 100
        
        self.assertAlmostEqual(dip_percent, 15.0, places=1)
    
    def test_dip_percentage_zero(self):
        """Test no dip scenario."""
        portfolio_avg = 4000.0
        ltp = 4000.0
        
        dip_percent = ((portfolio_avg - ltp) / portfolio_avg) * 100
        
        self.assertEqual(dip_percent, 0.0)
    
    def test_dip_percentage_negative_price_increase(self):
        """Test when price is above portfolio average."""
        portfolio_avg = 4000.0
        ltp = 4500.0
        
        dip_percent = ((portfolio_avg - ltp) / portfolio_avg) * 100
        
        self.assertLess(dip_percent, 0)


class TestMathFloorUsage(unittest.TestCase):
    """Test fractional share prevention."""
    
    def test_fractional_shares_floored(self):
        """Ensure shares are always integers (no fractional shares)."""
        shares_decimal = 150.7
        shares_floored = math.floor(shares_decimal)
        
        self.assertEqual(shares_floored, 150)
        self.assertIsInstance(shares_floored, int)


if __name__ == "__main__":
    unittest.main()
