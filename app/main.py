"""FastAPI main application."""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, close_db
from app.api import checks, usage, auth, users, organizations
from app.utils.error_handling import (
    SimilarityPlatformException,
    ValidationError,
    QuotaExceededError,
    DatabaseError,
    ProcessingError,
    ExternalServiceError,
    build_error_response
)

logger = logging.getLogger(__name__)


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
    - User & organization management
    - API key management

    ## Authentication

    ### For Similarity Checks (API Key)
    Use `X-API-Key` header with your organization's API key:
    ```
    X-API-Key: sk_live_your_api_key_here
    ```

    ### For User Management (JWT Token)
    1. Register: `POST /v1/auth/register`
    2. Login: `POST /v1/auth/login` (returns JWT token)
    3. Use token: Include in `Authorization: Bearer <token>` header

    ## Quick Start

    ### 1. Register (creates organization + admin user)
    ```bash
    curl -X POST http://localhost:8000/v1/auth/register \\
      -H "Content-Type: application/json" \\
      -d '{
        "email": "admin@example.com",
        "username": "admin",
        "password": "SecurePass123!",
        "organization_name": "My Company"
      }'
    ```

    ### 2. Create API Key
    ```bash
    curl -X POST http://localhost:8000/v1/organizations/current/api-keys \\
      -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
      -H "Content-Type: application/json" \\
      -d '{
        "name": "Production Key",
        "rate_limit_per_minute": 100
      }'
    ```

    ### 3. Check Similarity
    ```bash
    curl -X POST http://localhost:8000/v1/check \\
      -H "X-API-Key: YOUR_API_KEY" \\
      -H "Content-Type: application/json" \\
      -d '{
        "article_text": "Your article content...",
        "sources": ["articles", "youtube"]
      }'
    ```

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
# Authentication & User Management (no API key required)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(users.router, prefix=settings.api_v1_prefix)
app.include_router(organizations.router, prefix=settings.api_v1_prefix)

# Similarity Checking (requires API key)
app.include_router(checks.router, prefix=settings.api_v1_prefix)
app.include_router(usage.router, prefix=settings.api_v1_prefix)


# Custom exception handlers
@app.exception_handler(SimilarityPlatformException)
async def platform_exception_handler(request: Request, exc: SimilarityPlatformException):
    """Handle platform-specific exceptions with structured responses."""
    logger.warning(
        f"Platform exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "details": exc.details
        }
    )
    return build_error_response(exc, include_traceback=settings.debug)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )

    if settings.debug:
        raise exc

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": {}
            }
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
