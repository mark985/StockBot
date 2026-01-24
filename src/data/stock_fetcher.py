"""
Stock data fetcher.
Retrieves stock quotes, prices, and fundamentals from Robinhood.
"""
from typing import Optional, List
from datetime import datetime
from loguru import logger

from src.data.robinhood_client import get_robinhood_client, RobinhoodAPIError
from src.data.models import StockQuote


class StockFetcher:
    """Fetches stock market data."""

    def __init__(self):
        """Initialize stock fetcher."""
        self.client = get_robinhood_client()
        logger.debug("StockFetcher initialized")

    def get_quote(self, symbol: str) -> StockQuote:
        """
        Get current stock quote for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            StockQuote: Quote object with current prices

        Raises:
            RobinhoodAPIError: If fetching fails
        """
        try:
            logger.debug(f"Fetching quote for {symbol}")

            quote_data = self.client.get_stock_quote(symbol)

            if not quote_data:
                raise RobinhoodAPIError(f"No quote data returned for {symbol}")

            # Parse quote data
            quote = StockQuote(
                symbol=symbol.upper(),
                last_trade_price=float(quote_data.get('last_trade_price', 0)),
                bid_price=float(quote_data.get('bid_price')) if quote_data.get('bid_price') else None,
                ask_price=float(quote_data.get('ask_price')) if quote_data.get('ask_price') else None,
                previous_close=float(quote_data.get('previous_close')) if quote_data.get('previous_close') else None,
                volume=int(float(quote_data.get('volume', 0))),
                updated_at=datetime.now()
            )

            logger.info(
                f"{symbol} quote: ${quote.last_trade_price:.2f} "
                f"(bid: ${quote.bid_price:.2f}, ask: ${quote.ask_price:.2f})"
                if quote.bid_price and quote.ask_price
                else f"{symbol} quote: ${quote.last_trade_price:.2f}"
            )

            return quote

        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            raise

    def get_multiple_quotes(self, symbols: List[str]) -> List[StockQuote]:
        """
        Get quotes for multiple symbols.

        Args:
            symbols: List of stock ticker symbols

        Returns:
            list: List of StockQuote objects
        """
        quotes = []

        for symbol in symbols:
            try:
                quote = self.get_quote(symbol)
                quotes.append(quote)
            except Exception as e:
                logger.warning(f"Failed to fetch quote for {symbol}: {e}")
                continue

        logger.info(f"Fetched {len(quotes)}/{len(symbols)} quotes successfully")
        return quotes

    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for a symbol (simplified method).

        Args:
            symbol: Stock ticker symbol

        Returns:
            float: Current price
        """
        try:
            quote = self.get_quote(symbol)
            return quote.last_trade_price
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            raise

    def get_fundamentals(self, symbol: str) -> Optional[dict]:
        """
        Get fundamental data for a stock.

        Args:
            symbol: Stock ticker symbol

        Returns:
            dict: Fundamental data (market cap, PE ratio, etc.)
        """
        try:
            logger.debug(f"Fetching fundamentals for {symbol}")

            fundamentals = self.client.get_stock_fundamentals(symbol)

            if fundamentals:
                logger.info(f"Fetched fundamentals for {symbol}")
            else:
                logger.warning(f"No fundamentals data for {symbol}")

            return fundamentals

        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
            raise

    def get_bid_ask_spread(self, symbol: str) -> Optional[float]:
        """
        Calculate bid-ask spread for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            float: Bid-ask spread, or None if not available
        """
        try:
            quote = self.get_quote(symbol)

            if quote.bid_price and quote.ask_price:
                spread = quote.ask_price - quote.bid_price
                spread_percent = (spread / quote.last_trade_price) * 100
                logger.debug(
                    f"{symbol} spread: ${spread:.2f} ({spread_percent:.2f}%)"
                )
                return spread

            return None

        except Exception as e:
            logger.error(f"Failed to calculate spread for {symbol}: {e}")
            return None


# Singleton instance
_stock_fetcher = None


def get_stock_fetcher() -> StockFetcher:
    """Get or create StockFetcher singleton instance."""
    global _stock_fetcher
    if _stock_fetcher is None:
        _stock_fetcher = StockFetcher()
    return _stock_fetcher
