"""Organization management schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class OrganizationCreate(BaseModel):
    """Create new organization."""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    tier: str = Field(default="free", pattern="^(free|starter|pro|enterprise)$")
    monthly_check_limit: int = Field(default=100, ge=0)
    allow_corpus_inclusion: bool = Field(default=False)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation",
                "email": "contact@acme.com",
                "tier": "pro",
                "monthly_check_limit": 1000
            }
        }


class OrganizationUpdate(BaseModel):
    """Update organization."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    tier: Optional[str] = Field(None, pattern="^(free|starter|pro|enterprise)$")
    monthly_check_limit: Optional[int] = Field(None, ge=0)
    allow_corpus_inclusion: Optional[bool] = None
    store_embeddings: Optional[bool] = None
    is_active: Optional[bool] = None


class OrganizationResponse(BaseModel):
    """Organization response."""
    id: UUID
    name: str
    email: str
    tier: str
    allow_corpus_inclusion: bool
    store_embeddings: bool
    monthly_check_limit: int
    current_month_checks: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationDetailResponse(OrganizationResponse):
    """Organization detail with stats."""
    user_count: int = 0
    api_key_count: int = 0
    total_checks: int = 0


class OrganizationListResponse(BaseModel):
    """List of organizations."""
    organizations: List[OrganizationResponse]
    total: int
    page: int
    page_size: int


class APIKeyCreate(BaseModel):
    """Create API key."""
    name: str = Field(..., min_length=2, max_length=255, description="Human-readable name for the API key")
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Optional expiration in days")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Production API Key",
                "rate_limit_per_minute": 100,
                "expires_in_days": 90
            }
        }


class APIKeyResponse(BaseModel):
    """API key response."""
    id: UUID
    name: str
    key_prefix: str
    api_key: Optional[str] = Field(None, description="Full API key (only shown on creation)")
    is_active: bool
    rate_limit_per_minute: int
    last_used_at: Optional[datetime]
    total_requests: int
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """List of API keys."""
    api_keys: List[APIKeyResponse]
    total: int
