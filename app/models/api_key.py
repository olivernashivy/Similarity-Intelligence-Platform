"""API Key model."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class APIKey(Base):
    """API Key model for authentication."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Key info
    name = Column(String(255), nullable=False)  # Human-readable name
    key_hash = Column(String(255), unique=True, nullable=False, index=True)  # Hashed API key
    key_prefix = Column(String(32), nullable=False)  # First few chars for identification (e.g., "sk_live_abc")

    # Permissions & limits
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration

    # Relationships
    organization = relationship("Organization", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.key_prefix}... for {self.organization_id}>"

    @property
    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired
