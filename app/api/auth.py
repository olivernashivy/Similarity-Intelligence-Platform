"""Authentication endpoints."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
    PasswordChangeRequest
)
from app.auth.jwt import (
    verify_password,
    get_password_hash,
    create_access_token
)
from app.auth.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user and organization.

    Creates a new organization and the first admin user for that organization.

    **Note**: The first user created for an organization automatically becomes an admin.
    """
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Check if organization email exists
    result = await db.execute(
        select(Organization).where(Organization.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization email already registered"
        )

    # Create organization
    organization = Organization(
        name=request.organization_name,
        email=request.email,
        tier="free",
        monthly_check_limit=100
    )
    db.add(organization)
    await db.flush()

    # Create user (first user is admin)
    hashed_password = get_password_hash(request.password)
    user = User(
        organization_id=organization.id,
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        full_name=request.full_name,
        role="admin",  # First user is admin
        is_active=True,
        email_verified=False,
        last_login_at=datetime.utcnow()
    )
    db.add(user)

    await db.commit()
    await db.refresh(user)

    # Create access token
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "organization_id": user.organization_id,
            "role": user.role
        },
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.

    Returns a JWT access token for authenticated requests.

    **Token Usage**: Include the token in the Authorization header as `Bearer <token>`
    """
    # Get user by email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    # Create access token
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "organization_id": user.organization_id,
            "role": user.role
        },
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.

    Requires authentication token.
    """
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change password for current user.

    Requires authentication and current password verification.
    """
    # Verify old password
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Update password
    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.updated_at = datetime.utcnow()

    await db.commit()

    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout():
    """
    Logout endpoint.

    **Note**: JWT tokens are stateless. To properly logout:
    - Client should delete the token from storage
    - Token will expire after configured time
    - For immediate invalidation, implement token blacklisting
    """
    return {"message": "Logged out successfully. Please delete your access token."}
