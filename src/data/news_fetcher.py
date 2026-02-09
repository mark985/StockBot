"""
News fetcher for stock symbols.
Fetches the latest news for a given stock to help understand price movements.
"""
import requests
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from loguru import logger

from src.data.models import NewsArticle


class NewsFetcher:
    """Fetches news articles for stock symbols."""

    def __init__(self):
        """Initialize the news fetcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        logger.debug("NewsFetcher initialized")

    def get_news(self, symbol: str, limit: int = 20, max_age_hours: int = 24) -> List[NewsArticle]:
        """
        Fetch latest news for a stock symbol.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            limit: Maximum number of articles to return (default: 20)
            max_age_hours: Only include articles from the last N hours (default: 24)

        Returns:
            List of NewsArticle objects
        """
        try:
            logger.info(f"Fetching news for {symbol}")

            # Use Yahoo Finance API (no authentication required)
            url = "https://query2.finance.yahoo.com/v1/finance/search"
            params = {
                'q': symbol,
                'quotesCount': 0,
                'newsCount': limit,
                'enableFuzzyQuery': False,
                'quotesQueryId': 'tss_match_phrase_query',
                'newsQueryId': 'news_ss_symbols',
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            news_items = data.get('news', [])

            if not news_items:
                logger.warning(f"No news found for {symbol}")
                return []

            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=max_age_hours)
            articles = []

            for item in news_items:
                try:
                    # Parse publish time
                    publish_time = None
                    if 'providerPublishTime' in item:
                        publish_time = datetime.fromtimestamp(
                            item['providerPublishTime'], tz=timezone.utc
                        )

                    # Skip articles older than the cutoff
                    if publish_time and publish_time < cutoff:
                        continue

                    article = NewsArticle(
                        title=item.get('title', 'No title'),
                        publisher=item.get('publisher', 'Unknown'),
                        link=item.get('link', ''),
                        publish_time=publish_time,
                        thumbnail=item.get('thumbnail', {}).get('resolutions', [{}])[0].get('url') if item.get('thumbnail') else None,
                        summary=item.get('summary', '')
                    )
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to parse news item: {e}")
                    continue

            logger.info(f"Found {len(articles)} news articles for {symbol} (within {max_age_hours}h)")
            return articles

        except requests.RequestException as e:
            logger.error(f"Failed to fetch news for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching news for {symbol}: {e}")
            return []


# Singleton instance
_news_fetcher: Optional[NewsFetcher] = None


def get_news_fetcher() -> NewsFetcher:
    """Get or create the singleton NewsFetcher instance."""
    global _news_fetcher
    if _news_fetcher is None:
        _news_fetcher = NewsFetcher()
    return _news_fetcher
