"""
Portfolio data fetcher.
Retrieves and transforms portfolio and position data from Robinhood.
"""
from typing import List, Optional
from loguru import logger

from src.data.robinhood_client import get_robinhood_client, RobinhoodAPIError
from src.data.models import Portfolio, PortfolioPosition


class PortfolioFetcher:
    """Fetches and manages portfolio data."""

    def __init__(self):
        """Initialize portfolio fetcher."""
        self.client = get_robinhood_client()
        logger.debug("PortfolioFetcher initialized")

    def get_portfolio(self) -> Portfolio:
        """
        Fetch complete portfolio including all positions.

        Returns:
            Portfolio: Portfolio object with all positions

        Raises:
            RobinhoodAPIError: If fetching fails
        """
        try:
            logger.info("Fetching portfolio data")

            # Get portfolio summary
            portfolio_data = self.client.get_portfolio()

            if not portfolio_data:
                raise RobinhoodAPIError("No portfolio data returned")

            # Get all positions
            positions = self.get_positions()

            # Build Portfolio model
            portfolio = Portfolio(
                equity=float(portfolio_data.get('equity', 0)),
                extended_hours_equity=float(portfolio_data.get('extended_hours_equity', 0)) if portfolio_data.get('extended_hours_equity') else None,
                cash=float(portfolio_data.get('withdrawable_amount', 0)) if portfolio_data.get('withdrawable_amount') else None,
                buying_power=float(portfolio_data.get('excess_margin', 0)) if portfolio_data.get('excess_margin') else None,
                positions=positions
            )

            logger.info(
                f"Portfolio fetched: ${portfolio.equity:,.2f} equity, "
                f"{len(positions)} positions"
            )

            return portfolio

        except Exception as e:
            logger.error(f"Failed to fetch portfolio: {e}")
            raise

    def get_positions(self) -> List[PortfolioPosition]:
        """
        Fetch all current positions.

        Returns:
            list: List of PortfolioPosition objects
        """
        try:
            logger.info("Fetching positions")

            positions_data = self.client.get_all_positions()

            positions = []
            for pos_data in positions_data:
                try:
                    position = self._parse_position(pos_data)
                    if position:
                        positions.append(position)
                except Exception as e:
                    logger.warning(f"Failed to parse position: {e}")
                    continue

            logger.info(f"Fetched {len(positions)} positions")
            return positions

        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise

    def _parse_position(self, pos_data: dict) -> Optional[PortfolioPosition]:
        """
        Parse position data from Robinhood API response.

        Args:
            pos_data: Raw position data from API

        Returns:
            PortfolioPosition: Parsed position object
        """
        try:
            # Extract instrument URL to get symbol
            instrument_url = pos_data.get('instrument')
            if not instrument_url:
                logger.warning("Position missing instrument URL")
                return None

            # The symbol is typically in the URL or we need to fetch it
            # For now, we'll fetch instrument data
            import robin_stocks.robinhood as rh
            instrument = rh.stocks.get_instrument_by_url(instrument_url)
            symbol = instrument.get('symbol') if instrument else None

            if not symbol:
                logger.warning("Could not determine symbol for position")
                return None

            quantity = float(pos_data.get('quantity', 0))
            if quantity == 0:
                return None  # Skip zero quantity positions

            average_buy_price = float(pos_data.get('average_buy_price', 0))

            # Get current price if available
            current_price = None
            equity = pos_data.get('equity')
            if equity:
                current_price = float(equity) / quantity if quantity > 0 else None

            # Calculate percent change
            percent_change = None
            if current_price and average_buy_price > 0:
                percent_change = ((current_price - average_buy_price) / average_buy_price) * 100

            # Calculate equity change
            equity_change = None
            if current_price and average_buy_price:
                equity_change = (current_price - average_buy_price) * quantity

            position = PortfolioPosition(
                symbol=symbol,
                quantity=quantity,
                average_buy_price=average_buy_price,
                current_price=current_price,
                equity=float(equity) if equity else None,
                percent_change=percent_change,
                equity_change=equity_change,
                type="stock"
            )

            logger.debug(
                f"Parsed position: {symbol} - {quantity} shares @ ${average_buy_price:.2f}"
            )

            return position

        except Exception as e:
            logger.error(f"Error parsing position data: {e}")
            return None

    def get_covered_call_eligible_positions(self) -> List[PortfolioPosition]:
        """
        Get positions that are eligible for covered calls (100+ shares).

        Returns:
            list: List of eligible positions
        """
        try:
            portfolio = self.get_portfolio()
            eligible = portfolio.covered_call_eligible_positions

            logger.info(f"Found {len(eligible)} covered call eligible positions")

            for pos in eligible:
                contracts = int(pos.quantity // 100)
                logger.debug(
                    f"{pos.symbol}: {pos.quantity} shares ({contracts} contracts available)"
                )

            return eligible

        except Exception as e:
            logger.error(f"Failed to get eligible positions: {e}")
            raise


# Singleton instance
_portfolio_fetcher = None


def get_portfolio_fetcher() -> PortfolioFetcher:
    """Get or create PortfolioFetcher singleton instance."""
    global _portfolio_fetcher
    if _portfolio_fetcher is None:
        _portfolio_fetcher = PortfolioFetcher()
    return _portfolio_fetcher
