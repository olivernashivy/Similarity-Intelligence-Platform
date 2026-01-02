"""Fetch and extract article content from URLs."""
import logging
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup
from newspaper import Article
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ArticleCache:
    """Simple in-memory cache for fetched articles."""

    def __init__(self, ttl_hours: int = 24):
        """
        Initialize cache.

        Args:
            ttl_hours: Time-to-live for cached articles in hours
        """
        self.cache: Dict[str, Dict] = {}
        self.ttl_hours = ttl_hours

    def get(self, url: str) -> Optional[str]:
        """Get article from cache if available and not expired."""
        url_hash = self._hash_url(url)

        if url_hash in self.cache:
            cached = self.cache[url_hash]
            # Check if expired
            if datetime.utcnow() < cached['expires_at']:
                logger.debug(f"Cache hit for URL: {url[:50]}")
                return cached['content']
            else:
                # Remove expired entry
                del self.cache[url_hash]
                logger.debug(f"Cache expired for URL: {url[:50]}")

        return None

    def set(self, url: str, content: str):
        """Cache article content."""
        url_hash = self._hash_url(url)
        self.cache[url_hash] = {
            'content': content,
            'expires_at': datetime.utcnow() + timedelta(hours=self.ttl_hours),
            'cached_at': datetime.utcnow()
        }
        logger.debug(f"Cached article: {url[:50]}")

    def _hash_url(self, url: str) -> str:
        """Create hash of URL for cache key."""
        return hashlib.md5(url.encode()).hexdigest()

    def clear(self):
        """Clear all cached articles."""
        self.cache.clear()
        logger.info("Article cache cleared")


# Global cache instance
_article_cache = ArticleCache(ttl_hours=24)


class ArticleFetcher:
    """Fetch and extract article content from URLs."""

    def __init__(self, use_cache: bool = True, timeout: int = 10):
        """
        Initialize article fetcher.

        Args:
            use_cache: Whether to use caching
            timeout: Request timeout in seconds
        """
        self.use_cache = use_cache
        self.timeout = timeout

    def fetch_article(self, url: str) -> Optional[str]:
        """
        Fetch article content from URL.

        Tries multiple extraction methods:
        1. newspaper3k (best for articles)
        2. BeautifulSoup fallback (for difficult sites)

        Args:
            url: Article URL

        Returns:
            Article text content or None if failed
        """
        # Check cache first
        if self.use_cache:
            cached_content = _article_cache.get(url)
            if cached_content:
                return cached_content

        logger.info(f"Fetching article: {url}")

        # Try newspaper3k first (best for articles)
        content = self._fetch_with_newspaper(url)

        # Fallback to BeautifulSoup if newspaper fails
        if not content or len(content) < 100:
            logger.debug(f"Newspaper extraction failed, trying BeautifulSoup: {url}")
            content = self._fetch_with_beautifulsoup(url)

        # Cache successful fetch
        if content and self.use_cache:
            _article_cache.set(url, content)

        if content:
            logger.info(f"Successfully fetched article ({len(content)} chars): {url[:50]}")
        else:
            logger.warning(f"Failed to fetch article: {url}")

        return content

    def _fetch_with_newspaper(self, url: str) -> Optional[str]:
        """
        Fetch article using newspaper3k library.

        Args:
            url: Article URL

        Returns:
            Article text or None
        """
        try:
            article = Article(url)
            article.download()
            article.parse()

            # Get article text
            text = article.text

            # Validate we got substantive content
            if text and len(text) > 100:
                return text

            return None

        except Exception as e:
            logger.debug(f"Newspaper extraction failed for {url}: {e}")
            return None

    def _fetch_with_beautifulsoup(self, url: str) -> Optional[str]:
        """
        Fetch article using BeautifulSoup as fallback.

        Args:
            url: Article URL

        Returns:
            Article text or None
        """
        try:
            # Fetch HTML
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                script.decompose()

            # Try to find article content
            # Common article container tags/classes
            article_selectors = [
                {'name': 'article'},
                {'class_': lambda x: x and 'article' in str(x).lower()},
                {'class_': lambda x: x and 'content' in str(x).lower()},
                {'class_': lambda x: x and 'post' in str(x).lower()},
                {'id': lambda x: x and 'content' in str(x).lower()},
            ]

            article_text = None
            for selector in article_selectors:
                container = soup.find(**selector)
                if container:
                    # Get text from paragraphs
                    paragraphs = container.find_all('p')
                    if paragraphs:
                        article_text = '\n\n'.join(p.get_text().strip() for p in paragraphs)
                        break

            # Fallback: get all paragraphs
            if not article_text or len(article_text) < 100:
                paragraphs = soup.find_all('p')
                article_text = '\n\n'.join(p.get_text().strip() for p in paragraphs)

            # Validate we got content
            if article_text and len(article_text) > 100:
                return article_text

            return None

        except requests.exceptions.RequestException as e:
            logger.debug(f"HTTP error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.debug(f"BeautifulSoup extraction failed for {url}: {e}")
            return None

    def fetch_multiple(self, urls: list[str], max_failures: int = 3) -> Dict[str, str]:
        """
        Fetch multiple articles.

        Args:
            urls: List of URLs to fetch
            max_failures: Stop after this many consecutive failures

        Returns:
            Dict mapping URLs to article content (only successful fetches)
        """
        results = {}
        consecutive_failures = 0

        for url in urls:
            content = self.fetch_article(url)

            if content:
                results[url] = content
                consecutive_failures = 0
            else:
                consecutive_failures += 1

                # Stop if too many failures
                if consecutive_failures >= max_failures:
                    logger.warning(
                        f"Stopping after {consecutive_failures} consecutive failures"
                    )
                    break

        logger.info(f"Successfully fetched {len(results)}/{len(urls)} articles")
        return results


def fetch_article_content(url: str, use_cache: bool = True) -> Optional[str]:
    """
    Convenience function to fetch article content.

    Args:
        url: Article URL
        use_cache: Whether to use caching

    Returns:
        Article text or None
    """
    fetcher = ArticleFetcher(use_cache=use_cache)
    return fetcher.fetch_article(url)


def clear_article_cache():
    """Clear the global article cache."""
    _article_cache.clear()
