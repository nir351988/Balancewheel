"""
BalanceWheel - Mean-Reversion & Smart Averaging Trading Bot
Main execution engine for Angel One (SmartAPI) platform.
Monitors target stocks and executes precision buy orders during dips.
"""

import json
import sqlite3
import logging
import logging.handlers
import math
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Third-party imports (install via requirements.txt)
import requests
from smartapi_client import SmartConnect
from dotenv import load_dotenv
import pyotp

# Local imports
from auth_manager import AngelOneAuthManager

# Load environment variables from .env if present
load_dotenv(dotenv_path=Path(__file__).parent / ".env")


# ==================== LOGGING SETUP ====================
def setup_logger(config: Dict) -> logging.Logger:
    """
    Setup logging with RotatingFileHandler and StreamHandler.
    Preserves last 10 days of logs.
    """
    log_config = config["logging"]
    log_file = log_config["log_file"]
    
    # Create logs directory if not exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("BalanceWheel")
    logger.setLevel(getattr(logging, log_config["level"]))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # RotatingFileHandler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=log_config["max_bytes"],
        backupCount=log_config["backup_count"]
    )
    file_handler.setLevel(logging.DEBUG)
    
    # StreamHandler for terminal output
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    
    # Formatter with timezone
    class TimezoneFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            ct = self.converter(record.created)
            if datefmt:
                s = time.strftime(datefmt, ct)
                # Add timezone info
                import datetime
                dt = datetime.datetime.fromtimestamp(record.created)
                s += f" {dt.astimezone().tzname()}"
                return s
            else:
                return super().formatTime(record, datefmt)
    
    formatter = TimezoneFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return logger


# ==================== DATA CLASSES ====================
@dataclass
class StockAnalysis:
    """Result of stock analysis."""
    symbol: str
    ltp: float
    portfolio_avg_price: float
    dip_percentage: float
    action: str  # "BUY", "HIGH_ALERT", "STATUS_CHECKED", "SKIP"
    shares_to_buy: int = 0
    new_avg_price: Optional[float] = None
    reason: str = ""


