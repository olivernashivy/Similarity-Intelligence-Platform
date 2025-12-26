"""Shared dependencies for API routes."""
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.api_key import api_key_header, get_api_key_from_db, check_rate_limit
from app.models.api_key import APIKey
from app.models.organization import Organization


async def get_current_api_key(
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    """Validate and retrieve API key."""
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

    # Check rate limit
    await check_rate_limit(db_api_key, db)

    return db_api_key


async def get_current_organization(
    api_key: APIKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    """Get organization from validated API key."""
    from sqlalchemy import select

    result = await db.execute(
        select(Organization).where(Organization.id == api_key.organization_id)
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
