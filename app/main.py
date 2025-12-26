"""FastAPI main application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, close_db
from app.api import checks, usage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting Similarity Intelligence Platform...")
    await init_db()
    print("Database initialized")

    yield

    # Shutdown
    print("Shutting down...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    # Similarity Intelligence Platform API

    Editorial similarity analysis for written articles against:
    - Other articles
    - YouTube video transcripts

    ## Features
    - Async job processing
    - Semantic similarity detection
    - Cost-bounded operations (~$0.004 per check)
    - Privacy-preserving design

    ## Authentication
    All endpoints require an API key in the `X-API-Key` header.

    ## Typical Flow
    1. POST /v1/check - Submit article (returns job_id)
    2. GET /v1/check/{job_id} - Poll for results
    3. GET /v1/usage - Check usage stats

    ## Similarity Signals
    - **Low Risk** (0-65%): Minimal overlap
    - **Medium Risk** (65-75%): Some similarity worth reviewing
    - **High Risk** (75%+): Significant overlap detected
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment
    }


# Include routers
app.include_router(checks.router, prefix=settings.api_v1_prefix)
app.include_router(usage.router, prefix=settings.api_v1_prefix)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    if settings.debug:
        raise exc

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "type": "internal_error"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
