"""Error handling utilities and custom exceptions.

Provides structured error handling, logging, and user-friendly error responses.
"""
import logging
import traceback
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# Custom Exception Classes
class SimilarityPlatformException(Exception):
    """Base exception for all platform-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "PLATFORM_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(SimilarityPlatformException):
    """Input validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field, **(details or {})},
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ProcessingError(SimilarityPlatformException):
    """Errors during similarity processing."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class QuotaExceededError(SimilarityPlatformException):
    """Quota or rate limit exceeded."""

    def __init__(self, message: str, limit: Optional[int] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="QUOTA_EXCEEDED",
            details={"limit": limit, **(details or {})},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class ExternalServiceError(SimilarityPlatformException):
    """External service (YouTube, etc.) errors."""

    def __init__(self, message: str, service: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class DatabaseError(SimilarityPlatformException):
    """Database operation errors."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Error Response Builders
def build_error_response(
    exception: Exception,
    include_traceback: bool = False
) -> JSONResponse:
    """
    Build structured error response from exception.

    Args:
        exception: The exception to convert
        include_traceback: Include traceback in response (dev only)

    Returns:
        JSONResponse with error details
    """
    # Handle custom platform exceptions
    if isinstance(exception, SimilarityPlatformException):
        content = {
            "error": {
                "code": exception.error_code,
                "message": exception.message,
                "details": exception.details
            }
        }
        status_code = exception.status_code

    # Handle FastAPI HTTPException
    elif isinstance(exception, HTTPException):
        content = {
            "error": {
                "code": "HTTP_ERROR",
                "message": exception.detail,
                "details": {}
            }
        }
        status_code = exception.status_code

    # Handle generic exceptions
    else:
        content = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {
                    "type": type(exception).__name__
                }
            }
        }
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Add traceback in development
    if include_traceback:
        content["error"]["traceback"] = traceback.format_exc()

    return JSONResponse(
        status_code=status_code,
        content=content
    )


# Logging Helpers
def log_error(
    error: Exception,
    context: Optional[str] = None,
    user_id: Optional[str] = None,
    extra: Optional[Dict] = None
):
    """
    Log error with context and structured data.

    Args:
        error: The exception to log
        context: Context description (e.g., "similarity_check", "youtube_fetch")
        user_id: Optional user/org ID for tracking
        extra: Additional context data
    """
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "user_id": user_id,
        **(extra or {})
    }

    if isinstance(error, SimilarityPlatformException):
        log_data["error_code"] = error.error_code
        log_data["details"] = error.details

    logger.error(
        f"Error in {context}: {str(error)}",
        extra=log_data,
        exc_info=True
    )


def log_warning(
    message: str,
    context: Optional[str] = None,
    extra: Optional[Dict] = None
):
    """
    Log warning with structured data.

    Args:
        message: Warning message
        context: Context description
        extra: Additional data
    """
    log_data = {
        "context": context,
        **(extra or {})
    }

    logger.warning(message, extra=log_data)


def log_info(
    message: str,
    context: Optional[str] = None,
    extra: Optional[Dict] = None
):
    """
    Log info with structured data.

    Args:
        message: Info message
        context: Context description
        extra: Additional data
    """
    log_data = {
        "context": context,
        **(extra or {})
    }

    logger.info(message, extra=log_data)


# Safe Execution Wrapper
def safe_execute(
    func,
    *args,
    context: str,
    fallback_value=None,
    raise_on_error: bool = True,
    **kwargs
):
    """
    Safely execute function with error handling and logging.

    Args:
        func: Function to execute
        *args: Positional arguments
        context: Context description for logging
        fallback_value: Value to return on error (if raise_on_error=False)
        raise_on_error: Whether to re-raise exceptions
        **kwargs: Keyword arguments

    Returns:
        Function result or fallback_value

    Raises:
        Exception if raise_on_error=True
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_error(e, context=context)

        if raise_on_error:
            raise

        return fallback_value


# Validation Helpers
def validate_not_empty(value: Any, field_name: str):
    """Validate value is not empty."""
    if not value:
        raise ValidationError(
            message=f"{field_name} cannot be empty",
            field=field_name
        )


def validate_length(
    value: str,
    field_name: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
):
    """Validate string length."""
    if min_length and len(value) < min_length:
        raise ValidationError(
            message=f"{field_name} must be at least {min_length} characters",
            field=field_name,
            details={"current_length": len(value), "min_length": min_length}
        )

    if max_length and len(value) > max_length:
        raise ValidationError(
            message=f"{field_name} must not exceed {max_length} characters",
            field=field_name,
            details={"current_length": len(value), "max_length": max_length}
        )


def validate_word_count(
    text: str,
    field_name: str,
    min_words: Optional[int] = None,
    max_words: Optional[int] = None
):
    """Validate word count in text."""
    word_count = len(text.split())

    if min_words and word_count < min_words:
        raise ValidationError(
            message=f"{field_name} must have at least {min_words} words",
            field=field_name,
            details={"current_words": word_count, "min_words": min_words}
        )

    if max_words and word_count > max_words:
        raise ValidationError(
            message=f"{field_name} must not exceed {max_words} words",
            field=field_name,
            details={"current_words": word_count, "max_words": max_words}
        )
