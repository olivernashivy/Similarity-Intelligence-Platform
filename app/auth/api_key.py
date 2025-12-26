"""API key authentication and management."""
import secrets
from datetime import datetime
from typing import Optional, Tuple
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.models.api_key import APIKey
from app.models.organization import Organization

# Password context for hashing API keys
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def generate_api_key() -> Tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (raw_key, key_hash)
    """
    # Generate a random key
    raw_key = f"sk_live_{secrets.token_urlsafe(32)}"

    # Hash the key
    key_hash = pwd_context.hash(raw_key)

    return raw_key, key_hash


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        raw_key: Raw API key
        key_hash: Hashed API key

    Returns:
        True if valid, False otherwise
    """
    return pwd_context.verify(raw_key, key_hash)


async def get_api_key_from_db(
    db: AsyncSession,
    raw_key: str
) -> Optional[APIKey]:
    """
    Find and verify API key in database.

    Args:
        db: Database session
        raw_key: Raw API key from request

    Returns:
        APIKey object or None
    """
    # Extract prefix for efficient lookup
    prefix = raw_key[:15] if len(raw_key) > 15 else raw_key

    # Query for API keys with matching prefix
    result = await db.execute(
        select(APIKey)
        .where(APIKey.key_prefix == prefix)
        .where(APIKey.is_active == True)
    )
    api_keys = result.scalars().all()

    # Verify hash for each candidate
    for api_key in api_keys:
        if verify_api_key(raw_key, api_key.key_hash):
            # Update last used timestamp
            api_key.last_used_at = datetime.utcnow()
            api_key.total_requests += 1
            await db.commit()
            return api_key

    return None


async def get_current_api_key(
    api_key: str = Security(api_key_header),
    db: AsyncSession = None
) -> APIKey:
    """
    Dependency for validating API key.

    Args:
        api_key: API key from header
        db: Database session

    Returns:
        APIKey object

    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required"
        )

    # Validate API key
    db_api_key = await get_api_key_from_db(db, api_key)

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    if not db_api_key.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is expired or inactive"
        )

    return db_api_key


async def get_current_organization(
    api_key: APIKey,
    db: AsyncSession
) -> Organization:
    """
    Get organization from API key.

    Args:
        api_key: Validated API key
        db: Database session

    Returns:
        Organization object

    Raises:
        HTTPException: If organization is inactive
    """
    result = await db.execute(
        select(Organization)
        .where(Organization.id == api_key.organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    if not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive"
        )

    return organization


async def check_rate_limit(
    api_key: APIKey,
    db: AsyncSession
) -> None:
    """
    Check if API key has exceeded rate limit.

    Args:
        api_key: API key to check
        db: Database session

    Raises:
        HTTPException: If rate limit exceeded
    """
    # Simple rate limiting - check requests in last minute
    # In production, use Redis for distributed rate limiting

    # For MVP, skip detailed rate limiting
    # Just check monthly quota
    organization = await get_current_organization(api_key, db)

    if organization.current_month_checks >= organization.monthly_check_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly check limit ({organization.monthly_check_limit}) exceeded"
        )


async def create_api_key(
    db: AsyncSession,
    organization_id: str,
    name: str,
    rate_limit_per_minute: Optional[int] = None
) -> Tuple[str, APIKey]:
    """
    Create a new API key.

    Args:
        db: Database session
        organization_id: Organization ID
        name: Human-readable name
        rate_limit_per_minute: Optional rate limit

    Returns:
        Tuple of (raw_key, api_key_model)
    """
    # Generate key
    raw_key, key_hash = generate_api_key()
    prefix = raw_key[:15]

    # Create API key model
    api_key = APIKey(
        organization_id=organization_id,
        name=name,
        key_hash=key_hash,
        key_prefix=prefix,
        rate_limit_per_minute=rate_limit_per_minute or 60,
        is_active=True
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return raw_key, api_key
