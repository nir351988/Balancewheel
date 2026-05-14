"""
Authentication Manager for Angel One SmartAPI
Handles JWT token generation, refresh, and API credential management.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import pyotp
from SmartApi import SmartConnect

logger = logging.getLogger(__name__)


class AngelOneAuthManager:
    """
    Manages authentication with Angel One SmartAPI.
    Handles token generation, refresh, and credential validation.
    """

    def __init__(
        self,
        api_key: str,
        client_code: str,
        password: str,
        totp: Optional[str] = None,
        credentials_file: str = ".credentials.json",
    ):
        """
        Initialize Angel One Auth Manager.
        
        Args:
            api_key: Angel One API key
            client_code: Client code (usually numeric)
            password: Login password
            totp: Time-based OTP (if required)
            credentials_file: File to persist tokens
        """
        self.api_key = api_key
        self.client_code = client_code
        self.password = password
        self.totp = totp
        self.credentials_file = credentials_file
        self.auth_token = None
        self.refresh_token = None
        self.feed_token = None
        self.token_expiry = None
        self.smartapi = None
        
        logger.info("AngelOneAuthManager initialized")

    def authenticate(self) -> Tuple[bool, str]:
        """
        Authenticate with Angel One API.
        Attempts to use cached credentials first, then performs fresh login.
        
        Returns:
            Tuple[bool, str]: (success, message or error)
        """
        try:
            # Try loading cached credentials
            if self._load_cached_credentials():
                logger.info("Loaded cached credentials successfully")
                return True, "Authenticated with cached credentials"
            
            # Perform fresh authentication
            logger.info("Attempting fresh authentication...")
            
            # Initialize SmartConnect
            self.smartapi = SmartConnect(api_key=self.api_key)

            # Normalize TOTP secret into a one-time code if needed.
            login_totp = self.totp
            if login_totp and not login_totp.isdigit():
                try:
                    login_totp = pyotp.TOTP(login_totp).now()
                except Exception:
                    login_totp = self.totp

            # Login
            login_data = self.smartapi.generateSession(
                clientCode=self.client_code,
                password=self.password,
                totp=login_totp or "000000"
            )
            
            if login_data.get("status") is False:
                error_msg = login_data.get("message", "Unknown authentication error")
                logger.error(f"Authentication failed: {error_msg}")
                return False, f"Authentication failed: {error_msg}"
            
            # Extract tokens
            data = login_data.get("data", {})
            self.auth_token = data.get("jwtToken") or data.get("authToken")
            self.refresh_token = data.get("refreshToken")
            self.feed_token = data.get("feedToken")
            self.token_expiry = datetime.now() + timedelta(hours=24)
            
            # Cache credentials
            self._save_cached_credentials()
            
            logger.info(f"Fresh authentication successful. Token valid until {self.token_expiry}")
            return True, "Fresh authentication successful"
            
        except Exception as e:
            error_msg = f"Authentication exception: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def refresh_token(self) -> Tuple[bool, str]:
        """
        Refresh authentication token if expired or near expiry.
        
        Returns:
            Tuple[bool, str]: (success, message or error)
        """
        try:
            if self.token_expiry and datetime.now() < self.token_expiry - timedelta(hours=1):
                logger.debug("Token still valid, no refresh needed")
                return True, "Token valid"
            
            logger.info("Token refresh required...")
            # Force re-authentication
            self._clear_cached_credentials()
            return self.authenticate()
            
        except Exception as e:
            error_msg = f"Token refresh exception: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_auth_token(self) -> Optional[str]:
        """Get current auth token."""
        return self.auth_token

    def get_feed_token(self) -> Optional[str]:
        """Get current feed token."""
        return self.feed_token

    def get_smartapi_instance(self) -> Optional[SmartConnect]:
        """Get initialized SmartConnect instance."""
        return self.smartapi

    def is_token_valid(self) -> bool:
        """Check if current token is still valid."""
        if not self.token_expiry or not self.auth_token:
            return False
        return datetime.now() < self.token_expiry

    def _save_cached_credentials(self) -> None:
        """Save credentials to local file for reuse."""
        try:
            credentials = {
                "auth_token": self.auth_token,
                "refresh_token": self.refresh_token,
                "feed_token": self.feed_token,
                "token_expiry": self.token_expiry.isoformat() if self.token_expiry else None,
                "cached_at": datetime.now().isoformat(),
            }
            with open(self.credentials_file, "w") as f:
                json.dump(credentials, f)
            logger.debug("Credentials cached successfully")
        except Exception as e:
            logger.warning(f"Failed to cache credentials: {str(e)}")

    def _load_cached_credentials(self) -> bool:
        """Load cached credentials from file."""
        try:
            if not os.path.exists(self.credentials_file):
                return False
            
            with open(self.credentials_file, "r") as f:
                credentials = json.load(f)
            
            token_expiry = datetime.fromisoformat(credentials["token_expiry"])
            
            # Check if cached token is still valid (with 30-min buffer)
            if datetime.now() < token_expiry - timedelta(minutes=30):
                self.auth_token = credentials["auth_token"]
                self.refresh_token = credentials.get("refresh_token")
                self.feed_token = credentials["feed_token"]
                self.token_expiry = token_expiry
                self.smartapi = SmartConnect(
                    api_key=self.api_key,
                    access_token=self.auth_token,
                    refresh_token=self.refresh_token,
                )
                self.smartapi.setAccessToken(self.auth_token)
                self.smartapi.setRefreshToken(self.refresh_token)
                self.smartapi.setFeedToken(self.feed_token)

                # Validate restored session with a quick profile call.
                try:
                    profile = self.smartapi.getProfile(self.refresh_token)
                    if not profile or profile.get("success") is False or not profile.get("data"):
                        raise ValueError("Cached token validation failed")
                except Exception as e:
                    logger.warning(f"Cached credentials validation failed: {e}")
                    self._clear_cached_credentials()
                    return False

                logger.debug("Loaded valid cached credentials")
                return True
            else:
                logger.debug("Cached credentials expired")
                return False
                
        except Exception as e:
            logger.debug(f"Failed to load cached credentials: {str(e)}")
            return False

    def _clear_cached_credentials(self) -> None:
        """Clear cached credentials file."""
        try:
            if os.path.exists(self.credentials_file):
                os.remove(self.credentials_file)
                logger.debug("Cached credentials cleared")
        except Exception as e:
            logger.warning(f"Failed to clear cached credentials: {str(e)}")

    def __repr__(self) -> str:
        return (
            f"AngelOneAuthManager(client_code={self.client_code}, "
            f"token_valid={self.is_token_valid()})"
        )
