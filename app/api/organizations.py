"""Organization management endpoints."""
from uuid import UUID
from datetime import datetime, timedelta
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.organization import Organization
from app.models.user import User
from app.models.api_key import APIKey
from app.models.check import Check
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationDetailResponse,
    OrganizationListResponse,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse
)
from app.auth.dependencies import (
    get_current_user,
    get_current_admin_user,
    get_current_superuser,
    get_user_organization
)
from app.auth.api_key import hash_api_key

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/current", response_model=OrganizationDetailResponse)
async def get_current_organization(
    organization: Organization = Depends(get_user_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's organization with statistics.

    Returns detailed organization information including usage stats.
    """
    # Get counts
    user_count_result = await db.execute(
        select(func.count(User.id))
        .where(User.organization_id == organization.id)
    )
    user_count = user_count_result.scalar() or 0

    api_key_count_result = await db.execute(
        select(func.count(APIKey.id))
        .where(APIKey.organization_id == organization.id)
    )
    api_key_count = api_key_count_result.scalar() or 0

    total_checks_result = await db.execute(
        select(func.count(Check.id))
        .where(Check.organization_id == organization.id)
    )
    total_checks = total_checks_result.scalar() or 0

    return OrganizationDetailResponse(
        **organization.__dict__,
        user_count=user_count,
        api_key_count=api_key_count,
        total_checks=total_checks
    )


@router.patch("/current", response_model=OrganizationResponse)
async def update_current_organization(
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_admin_user),
    organization: Organization = Depends(get_user_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current organization.

    **Requires**: Admin role

    Admins can update their organization's settings.
    """
    # Update fields
    if org_data.name is not None:
        organization.name = org_data.name

    if org_data.email is not None:
        # Check email uniqueness
        result = await db.execute(
            select(Organization)
            .where(Organization.email == org_data.email)
            .where(Organization.id != organization.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use by another organization"
            )
        organization.email = org_data.email

    if org_data.allow_corpus_inclusion is not None:
        organization.allow_corpus_inclusion = org_data.allow_corpus_inclusion

    if org_data.store_embeddings is not None:
        organization.store_embeddings = org_data.store_embeddings

    organization.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(organization)

    return OrganizationResponse.model_validate(organization)


# Superuser-only endpoints
@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    List all organizations.

    **Requires**: Superuser role

    Returns paginated list of all organizations in the system.
    """
    # Count total
    total_result = await db.execute(select(func.count(Organization.id)))
    total = total_result.scalar() or 0

    # Get organizations
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Organization)
        .order_by(Organization.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    organizations = result.scalars().all()

    return OrganizationListResponse(
        organizations=[OrganizationResponse.model_validate(org) for org in organizations],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new organization.

    **Requires**: Superuser role

    Creates a new organization with specified settings.
    """
    # Check email uniqueness
    result = await db.execute(
        select(Organization).where(Organization.email == org_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create organization
    organization = Organization(
        name=org_data.name,
        email=org_data.email,
        tier=org_data.tier,
        monthly_check_limit=org_data.monthly_check_limit,
        allow_corpus_inclusion=org_data.allow_corpus_inclusion
    )

    db.add(organization)
    await db.commit()
    await db.refresh(organization)

    return OrganizationResponse.model_validate(organization)


@router.get("/{organization_id}", response_model=OrganizationDetailResponse)
async def get_organization(
    organization_id: UUID,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get organization by ID.

    **Requires**: Superuser role
    """
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Get counts
    user_count_result = await db.execute(
        select(func.count(User.id))
        .where(User.organization_id == organization.id)
    )
    user_count = user_count_result.scalar() or 0

    api_key_count_result = await db.execute(
        select(func.count(APIKey.id))
        .where(APIKey.organization_id == organization.id)
    )
    api_key_count = api_key_count_result.scalar() or 0

    total_checks_result = await db.execute(
        select(func.count(Check.id))
        .where(Check.organization_id == organization.id)
    )
    total_checks = total_checks_result.scalar() or 0

    return OrganizationDetailResponse(
        **organization.__dict__,
        user_count=user_count,
        api_key_count=api_key_count,
        total_checks=total_checks
    )


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Update organization.

    **Requires**: Superuser role

    Superusers can update any organization and change tier/limits.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Update fields
    if org_data.name is not None:
        organization.name = org_data.name

    if org_data.email is not None:
        result = await db.execute(
            select(Organization)
            .where(Organization.email == org_data.email)
            .where(Organization.id != organization_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        organization.email = org_data.email

    if org_data.tier is not None:
        organization.tier = org_data.tier

    if org_data.monthly_check_limit is not None:
        organization.monthly_check_limit = org_data.monthly_check_limit

    if org_data.allow_corpus_inclusion is not None:
        organization.allow_corpus_inclusion = org_data.allow_corpus_inclusion

    if org_data.store_embeddings is not None:
        organization.store_embeddings = org_data.store_embeddings

    if org_data.is_active is not None:
        organization.is_active = org_data.is_active

    organization.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(organization)

    return OrganizationResponse.model_validate(organization)


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: UUID,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an organization.

    **Requires**: Superuser role

    **Warning**: This will delete all associated users, API keys, and checks.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    await db.delete(organization)
    await db.commit()

    return None


# API Key Management
@router.get("/current/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: User = Depends(get_current_admin_user),
    organization: Organization = Depends(get_user_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    List API keys for current organization.

    **Requires**: Admin role

    Returns all API keys (without the actual key values).
    """
    result = await db.execute(
        select(APIKey)
        .where(APIKey.organization_id == organization.id)
        .order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()

    total = len(api_keys)

    return APIKeyListResponse(
        api_keys=[APIKeyResponse.model_validate(key) for key in api_keys],
        total=total
    )


@router.post("/current/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_admin_user),
    organization: Organization = Depends(get_user_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key.

    **Requires**: Admin role

    **Important**: The full API key is only shown once. Save it securely!
    """
    # Generate API key
    api_key_value = f"sk_live_{secrets.token_urlsafe(32)}"
    key_prefix = api_key_value[:12]  # e.g., "sk_live_abc"

    # Hash the key
    key_hash = hash_api_key(api_key_value)

    # Calculate expiration
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

    # Create API key
    api_key = APIKey(
        organization_id=organization.id,
        name=key_data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        rate_limit_per_minute=key_data.rate_limit_per_minute,
        expires_at=expires_at
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Return response with full key (only time it's shown)
    response = APIKeyResponse.model_validate(api_key)
    response.api_key = api_key_value  # Add full key to response

    return response


@router.delete("/current/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    organization: Organization = Depends(get_user_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an API key.

    **Requires**: Admin role

    **Warning**: This will immediately revoke the API key.
    """
    result = await db.execute(
        select(APIKey)
        .where(APIKey.id == key_id)
        .where(APIKey.organization_id == organization.id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    await db.delete(api_key)
    await db.commit()

    return None
