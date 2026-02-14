"""
Options data fetcher.
Retrieves options chains, contracts, and market data from Robinhood.
Uses the custom Robinhood client for reliable API access.
"""
from typing import List, Optional
from datetime import datetime, date
from loguru import logger

from src.robinhood.client import RobinhoodClient
from src.robinhood.endpoints import Endpoints
from src.auth.robinhood_auth import ensure_authenticated
from src.data.models import OptionContract
from config.settings import get_settings


class OptionsFetcher:
    """Fetches options chain and contract data using custom Robinhood client."""

    def __init__(self):
        """Initialize options fetcher."""
        self.settings = get_settings()
        self._client = None
        logger.debug("OptionsFetcher initialized")

    @property
    def client(self) -> RobinhoodClient:
        """Get authenticated Robinhood client."""
        if self._client is None:
            auth = ensure_authenticated()
            self._client = auth.get_client()
        return self._client

    def get_options_chain(self, symbol: str) -> dict:
        """
        Get options chain metadata for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            dict: Options chain with id, expiration_dates, etc.
        """
        try:
            logger.debug(f"Fetching options chain for {symbol}")

            # First, get the instrument to find the instrument ID
            instrument = self.client.get_instrument_by_symbol(symbol.upper())
            instrument_id = instrument.get("id")

            if not instrument_id:
                raise ValueError(f"Could not find instrument ID for {symbol}")

            logger.debug(f"Found instrument ID for {symbol}: {instrument_id}")

            # Query options chain by instrument ID
            response = self.client.get(Endpoints.OPTIONS_CHAINS, params={"equity_instrument_ids": instrument_id})

            results = response.get("results", [])
            if not results:
                raise ValueError(f"No options chain found for {symbol}")

            chain = results[0]
            expiration_count = len(chain.get("expiration_dates", []))
            logger.info(f"Found options chain for {symbol}: {expiration_count} expirations")

            if expiration_count == 0:
                logger.warning(f"Options chain for {symbol} has no expiration dates")

            return chain

        except Exception as e:
            logger.error(f"Failed to fetch options chain for {symbol}: {e}")
            raise

    def get_available_expirations(self, symbol: str) -> List[str]:
        """
        Get available option expiration dates for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            list: List of expiration dates (YYYY-MM-DD format)
        """
        try:
            chain = self.get_options_chain(symbol)
            dates = chain.get("expiration_dates", [])
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
            logger.debug(f"Fetching call options for {symbol} expiring {expiration_date}")

            # Get options chain ID first
            chain = self.get_options_chain(symbol)
            chain_id = chain["id"]

            # Fetch call options instruments
            instruments = self.client.get_options_instruments(
                chain_id=chain_id,
                expiration_dates=[expiration_date],
                option_type="call"
            )

            if not instruments:
                logger.info(f"No call options found for {symbol} ({expiration_date})")
                return []

            # Filter by strike price if specified
            if strike_price is not None:
                instruments = [i for i in instruments if abs(float(i.get("strike_price", 0)) - strike_price) < 0.01]

            # Get market data for all options in batch
            option_ids = [inst["id"] for inst in instruments if inst.get("id")]
            market_data_map = {}

            if option_ids:
                try:
                    market_data_list = self.client.get_options_market_data(option_ids)
                    for md in market_data_list:
                        if md and md.get("instrument"):
                            inst_id = md["instrument"].split("/")[-2]
                            market_data_map[inst_id] = md
                except Exception as e:
                    logger.warning(f"Could not fetch market data: {e}")

            # Parse options
            options = []
            for inst in instruments:
                try:
                    inst_id = inst.get("id")
                    market_data = market_data_map.get(inst_id, {})
                    option = self._parse_option_contract(symbol, inst, market_data, "call")
                    if option:
                        options.append(option)
                except Exception as e:
                    logger.warning(f"Failed to parse option contract: {e}")
                    continue

            logger.info(f"Fetched {len(options)} call options for {symbol} ({expiration_date})")
            return options

        except Exception as e:
            logger.error(f"Failed to fetch call options for {symbol} ({expiration_date}): {e}")
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
            logger.info(f"Finding covered call options for {symbol} @ ${current_price:.2f}")

            # Get options chain and filtered expirations
            chain = self.get_options_chain(symbol)
            chain_id = chain["id"]

            # Get filtered expiration dates
            all_dates = chain.get("expiration_dates", [])
            if min_days is None:
                min_days = self.settings.strategy.min_days_to_expiration
            if max_days is None:
                max_days = self.settings.strategy.max_days_to_expiration

            today = date.today()
            expirations = []
            for date_str in all_dates:
                exp_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                days_to_exp = (exp_date - today).days
                if min_days <= days_to_exp <= max_days:
                    expirations.append(date_str)

            if not expirations:
                logger.warning(f"No suitable expiration dates found for {symbol}")
                return []

            logger.info(f"Filtered to {len(expirations)} expirations ({min_days}-{max_days} days)")

            # Calculate strike price range
            min_strike_multiplier, max_strike_multiplier = self.settings.strike_range
            min_strike = current_price * min_strike_multiplier
            max_strike = current_price * max_strike_multiplier

            logger.debug(f"Strike range: ${min_strike:.2f} - ${max_strike:.2f}")

            # Fetch all call options for these expirations in one request
            instruments = self.client.get_options_instruments(
                chain_id=chain_id,
                expiration_dates=expirations,
                option_type="call"
            )

            if not instruments:
                logger.warning(f"No call options found for {symbol}")
                return []

            # Filter by strike price range
            filtered_instruments = [
                inst for inst in instruments
                if min_strike <= float(inst.get("strike_price", 0)) <= max_strike
            ]

            logger.info(f"Filtered to {len(filtered_instruments)} options in strike range")

            # Get market data for filtered options
            option_ids = [inst["id"] for inst in filtered_instruments if inst.get("id")]
            market_data_map = {}

            if option_ids:
                try:
                    market_data_list = self.client.get_options_market_data(option_ids)
                    for md in market_data_list:
                        if md and md.get("instrument"):
                            inst_id = md["instrument"].split("/")[-2]
                            market_data_map[inst_id] = md
                except Exception as e:
                    logger.warning(f"Could not fetch market data: {e}")

            # Parse options
            options = []
            for inst in filtered_instruments:
                try:
                    inst_id = inst.get("id")
                    market_data = market_data_map.get(inst_id, {})
                    option = self._parse_option_contract(symbol, inst, market_data, "call")
                    if option:
                        options.append(option)
                except Exception as e:
                    logger.warning(f"Failed to parse option contract: {e}")
                    continue

            # Apply quality filters (volume, OI, bid/ask spread)
            pre_filter_count = len(options)
            min_volume = self.settings.strategy.min_option_volume
            min_oi = self.settings.strategy.min_open_interest
            max_spread_pct = self.settings.strategy.max_bid_ask_spread_percent

            quality_options = []
            for opt in options:
                # Skip if volume is below minimum
                if not opt.volume or opt.volume < min_volume:
                    continue
                # Skip if open interest is below minimum
                if not opt.open_interest or opt.open_interest < min_oi:
                    continue
                # Skip if bid/ask is missing
                if not opt.bid_price or not opt.ask_price:
                    continue
                # Skip if bid/ask spread is too wide
                midpoint = (opt.bid_price + opt.ask_price) / 2
                if midpoint > 0:
                    spread = (opt.ask_price - opt.bid_price) / midpoint
                    if spread > max_spread_pct:
                        continue
                quality_options.append(opt)

            filtered_out = pre_filter_count - len(quality_options)
            if filtered_out > 0:
                logger.info(
                    f"Quality filter removed {filtered_out} options for {symbol} "
                    f"(vol>={min_volume}, OI>={min_oi}, spread<{max_spread_pct:.0%})"
                )

            logger.info(f"Found {len(quality_options)} covered call candidates for {symbol}")
            return quality_options

        except Exception as e:
            logger.error(f"Failed to fetch covered call options for {symbol}: {e}")
            raise

    def get_put_options(
        self,
        symbol: str,
        expiration_date: str,
        strike_price: Optional[float] = None
    ) -> List[OptionContract]:
        """
        Get put options for a specific expiration.

        Args:
            symbol: Stock ticker symbol
            expiration_date: Expiration date (YYYY-MM-DD)
            strike_price: Optional specific strike price

        Returns:
            list: List of OptionContract objects
        """
        try:
            logger.debug(f"Fetching put options for {symbol} expiring {expiration_date}")

            chain = self.get_options_chain(symbol)
            chain_id = chain["id"]

            instruments = self.client.get_options_instruments(
                chain_id=chain_id,
                expiration_dates=[expiration_date],
                option_type="put"
            )

            if not instruments:
                logger.info(f"No put options found for {symbol} ({expiration_date})")
                return []

            if strike_price is not None:
                instruments = [i for i in instruments if abs(float(i.get("strike_price", 0)) - strike_price) < 0.01]

            option_ids = [inst["id"] for inst in instruments if inst.get("id")]
            market_data_map = {}

            if option_ids:
                try:
                    market_data_list = self.client.get_options_market_data(option_ids)
                    for md in market_data_list:
                        if md and md.get("instrument"):
                            inst_id = md["instrument"].split("/")[-2]
                            market_data_map[inst_id] = md
                except Exception as e:
                    logger.warning(f"Could not fetch market data: {e}")

            options = []
            for inst in instruments:
                try:
                    inst_id = inst.get("id")
                    market_data = market_data_map.get(inst_id, {})
                    option = self._parse_option_contract(symbol, inst, market_data, "put")
                    if option:
                        options.append(option)
                except Exception as e:
                    logger.warning(f"Failed to parse option contract: {e}")
                    continue

            logger.info(f"Fetched {len(options)} put options for {symbol} ({expiration_date})")
            return options

        except Exception as e:
            logger.error(f"Failed to fetch put options for {symbol} ({expiration_date}): {e}")
            raise

    def get_cash_secured_put_options(
        self,
        symbol: str,
        current_price: float,
        min_days: Optional[int] = None,
        max_days: Optional[int] = None
    ) -> List[OptionContract]:
        """
        Get suitable put options for cash-secured put strategy.

        Filters options by:
        - Expiration date range
        - Out-of-the-money strikes (below current price)
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
            logger.info(f"Finding cash-secured put options for {symbol} @ ${current_price:.2f}")

            chain = self.get_options_chain(symbol)
            chain_id = chain["id"]

            all_dates = chain.get("expiration_dates", [])
            if min_days is None:
                min_days = self.settings.strategy.min_days_to_expiration
            if max_days is None:
                max_days = self.settings.strategy.max_days_to_expiration

            today = date.today()
            expirations = []
            for date_str in all_dates:
                exp_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                days_to_exp = (exp_date - today).days
                if min_days <= days_to_exp <= max_days:
                    expirations.append(date_str)

            if not expirations:
                logger.warning(f"No suitable expiration dates found for {symbol}")
                return []

            logger.info(f"Filtered to {len(expirations)} expirations ({min_days}-{max_days} days)")

            # Calculate strike price range (below current price for OTM puts)
            min_strike_multiplier, max_strike_multiplier = self.settings.put_strike_range
            min_strike = current_price * min_strike_multiplier
            max_strike = current_price * max_strike_multiplier

            logger.debug(f"Put strike range: ${min_strike:.2f} - ${max_strike:.2f}")

            instruments = self.client.get_options_instruments(
                chain_id=chain_id,
                expiration_dates=expirations,
                option_type="put"
            )

            if not instruments:
                logger.warning(f"No put options found for {symbol}")
                return []

            filtered_instruments = [
                inst for inst in instruments
                if min_strike <= float(inst.get("strike_price", 0)) <= max_strike
            ]

            logger.info(f"Filtered to {len(filtered_instruments)} options in strike range")

            option_ids = [inst["id"] for inst in filtered_instruments if inst.get("id")]
            market_data_map = {}

            if option_ids:
                try:
                    market_data_list = self.client.get_options_market_data(option_ids)
                    for md in market_data_list:
                        if md and md.get("instrument"):
                            inst_id = md["instrument"].split("/")[-2]
                            market_data_map[inst_id] = md
                except Exception as e:
                    logger.warning(f"Could not fetch market data: {e}")

            options = []
            for inst in filtered_instruments:
                try:
                    inst_id = inst.get("id")
                    market_data = market_data_map.get(inst_id, {})
                    option = self._parse_option_contract(symbol, inst, market_data, "put")
                    if option:
                        options.append(option)
                except Exception as e:
                    logger.warning(f"Failed to parse option contract: {e}")
                    continue

            # Apply quality filters (volume, OI, bid/ask spread)
            pre_filter_count = len(options)
            min_volume = self.settings.strategy.min_option_volume
            min_oi = self.settings.strategy.min_open_interest
            max_spread_pct = self.settings.strategy.max_bid_ask_spread_percent

            quality_options = []
            for opt in options:
                if not opt.volume or opt.volume < min_volume:
                    continue
                if not opt.open_interest or opt.open_interest < min_oi:
                    continue
                if not opt.bid_price or not opt.ask_price:
                    continue
                midpoint = (opt.bid_price + opt.ask_price) / 2
                if midpoint > 0:
                    spread = (opt.ask_price - opt.bid_price) / midpoint
                    if spread > max_spread_pct:
                        continue
                quality_options.append(opt)

            filtered_out = pre_filter_count - len(quality_options)
            if filtered_out > 0:
                logger.info(
                    f"Quality filter removed {filtered_out} options for {symbol} "
                    f"(vol>={min_volume}, OI>={min_oi}, spread<{max_spread_pct:.0%})"
                )

            logger.info(f"Found {len(quality_options)} cash-secured put candidates for {symbol}")
            return quality_options

        except Exception as e:
            logger.error(f"Failed to fetch cash-secured put options for {symbol}: {e}")
            raise

    def _parse_option_contract(
        self,
        symbol: str,
        instrument: dict,
        market_data: dict,
        option_type: str
    ) -> Optional[OptionContract]:
        """
        Parse option contract from instrument and market data.

        Args:
            symbol: Stock ticker symbol
            instrument: Option instrument data
            market_data: Market data (prices, Greeks)
            option_type: 'call' or 'put'

        Returns:
            OptionContract: Parsed option contract
        """
        try:
            strike_price = float(instrument.get('strike_price', 0))
            expiration_str = instrument.get('expiration_date')
            contract_id = instrument.get('id')

            if not expiration_str or strike_price == 0:
                return None

            expiration_date = datetime.strptime(expiration_str, "%Y-%m-%d").date()

            # Parse pricing from market data
            bid_price = self._safe_float(market_data.get('bid_price'))
            ask_price = self._safe_float(market_data.get('ask_price'))
            last_trade_price = self._safe_float(market_data.get('last_trade_price'))

            # Calculate mark price (mid-point)
            mark_price = None
            if bid_price and ask_price:
                mark_price = (bid_price + ask_price) / 2

            # Parse Greeks
            delta = self._safe_float(market_data.get('delta'))
            gamma = self._safe_float(market_data.get('gamma'))
            theta = self._safe_float(market_data.get('theta'))
            vega = self._safe_float(market_data.get('vega'))
            implied_volatility = self._safe_float(market_data.get('implied_volatility'))

            # Parse volume and open interest
            volume = self._safe_int(market_data.get('volume'))
            open_interest = self._safe_int(market_data.get('open_interest'))

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
