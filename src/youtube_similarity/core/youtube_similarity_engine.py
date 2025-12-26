"""Main YouTube similarity detection engine."""

import logging
from typing import List, Optional
from datetime import datetime

from ..config import settings
from ..models import (
    ArticleAnalysisRequest,
    ArticleAnalysisResponse,
    VideoSimilarityResult,
    KeywordExtractionResult
)
from ..services.keyword_extractor import KeywordExtractor
from ..services.video_discovery import VideoDiscoveryService
from ..services.transcript_fetcher import TranscriptFetcherService
from ..services.transcript_processor import TranscriptProcessor
from ..services.embedding_service import EmbeddingService
from ..services.cache_service import CacheService
from ..services.similarity_matcher import SimilarityMatcher

logger = logging.getLogger(__name__)


class YouTubeSimilarityEngine:
    """
    Main engine for detecting similarities between articles and YouTube videos.

    Orchestrates the complete pipeline:
    1. Keyword extraction from article
    2. Video discovery via YouTube search
    3. Transcript fetching
    4. Text processing and chunking
    5. Embedding generation
    6. Similarity matching
    7. Result aggregation and reporting
    """

    def __init__(
        self,
        youtube_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        enable_cache: bool = True
    ):
        """
        Initialize the YouTube similarity engine.

        Args:
            youtube_api_key: YouTube Data API key
            openai_api_key: OpenAI API key
            enable_cache: Whether to enable caching
        """
        logger.info("Initializing YouTube Similarity Engine")

        # Initialize services
        self.keyword_extractor = KeywordExtractor()
        self.video_discovery = VideoDiscoveryService(api_key=youtube_api_key)
        self.transcript_fetcher = TranscriptFetcherService()
        self.transcript_processor = TranscriptProcessor()
        self.embedding_service = EmbeddingService(api_key=openai_api_key)
        self.similarity_matcher = SimilarityMatcher()

        # Initialize cache (optional)
        self.cache = CacheService() if enable_cache else None

        logger.info("YouTube Similarity Engine initialized successfully")

    def analyze_article(
        self,
        request: ArticleAnalysisRequest
    ) -> ArticleAnalysisResponse:
        """
        Analyze an article for similarities with YouTube videos.

        Args:
            request: Article analysis request

        Returns:
            Article analysis response with similarity results
        """
        logger.info(f"Starting analysis for article: '{request.title}'")

        try:
            # Step 1: Extract keywords from article
            keywords = self._extract_keywords(request.title, request.content)

            # Step 2: Build search query and discover videos
            videos = self._discover_videos(keywords)

            if not videos:
                logger.warning("No relevant videos found")
                return self._create_empty_response(request, keywords)

            # Step 3: Process article into chunks and generate embeddings
            article_chunks = self.transcript_processor.process_article(
                request.title,
                request.content
            )
            article_embeddings = self.embedding_service.generate_embeddings_batch(
                article_chunks
            )

            # Step 4: Process each video
            results = []
            for video in videos:
                logger.info(f"Processing video: {video.title}")

                try:
                    result = self._process_video(
                        video,
                        article_embeddings
                    )

                    # Only include videos with matches
                    if result.matched_chunks_count > 0:
                        results.append(result)

                except Exception as e:
                    logger.error(f"Error processing video {video.video_id}: {e}")
                    continue

            # Step 5: Rank and filter results
            results = self.similarity_matcher.rank_results(results)

            # Step 6: Create response
            response = ArticleAnalysisResponse(
                article_title=request.title,
                analyzed_at=datetime.utcnow(),
                videos_analyzed=len(videos),
                matches_found=len(results),
                results=results,
                keywords_extracted=keywords.all_keywords
            )

            logger.info(
                f"Analysis complete: {len(results)} matches found "
                f"from {len(videos)} videos"
            )

            return response

        except Exception as e:
            logger.error(f"Error analyzing article: {e}")
            raise

    def _extract_keywords(
        self,
        title: str,
        content: str
    ) -> KeywordExtractionResult:
        """
        Extract keywords from article.

        Args:
            title: Article title
            content: Article content

        Returns:
            Extracted keywords
        """
        logger.info("Extracting keywords from article")

        keywords_dict = self.keyword_extractor.extract_keywords(title, content)

        return KeywordExtractionResult(
            title_weighted_terms=keywords_dict["title_weighted_terms"],
            named_entities=keywords_dict["named_entities"],
            tfidf_phrases=keywords_dict["tfidf_phrases"],
            all_keywords=keywords_dict["all_keywords"]
        )

    def _discover_videos(
        self,
        keywords: KeywordExtractionResult
    ) -> List:
        """
        Discover relevant YouTube videos.

        Args:
            keywords: Extracted keywords

        Returns:
            List of video metadata
        """
        logger.info("Discovering relevant YouTube videos")

        # Build search query
        search_query = self.keyword_extractor.build_search_query(
            {
                "title_weighted_terms": keywords.title_weighted_terms,
                "named_entities": keywords.named_entities,
                "tfidf_phrases": keywords.tfidf_phrases
            }
        )

        logger.info(f"Search query: '{search_query}'")

        # Search for videos
        videos = self.video_discovery.search_videos(search_query)

        logger.info(f"Found {len(videos)} relevant videos")
        return videos

    def _process_video(
        self,
        video,
        article_embeddings: List
    ) -> VideoSimilarityResult:
        """
        Process a single video for similarity matching.

        Args:
            video: Video metadata
            article_embeddings: Article chunk embeddings

        Returns:
            Video similarity result
        """
        # Check cache first
        cached_embeddings = None
        cached_chunks = None

        if self.cache and self.cache.enabled:
            cached_embeddings = self.cache.get_video_embeddings(video.video_id)
            cached_chunks_dict = self.cache.get_video_chunks(video.video_id)

            if cached_chunks_dict:
                # Reconstruct chunks from cache
                from ..models import TranscriptChunk
                cached_chunks = [
                    TranscriptChunk(**chunk_dict)
                    for chunk_dict in cached_chunks_dict
                ]

        # Use cached data if available
        if cached_embeddings and cached_chunks:
            logger.info(f"Using cached data for video {video.video_id}")
            transcript_chunks = cached_chunks
            transcript_embeddings = cached_embeddings
        else:
            # Fetch and process transcript
            transcript_segments = self.transcript_fetcher.fetch_transcript(
                video.video_id
            )

            if not transcript_segments:
                logger.warning(f"No transcript available for video {video.video_id}")
                return self.similarity_matcher._create_empty_result(video)

            # Process transcript into chunks
            transcript_chunks = self.transcript_processor.process_transcript(
                transcript_segments,
                video.video_id
            )

            if not transcript_chunks:
                logger.warning(f"No chunks created for video {video.video_id}")
                return self.similarity_matcher._create_empty_result(video)

            # Generate embeddings
            chunk_texts = [chunk.text for chunk in transcript_chunks]
            transcript_embeddings = self.embedding_service.generate_embeddings_batch(
                chunk_texts
            )

            # Cache for future use
            if self.cache and self.cache.enabled:
                self.cache.set_video_embeddings(video.video_id, transcript_embeddings)
                chunks_dict = [chunk.model_dump() for chunk in transcript_chunks]
                self.cache.set_video_chunks(video.video_id, chunks_dict)

        # Perform similarity matching
        result = self.similarity_matcher.find_matches(
            article_embeddings,
            transcript_chunks,
            transcript_embeddings,
            video
        )

        return result

    def _create_empty_response(
        self,
        request: ArticleAnalysisRequest,
        keywords: KeywordExtractionResult
    ) -> ArticleAnalysisResponse:
        """
        Create empty response when no results found.

        Args:
            request: Original request
            keywords: Extracted keywords

        Returns:
            Empty article analysis response
        """
        return ArticleAnalysisResponse(
            article_title=request.title,
            analyzed_at=datetime.utcnow(),
            videos_analyzed=0,
            matches_found=0,
            results=[],
            keywords_extracted=keywords.all_keywords,
            message="No similar YouTube videos found"
        )

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        if self.cache:
            return self.cache.get_cache_stats()
        return {"enabled": False}

    def clear_cache(self) -> bool:
        """
        Clear all cached data.

        Returns:
            True if successfully cleared
        """
        if self.cache:
            return self.cache.clear_all()
        return False
