"""API routes for YouTube similarity detection."""

import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from ...youtube_similarity.models import ArticleAnalysisRequest, ArticleAnalysisResponse
from ...youtube_similarity.core.youtube_similarity_engine import YouTubeSimilarityEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/similarity", tags=["similarity"])

# Global engine instance (initialized on startup)
engine: YouTubeSimilarityEngine = None


def initialize_engine():
    """Initialize the YouTube similarity engine."""
    global engine
    if engine is None:
        logger.info("Initializing YouTube Similarity Engine")
        engine = YouTubeSimilarityEngine()
        logger.info("Engine initialized successfully")


@router.post(
    "/analyze",
    response_model=ArticleAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze article for YouTube similarities",
    description=(
        "Analyzes an article to identify semantic similarities with YouTube video transcripts. "
        "Returns a list of matching videos with similarity scores and timestamp ranges."
    )
)
async def analyze_article(request: ArticleAnalysisRequest):
    """
    Analyze an article for similarities with YouTube videos.

    The endpoint:
    1. Extracts keywords from the article
    2. Searches YouTube for relevant videos
    3. Fetches and processes transcripts
    4. Compares article content with transcripts
    5. Returns matching videos with similarity scores

    Args:
        request: Article analysis request containing title and content

    Returns:
        Analysis response with matching videos and similarity scores

    Raises:
        HTTPException: If analysis fails
    """
    if engine is None:
        initialize_engine()

    try:
        logger.info(f"Received analysis request for article: '{request.title}'")

        # Perform analysis
        result = engine.analyze_article(request)

        logger.info(
            f"Analysis complete: {result.matches_found} matches found "
            f"from {result.videos_analyzed} videos"
        )

        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing article: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the article"
        )


@router.get(
    "/cache/stats",
    summary="Get cache statistics",
    description="Returns statistics about the cache system, including hit rate and stored items."
)
async def get_cache_stats():
    """
    Get cache statistics.

    Returns:
        Cache statistics including enabled status, key count, and memory usage
    """
    if engine is None:
        initialize_engine()

    try:
        stats = engine.get_cache_stats()
        return JSONResponse(content=stats)

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving cache statistics"
        )


@router.delete(
    "/cache/clear",
    summary="Clear cache",
    description="Clears all cached transcript embeddings and chunks. Use with caution."
)
async def clear_cache():
    """
    Clear all cached data.

    Returns:
        Success message
    """
    if engine is None:
        initialize_engine()

    try:
        success = engine.clear_cache()

        if success:
            return JSONResponse(
                content={"message": "Cache cleared successfully"},
                status_code=status.HTTP_200_OK
            )
        else:
            return JSONResponse(
                content={"message": "Cache is disabled or clear failed"},
                status_code=status.HTTP_200_OK
            )

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error clearing cache"
        )


@router.get(
    "/health",
    summary="Health check",
    description="Check if the similarity detection service is healthy and operational."
)
async def health_check():
    """
    Health check endpoint.

    Returns:
        Service health status
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "youtube-similarity-detection",
            "version": "0.1.0"
        }
    )