# ==================== DATABASE MANAGER ====================
class ObservationDatabase:
    """Manages persistent observations in SQLite."""
    
    def __init__(self, db_file: str, logger: logging.Logger):
        self.db_file = db_file
        self.logger = logger
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        try:
            Path(self.db_file).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    ltp REAL NOT NULL,
                    portfolio_avg_price REAL NOT NULL,
                    dip_percentage REAL NOT NULL,
                    action TEXT NOT NULL,
                    shares_to_buy INTEGER,
                    new_avg_price REAL,
                    reason TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS executed_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    order_id TEXT,
                    dry_run BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.commit()
            conn.close()
            self.logger.info(f"Database initialized: {self.db_file}")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
    
    def log_observation(self, analysis: StockAnalysis) -> None:
        """Log stock analysis observation."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO observations 
                (timestamp, symbol, ltp, portfolio_avg_price, dip_percentage, 
                 action, shares_to_buy, new_avg_price, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                analysis.symbol,
                analysis.ltp,
                analysis.portfolio_avg_price,
                analysis.dip_percentage,
                analysis.action,
                analysis.shares_to_buy,
                analysis.new_avg_price,
                analysis.reason
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to log observation: {str(e)}")
    
    def log_trade(self, symbol: str, qty: int, price: float, order_id: Optional[str], dry_run: bool) -> None:
        """Log executed trade."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            total_amount = qty * price
            cursor.execute("""
                INSERT INTO executed_trades 
                (timestamp, symbol, quantity, price, total_amount, order_id, dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                symbol,
                qty,
                price,
                total_amount,
                order_id,
                dry_run
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to log trade: {str(e)}")
    
    def get_last_buy_date(self, symbol: str) -> Optional[datetime]:
        """Get last buy date for a symbol (for cool-down logic)."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp FROM executed_trades 
                WHERE symbol = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (symbol,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return datetime.fromisoformat(result[0])
            return None
        except Exception as e:
            self.logger.error(f"Failed to get last buy date: {str(e)}")
            return None
    
    def get_sector_trades_today(self, sector: str) -> int:
        """Get count of trades in a sector today."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            today = datetime.now().date().isoformat()
            
            # Get all symbols in this sector
            cursor.execute("""
                SELECT COUNT(*) FROM executed_trades 
                WHERE DATE(timestamp) = ? AND symbol IN (
                    SELECT symbol FROM observations 
                    WHERE DATE(timestamp) = ?
                )
            """, (today, today))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to get sector trades today: {str(e)}")
            return 0


# ==================== MARKET DATA MANAGER ====================
def normalize_equity_symbol(tradingsymbol: str = "", symbol: str = "") -> str:
    """Map Angel One holding symbols to config-style tickers (e.g. HCLTECH-EQ -> HCLTECH)."""
    raw = (tradingsymbol or symbol or "").strip().upper()
    if raw.endswith("-EQ"):
        raw = raw[:-3]
    return raw


class MarketDataManager:
    """Fetches and manages market data from Angel One API."""
    
    def __init__(self, smartapi: SmartConnect, logger: logging.Logger):
        self.smartapi = smartapi
        self.logger = logger
        self._holdings_cache: Optional[List[Dict]] = None

    def clear_holdings_cache(self) -> None:
        """Clear cached holdings (call at the start of each trading cycle)."""
        self._holdings_cache = None

    def _fetch_holdings_list(self) -> List[Dict]:
        """Fetch raw holding rows from Angel One (single API round-trip)."""
        holdings = self.smartapi.holding()
        if not holdings or holdings.get("success") is False:
            holdings = self.smartapi.allholding()
        if not holdings or not holdings.get("data"):
            return []
        holdings_data = holdings["data"]
        if isinstance(holdings_data, dict):
            return (
                holdings_data.get("holding")
                or holdings_data.get("holdings")
                or holdings_data.get("data")
                or []
            )
        return holdings_data if isinstance(holdings_data, list) else []

    def get_all_holdings(self) -> List[Dict]:
        """
        Return all demat equity holdings with normalized symbol, qty, and average price.
        Results are cached until clear_holdings_cache() is called.
        """
        if self._holdings_cache is not None:
            return self._holdings_cache

        parsed: List[Dict] = []
        for holding in self._fetch_holdings_list():
            tradingsymbol = holding.get("tradingsymbol", "") or ""
            symbol = normalize_equity_symbol(tradingsymbol, holding.get("symbol", ""))
            if not symbol:
                continue
            quantity = int(float(holding.get("quantity", holding.get("qty", 0)) or 0))
            if quantity <= 0:
                continue
            avg_price = float(holding.get("avgprice", holding.get("averageprice", 0)) or 0)
            if avg_price <= 0:
                continue
            parsed.append(
                {
                    "symbol": symbol,
                    "tradingsymbol": tradingsymbol,
                    "quantity": quantity,
                    "avg_price": avg_price,
                    "ltp": float(holding.get("ltp", 0) or 0),
                    "exchange": holding.get("exchange", "NSE") or "NSE",
                }
            )

        self._holdings_cache = parsed
        self.logger.info(f"Loaded {len(parsed)} portfolio holding(s) from demat")
        return parsed
    
    def _lookup_symbol_token(self, symbol: str, exchange: str = "NSE") -> Tuple[Optional[str], Optional[str]]:
        """Look up exchange symbol token and tradingsymbol via Angel One searchScrip."""
        try:
            search_data = self.smartapi.searchScrip(exchange, symbol)
            if not search_data:
                return None, None

            data = search_data.get("data")
            if not data:
                return None, None

            if isinstance(data, dict):
                data = data.get("holdings") or data.get("holding") or data.get("data") or [data]

            if isinstance(data, list):
                # Prefer exact symbol matches or NSE equity names ending with -EQ
                symbol_upper = symbol.upper()
                for item in data:
                    tradingsymbol = item.get("tradingsymbol", "").upper()
                    if tradingsymbol == symbol_upper or tradingsymbol == f"{symbol_upper}-EQ":
                        return item.get("symboltoken"), item.get("tradingsymbol")
                first_item = data[0]
                return first_item.get("symboltoken"), first_item.get("tradingsymbol")

        except Exception as e:
            self.logger.error(f"Error searching symbol token for {symbol}: {str(e)}")
        return None, None

    def _parse_market_quote(self, quote_data: Dict) -> Optional[float]:
        if not quote_data:
            return None
        data = quote_data.get("data")
        if data is None:
            return None
        if isinstance(data, list) and len(data) > 0:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            return None
        ltp = item.get("ltp") or item.get("LTP") or item.get("last_price")
        if ltp is None:
            return None
        try:
            return float(ltp)
        except (TypeError, ValueError):
            return None

    def _fetch_yahoo_quote(self, url: str) -> Optional[float]:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        quote = data.get("quoteResponse", {}).get("result", [])
        if quote:
            price = quote[0].get("regularMarketPrice") or quote[0].get("regularMarketPreviousClose")
            if price is not None:
                return float(price)
        return None

    def _fetch_yahoo_quote_data(self, url: str) -> Tuple[Optional[float], Optional[float]]:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        quote = data.get("quoteResponse", {}).get("result", [])
        if quote:
            price = quote[0].get("regularMarketPrice")
            prev_close = quote[0].get("regularMarketPreviousClose")
            return (
                float(price) if price is not None else None,
                float(prev_close) if prev_close is not None else None,
            )
        return None, None

    def _fetch_yahoo_chart(self, symbol: str) -> Optional[float]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(symbol)}?interval=1d&range=1d"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        result = data.get("chart", {}).get("result")
        if result:
            meta = result[0].get("meta", {})
            regular_market_price = meta.get("regularMarketPrice")
            if regular_market_price is not None:
                return float(regular_market_price)
        return None

    def get_ltp_from_yahoo(self, symbol: str, exchange: str = "NSE") -> Optional[float]:
        """Fetch LTP from Yahoo Finance as a fallback source."""
        query_symbol = f"{symbol}.NS" if exchange.upper() == "NSE" else symbol
        endpoints = [
            f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={requests.utils.quote(query_symbol)}",
            f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={requests.utils.quote(query_symbol)}"
        ]
        last_error = None
        for url in endpoints:
            try:
                price = self._fetch_yahoo_quote(url)
                if price is not None:
                    self.logger.debug(f"Yahoo Finance fallback LTP for {symbol}: {price}")
                    return price
            except Exception as e:
                last_error = e
                self.logger.debug(f"Yahoo Finance endpoint failed ({url}): {e}")

        try:
            price = self._fetch_yahoo_chart(query_symbol)
            if price is not None:
                self.logger.debug(f"Yahoo Finance chart fallback LTP for {symbol}: {price}")
                return price
        except Exception as e:
            last_error = e
            self.logger.debug(f"Yahoo Finance chart endpoint failed: {e}")

        self.logger.error(f"Yahoo Finance fallback failed for {symbol}: {last_error}")
        return None

    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Optional[float]:
        """Get Last Traded Price (LTP) for a symbol."""
        try:
            symbol_token, trading_symbol = self._lookup_symbol_token(symbol, exchange)
            if symbol_token and trading_symbol:
                quote_data = self.smartapi.ltpData(exchange, trading_symbol, symbol_token)
                ltp = self._parse_market_quote(quote_data)
                if ltp is not None:
                    self.logger.debug(f"Fetched LTP for {symbol} via Angel One ltpData: {ltp}")
                    return ltp
                self.logger.warning(f"Angel One ltpData returned no LTP for {symbol}")
            else:
                self.logger.warning(f"Could not resolve Angel One symbol token for {symbol}")

            self.logger.warning(f"Angel One market data unavailable for {symbol}; using fallback source")
            fallback_ltp = self.get_ltp_from_yahoo(symbol, exchange)
            if fallback_ltp is not None:
                return fallback_ltp

            self.logger.warning(f"Failed to fetch LTP for {symbol}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching LTP for {symbol}: {str(e)}")
            return None
    
    def get_portfolio_position(self, symbol: str) -> Optional[Dict[str, float]]:
        """Fetch current holding quantity and average price for a symbol (uses holdings cache)."""
        try:
            symbol_upper = symbol.upper()
            for holding in self.get_all_holdings():
                if holding["symbol"] == symbol_upper:
                    self.logger.debug(
                        f"Portfolio position for {symbol}: qty={holding['quantity']}, "
                        f"avg_price={holding['avg_price']}"
                    )
                    return {
                        "quantity": holding["quantity"],
                        "avg_price": holding["avg_price"],
                    }
            self.logger.warning(f"No holdings found for {symbol}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching portfolio position for {symbol}: {str(e)}")
            return None

    def get_portfolio_avg_price(self, symbol: str) -> Optional[float]:
        """Fetch portfolio average price for a symbol."""
        position = self.get_portfolio_position(symbol)
        return position["avg_price"] if position else None

    def get_available_balance(self) -> Optional[float]:
        """Get available DMAT funds."""
        try:
            profile = None
            refresh_token = getattr(self.smartapi, "refresh_token", None)

            if refresh_token:
                try:
                    profile = self.smartapi.getProfile(refresh_token)
                    self.logger.debug(f"getProfile(refresh_token) response: {profile}")
                except Exception as e:
                    self.logger.debug(f"getProfile(refresh_token) failed: {e}")

            if not profile:
                try:
                    profile = self.smartapi.getProfile(None)
                    self.logger.debug(f"getProfile(None) response: {profile}")
                except Exception as e:
                    self.logger.debug(f"getProfile(None) failed: {e}")

            if profile:
                self.logger.debug(f"Profile response object: {profile}")
                if profile.get("status") is True and isinstance(profile.get("data"), dict):
                    data = profile["data"]
                    for key in ["cash", "cashbalance", "availablecash", "available_cash", "netcash", "net_cash"]:
                        if key in data and data[key] is not None:
                            try:
                                cash = float(data[key])
                                self.logger.debug(f"Available balance from profile {key}: {cash} INR")
                                return cash
                            except (TypeError, ValueError):
                                continue
                else:
                    self.logger.warning(f"Profile response returned no usable data: {profile}")

            rms_data = self.smartapi.rmsLimit()
            self.logger.debug(f"rmsLimit response: {rms_data}")
            if rms_data and rms_data.get("data"):
                data = rms_data["data"]
                for key in ["availablecash", "availableMargin", "availablemargin", "netcash", "net", "cash"]:
                    if key in data and data[key] is not None:
                        try:
                            cash = float(data[key])
                            self.logger.debug(f"Available balance from RMS data {key}: {cash} INR")
                            return cash
                        except (TypeError, ValueError):
                            continue

            self.logger.warning("Failed to fetch available balance")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching available balance: {str(e)}")
            return None

    def get_holdings_value(self) -> float:
        """Compute total market value of DMAT holdings (uses holdings cache)."""
        try:
            total_value = 0.0
            for holding in self.get_all_holdings():
                ltp = holding.get("ltp") or 0.0
                if ltp <= 0:
                    ltp = self.get_ltp(holding["symbol"], holding.get("exchange", "NSE")) or 0.0
                total_value += holding["quantity"] * ltp
            self.logger.debug(f"Total holdings value: {total_value} INR")
            return total_value
        except Exception as e:
            self.logger.error(f"Error computing holdings value: {str(e)}")
            return 0.0

    def get_total_dmat_value(self) -> Optional[float]:
        """Compute total DMAT value including available cash and holdings."""
        try:
            cash = self.get_available_balance() or 0.0
            holdings_value = self.get_holdings_value()
            total = cash + holdings_value
            self.logger.debug(f"Total DMAT value: cash={cash} + holdings={holdings_value} = {total} INR")
            return total
        except Exception as e:
            self.logger.error(f"Error computing total DMAT value: {str(e)}")
            return None

    def get_nifty_50_change_percent(self) -> Optional[float]:
        """Get Nifty 50 price change percentage."""
        try:
            try:
                quote_data = self.smartapi.getMarketData(mode="LTP", exchangeTokens=["NIFTY 50"])
                if quote_data and "data" in quote_data:
                    data = quote_data["data"]
                    if isinstance(data, list) and data:
                        data = data[0]
                    ltp = float(data.get("ltp", 0))
                    close = float(data.get("close", ltp))
                    if close != 0:
                        change_percent = ((ltp - close) / close) * 100
                        self.logger.debug(f"Nifty 50 change: {change_percent:.2f}%")
                        return change_percent
            except Exception:
                self.logger.debug("SmartAPI Nifty 50 market data failed, falling back to Yahoo Finance")

            # Fallback to Yahoo Finance for Nifty 50 index data
            quote_url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=%5ENSEI"
            price, prev_close = self._fetch_yahoo_quote_data(quote_url)
            if price is not None and prev_close not in (None, 0):
                change_percent = ((price - prev_close) / prev_close) * 100
                self.logger.debug(f"Nifty 50 Yahoo fallback change: {change_percent:.2f}%")
                return change_percent

            self.logger.warning("Failed to fetch Nifty 50 data")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching Nifty 50 data: {str(e)}")
            return None


# ==================== TRADING LOGIC ENGINE ====================
class BalanceWheelEngine:
    """Core trading logic and decision engine."""
    
    def __init__(
        self,
        config: Dict,
        auth_manager: AngelOneAuthManager,
        db_manager: ObservationDatabase,
        market_data_manager: MarketDataManager,
        logger: logging.Logger
    ):
        self.config = config
        self.auth_manager = auth_manager
        self.db_manager = db_manager
        self.market_data_manager = market_data_manager
        self.logger = logger
        self.rules = config["trading_rules"]
    
    def analyze_stock(self, stock: Dict, ltp: float, portfolio_avg_price: float, current_qty: int) -> StockAnalysis:
        """
        Analyze a single stock using the 15/5 rule and actual portfolio quantity.

        Returns: StockAnalysis with action and calculation details.
        """
        symbol = stock["symbol"]
        sector = stock["sector"]

        if portfolio_avg_price == 0 or current_qty <= 0:
            dip_percentage = 0
            reason = f"Skipping {symbol}: missing holding quantity or average price"
            return StockAnalysis(
                symbol=symbol,
                ltp=ltp,
                portfolio_avg_price=portfolio_avg_price,
                dip_percentage=dip_percentage,
                action="SKIP",
                reason=reason
            )

        dip_percentage = ((portfolio_avg_price - ltp) / portfolio_avg_price) * 100

        # Determine action based on 15/5 rule
        if dip_percentage >= self.rules["price_dip_threshold_percent"]:
            # Rule: Buy if dip >= 15%, using actual holding quantity to average down to target.
            shares, new_avg = self._calculate_smart_average(
                current_qty, portfolio_avg_price, ltp
            )

            if shares == 0:
                action = "STATUS_CHECKED"
                reason = (
                    f"Price dip {dip_percentage:.2f}% >= {self.rules['price_dip_threshold_percent']}%, "
                    f"but existing position of {current_qty} shares already meets the target average buffer."
                )
            else:
                action = "BUY"
                reason = (
                    f"Price dip {dip_percentage:.2f}% >= {self.rules['price_dip_threshold_percent']}%. "
                    f"Buy {shares} shares to move avg toward {self.rules['target_average_buffer_percent']}% buffer above LTP."
                )

            return StockAnalysis(
                symbol=symbol,
                ltp=ltp,
                portfolio_avg_price=portfolio_avg_price,
                dip_percentage=dip_percentage,
                action=action,
                shares_to_buy=shares,
                new_avg_price=new_avg,
                reason=reason
            )
        
        elif (dip_percentage > self.rules["high_alert_lower_threshold_percent"] and
              dip_percentage < self.rules["high_alert_upper_threshold_percent"]):
            # Rule: High Alert if 12% < dip < 15%
            action = "HIGH_ALERT"
            reason = f"Price dip {dip_percentage:.2f}% between {self.rules['high_alert_lower_threshold_percent']}% and {self.rules['high_alert_upper_threshold_percent']}%. High Alert - Watch closely."
            
            return StockAnalysis(
                symbol=symbol,
                ltp=ltp,
                portfolio_avg_price=portfolio_avg_price,
                dip_percentage=dip_percentage,
                action=action,
                reason=reason
            )
        
        else:
            # Rule: Status Checked otherwise
            action = "STATUS_CHECKED"
            reason = f"Price dip {dip_percentage:.2f}%. Status: Normal monitoring."
            
            return StockAnalysis(
                symbol=symbol,
                ltp=ltp,
                portfolio_avg_price=portfolio_avg_price,
                dip_percentage=dip_percentage,
                action=action,
                reason=reason
            )
    
    def _calculate_smart_average(
        self, current_qty: int, portfolio_avg_price: float, ltp: float
    ) -> Tuple[int, float]:
        """
        Calculate shares needed to bring weighted average within target buffer above LTP.

        Formula: n = Q * (P_avg - T) / (T - P_ltp)
        Where: Q = current quantity, P_avg = portfolio avg, P_ltp = LTP,
        T = LTP * (1 + target_average_buffer_percent / 100)

        Returns: (shares_to_buy, new_weighted_average)
        """
        try:
            if current_qty <= 0 or ltp <= 0:
                return 0, portfolio_avg_price

            target_avg = ltp * (1 + self.rules["target_average_buffer_percent"] / 100)
            if portfolio_avg_price <= target_avg:
                return 0, portfolio_avg_price

            denominator = target_avg - ltp
            if denominator == 0:
                return 0, portfolio_avg_price

            shares_to_buy = (current_qty * portfolio_avg_price - current_qty * target_avg) / denominator
            shares_to_buy = math.floor(max(0, shares_to_buy))

            if current_qty + shares_to_buy > 0:
                new_avg = (current_qty * portfolio_avg_price + shares_to_buy * ltp) / (current_qty + shares_to_buy)
            else:
                new_avg = portfolio_avg_price

            self.logger.debug(
                f"Smart average calculation: qty={current_qty}, shares={shares_to_buy}, new_avg={new_avg:.2f}"
            )
            return shares_to_buy, new_avg
        except Exception as e:
            self.logger.error(f"Error calculating smart average: {str(e)}")
            return 0, portfolio_avg_price
    
    def check_execution_constraints(
        self,
        symbol: str,
        sector: str,
        shares_to_buy: int,
        ltp: float
    ) -> Tuple[bool, int, str]:
        """
        Check execution constraints:
        1. Minimum balance
        2. Cool-down period
        3. Sector diversification
        4. Market sentiment
        
        Returns: (can_execute, adjusted_shares, reason)
        """
        # Check 1: Minimum Balance
        available_balance = self.market_data_manager.get_available_balance()
        if not available_balance or available_balance < self.rules["minimum_balance_required_inr"]:
            return False, 0, f"Insufficient Funds: Balance = {available_balance} INR"
        
        # Check 2: Cool-down Logic (7 days)
        last_buy_date = self.db_manager.get_last_buy_date(symbol)
        if last_buy_date:
            days_since_buy = (datetime.now() - last_buy_date).days
            if days_since_buy < self.rules["cooldown_days"]:
                return False, 0, f"Cool-down active: Last buy {days_since_buy} days ago"
        
        # Check 3: Sector Diversification (max 1 buy per sector per day)
        # TODO: Implement sector diversification check with config
        
        # Check 4: Market Sentiment (Nifty down > 3%)
        # Skip this check if we can't fetch Nifty data (don't block execution)
        try:
            nifty_change = self.market_data_manager.get_nifty_50_change_percent()
            if nifty_change and nifty_change < -self.rules["market_sentiment_nifty_down_percent"]:
                return False, 0, f"Market Sentiment Lock: Nifty down {abs(nifty_change):.2f}% (> {self.rules['market_sentiment_nifty_down_percent']}%)"
        except Exception as e:
            # Log the error but don't block execution due to sentiment check failure
            self.logger.warning(f"Could not check market sentiment: {str(e)}. Proceeding with execution.")
        
        # Check 5: Safety Buffer - Adjust shares if needed
        required_amount = shares_to_buy * ltp
        if required_amount > available_balance:
            # Calculate max possible shares
            max_shares = math.floor(available_balance / ltp)
            # Subtract 1 for safety buffer (tax/charges)
            adjusted_shares = max(0, max_shares - self.rules["safety_buffer_subtract_shares"])
            
            if adjusted_shares > 0:
                return True, adjusted_shares, f"Safety buffer applied: {adjusted_shares} shares (reduced from {shares_to_buy})"
            else:
                return False, 0, f"Insufficient balance after safety buffer"
        
        return True, shares_to_buy, "All constraints passed"
    
    def execute_buy_order(
        self,
        symbol: str,
        quantity: int,
        ltp: float
    ) -> Tuple[bool, Optional[str], str]:
        """
        Execute buy order on Angel One platform.
        Respects DRY_RUN mode.
        
        Returns: (success, order_id, message)
        """
        dry_run = self.config.get("dry_run", False)
        
        try:
            if dry_run:
                order_id = f"DRY_{symbol}_{datetime.now().timestamp()}"
                total_amount = quantity * ltp
                self.logger.info(
                    f"[DRY RUN] Would place order: {symbol} x{quantity} @ {ltp} = {total_amount:.2f} INR"
                )
                self.db_manager.log_trade(symbol, quantity, ltp, order_id, True)
                return True, order_id, f"DRY RUN: {symbol} x{quantity} @ {ltp}"
            
            # Real execution - Fetch correct symbol token
            symbol_token, trading_symbol = self.market_data_manager._lookup_symbol_token(symbol, "NSE")
            if not symbol_token or not trading_symbol:
                error_msg = f"Could not resolve symbol token for {symbol}"
                self.logger.error(f"Order placement failed for {symbol}: {error_msg}")
                return False, None, error_msg
            
            order_params = {
                "variety": "REGULAR",
                "symboltoken": symbol_token,
                "transactiontype": "BUY",
                "quantity": quantity,
                "price": ltp,
                "pricetype": "LIMIT",
                "producttype": "MIS"  # Margin Intraday Short
            }
            
            self.logger.debug(f"Placing order with params: {order_params}")
            order_response = self.auth_manager.get_smartapi_instance().placeOrder(order_params)
            self.logger.debug(f"Order response type: {type(order_response)}, value: {order_response}")
            
            if order_response and isinstance(order_response, str):
                # Successful order - response is order ID string
                order_id = order_response
                total_amount = quantity * ltp
                
                self.logger.info(
                    f"Order placed successfully: {symbol} x{quantity} @ {ltp}. "
                    f"Order ID: {order_id}. Total: {total_amount:.2f} INR"
                )
                self.db_manager.log_trade(symbol, quantity, ltp, order_id, False)
                return True, order_id, f"Order placed: {order_id}"
            elif order_response and isinstance(order_response, dict):
                # Error response - dict format
                error_msg = order_response.get("message", "Unknown error")
                self.logger.error(f"Order placement failed for {symbol}: {error_msg}")
                return False, None, f"Order failed: {error_msg}"
            else:
                # Failed or None response
                error_msg = f"No response from broker for {symbol} - Order rejected or error occurred"
                self.logger.error(f"Order placement failed for {symbol}: {error_msg}")
                return False, None, error_msg
        
        except Exception as e:
            error_msg = f"Exception during order execution: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg


# ==================== MAIN BOT CLASS ====================
class BalanceWheelBot:
    """Main BalanceWheel bot orchestrator."""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.logger = setup_logger(self.config)
        
        self.logger.info("=" * 80)
        self.logger.info(f"BalanceWheel Bot Initialized - {self.config['app_name']} v{self.config['version']}")
        if self.is_dry_run():
            self.logger.warning("DRY RUN MODE — no real orders will be placed (set DRY_RUN=false to trade live)")
        else:
            self.logger.warning(
                "LIVE PRODUCTION MODE — real BUY orders will be sent to Angel One when signals fire"
            )
        github_repo = self.config.get("github_repo")
        if github_repo:
            self.logger.info(f"Repository configured from env: {github_repo}")
        if self.config.get("github_token"):
            self.logger.info("GitHub token loaded from environment (hidden)")
        self.logger.info("=" * 80)
        
        # Initialize components
        self.auth_manager = self._init_auth()
        self.db_manager = None
        self.market_data_manager = None
        self.engine = None
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
            config = self._apply_env_overrides(config)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in config file: {self.config_file}")
    
    def _apply_env_overrides(self, config: Dict) -> Dict:
        """Override configuration settings with environment variables."""
        broker_config = config.get("broker", {})

        env_password = os.getenv("ANGEL_PASSWORD") or os.getenv("ANGELONE_PIN") or os.getenv("ANGEL_PIN")
        if env_password:
            broker_config["password"] = env_password

        env_totp = os.getenv("ANGEL_TOTP") or os.getenv("ANGEL_TOTP_SECRET")
        if env_totp:
            if env_totp.isdigit() and len(env_totp) == 6:
                broker_config["totp"] = env_totp
            else:
                try:
                    broker_config["totp"] = pyotp.TOTP(env_totp).now()
                except Exception:
                    broker_config["totp"] = env_totp

        env_api = os.getenv("ANGEL_API_KEY")
        if env_api:
            broker_config["api_key"] = env_api

        env_client = os.getenv("ANGEL_CLIENT_CODE")
        if env_client:
            broker_config["client_code"] = env_client

        config["broker"] = broker_config

        # Production by default. Opt into dry-run only when DRY_RUN or PAPER_TRADING is set in .env
        if os.getenv("DRY_RUN") is not None:
            config["dry_run"] = os.getenv("DRY_RUN").strip().lower() in {"1", "true", "yes"}
        elif os.getenv("PAPER_TRADING") is not None:
            config["dry_run"] = os.getenv("PAPER_TRADING").strip().lower() in {"1", "true", "yes"}
        else:
            config["dry_run"] = bool(config.get("dry_run", False))

        if os.getenv("PAPER_TRADING") is not None:
            config["paper_trading"] = os.getenv("PAPER_TRADING").strip().lower() in {"1", "true", "yes"}

        if os.getenv("MIN_WALLET_BALANCE") is not None:
            try:
                config["trading_rules"]["minimum_balance_required_inr"] = float(os.getenv("MIN_WALLET_BALANCE"))
            except ValueError:
                pass

        github_repo = os.getenv("GITHUB_REPO")
        if github_repo:
            config["github_repo"] = github_repo

        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            config["github_token"] = github_token

        return config

    def is_dry_run(self) -> bool:
        """True only when dry-run is explicitly enabled (config or DRY_RUN/PAPER_TRADING env)."""
        return bool(self.config.get("dry_run", False))

    def _init_auth(self) -> AngelOneAuthManager:
        """Initialize Angel One authentication."""
        broker_config = self.config["broker"]
        auth_mgr = AngelOneAuthManager(
            api_key=broker_config["api_key"],
            client_code=broker_config["client_code"],
            password=broker_config["password"],
            totp=broker_config.get("totp")
        )
        return auth_mgr
    
    def startup(self) -> bool:
        """Perform startup checks and initialization."""
        try:
            self.logger.info("Starting up BalanceWheel bot...")
            
            # Authenticate
            success, msg = self.auth_manager.authenticate()
            if not success:
                self.logger.error(f"Authentication failed: {msg}")
                return False
            self.logger.info(f"Authentication successful: {msg}")
            
            # Initialize database
            self.db_manager = ObservationDatabase(
                self.config["database"]["file"],
                self.logger
            )
            
            # Initialize market data manager
            smartapi = self.auth_manager.get_smartapi_instance()
            self.market_data_manager = MarketDataManager(smartapi, self.logger)
            
            # Initialize trading engine
            self.engine = BalanceWheelEngine(
                self.config,
                self.auth_manager,
                self.db_manager,
                self.market_data_manager,
                self.logger
            )
            
            self.logger.info("Bot startup completed successfully!")
            return True
        
        except Exception as e:
            self.logger.error(f"Startup failed: {str(e)}", exc_info=True)
            return False
    
    def _target_stocks_by_symbol(self) -> Dict[str, Dict]:
        """Index target_stocks watchlist by symbol for metadata lookup."""
        return {entry["symbol"].upper(): entry for entry in self.config.get("target_stocks", [])}

    def _stock_metadata_for_holding(self, symbol: str, holding: Dict) -> Dict:
        """
        Build stock config for analysis: watchlist entry if listed, else portfolio defaults.
        """
        watchlist = self._target_stocks_by_symbol()
        if symbol.upper() in watchlist:
            stock = dict(watchlist[symbol.upper()])
            stock["symbol"] = symbol.upper()
            stock["on_watchlist"] = True
            return stock
        return {
            "symbol": symbol.upper(),
            "exchange": holding.get("exchange", "NSE"),
            "sector": "Portfolio",
            "category": "Holding",
            "priority": 2,
            "on_watchlist": False,
        }

    def _iter_cycle_stocks(self) -> List[Tuple[Dict, Dict]]:
        """
        Return (stock_metadata, position) pairs to analyze this cycle.
        Default: all demat holdings. Legacy: target_stocks you actually hold.
        """
        analyze_holdings_only = self.config.get("analyze_holdings_only", True)
        pairs: List[Tuple[Dict, Dict]] = []

        if analyze_holdings_only:
            for holding in self.market_data_manager.get_all_holdings():
                symbol = holding["symbol"]
                stock = self._stock_metadata_for_holding(symbol, holding)
                position = {"quantity": holding["quantity"], "avg_price": holding["avg_price"]}
                pairs.append((stock, position))
            return pairs

        for stock in self.config.get("target_stocks", []):
            symbol = stock["symbol"]
            position = self.market_data_manager.get_portfolio_position(symbol)
            if position and position.get("quantity", 0) > 0:
                pairs.append((stock, position))
        return pairs

    def run_cycle(self) -> None:
        """Run a single trading cycle."""
        if not self.engine:
            self.logger.error("Engine not initialized. Call startup() first.")
            return
        
        try:
            self.logger.info("-" * 80)
            self.logger.info(f"Starting trading cycle at {datetime.now()}")
            self.market_data_manager.clear_holdings_cache()

            if self.config.get("analyze_holdings_only", True):
                watchlist_count = len(self.config.get("target_stocks", []))
                self.logger.info(
                    f"Portfolio mode: analyzing demat holdings only "
                    f"(watchlist has {watchlist_count} names for sector/metadata reference)"
                )

            cycle_results = []
            
            for stock, position in self._iter_cycle_stocks():
                symbol = stock["symbol"]
                try:
                    self.logger.debug(f"Analyzing {symbol}...")
                    
                    ltp = self.market_data_manager.get_ltp(symbol, stock.get("exchange", "NSE"))
                    if not ltp:
                        self.logger.warning(f"Skipping {symbol}: could not fetch LTP")
                        continue

                    avg_price = position["avg_price"]
                    current_qty = position["quantity"]

                    analysis = self.engine.analyze_stock(stock, ltp, avg_price, current_qty)
                    cycle_results.append(analysis)
                    
                    self.db_manager.log_observation(analysis)
                    watchlist_note = " [watchlist]" if stock.get("on_watchlist") else " [portfolio only]"
                    self.logger.info(f"[{analysis.action}] {symbol}{watchlist_note}: {analysis.reason}")
                    
                    if analysis.action == "BUY":
                        can_exec, adjusted_qty, exec_reason = self.engine.check_execution_constraints(
                            symbol, stock["sector"], analysis.shares_to_buy, ltp
                        )
                        
                        if can_exec and adjusted_qty > 0:
                            success, order_id, msg = self.engine.execute_buy_order(
                                symbol, adjusted_qty, ltp
                            )
                            self.logger.info(f"Execution result: {msg}")
                        else:
                            self.logger.warning(f"Execution blocked: {exec_reason}")
                
                except Exception as e:
                    self.logger.error(f"Error processing {symbol}: {str(e)}", exc_info=True)
            
            self.logger.info(f"Trading cycle completed. Processed {len(cycle_results)} holding(s).")
            self.logger.info("-" * 80)
        
        except Exception as e:
            self.logger.error(f"Trading cycle failed: {str(e)}", exc_info=True)
    
    def _push_logs_to_github(self) -> None:
        """Push logs to GitHub repository for centralized analysis."""
        try:
            import subprocess
            import os
            
            # Get GitHub token from env
            github_token = os.getenv("GITHUB_TOKEN")
            if not github_token:
                self.logger.warning("GITHUB_TOKEN not found in environment. Skipping log push to GitHub.")
                return
            
            # Get project root (current working directory)
            project_root = os.getcwd()
            
            # Set up environment for git with credentials
            env = os.environ.copy()
            env['GIT_AUTHOR_NAME'] = 'BalanceWheel Bot'
            env['GIT_AUTHOR_EMAIL'] = 'bot@balancewheel.local'
            env['GIT_COMMITTER_NAME'] = 'BalanceWheel Bot'
            env['GIT_COMMITTER_EMAIL'] = 'bot@balancewheel.local'
            
            # Commands to push logs
            commands = [
                ["git", "config", "--local", "user.name", "BalanceWheel Bot"],
                ["git", "config", "--local", "user.email", "bot@balancewheel.local"],
                ["git", "add", "logs/", "-f"],  # Force add logs
                ["git", "commit", "-m", f"Logs update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {os.uname().sysname if hasattr(os, 'uname') else 'Windows'}"],  # Commit with timestamp and system info
                ["git", "push", f"https://nir351988:{github_token}@github.com/nir351988/Balancewheel.git", "master"]  # Push with auth
            ]
            
            for cmd in commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)
                    if result.returncode != 0:
                        # Sanitize error message to avoid logging tokens
                        error_msg = result.stderr.strip()
                        # Remove any URLs with tokens
                        error_msg = re.sub(r'https://[^@]+@github\.com', 'https://[REDACTED]@github.com', error_msg)
                        # Log sanitized message
                        if error_msg and "already exists" not in error_msg.lower():
                            self.logger.warning(f"Git command failed: {' '.join(cmd[:2])} - {error_msg[:100]}")
                    else:
                        self.logger.info(f"Git command successful: {' '.join(cmd[:2])}")
                except Exception as e:
                    self.logger.error(f"Error running git command: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Failed to push logs to GitHub: {str(e)}")
    
    def shutdown(self, reason: str = "Normal exit") -> None:
        """Graceful shutdown."""
        try:
            self.logger.info("=" * 80)
            self.logger.info(f"BalanceWheel Bot shutting down: {reason}")
            self.logger.info("=" * 80)
            
            # Push logs to GitHub
            self._push_logs_to_github()
        except Exception as e:
            print(f"Error during shutdown: {str(e)}")


# ==================== MAIN ENTRY POINT ====================
def main():
    """Main entry point for the bot."""
    bot = BalanceWheelBot(config_file="config.json")
    
    try:
        if not bot.startup():
            bot.shutdown("Startup failed")
            return
        
        # Run a single cycle (can be scheduled with APScheduler for PythonAnywhere)
        bot.run_cycle()
        
        bot.shutdown("Trading cycle completed")
    
    except KeyboardInterrupt:
        bot.shutdown("Interrupted by user")
    except Exception as e:
        bot.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        bot.shutdown(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
