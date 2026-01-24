"""
Robinhood API client wrapper with rate limiting and error handling.
Central interface for all Robinhood API calls.
"""
import robin_stocks.robinhood as rh
from typing import Optional, Dict, Any, List
from loguru import logger

from src.data.rate_limiter import rate_limited, with_exponential_backoff, get_rate_limiter
from src.auth.robinhood_auth import ensure_authenticated


class RobinhoodAPIError(Exception):
    """Custom exception for Robinhood API errors."""
    pass


class RobinhoodClient:
    """
    Wrapper around robin_stocks with rate limiting and error handling.

    All Robinhood API calls should go through this client to ensure:
    - Rate limiting is enforced
    - Errors are handled consistently
    - Authentication is maintained
    - Logging is centralized
    """

    def __init__(self):
        """Initialize Robinhood client."""
        self.rate_limiter = get_rate_limiter()
        logger.debug("RobinhoodClient initialized")

    def ensure_auth(self) -> None:
        """Ensure we're authenticated before making API calls."""
        try:
            ensure_authenticated()
        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            raise RobinhoodAPIError(f"Not authenticated: {e}") from e

    @with_exponential_backoff(max_tries=3)
    @rate_limited
    def get_account_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get account profile information.

        Returns:
            dict: Account profile data
        """
        try:
            self.ensure_auth()
            logger.debug("Fetching account profile")
            profile = rh.profiles.load_account_profile()
            return profile
        except Exception as e:
            logger.error(f"Failed to fetch account profile: {e}")
            raise RobinhoodAPIError(f"Failed to get account profile: {e}") from e

    @with_exponential_backoff(max_tries=3)
    @rate_limited
    def get_portfolio(self) -> Optional[Dict[str, Any]]:
        """
        Get portfolio summary.

        Returns:
            dict: Portfolio data including equity, buying power, etc.
        """
        try:
            self.ensure_auth()
            logger.debug("Fetching portfolio summary")
            portfolio = rh.profiles.load_portfolio_profile()
            return portfolio
        except Exception as e:
            logger.error(f"Failed to fetch portfolio: {e}")
            raise RobinhoodAPIError(f"Failed to get portfolio: {e}") from e

    @with_exponential_backoff(max_tries=3)
    @rate_limited
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        Get all current stock positions.

        Returns:
            list: List of position dictionaries
        """
        try:
            self.ensure_auth()
            logger.debug("Fetching all positions")
            positions = rh.account.get_open_stock_positions()
            return positions or []
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise RobinhoodAPIError(f"Failed to get positions: {e}") from e

    @with_exponential_backoff(max_tries=3)
    @rate_limited
    def get_stock_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get stock quote for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            dict: Quote data
        """
        try:
            self.ensure_auth()
            logger.debug(f"Fetching quote for {symbol}")
            quote = rh.stocks.get_latest_price(symbol, priceType='regular', includeExtendedHours=True)

            # Get additional quote data
            quote_data = rh.stocks.get_quotes(symbol)

            if quote_data and len(quote_data) > 0:
                return quote_data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            raise RobinhoodAPIError(f"Failed to get quote for {symbol}: {e}") from e

    @with_exponential_backoff(max_tries=3)
    @rate_limited
    def get_stock_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get stock fundamentals.

        Args:
            symbol: Stock ticker symbol

        Returns:
            dict: Fundamental data
        """
        try:
            self.ensure_auth()
            logger.debug(f"Fetching fundamentals for {symbol}")
            fundamentals = rh.stocks.get_fundamentals(symbol)
            if fundamentals and len(fundamentals) > 0:
                return fundamentals[0]
            return None
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
            raise RobinhoodAPIError(f"Failed to get fundamentals for {symbol}: {e}") from e

    @with_exponential_backoff(max_tries=3)
    @rate_limited
    def get_options_chains(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get options chain IDs for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            dict: Options chain data
        """
        try:
            self.ensure_auth()
            logger.debug(f"Fetching options chains for {symbol}")
            chains = rh.options.get_chains(symbol)
            return chains
        except Exception as e:
            logger.error(f"Failed to fetch options chains for {symbol}: {e}")
            raise RobinhoodAPIError(f"Failed to get options chains for {symbol}: {e}") from e

    @with_exponential_backoff(max_tries=3)
    @rate_limited
    def find_options_for_stock(
        self,
        symbol: str,
        expiration_date: Optional[str] = None,
        option_type: str = "call",
        strike_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find options for a stock with filters.

        Args:
            symbol: Stock ticker symbol
            expiration_date: Expiration date (YYYY-MM-DD format)
            option_type: 'call' or 'put'
            strike_price: Specific strike price

        Returns:
            list: List of option contracts
        """
        try:
            self.ensure_auth()
            logger.debug(
                f"Finding {option_type} options for {symbol} "
                f"(expiration={expiration_date}, strike={strike_price})"
            )

            options = rh.options.find_options_for_stock_by_expiration(
                symbol,
                expirationDate=expiration_date,
                optionType=option_type
            )

            # Filter by strike price if specified
            if strike_price and options:
                options = [opt for opt in options if float(opt.get('strike_price', 0)) == strike_price]

            return options or []
        except Exception as e:
            logger.error(f"Failed to find options for {symbol}: {e}")
            raise RobinhoodAPIError(f"Failed to find options for {symbol}: {e}") from e

    @with_exponential_backoff(max_tries=3)
    @rate_limited
    def get_option_market_data(self, option_id: str) -> Optional[Dict[str, Any]]:
        """
        Get market data for a specific option contract.

        Args:
            option_id: Option instrument ID

        Returns:
            dict: Market data including bid, ask, volume, etc.
        """
        try:
            self.ensure_auth()
            logger.debug(f"Fetching market data for option {option_id}")
            market_data = rh.options.get_option_market_data_by_id(option_id)
            return market_data
        except Exception as e:
            logger.error(f"Failed to fetch option market data for {option_id}: {e}")
            raise RobinhoodAPIError(f"Failed to get option market data: {e}") from e

    @with_exponential_backoff(max_tries=3)
    @rate_limited
    def get_available_expiration_dates(self, symbol: str) -> List[str]:
        """
        Get available option expiration dates for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            list: List of expiration dates (YYYY-MM-DD format)
        """
        try:
            self.ensure_auth()
            logger.debug(f"Fetching expiration dates for {symbol}")
            dates = rh.options.get_chains(symbol)

            if dates and 'expiration_dates' in dates:
                return dates['expiration_dates']
            return []
        except Exception as e:
            logger.error(f"Failed to fetch expiration dates for {symbol}: {e}")
            raise RobinhoodAPIError(f"Failed to get expiration dates: {e}") from e

    def get_rate_limiter_stats(self) -> Dict[str, Any]:
        """
        Get current rate limiter statistics.

        Returns:
            dict: Rate limiter stats
        """
        return self.rate_limiter.get_stats()

    def log_rate_limit_status(self) -> None:
        """Log current rate limiting status."""
        stats = self.get_rate_limiter_stats()
        logger.info(
            f"Rate limit status: {stats['calls_last_minute']}/{stats['minute_limit']} per minute, "
            f"{stats['calls_last_hour']}/{stats['hour_limit']} per hour, "
            f"failures: {stats['failure_count']}, "
            f"circuit_open: {stats['circuit_open']}"
        )


# Singleton instance
_robinhood_client = None


def get_robinhood_client() -> RobinhoodClient:
    """Get or create RobinhoodClient singleton instance."""
    global _robinhood_client
    if _robinhood_client is None:
        _robinhood_client = RobinhoodClient()
    return _robinhood_client
