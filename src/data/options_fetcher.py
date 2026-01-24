"""
Options data fetcher.
Retrieves options chains, contracts, and market data from Robinhood.
"""
from typing import List, Optional
from datetime import datetime, date, timedelta
from loguru import logger

from src.data.robinhood_client import get_robinhood_client, RobinhoodAPIError
from src.data.models import OptionContract
from config.settings import get_settings


class OptionsFetcher:
    """Fetches options chain and contract data."""

    def __init__(self):
        """Initialize options fetcher."""
        self.client = get_robinhood_client()
        self.settings = get_settings()
        logger.debug("OptionsFetcher initialized")

    def get_available_expirations(self, symbol: str) -> List[str]:
        """
        Get available option expiration dates for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            list: List of expiration dates (YYYY-MM-DD format)
        """
        try:
            logger.debug(f"Fetching expiration dates for {symbol}")

            dates = self.client.get_available_expiration_dates(symbol)

            logger.info(f"Found {len(dates)} expiration dates for {symbol}")
            return dates

        except Exception as e:
            logger.error(f"Failed to fetch expiration dates for {symbol}: {e}")
            raise

    def get_filtered_expirations(
        self,
        symbol: str,
        min_days: Optional[int] = None,
        max_days: Optional[int] = None
    ) -> List[str]:
        """
        Get filtered expiration dates within a day range.

        Args:
            symbol: Stock ticker symbol
            min_days: Minimum days to expiration (default from settings)
            max_days: Maximum days to expiration (default from settings)

        Returns:
            list: Filtered list of expiration dates
        """
        try:
            # Use settings defaults if not provided
            if min_days is None:
                min_days = self.settings.strategy.min_days_to_expiration
            if max_days is None:
                max_days = self.settings.strategy.max_days_to_expiration

            all_dates = self.get_available_expirations(symbol)

            today = date.today()
            filtered_dates = []

            for date_str in all_dates:
                exp_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                days_to_exp = (exp_date - today).days

                if min_days <= days_to_exp <= max_days:
                    filtered_dates.append(date_str)

            logger.info(
                f"Filtered to {len(filtered_dates)} expirations for {symbol} "
                f"({min_days}-{max_days} days out)"
            )

            return filtered_dates

        except Exception as e:
            logger.error(f"Failed to filter expiration dates for {symbol}: {e}")
            raise

    def get_call_options(
        self,
        symbol: str,
        expiration_date: str,
        strike_price: Optional[float] = None
    ) -> List[OptionContract]:
        """
        Get call options for a specific expiration.

        Args:
            symbol: Stock ticker symbol
            expiration_date: Expiration date (YYYY-MM-DD)
            strike_price: Optional specific strike price

        Returns:
            list: List of OptionContract objects
        """
        try:
            logger.debug(
                f"Fetching call options for {symbol} expiring {expiration_date}"
            )

            options_data = self.client.find_options_for_stock(
                symbol=symbol,
                expiration_date=expiration_date,
                option_type="call",
                strike_price=strike_price
            )

            options = []
            for opt_data in options_data:
                try:
                    option = self._parse_option_contract(symbol, opt_data, "call")
                    if option:
                        options.append(option)
                except Exception as e:
                    logger.warning(f"Failed to parse option contract: {e}")
                    continue

            logger.info(f"Fetched {len(options)} call options for {symbol}")
            return options

        except Exception as e:
            logger.error(
                f"Failed to fetch call options for {symbol} ({expiration_date}): {e}"
            )
            raise

    def get_covered_call_options(
        self,
        symbol: str,
        current_price: float,
        min_days: Optional[int] = None,
        max_days: Optional[int] = None
    ) -> List[OptionContract]:
        """
        Get suitable call options for covered call strategy.

        Filters options by:
        - Expiration date range
        - Out-of-the-money strikes (above current price)
        - Strike price range from settings

        Args:
            symbol: Stock ticker symbol
            current_price: Current stock price
            min_days: Minimum days to expiration
            max_days: Maximum days to expiration

        Returns:
            list: List of suitable OptionContract objects
        """
        try:
            logger.info(
                f"Finding covered call options for {symbol} @ ${current_price:.2f}"
            )

            # Get filtered expiration dates
            expirations = self.get_filtered_expirations(symbol, min_days, max_days)

            if not expirations:
                logger.warning(f"No suitable expiration dates found for {symbol}")
                return []

            # Calculate strike price range
            min_strike_multiplier, max_strike_multiplier = self.settings.strike_range
            min_strike = current_price * min_strike_multiplier
            max_strike = current_price * max_strike_multiplier

            logger.debug(
                f"Strike range: ${min_strike:.2f} - ${max_strike:.2f} "
                f"({min_strike_multiplier:.1%} - {max_strike_multiplier:.1%} OTM)"
            )

            all_options = []

            # Fetch options for each expiration
            for expiration in expirations:
                try:
                    options = self.get_call_options(symbol, expiration)

                    # Filter by strike price
                    filtered = [
                        opt for opt in options
                        if min_strike <= opt.strike_price <= max_strike
                    ]

                    all_options.extend(filtered)

                except Exception as e:
                    logger.warning(
                        f"Failed to fetch options for {symbol} ({expiration}): {e}"
                    )
                    continue

            logger.info(
                f"Found {len(all_options)} covered call candidates for {symbol}"
            )

            return all_options

        except Exception as e:
            logger.error(
                f"Failed to fetch covered call options for {symbol}: {e}"
            )
            raise

    def _parse_option_contract(
        self,
        symbol: str,
        opt_data: dict,
        option_type: str
    ) -> Optional[OptionContract]:
        """
        Parse option contract data from Robinhood API response.

        Args:
            symbol: Stock ticker symbol
            opt_data: Raw option data from API
            option_type: 'call' or 'put'

        Returns:
            OptionContract: Parsed option contract
        """
        try:
            # Extract basic info
            strike_price = float(opt_data.get('strike_price', 0))
            expiration_str = opt_data.get('expiration_date')
            contract_id = opt_data.get('id') or opt_data.get('url')

            if not expiration_str or strike_price == 0:
                return None

            expiration_date = datetime.strptime(expiration_str, "%Y-%m-%d").date()

            # Get market data for pricing and Greeks
            market_data = {}
            if contract_id:
                try:
                    market_data = self.client.get_option_market_data(contract_id) or {}
                except Exception as e:
                    logger.debug(f"Could not fetch market data for option: {e}")

            # Parse pricing
            bid_price = self._safe_float(opt_data.get('bid_price') or market_data.get('bid_price'))
            ask_price = self._safe_float(opt_data.get('ask_price') or market_data.get('ask_price'))
            last_trade_price = self._safe_float(opt_data.get('last_trade_price') or market_data.get('last_trade_price'))

            # Calculate mark price (mid-point)
            mark_price = None
            if bid_price and ask_price:
                mark_price = (bid_price + ask_price) / 2

            # Parse Greeks
            delta = self._safe_float(opt_data.get('delta') or market_data.get('delta'))
            gamma = self._safe_float(opt_data.get('gamma') or market_data.get('gamma'))
            theta = self._safe_float(opt_data.get('theta') or market_data.get('theta'))
            vega = self._safe_float(opt_data.get('vega') or market_data.get('vega'))
            implied_volatility = self._safe_float(opt_data.get('implied_volatility') or market_data.get('implied_volatility'))

            # Parse volume and open interest
            volume = self._safe_int(opt_data.get('volume') or market_data.get('volume'))
            open_interest = self._safe_int(opt_data.get('open_interest') or market_data.get('open_interest'))

            option = OptionContract(
                symbol=symbol.upper(),
                strike_price=strike_price,
                expiration_date=expiration_date,
                option_type=option_type,
                bid_price=bid_price,
                ask_price=ask_price,
                mark_price=mark_price,
                last_trade_price=last_trade_price,
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                implied_volatility=implied_volatility,
                volume=volume,
                open_interest=open_interest,
                contract_id=contract_id
            )

            return option

        except Exception as e:
            logger.error(f"Error parsing option contract: {e}")
            return None

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        """Safely convert value to int."""
        try:
            return int(float(value)) if value is not None else None
        except (ValueError, TypeError):
            return None


# Singleton instance
_options_fetcher = None


def get_options_fetcher() -> OptionsFetcher:
    """Get or create OptionsFetcher singleton instance."""
    global _options_fetcher
    if _options_fetcher is None:
        _options_fetcher = OptionsFetcher()
    return _options_fetcher
