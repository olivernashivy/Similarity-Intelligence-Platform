"""Authentication schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # seconds


class TokenData(BaseModel):
    """Data stored in JWT token."""
    user_id: UUID
    email: str
    organization_id: UUID
    role: str


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!"
            }
        }


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=100, description="Unique username")
    password: str = Field(..., min_length=8, description="Strong password")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    organization_name: str = Field(..., min_length=2, max_length=255, description="Organization name")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePassword123!",
                "full_name": "John Doe",
                "organization_name": "Acme Corp"
            }
        }


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: "UserResponse"


class UserResponse(BaseModel):
    """User information response."""
    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    role: str
    organization_id: UUID
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr
