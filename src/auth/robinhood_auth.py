"""
Robinhood authentication module with 2FA support.
Handles login, session management, and token persistence.
"""
import robin_stocks.robinhood as rh
import pickle
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
import pyotp

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
    - 2FA/MFA support using pyotp
    - Session token persistence
    - Automatic token refresh
    """

    def __init__(self):
        """Initialize Robinhood authenticator."""
        self.settings = get_settings()
        self.credentials_manager = get_credentials_manager()
        self.token_file = self.settings.base_dir / ".tokens" / "robinhood.pickle"
        self.is_authenticated = False
        self.username = None

        # Ensure token directory exists
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

        logger.debug("RobinhoodAuth initialized")

    def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        mfa_code: Optional[str] = None,
        store_session: bool = True,
    ) -> bool:
        """
        Login to Robinhood.

        Args:
            username: Robinhood username (optional, will use stored if not provided)
            password: Robinhood password (optional, will use stored if not provided)
            mfa_code: 2FA/MFA code if required
            store_session: Whether to persist session token

        Returns:
            bool: True if login successful, False otherwise

        Raises:
            RobinhoodAuthError: If login fails
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

            # Attempt login with MFA if provided
            if mfa_code:
                logger.debug("Logging in with MFA code")
                login_result = rh.login(username, password, mfa_code=mfa_code, store_session=store_session)
            else:
                logger.debug("Logging in without MFA code")
                login_result = rh.login(username, password, store_session=store_session)

            # Check if login was successful
            if login_result:
                self.is_authenticated = True
                self.username = username
                logger.info(f"Successfully logged in to Robinhood as {username}")

                # Store session token if requested
                if store_session:
                    self._save_session_token()

                return True
            else:
                logger.error("Login failed: No result returned from robin_stocks")
                raise RobinhoodAuthError("Login failed")

        except Exception as e:
            error_msg = str(e)

            # Check if MFA is required
            if "mfa_required" in error_msg.lower() or "challenge" in error_msg.lower():
                logger.warning("MFA/2FA required for login")
                raise RobinhoodAuthError(
                    "MFA/2FA code required. Please provide mfa_code parameter."
                ) from e

            logger.error(f"Robinhood login failed: {error_msg}")
            raise RobinhoodAuthError(f"Login failed: {error_msg}") from e

    def login_with_stored_session(self) -> bool:
        """
        Attempt to login using stored session token.

        Returns:
            bool: True if login successful, False otherwise
        """
        if not self.token_file.exists():
            logger.debug("No stored session token found")
            return False

        try:
            logger.info("Attempting to login with stored session token")

            # Load stored session
            with open(self.token_file, "rb") as f:
                session_data = pickle.load(f)

            username = session_data.get("username")
            if not username:
                logger.warning("No username in stored session")
                return False

            # robin_stocks will automatically use stored session
            # We just need to call login with store_session=True
            login_result = rh.login(username, store_session=True)

            if login_result:
                self.is_authenticated = True
                self.username = username
                logger.info(f"Successfully restored session for {username}")
                return True
            else:
                logger.warning("Stored session is invalid or expired")
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
            rh.logout()

            # Clear session token file
            if self.token_file.exists():
                self.token_file.unlink()
                logger.debug("Session token file deleted")

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
            # Try to fetch account info as a test
            account_info = rh.profiles.load_account_profile()

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

    def _save_session_token(self) -> bool:
        """
        Save current session token to file.

        Returns:
            bool: True if successful
        """
        try:
            session_data = {
                "username": self.username,
            }

            with open(self.token_file, "wb") as f:
                pickle.dump(session_data, f)

            logger.debug(f"Session token saved to {self.token_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session token: {e}")
            return False

    def get_authentication_status(self) -> Dict[str, Any]:
        """
        Get current authentication status.

        Returns:
            dict: Authentication status information
        """
        return {
            "is_authenticated": self.is_authenticated,
            "username": self.username,
            "has_stored_session": self.token_file.exists(),
            "has_stored_credentials": self.credentials_manager.has_robinhood_credentials(),
        }

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
