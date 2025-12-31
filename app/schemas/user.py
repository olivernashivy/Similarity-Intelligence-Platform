"""User management schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    """Create new user."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "role": "member"
            }
        }


class UserUpdate(BaseModel):
    """Update user information."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|member|viewer)$")
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response."""
    id: UUID
    organization_id: UUID
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_superuser: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """List of users."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
