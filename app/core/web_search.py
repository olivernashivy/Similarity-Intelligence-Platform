"""Web search for articles using Google Custom Search and Bing Search APIs."""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result from web search."""
    title: str
    url: str
    snippet: str
    source: str  # 'google' or 'bing'


class WebArticleSearcher:
    """Search for articles on the web using multiple search engines."""

    def __init__(self):
        """Initialize web search clients."""
        # Google Custom Search
        self.google_client = None
        if settings.google_search_api_key and settings.google_search_engine_id:
            try:
                self.google_client = build(
                    'customsearch', 'v1',
                    developerKey=settings.google_search_api_key
                )
                logger.info("Google Custom Search initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Custom Search: {e}")

        # Bing Search
        self.bing_api_key = settings.bing_search_api_key
        if self.bing_api_key:
            logger.info("Bing Search API key configured")

    def search_google(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search Google for articles.

        Args:
            query: Search query
            num_results: Number of results to return (max 10 per request)
            **kwargs: Additional search parameters (dateRestrict, siteSearch, etc.)

        Returns:
            List of search results
        """
        if not self.google_client:
            logger.warning("Google Custom Search not configured")
            return []

        try:
            # Build search request
            search_params = {
                'q': query,
                'cx': settings.google_search_engine_id,
                'num': min(num_results, 10),  # Max 10 per request
                'safe': 'active',
                'lr': 'lang_en',  # English results
            }
            search_params.update(kwargs)

            # Execute search
            result = self.google_client.cse().list(**search_params).execute()

            # Parse results
            search_results = []
            for item in result.get('items', []):
                search_results.append(
                    SearchResult(
                        title=item.get('title', ''),
                        url=item.get('link', ''),
                        snippet=item.get('snippet', ''),
                        source='google'
                    )
                )

            logger.info(f"Google search returned {len(search_results)} results for: {query[:50]}")
            return search_results

        except HttpError as e:
            logger.error(f"Google Custom Search API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching Google: {e}")
            return []

    def search_bing(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search Bing for articles.

        Args:
            query: Search query
            num_results: Number of results to return
            **kwargs: Additional search parameters

        Returns:
            List of search results
        """
        if not self.bing_api_key:
            logger.warning("Bing Search API key not configured")
            return []

        try:
            # Bing Search API endpoint
            endpoint = "https://api.bing.microsoft.com/v7.0/search"

            # Build headers
            headers = {
                'Ocp-Apim-Subscription-Key': self.bing_api_key
            }

            # Build parameters
            params = {
                'q': query,
                'count': num_results,
                'mkt': 'en-US',
                'safeSearch': 'Moderate',
                'textDecorations': False,
                'textFormat': 'Raw'
            }
            params.update(kwargs)

            # Execute search
            response = requests.get(endpoint, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse results
            search_results = []
            for item in data.get('webPages', {}).get('value', []):
                search_results.append(
                    SearchResult(
                        title=item.get('name', ''),
                        url=item.get('url', ''),
                        snippet=item.get('snippet', ''),
                        source='bing'
                    )
                )

            logger.info(f"Bing search returned {len(search_results)} results for: {query[:50]}")
            return search_results

        except requests.exceptions.RequestException as e:
            logger.error(f"Bing Search API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching Bing: {e}")
            return []

    def search_articles(
        self,
        keywords: List[str],
        max_results: int = 10,
        use_both_engines: bool = True
    ) -> List[SearchResult]:
        """
        Search for articles using available search engines.

        Args:
            keywords: List of keywords to search for
            max_results: Maximum total results to return
            use_both_engines: If True, use both Google and Bing; otherwise use best available

        Returns:
            Combined list of search results (deduplicated by URL)
        """
        # Build search query from keywords
        query = ' '.join(keywords[:5])  # Use top 5 keywords
        logger.info(f"Searching web articles for: {query}")

        all_results = []

        if use_both_engines:
            # Use both engines and combine results
            results_per_engine = max_results // 2

            # Search Google
            google_results = self.search_google(query, num_results=results_per_engine)
            all_results.extend(google_results)

            # Search Bing
            bing_results = self.search_bing(query, num_results=results_per_engine)
            all_results.extend(bing_results)

        else:
            # Use single best available engine
            if self.google_client:
                all_results = self.search_google(query, num_results=max_results)
            elif self.bing_api_key:
                all_results = self.search_bing(query, num_results=max_results)
            else:
                logger.warning("No search engines configured")
                return []

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)

        # Limit to max_results
        final_results = unique_results[:max_results]

        logger.info(f"Web search returned {len(final_results)} unique articles")
        return final_results

    def filter_relevant_articles(
        self,
        results: List[SearchResult],
        exclude_domains: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Filter search results to keep only relevant articles.

        Args:
            results: List of search results
            exclude_domains: Domains to exclude (e.g., social media)

        Returns:
            Filtered list of results
        """
        if exclude_domains is None:
            exclude_domains = [
                'facebook.com',
                'twitter.com',
                'instagram.com',
                'tiktok.com',
                'reddit.com',
                'youtube.com',  # Already handled separately
                'pinterest.com'
            ]

        filtered = []
        for result in results:
            # Check if domain is excluded
            url_lower = result.url.lower()
            if any(domain in url_lower for domain in exclude_domains):
                logger.debug(f"Excluding social media URL: {result.url}")
                continue

            # Check if it looks like an article
            # Articles typically have substantive snippets
            if len(result.snippet) < 50:
                logger.debug(f"Excluding short snippet: {result.url}")
                continue

            filtered.append(result)

        logger.info(f"Filtered {len(filtered)} relevant articles from {len(results)} results")
        return filtered


def search_web_articles(
    keywords: List[str],
    max_results: int = 10,
    filter_results: bool = True
) -> List[SearchResult]:
    """
    Convenience function to search for web articles.

    Args:
        keywords: List of keywords to search for
        max_results: Maximum number of results
        filter_results: Whether to filter out non-articles

    Returns:
        List of search results
    """
    searcher = WebArticleSearcher()
    results = searcher.search_articles(keywords, max_results=max_results)

    if filter_results:
        results = searcher.filter_relevant_articles(results)

    return results
