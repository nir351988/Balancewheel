"""Tests for portfolio-only cycle and symbol normalization."""

import unittest
import sys

sys.path.insert(0, "..")

from balance_wheel import normalize_equity_symbol, BalanceWheelBot


class TestNormalizeEquitySymbol(unittest.TestCase):
    def test_strips_eq_suffix(self):
        self.assertEqual(normalize_equity_symbol("HCLTECH-EQ", ""), "HCLTECH")

    def test_keeps_hyphenated_symbols(self):
        self.assertEqual(normalize_equity_symbol("BAJAJ-AUTO-EQ", ""), "BAJAJ-AUTO")

    def test_symbol_fallback(self):
        self.assertEqual(normalize_equity_symbol("", "hdfcbank"), "HDFCBANK")


class TestPortfolioMetadata(unittest.TestCase):
    def setUp(self):
        self.bot = BalanceWheelBot.__new__(BalanceWheelBot)
        self.bot.config = {
            "target_stocks": [
                {"symbol": "HDFCBANK", "exchange": "NSE", "sector": "Banking", "category": "Sector Leader", "priority": 1}
            ]
        }

    def test_watchlist_match(self):
        stock = self.bot._stock_metadata_for_holding("HDFCBANK", {"exchange": "NSE"})
        self.assertEqual(stock["sector"], "Banking")
        self.assertTrue(stock["on_watchlist"])

    def test_portfolio_only_holding(self):
        stock = self.bot._stock_metadata_for_holding("BAJAJFINSV", {"exchange": "NSE"})
        self.assertEqual(stock["sector"], "Portfolio")
        self.assertFalse(stock["on_watchlist"])


if __name__ == "__main__":
    unittest.main()
