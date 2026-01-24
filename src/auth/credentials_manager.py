"""
Secure credentials management for StockBot.
Prioritizes keyring for secure OS-level storage, with .env file fallback.
"""
import keyring
from typing import Optional
from loguru import logger
from config.settings import get_settings


class CredentialsManager:
    """
    Manages secure storage and retrieval of credentials.

    Priority order:
    1. OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
    2. Environment variables from .env file
    3. Direct input (for testing or one-time use)
    """

    SERVICE_NAME = "stockbot"

    # Credential keys
    KEY_ROBINHOOD_USERNAME = "robinhood_username"
    KEY_ROBINHOOD_PASSWORD = "robinhood_password"
    KEY_GEMINI_API_KEY = "gemini_api_key"
    KEY_ROBINHOOD_MFA_CODE = "robinhood_mfa_code"  # Temporary storage for MFA

    def __init__(self):
        """Initialize credentials manager."""
        self.settings = get_settings()
        logger.debug("CredentialsManager initialized")

    def store_robinhood_credentials(self, username: str, password: str) -> bool:
        """
        Store Robinhood credentials in keyring.

        Args:
            username: Robinhood account username
            password: Robinhood account password

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            keyring.set_password(self.SERVICE_NAME, self.KEY_ROBINHOOD_USERNAME, username)
            keyring.set_password(self.SERVICE_NAME, self.KEY_ROBINHOOD_PASSWORD, password)
            logger.info(f"Robinhood credentials stored securely for user: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to store Robinhood credentials in keyring: {e}")
            return False

    def get_robinhood_username(self) -> Optional[str]:
        """
        Retrieve Robinhood username.

        Priority: keyring > environment variable

        Returns:
            str: Username if found, None otherwise
        """
        # Try keyring first
        try:
            username = keyring.get_password(self.SERVICE_NAME, self.KEY_ROBINHOOD_USERNAME)
            if username:
                logger.debug("Robinhood username retrieved from keyring")
                return username
        except Exception as e:
            logger.warning(f"Could not retrieve from keyring: {e}")

        # Fallback to environment variable
        if self.settings.robinhood_username:
            logger.debug("Robinhood username retrieved from environment")
            return self.settings.robinhood_username

        logger.warning("Robinhood username not found in keyring or environment")
        return None

    def get_robinhood_password(self) -> Optional[str]:
        """
        Retrieve Robinhood password.

        Priority: keyring > environment variable

        Returns:
            str: Password if found, None otherwise
        """
        # Try keyring first
        try:
            password = keyring.get_password(self.SERVICE_NAME, self.KEY_ROBINHOOD_PASSWORD)
            if password:
                logger.debug("Robinhood password retrieved from keyring")
                return password
        except Exception as e:
            logger.warning(f"Could not retrieve from keyring: {e}")

        # Fallback to environment variable
        if self.settings.robinhood_password:
            logger.debug("Robinhood password retrieved from environment")
            return self.settings.robinhood_password

        logger.warning("Robinhood password not found in keyring or environment")
        return None

    def store_gemini_api_key(self, api_key: str) -> bool:
        """
        Store Gemini API key in keyring.

        Args:
            api_key: Google Gemini API key

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            keyring.set_password(self.SERVICE_NAME, self.KEY_GEMINI_API_KEY, api_key)
            logger.info("Gemini API key stored securely")
            return True
        except Exception as e:
            logger.error(f"Failed to store Gemini API key in keyring: {e}")
            return False

    def get_gemini_api_key(self) -> Optional[str]:
        """
        Retrieve Gemini API key.

        Priority: keyring > environment variable

        Returns:
            str: API key if found, None otherwise
        """
        # Try keyring first
        try:
            api_key = keyring.get_password(self.SERVICE_NAME, self.KEY_GEMINI_API_KEY)
            if api_key:
                logger.debug("Gemini API key retrieved from keyring")
                return api_key
        except Exception as e:
            logger.warning(f"Could not retrieve from keyring: {e}")

        # Fallback to environment variable
        if self.settings.gemini_api_key:
            logger.debug("Gemini API key retrieved from environment")
            return self.settings.gemini_api_key

        logger.warning("Gemini API key not found in keyring or environment")
        return None

    def delete_robinhood_credentials(self) -> bool:
        """
        Delete Robinhood credentials from keyring.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            keyring.delete_password(self.SERVICE_NAME, self.KEY_ROBINHOOD_USERNAME)
            keyring.delete_password(self.SERVICE_NAME, self.KEY_ROBINHOOD_PASSWORD)
            logger.info("Robinhood credentials deleted from keyring")
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning("No Robinhood credentials found to delete")
            return False
        except Exception as e:
            logger.error(f"Failed to delete Robinhood credentials: {e}")
            return False

    def delete_gemini_api_key(self) -> bool:
        """
        Delete Gemini API key from keyring.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            keyring.delete_password(self.SERVICE_NAME, self.KEY_GEMINI_API_KEY)
            logger.info("Gemini API key deleted from keyring")
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning("No Gemini API key found to delete")
            return False
        except Exception as e:
            logger.error(f"Failed to delete Gemini API key: {e}")
            return False

    def clear_all_credentials(self) -> bool:
        """
        Clear all stored credentials from keyring.

        Returns:
            bool: True if all successful, False otherwise
        """
        success = True
        success &= self.delete_robinhood_credentials()
        success &= self.delete_gemini_api_key()

        if success:
            logger.info("All credentials cleared successfully")
        else:
            logger.warning("Some credentials could not be cleared")

        return success

    def has_robinhood_credentials(self) -> bool:
        """
        Check if Robinhood credentials are available.

        Returns:
            bool: True if both username and password are available
        """
        username = self.get_robinhood_username()
        password = self.get_robinhood_password()
        return username is not None and password is not None

    def has_gemini_api_key(self) -> bool:
        """
        Check if Gemini API key is available.

        Returns:
            bool: True if API key is available
        """
        return self.get_gemini_api_key() is not None

    def get_credentials_status(self) -> dict:
        """
        Get status of all credentials.

        Returns:
            dict: Status of each credential type
        """
        return {
            "robinhood_username": self.get_robinhood_username() is not None,
            "robinhood_password": self.get_robinhood_password() is not None,
            "gemini_api_key": self.get_gemini_api_key() is not None,
        }


# Singleton instance
_credentials_manager = None


def get_credentials_manager() -> CredentialsManager:
    """Get or create CredentialsManager singleton instance."""
    global _credentials_manager
    if _credentials_manager is None:
        _credentials_manager = CredentialsManager()
    return _credentials_manager
