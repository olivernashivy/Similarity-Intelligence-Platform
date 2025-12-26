"""Main FastAPI application for YouTube Similarity Detection API."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from ..youtube_similarity.config import settings
from .routes import similarity

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting YouTube Similarity Detection API")
    similarity.initialize_engine()

    yield

    # Shutdown
    logger.info("Shutting down YouTube Similarity Detection API")


# Create FastAPI application
app = FastAPI(
    title="YouTube Similarity Intelligence Platform",
    description=(
        "API for detecting semantic similarities between articles and YouTube video transcripts. "
        "Uses advanced NLP techniques and embeddings to identify potential content similarities."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(similarity.router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health():
    """
    Root health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "youtube-similarity-platform",
        "version": "0.1.0"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
