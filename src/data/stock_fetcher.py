"""
Stock data fetcher.
Retrieves stock quotes, prices, and fundamentals from Robinhood.
Uses the custom Robinhood client for reliable API access.
"""
from typing import Optional, List
from datetime import datetime
from loguru import logger

from src.robinhood.client import RobinhoodClient
from src.robinhood.exceptions import APIError
from src.auth.robinhood_auth import ensure_authenticated
from src.data.models import StockQuote


class StockFetcher:
    """Fetches stock market data using custom Robinhood client."""

    def __init__(self):
        """Initialize stock fetcher."""
        self._client = None
        logger.debug("StockFetcher initialized")

    @property
    def client(self) -> RobinhoodClient:
        """Get authenticated Robinhood client."""
        if self._client is None:
            auth = ensure_authenticated()
            self._client = auth.get_client()
        return self._client

    def get_quote(self, symbol: str) -> StockQuote:
        """
        Get current stock quote for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            StockQuote: Quote object with current prices

        Raises:
            APIError: If fetching fails
        """
        try:
            logger.debug(f"Fetching quote for {symbol}")

            quote_data = self.client.get_quote(symbol.upper())

            if not quote_data:
                raise APIError(f"No quote data returned for {symbol}")

            # Parse quote data
            quote = StockQuote(
                symbol=symbol.upper(),
                last_trade_price=float(quote_data.get('last_trade_price', 0)),
                bid_price=float(quote_data.get('bid_price')) if quote_data.get('bid_price') else None,
                ask_price=float(quote_data.get('ask_price')) if quote_data.get('ask_price') else None,
                previous_close=float(quote_data.get('previous_close')) if quote_data.get('previous_close') else None,
                volume=int(float(quote_data.get('volume', 0))) if quote_data.get('volume') else 0,
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
        Get quotes for multiple symbols efficiently.

        Args:
            symbols: List of stock ticker symbols

        Returns:
            list: List of StockQuote objects
        """
        try:
            logger.debug(f"Fetching quotes for {len(symbols)} symbols")

            # Use batch quotes endpoint
            quotes_data = self.client.get_quotes([s.upper() for s in symbols])

            quotes = []
            for quote_data in quotes_data:
                if quote_data:
                    try:
                        quote = StockQuote(
                            symbol=quote_data.get('symbol', '').upper(),
                            last_trade_price=float(quote_data.get('last_trade_price', 0)),
                            bid_price=float(quote_data.get('bid_price')) if quote_data.get('bid_price') else None,
                            ask_price=float(quote_data.get('ask_price')) if quote_data.get('ask_price') else None,
                            previous_close=float(quote_data.get('previous_close')) if quote_data.get('previous_close') else None,
                            volume=int(float(quote_data.get('volume', 0))) if quote_data.get('volume') else 0,
                            updated_at=datetime.now()
                        )
                        quotes.append(quote)
                    except Exception as e:
                        logger.warning(f"Failed to parse quote: {e}")
                        continue

            logger.info(f"Fetched {len(quotes)}/{len(symbols)} quotes successfully")
            return quotes

        except Exception as e:
            logger.error(f"Failed to fetch multiple quotes: {e}")
            # Fall back to individual fetching
            quotes = []
            for symbol in symbols:
                try:
                    quote = self.get_quote(symbol)
                    quotes.append(quote)
                except Exception:
                    continue
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

            # Fundamentals endpoint
            url = f"https://api.robinhood.com/fundamentals/{symbol.upper()}/"
            fundamentals = self.client.get(url)

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
