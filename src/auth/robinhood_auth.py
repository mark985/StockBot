"""
Robinhood authentication module with 2FA support.
Handles login, session management, and token persistence.

This module now uses the custom Robinhood client built from scratch,
replacing the unreliable robin_stocks library.
"""
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
import pyotp

from src.robinhood.client import RobinhoodClient
from src.robinhood.exceptions import AuthenticationError as RHAuthError
from src.auth.credentials_manager import get_credentials_manager
from config.settings import get_settings


class RobinhoodAuthError(Exception):
    """Custom exception for Robinhood authentication errors."""
    pass


class RobinhoodAuth:
    """
    Manages Robinhood authentication and session persistence.

    Features:
    - Username/password authentication
    - SMS/Email verification support (prefer_sms option)
    - Session token persistence
    - Automatic token refresh

    This class wraps the custom RobinhoodClient for compatibility with existing code.
    """

    def __init__(self):
        """Initialize Robinhood authenticator."""
        self.settings = get_settings()
        self.credentials_manager = get_credentials_manager()

        # Create custom Robinhood client
        self.client = RobinhoodClient()

        # Legacy compatibility
        self.is_authenticated = False
        self.username = None

        logger.debug("RobinhoodAuth initialized with custom client")

    def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        mfa_code: Optional[str] = None,
        store_session: bool = True,
        prefer_sms: bool = False,
    ) -> bool:
        """
        Login to Robinhood.

        Args:
            username: Robinhood username (optional, will use stored if not provided)
            password: Robinhood password (optional, will use stored if not provided)
            mfa_code: 2FA/MFA code if required (leave None to use interactive prompt)
            store_session: Whether to persist session token
            prefer_sms: If True, request SMS/email verification instead of app push

        Returns:
            bool: True if login successful, False otherwise

        Raises:
            RobinhoodAuthError: If login fails

        Note:
            The custom client will automatically handle verification workflows,
            including SMS/email verification if prefer_sms=True.
        """
        # Get credentials from parameters or stored location
        if not username:
            username = self.credentials_manager.get_robinhood_username()
        if not password:
            password = self.credentials_manager.get_robinhood_password()

        if not username or not password:
            raise RobinhoodAuthError(
                "Username and password required. "
                "Set them in environment or use credentials_manager.store_robinhood_credentials()"
            )

        try:
            logger.info(f"Attempting to login to Robinhood for user: {username}")

            # Use custom Robinhood client for login
            login_result = self.client.login(
                username=username,
                password=password,
                mfa_code=mfa_code,
                prefer_sms=prefer_sms
            )

            # Custom client returns a dict with access_token on success
            if login_result and isinstance(login_result, dict) and 'access_token' in login_result:
                self.is_authenticated = True
                self.username = username
                logger.info(f"Successfully logged in to Robinhood as {username}")
                return True
            else:
                raise RobinhoodAuthError("Login failed: Invalid response from Robinhood")

        except RobinhoodAuthError:
            # Re-raise our custom errors
            raise
        except RHAuthError as e:
            # Convert custom client auth errors to RobinhoodAuthError
            logger.error(f"Authentication error from custom client: {e}")
            raise RobinhoodAuthError(f"Login failed: {str(e)}") from e
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Robinhood login failed with exception: {error_msg}")
            raise RobinhoodAuthError(f"Login failed: {error_msg}") from e

    def login_with_stored_session(self) -> bool:
        """
        Attempt to login using stored session token.

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            logger.info("Attempting to login with stored session token")

            # Custom client automatically loads session from ~/.tokens/robinhood_custom.pickle
            if self.client.load_session():
                self.is_authenticated = self.client.is_authenticated
                logger.info("Successfully restored session")
                return True
            else:
                logger.warning("No stored session or session is invalid")
                return False

        except Exception as e:
            logger.error(f"Failed to restore session: {e}")
            return False

    def logout(self) -> bool:
        """
        Logout from Robinhood and clear session.

        Returns:
            bool: True if logout successful
        """
        try:
            logger.info("Logging out from Robinhood")
            self.client.logout()

            self.is_authenticated = False
            self.username = None
            logger.info("Successfully logged out")
            return True

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

    def verify_authentication(self) -> bool:
        """
        Verify if current session is authenticated.

        Returns:
            bool: True if authenticated and session is valid
        """
        try:
            # Try to fetch account info as a test using custom client
            account_info = self.client.get_account()

            if account_info:
                self.is_authenticated = True
                logger.debug("Authentication verified successfully")
                return True
            else:
                self.is_authenticated = False
                logger.warning("Authentication verification failed")
                return False

        except Exception as e:
            logger.error(f"Authentication verification failed: {e}")
            self.is_authenticated = False
            return False

    def get_authentication_status(self) -> Dict[str, Any]:
        """
        Get current authentication status.

        Returns:
            dict: Authentication status information
        """
        return {
            "is_authenticated": self.is_authenticated or self.client.is_authenticated,
            "username": self.username,
            "has_stored_session": self.client.session_file.exists(),
            "has_stored_credentials": self.credentials_manager.has_robinhood_credentials(),
        }

    def get_client(self) -> RobinhoodClient:
        """
        Get the underlying custom Robinhood client for direct API access.

        Returns:
            RobinhoodClient: The custom client instance
        """
        return self.client

    @staticmethod
    def generate_mfa_code(secret: str) -> str:
        """
        Generate MFA/2FA code from secret key.

        This is useful if user has set up TOTP-based 2FA.

        Args:
            secret: TOTP secret key (base32 encoded)

        Returns:
            str: 6-digit MFA code
        """
        totp = pyotp.TOTP(secret)
        return totp.now()


# Singleton instance
_robinhood_auth = None


def get_robinhood_auth() -> RobinhoodAuth:
    """Get or create RobinhoodAuth singleton instance."""
    global _robinhood_auth
    if _robinhood_auth is None:
        _robinhood_auth = RobinhoodAuth()
    return _robinhood_auth


def ensure_authenticated() -> RobinhoodAuth:
    """
    Ensure Robinhood is authenticated.

    Attempts to restore session, then falls back to fresh login.

    Returns:
        RobinhoodAuth: Authenticated instance

    Raises:
        RobinhoodAuthError: If authentication fails
    """
    auth = get_robinhood_auth()

    # First try to verify existing authentication
    if auth.verify_authentication():
        return auth

    # Try to restore from stored session
    if auth.login_with_stored_session():
        return auth

    # If both fail, require fresh login
    raise RobinhoodAuthError(
        "Not authenticated. Please login using robinhood_auth.login() "
        "or run 'stockbot login' command."
    )
