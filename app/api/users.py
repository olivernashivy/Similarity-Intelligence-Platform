"""User management endpoints."""
from uuid import UUID
from datetime import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse
)
from app.auth.dependencies import get_current_user, get_current_admin_user
from app.auth.jwt import get_password_hash
from app.utils.sanitization import sanitize_text
from app.utils.error_handling import (
    ValidationError,
    DatabaseError,
    log_error,
    log_info,
    log_warning
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users in current organization.

    **Requires**: Admin role

    Returns paginated list of users.
    """
    # Count total users
    total_result = await db.execute(
        select(func.count(User.id))
        .where(User.organization_id == current_user.organization_id)
    )
    total = total_result.scalar() or 0

    # Get users
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    users = result.scalars().all()

    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user in current organization.

    **Requires**: Admin role

    Creates a new user with the specified role (admin, member, or viewer).
    """
    log_info(
        f"Creating new user: {user_data.email}",
        context="create_user",
        extra={
            "admin_user_id": str(current_user.id),
            "new_user_email": user_data.email
        }
    )

    try:
        # Sanitize inputs
        email = sanitize_text(user_data.email, max_length=255).strip().lower()
        username = sanitize_text(user_data.username, max_length=100).strip()
        full_name = sanitize_text(user_data.full_name, max_length=255).strip() if user_data.full_name else None

        # Validate email
        if not email or '@' not in email:
            raise ValidationError("Invalid email format", field="email")

        # Validate username
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters", field="username")

        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == email)
        )
        if result.scalar_one_or_none():
            log_warning(
                f"User creation failed: Email already exists - {email}",
                context="create_user"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check if username already exists
        result = await db.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            log_warning(
                f"User creation failed: Username already taken - {username}",
                context="create_user"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # Create user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            organization_id=current_user.organization_id,
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            role=user_data.role,
            is_active=True
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        log_info(
            f"User created successfully: {user.id}",
            context="create_user",
            extra={
                "user_id": str(user.id),
                "organization_id": str(current_user.organization_id),
                "role": user_data.role
            }
        )

        return UserResponse.model_validate(user)

    except (ValidationError, HTTPException):
        raise

    except SQLAlchemyError as e:
        log_error(
            e,
            context="create_user",
            user_id=str(current_user.id),
            extra={"error_type": "database"}
        )
        raise DatabaseError(
            "Failed to create user due to database error",
            details={"error": str(e)}
        )

    except Exception as e:
        log_error(
            e,
            context="create_user",
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID.

    Users can view their own profile or admins can view any user in their organization.
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Non-admin users can only view themselves
    if not current_user.is_admin and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user information.

    **Requires**: Admin role

    Admins can update any user in their organization.
    """
    log_info(
        f"Updating user: {user_id}",
        context="update_user",
        extra={"admin_user_id": str(current_user.id), "target_user_id": str(user_id)}
    )

    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check same organization
        if user.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Update fields
        if user_data.email is not None:
            # Sanitize email
            email = sanitize_text(user_data.email, max_length=255).strip().lower()

            # Validate email
            if not email or '@' not in email:
                raise ValidationError("Invalid email format", field="email")

            # Check email uniqueness
            result = await db.execute(
                select(User).where(User.email == email).where(User.id != user_id)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
            user.email = email

        if user_data.username is not None:
            # Sanitize username
            username = sanitize_text(user_data.username, max_length=100).strip()

            # Validate username
            if not username or len(username) < 3:
                raise ValidationError("Username must be at least 3 characters", field="username")

            # Check username uniqueness
            result = await db.execute(
                select(User).where(User.username == username).where(User.id != user_id)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            user.username = username

        if user_data.full_name is not None:
            user.full_name = sanitize_text(user_data.full_name, max_length=255).strip()

        if user_data.role is not None:
            user.role = user_data.role

        if user_data.is_active is not None:
            user.is_active = user_data.is_active

        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        log_info(
            f"User updated successfully: {user.id}",
            context="update_user",
            extra={"user_id": str(user.id), "admin_user_id": str(current_user.id)}
        )

        return UserResponse.model_validate(user)

    except (ValidationError, HTTPException):
        raise

    except SQLAlchemyError as e:
        log_error(
            e,
            context="update_user",
            user_id=str(current_user.id),
            extra={"target_user_id": str(user_id), "error_type": "database"}
        )
        raise DatabaseError(
            "Failed to update user due to database error",
            details={"error": str(e)}
        )

    except Exception as e:
        log_error(
            e,
            context="update_user",
            user_id=str(current_user.id),
            extra={"target_user_id": str(user_id)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user.

    **Requires**: Admin role

    **Warning**: This action cannot be undone.
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check same organization
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    await db.delete(user)
    await db.commit()

    return None
